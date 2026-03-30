"""Tests for VectorStore."""
import os
import pytest

from app.infrastructure.vector_store import VectorStore, SearchResult


class TestVectorStore:
    """Test suite for VectorStore (ChromaDB wrapper)."""

    @pytest.fixture
    def store(self, tmp_dir):
        return VectorStore(os.path.join(tmp_dir, "chroma"))

    def test_create_collection(self, store):
        collection = store.get_or_create_collection("test_collection")
        assert collection is not None
        assert collection.count() == 0

    def test_list_collections(self, store):
        store.get_or_create_collection("col_a")
        store.get_or_create_collection("col_b")
        names = store.list_collections()
        assert "col_a" in names
        assert "col_b" in names

    def test_upsert_and_count(self, store):
        dim = 384  # MiniLM dimension
        store.upsert(
            collection_name="test",
            ids=["c1", "c2", "c3"],
            documents=["doc one", "doc two", "doc three"],
            embeddings=[[0.1] * dim, [0.2] * dim, [0.3] * dim],
            metadatas=[
                {"doc_id": "d1", "file_name": "a.txt"},
                {"doc_id": "d1", "file_name": "a.txt"},
                {"doc_id": "d2", "file_name": "b.txt"},
            ],
        )
        assert store.collection_count("test") == 3

    def test_similarity_search(self, store):
        dim = 384
        store.upsert(
            collection_name="search_test",
            ids=["s1", "s2", "s3"],
            documents=["apple fruit", "banana fruit", "car vehicle"],
            embeddings=[
                [1.0] + [0.0] * (dim - 1),
                [0.9] + [0.1] * (dim - 1),
                [0.0] + [1.0] * (dim - 1),
            ],
        )

        results = store.similarity_search(
            collection_name="search_test",
            query_embedding=[1.0] + [0.0] * (dim - 1),
            top_k=2,
        )
        assert len(results) == 2
        assert isinstance(results[0], SearchResult)
        # First result should be most similar
        assert results[0].chunk_id == "s1"

    def test_search_empty_collection(self, store):
        results = store.similarity_search(
            collection_name="empty_col",
            query_embedding=[0.1] * 384,
            top_k=5,
        )
        assert results == []

    def test_delete_collection(self, store):
        store.get_or_create_collection("to_delete")
        assert "to_delete" in store.list_collections()
        store.delete_collection("to_delete")
        assert "to_delete" not in store.list_collections()

    def test_delete_documents_by_doc_id(self, store):
        dim = 384
        store.upsert(
            collection_name="del_test",
            ids=["c1", "c2", "c3"],
            documents=["a", "b", "c"],
            embeddings=[[0.1] * dim, [0.2] * dim, [0.3] * dim],
            metadatas=[
                {"doc_id": "d1"},
                {"doc_id": "d1"},
                {"doc_id": "d2"},
            ],
        )
        assert store.collection_count("del_test") == 3

        store.delete_documents("del_test", "d1")
        assert store.collection_count("del_test") == 1

    def test_sanitize_name(self):
        assert VectorStore._sanitize_name("test") == "test"
        assert len(VectorStore._sanitize_name("ab")) >= 3  # Minimum length
        assert VectorStore._sanitize_name("123") == "_123"  # Starts with number
        # Special chars replaced
        sanitized = VectorStore._sanitize_name("my collection!")
        assert "!" not in sanitized

    def test_upsert_large_batch(self, store):
        """Test batch upsert exceeding ChromaDB batch limit."""
        dim = 10
        n = 600  # > 500 batch limit
        store.upsert(
            collection_name="large_batch",
            ids=[f"id_{i}" for i in range(n)],
            documents=[f"doc {i}" for i in range(n)],
            embeddings=[[float(i) / n] * dim for i in range(n)],
        )
        assert store.collection_count("large_batch") == n
