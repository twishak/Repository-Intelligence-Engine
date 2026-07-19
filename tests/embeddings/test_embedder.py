import math

import numpy as np
import pytest

from codebase_agent.embeddings import CodeEmbedder


def test_embed_empty_list_returns_empty_without_loading_model():
    embedder = CodeEmbedder()
    assert embedder.embed([]) == []
    assert embedder._model is None


class _FakeTokenizer:
    """One "token" per character, so token counts are predictable in tests."""

    def encode(self, text, add_special_tokens=True):
        return list(text)

    def decode(self, token_ids, skip_special_tokens=True):
        return "".join(token_ids)


class _FakeModel:
    def __init__(self, max_seq_length):
        self.max_seq_length = max_seq_length
        self.tokenizer = _FakeTokenizer()
        self.encode_calls: list[list[str]] = []

    def encode(self, texts, **kwargs):
        self.encode_calls.append(list(texts))
        # Each vector's first component is the text's length, so tests can
        # verify embed() maps results back to the right original text.
        return np.array([[float(len(t))] * 4 for t in texts])

    @property
    def encoded_texts(self) -> list[str]:
        """All texts passed to encode(), across every batch call, in call order."""
        return [text for call in self.encode_calls for text in call]


def _embedder_with_fake_model(max_seq_length: int) -> tuple[CodeEmbedder, _FakeModel]:
    embedder = CodeEmbedder()
    fake_model = _FakeModel(max_seq_length)
    embedder._model = fake_model
    return embedder, fake_model


def test_embed_truncates_oversized_text_before_encoding():
    embedder, fake_model = _embedder_with_fake_model(max_seq_length=10)
    oversized = "x" * 50

    embedder.embed([oversized])

    assert fake_model.encoded_texts == ["x" * 10]


def test_embed_truncates_to_configured_cap_even_when_model_allows_more():
    # Regression test: a single chunk near the model's native max_seq_length
    # (e.g. jina-code's 8192) can OOM a consumer GPU via quadratic attention
    # memory alone, independent of batch size. embedding_max_tokens caps
    # truncation below the model's native limit regardless of hardware.
    embedder, fake_model = _embedder_with_fake_model(max_seq_length=10_000)
    embedder._max_tokens = 10
    oversized = "x" * 50

    embedder.embed([oversized])

    assert fake_model.encoded_texts == ["x" * 10]


def test_embed_leaves_normal_sized_text_unchanged():
    embedder, fake_model = _embedder_with_fake_model(max_seq_length=10)
    normal = "x" * 5

    embedder.embed([normal])

    assert fake_model.encoded_texts == [normal]


def test_embed_warns_when_truncating(caplog):
    embedder, _ = _embedder_with_fake_model(max_seq_length=10)

    with caplog.at_level("WARNING"):
        embedder.embed(["x" * 50])

    assert any(
        "exceeded the embedding model's max length" in record.message
        for record in caplog.records
    )


def test_embed_does_not_warn_for_normal_sized_text(caplog):
    embedder, _ = _embedder_with_fake_model(max_seq_length=10)

    with caplog.at_level("WARNING"):
        embedder.embed(["x" * 5])

    assert caplog.records == []


def test_embed_emits_one_aggregate_warning_not_one_per_truncated_chunk(caplog):
    # Regression test: a repo with many oversized chunks used to log one
    # multi-line WARNING per chunk, which drowned out the batch progress bar
    # and any other real signal. There should be exactly one summary WARNING
    # regardless of how many chunks were truncated.
    embedder, _ = _embedder_with_fake_model(max_seq_length=10)

    with caplog.at_level("WARNING"):
        embedder.embed(["x" * 50, "y" * 80, "z" * 30])

    warnings = [r for r in caplog.records if r.levelname == "WARNING"]
    assert len(warnings) == 1
    assert "3 of 3 chunks" in warnings[0].message
    assert "largest was 80 tokens" in warnings[0].message


def test_embed_logs_per_chunk_truncation_detail_at_info_not_warning(caplog):
    embedder, _ = _embedder_with_fake_model(max_seq_length=10)

    with caplog.at_level("INFO"):
        embedder.embed(["x" * 50])

    info_records = [r for r in caplog.records if r.levelname == "INFO"]
    assert any("exceeds embedding model max" in r.message for r in info_records)


def test_embed_groups_batches_by_token_length_not_original_order():
    embedder, fake_model = _embedder_with_fake_model(max_seq_length=1000)
    embedder._batch_size = 2
    # Original order is deliberately not sorted by length.
    texts = ["a" * 50, "b" * 5, "c" * 40, "d" * 3]

    embedder.embed(texts)

    assert fake_model.encode_calls == [
        ["d" * 3, "b" * 5],
        ["c" * 40, "a" * 50],
    ]


def test_embed_isolates_a_single_long_chunk_into_its_own_batch():
    # Regression test: previously, wherever a long chunk fell in the original
    # order, every other chunk in the same fixed-size batch got padded up to
    # its length. With enough short chunks to fill full batches of their own,
    # length-based bucketing should isolate the one outlier into a batch with
    # no unrelated short chunks in it at all.
    embedder, fake_model = _embedder_with_fake_model(max_seq_length=10_000)
    embedder._batch_size = 4
    embedder._max_tokens = 10_000  # this test is about batching, not the truncation cap
    shorts = [f"short{i}" for i in range(8)]  # 8 equal-length chunks -> 2 full batches
    long_chunk = "x" * 5000
    texts = [
        *shorts[:3],
        long_chunk,
        *shorts[3:],
    ]  # interleaved, not appended at the end

    embedder.embed(texts)

    calls_with_long_chunk = [
        call for call in fake_model.encode_calls if long_chunk in call
    ]
    assert calls_with_long_chunk == [[long_chunk]]


def test_embed_shrinks_batch_size_for_many_long_chunks_to_respect_token_budget():
    # Regression test: a real ingestion OOM'd even after individual chunks
    # were capped at embedding_max_tokens, because up to embedding_batch_size
    # chunks that were each under the cap still landed in the same batch -
    # and GPU attention memory scales with batch_size x seq_len^2, not just
    # seq_len. The token budget (count x longest item) must shrink the batch
    # itself as the chunks going into it get longer.
    embedder, fake_model = _embedder_with_fake_model(max_seq_length=10_000)
    embedder._batch_size = 32
    embedder._max_tokens_per_batch = 2000
    texts = ["x" * 1000] * 4  # 4 chunks x 1000 tokens: budget allows 2 per batch

    embedder.embed(texts)

    assert [len(call) for call in fake_model.encode_calls] == [2, 2]


def test_embed_preserves_original_order_in_results():
    embedder, _ = _embedder_with_fake_model(max_seq_length=1000)
    embedder._batch_size = 2
    texts = ["a" * 50, "b" * 5, "c" * 40, "d" * 3]

    vectors = embedder.embed(texts)

    assert [v[0] for v in vectors] == [50.0, 5.0, 40.0, 3.0]


def test_embed_tokenizes_each_text_only_once():
    embedder, fake_model = _embedder_with_fake_model(max_seq_length=1000)
    calls = []
    original_encode = fake_model.tokenizer.encode
    fake_model.tokenizer.encode = lambda text, **kw: (
        calls.append(text) or original_encode(text, **kw)
    )

    embedder.embed(["a", "bb", "ccc"])

    assert calls == ["a", "bb", "ccc"]


@pytest.fixture(scope="module")
def embedder():
    return CodeEmbedder()


@pytest.mark.integration
def test_embed_produces_normalized_vectors_of_expected_dimension(embedder):
    vectors = embedder.embed(
        [
            "# file: sample.py\n# list_users\ndef list_users():\n    return db.query(User).all()",
            "# file: sample.py\n# delete_user\ndef delete_user(user_id):\n"
            "    db.query(User).filter_by(id=user_id).delete()",
        ]
    )

    assert len(vectors) == 2
    assert len(vectors[0]) == 768
    for vector in vectors:
        norm = math.sqrt(sum(x * x for x in vector))
        assert abs(norm - 1.0) < 1e-3


@pytest.mark.integration
def test_similar_code_embeds_closer_than_unrelated_code(embedder):
    query, similar, unrelated = embedder.embed(
        [
            "# file: sample.py\n# get_user\ndef get_user(user_id):\n    return db.query(User).get(user_id)",
            "# file: sample.py\n# fetch_user\ndef fetch_user(uid):\n"
            "    return db.session.query(User).filter_by(id=uid).first()",
            "# file: sample.py\n# calculate_tax\ndef calculate_tax(amount):\n    return amount * 0.2",
        ]
    )

    def cosine(a, b):
        return sum(x * y for x, y in zip(a, b, strict=True))  # already unit-normalized

    assert cosine(query, similar) > cosine(query, unrelated)
