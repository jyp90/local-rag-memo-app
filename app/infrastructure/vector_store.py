"""VectorStore - ChromaDB local vector database wrapper.

Manages collections, upsert, similarity search, and deletion.
Persists to ~/.local-rag-memo/chroma/
"""
import logging
from dataclasses import dataclass

import chromadb
from chromadb.config import Settings

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """Result from similarity search."""
    chunk_id: str
    text: str
    score: float
    metadata: dict


class VectorStore:
    """ChromaDB local vector DB wrapper."""

    def __init__(self, persist_dir: str):
        self._persist_dir = persist_dir
        self._client = chromadb.PersistentClient(
            path=persist_dir,
            settings=Settings(anonymized_telemetry=False),
        )

    def get_or_create_collection(self, name: str) -> chromadb.Collection:
        """Get an existing collection or create a new one."""
        # ChromaDB collection names must match [a-zA-Z0-9_-]
        safe_name = self._sanitize_name(name)
        return self._client.get_or_create_collection(
            name=safe_name,
            metadata={"hnsw:space": "cosine"},
        )

    def upsert(
        self,
        collection_name: str,
        ids: list[str],
        documents: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict] | None = None,
    ) -> None:
        """Upsert chunks into a collection.

        Args:
            collection_name: Target collection name.
            ids: Unique IDs for each chunk.
            documents: Chunk text contents.
            embeddings: Pre-computed embedding vectors.
            metadatas: Optional metadata dicts per chunk.
        """
        collection = self.get_or_create_collection(collection_name)
        # ChromaDB has a batch limit; process in batches of 500
        batch_size = 500
        for i in range(0, len(ids), batch_size):
            batch_ids = ids[i : i + batch_size]
            batch_docs = documents[i : i + batch_size]
            batch_embs = embeddings[i : i + batch_size]
            batch_meta = metadatas[i : i + batch_size] if metadatas else None

            collection.upsert(
                ids=batch_ids,
                documents=batch_docs,
                embeddings=batch_embs,
                metadatas=batch_meta,
            )

    def similarity_search(
        self,
        collection_name: str,
        query_embedding: list[float],
        top_k: int = 5,
    ) -> list[SearchResult]:
        """Search for similar chunks in a collection.

        Args:
            collection_name: Collection to search.
            query_embedding: Query vector.
            top_k: Number of results to return.

        Returns:
            List of SearchResult sorted by relevance (highest first).
        """
        try:
            collection = self.get_or_create_collection(collection_name)

            if collection.count() == 0:
                return []

            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=min(top_k, collection.count()),
                include=["documents", "metadatas", "distances"],
            )

            search_results = []
            if results and results["ids"] and results["ids"][0]:
                for i, chunk_id in enumerate(results["ids"][0]):
                    # ChromaDB returns cosine distance; convert to similarity score
                    distance = results["distances"][0][i] if results["distances"] else 0.0
                    score = 1.0 - distance  # cosine similarity = 1 - cosine distance

                    search_results.append(SearchResult(
                        chunk_id=chunk_id,
                        text=results["documents"][0][i] if results["documents"] else "",
                        score=score,
                        metadata=results["metadatas"][0][i] if results["metadatas"] else {},
                    ))

            return search_results

        except Exception as e:
            logger.error(f"Similarity search error: {e}")
            return []

    def delete_collection(self, name: str) -> bool:
        """Delete an entire collection."""
        try:
            safe_name = self._sanitize_name(name)
            self._client.delete_collection(name=safe_name)
            return True
        except Exception as e:
            logger.error(f"Failed to delete collection '{name}': {e}")
            return False

    def delete_documents(self, collection_name: str, doc_id: str) -> bool:
        """Delete all chunks belonging to a document from a collection."""
        try:
            collection = self.get_or_create_collection(collection_name)
            # Get all chunk IDs with this doc_id
            results = collection.get(
                where={"doc_id": doc_id},
                include=[],
            )
            if results["ids"]:
                collection.delete(ids=results["ids"])
            return True
        except Exception as e:
            logger.error(f"Failed to delete document chunks: {e}")
            return False

    def list_collections(self) -> list[str]:
        """List all collection names."""
        try:
            collections = self._client.list_collections()
            return [c.name for c in collections]
        except Exception as e:
            logger.error(f"Failed to list collections: {e}")
            return []

    def collection_count(self, collection_name: str) -> int:
        """Get the number of items in a collection."""
        try:
            collection = self.get_or_create_collection(collection_name)
            return collection.count()
        except Exception:
            return 0

    @staticmethod
    def _sanitize_name(name: str) -> str:
        """Sanitize collection name for ChromaDB compatibility."""
        import re
        sanitized = re.sub(r"[^a-zA-Z0-9_-]", "_", name)
        # Must start with letter or underscore
        if sanitized and not sanitized[0].isalpha() and sanitized[0] != "_":
            sanitized = "_" + sanitized
        # Minimum 3 characters
        while len(sanitized) < 3:
            sanitized += "_"
        # Maximum 63 characters
        return sanitized[:63]
