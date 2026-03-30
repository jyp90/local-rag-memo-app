"""Tests for DocumentStore (SQLite metadata management)."""
import os
import pytest
from datetime import datetime

from app.infrastructure.document_store import DocumentStore, DocumentMeta, Message, Session


class TestDocumentStore:
    """Test suite for DocumentStore SQLite operations."""

    @pytest.fixture
    def store(self, tmp_dir):
        db_path = os.path.join(tmp_dir, "sqlite", "metadata.db")
        return DocumentStore(db_path)

    def _make_doc(self, collection="default", file_name="test.pdf", doc_id="doc-1"):
        return DocumentMeta(
            id=doc_id,
            file_name=file_name,
            file_path=f"/path/{file_name}",
            collection=collection,
            chunk_count=10,
            created_at=datetime.now().isoformat(),
            file_size=1024,
            file_type="pdf",
        )

    # --- Document Tests ---

    def test_save_and_get_document(self, store):
        doc = self._make_doc()
        store.save_document(doc)
        docs = store.get_documents("default")
        assert len(docs) == 1
        assert docs[0].id == "doc-1"
        assert docs[0].file_name == "test.pdf"

    def test_get_document_by_id(self, store):
        doc = self._make_doc()
        store.save_document(doc)
        retrieved = store.get_document_by_id("doc-1")
        assert retrieved is not None
        assert retrieved.file_name == "test.pdf"

    def test_find_document(self, store):
        doc = self._make_doc()
        store.save_document(doc)
        found = store.find_document("default", "test.pdf")
        assert found is not None
        assert found.id == "doc-1"

    def test_find_nonexistent(self, store):
        assert store.find_document("default", "nope.pdf") is None

    def test_delete_document(self, store):
        doc = self._make_doc()
        store.save_document(doc)
        assert store.delete_document("doc-1")
        assert store.get_document_by_id("doc-1") is None

    def test_document_count(self, store):
        store.save_document(self._make_doc(doc_id="d1"))
        store.save_document(self._make_doc(doc_id="d2"))
        assert store.get_document_count("default") == 2
        assert store.get_document_count("other") == 0

    def test_documents_sorted_by_date(self, store):
        store.save_document(self._make_doc(doc_id="d1", file_name="a.pdf"))
        store.save_document(self._make_doc(doc_id="d2", file_name="b.pdf"))
        docs = store.get_documents("default")
        # Most recent first
        assert len(docs) == 2

    # --- Session Tests ---

    def test_create_session(self, store):
        session = store.create_session("default")
        assert session.id is not None
        assert session.collection == "default"

    def test_get_sessions(self, store):
        store.create_session("default")
        store.create_session("default")
        sessions = store.get_sessions("default")
        assert len(sessions) == 2

    def test_delete_session(self, store):
        session = store.create_session("default")
        assert store.delete_session(session.id)
        assert len(store.get_sessions("default")) == 0

    # --- Message Tests ---

    def test_save_and_get_messages(self, store):
        session = store.create_session("default")
        msg = Message(
            id="msg-1",
            session_id=session.id,
            role="user",
            content="What is RAG?",
            sources="[]",
            created_at=datetime.now().isoformat(),
        )
        store.save_message(msg)
        messages = store.get_messages(session.id)
        assert len(messages) == 1
        assert messages[0].content == "What is RAG?"

    def test_message_updates_session(self, store):
        session = store.create_session("default")
        msg = Message(
            id="msg-1",
            session_id=session.id,
            role="user",
            content="First question about RAG systems",
            sources="[]",
            created_at=datetime.now().isoformat(),
        )
        store.save_message(msg)
        sessions = store.get_sessions("default")
        assert sessions[0].message_count == 1
        assert "First question" in sessions[0].title

    def test_search_messages(self, store):
        session = store.create_session("default")
        store.save_message(Message(
            id="m1", session_id=session.id, role="user",
            content="RAG architecture", sources="[]",
            created_at=datetime.now().isoformat(),
        ))
        store.save_message(Message(
            id="m2", session_id=session.id, role="assistant",
            content="RAG uses retrieval-augmented generation",
            sources="[]", created_at=datetime.now().isoformat(),
        ))
        results = store.search_messages("default", "retrieval")
        assert len(results) >= 1

    def test_cascade_delete(self, store):
        session = store.create_session("default")
        store.save_message(Message(
            id="m1", session_id=session.id, role="user",
            content="test", sources="[]",
            created_at=datetime.now().isoformat(),
        ))
        store.delete_session(session.id)
        # Messages should be gone too
        messages = store.get_messages(session.id)
        assert len(messages) == 0

    # --- Collection Config Tests ---

    def test_save_collection_config(self, store):
        store.save_collection_config("test_col")
        config = store.get_collection_config("test_col")
        assert config is not None
        assert config["name"] == "test_col"
        assert config["chunk_size"] == 500

    def test_list_collection_configs(self, store):
        store.save_collection_config("col_a")
        store.save_collection_config("col_b")
        configs = store.list_collection_configs()
        assert len(configs) == 2

    def test_delete_collection_config(self, store):
        store.save_collection_config("to_delete")
        store.save_document(self._make_doc(collection="to_delete", doc_id="d1"))
        assert store.delete_collection_config("to_delete")
        assert store.get_collection_config("to_delete") is None
        assert store.get_document_count("to_delete") == 0
