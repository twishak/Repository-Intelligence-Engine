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
        self.encoded_texts: list[str] | None = None

    def encode(self, texts, **kwargs):
        self.encoded_texts = list(texts)
        return np.zeros((len(texts), 4))


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
        "exceeds embedding model max" in record.message for record in caplog.records
    )


def test_embed_does_not_warn_for_normal_sized_text(caplog):
    embedder, _ = _embedder_with_fake_model(max_seq_length=10)

    with caplog.at_level("WARNING"):
        embedder.embed(["x" * 5])

    assert caplog.records == []


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
