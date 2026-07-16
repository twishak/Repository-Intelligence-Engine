import math

import pytest

from codebase_agent.embeddings import CodeEmbedder


def test_embed_empty_list_returns_empty_without_loading_model():
    embedder = CodeEmbedder()
    assert embedder.embed([]) == []
    assert embedder._model is None


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
