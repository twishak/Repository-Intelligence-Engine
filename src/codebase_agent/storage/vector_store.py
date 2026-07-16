import re
from pathlib import Path

import chromadb

from codebase_agent.chunking.models import CodeChunk
from codebase_agent.config import settings
from codebase_agent.storage.models import RetrievedChunk


class CodeVectorStore:
    def __init__(self, persist_dir: Path | None = None) -> None:
        self._client = chromadb.PersistentClient(
            path=str(persist_dir or settings.chroma_dir)
        )

    def rebuild_repo_collection(
        self, repo_name: str, chunks: list[CodeChunk], vectors: list[list[float]]
    ) -> None:
        """Replace the repo's collection wholesale rather than diffing old vs. new chunk ids."""
        name = _collection_name(repo_name)
        try:
            self._client.delete_collection(name)
        except (ValueError, chromadb.errors.NotFoundError):
            pass

        collection = self._client.create_collection(
            name, metadata={"hnsw:space": "cosine"}
        )
        if not chunks:
            return

        collection.upsert(
            ids=[c.id for c in chunks],
            embeddings=vectors,
            documents=[c.content for c in chunks],
            metadatas=[_to_metadata(c) for c in chunks],
        )

    def query(
        self, repo_name: str, query_vector: list[float], n_results: int = 8
    ) -> list[RetrievedChunk]:
        collection = self._client.get_collection(_collection_name(repo_name))
        result = collection.query(query_embeddings=[query_vector], n_results=n_results)
        return [_to_retrieved_chunk(result, i) for i in range(len(result["ids"][0]))]

    def get_by_qualified_name(
        self, repo_name: str, qualified_name: str, n_results: int = 8
    ) -> list[RetrievedChunk]:
        """Exact metadata match - no embeddings or similarity ranking involved."""
        collection = self._client.get_collection(_collection_name(repo_name))
        result = collection.get(
            where={"qualified_name": {"$eq": qualified_name}},
            limit=n_results,
            include=["metadatas", "documents"],
        )
        return [
            _to_retrieved_chunk_from_get(result, i) for i in range(len(result["ids"]))
        ]

    def search_document_text(
        self, repo_name: str, substring: str, n_results: int = 8
    ) -> list[RetrievedChunk]:
        """Lexical containment search over chunk content, not similarity-ranked."""
        collection = self._client.get_collection(_collection_name(repo_name))
        result = collection.get(
            where_document={"$contains": substring},
            limit=n_results,
            include=["metadatas", "documents"],
        )
        return [
            _to_retrieved_chunk_from_get(result, i) for i in range(len(result["ids"]))
        ]

    def has_collection(self, repo_name: str) -> bool:
        try:
            self._client.get_collection(_collection_name(repo_name))
            return True
        except (ValueError, chromadb.errors.NotFoundError):
            return False

    def list_repos(self) -> list[str]:
        """Names of ingested repo collections (slugified - see `_collection_name`)."""
        return sorted(c.name for c in self._client.list_collections())


def _to_metadata(chunk: CodeChunk) -> dict:
    return {
        "file_path": chunk.file_path,
        "chunk_type": chunk.chunk_type,
        "qualified_name": chunk.qualified_name,
        "start_line": chunk.start_line,
        "end_line": chunk.end_line,
        "docstring": chunk.docstring or "",
    }


def _to_retrieved_chunk(result: dict, index: int) -> RetrievedChunk:
    metadata = result["metadatas"][0][index]
    return RetrievedChunk(
        id=result["ids"][0][index],
        file_path=metadata["file_path"],
        chunk_type=metadata["chunk_type"],
        qualified_name=metadata["qualified_name"],
        start_line=metadata["start_line"],
        end_line=metadata["end_line"],
        content=result["documents"][0][index],
        docstring=metadata["docstring"] or None,
        distance=result["distances"][0][index],
    )


def _to_retrieved_chunk_from_get(result: dict, index: int) -> RetrievedChunk:
    metadata = result["metadatas"][index]
    return RetrievedChunk(
        id=result["ids"][index],
        file_path=metadata["file_path"],
        chunk_type=metadata["chunk_type"],
        qualified_name=metadata["qualified_name"],
        start_line=metadata["start_line"],
        end_line=metadata["end_line"],
        content=result["documents"][index],
        docstring=metadata["docstring"] or None,
        distance=None,
    )


def _collection_name(repo_name: str) -> str:
    # Chroma collection names must be 3-63 chars, alphanumeric/underscore/hyphen,
    # and start/end with an alphanumeric character.
    slug = re.sub(r"[^a-z0-9_-]", "-", repo_name.lower())
    slug = slug.strip("-_")[:63]
    if len(slug) < 3:
        slug = f"repo-{slug}"
    return slug
