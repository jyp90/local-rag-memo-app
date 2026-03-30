"""Tests for ConversationManager."""
import os
import pytest

from app.domain.conversation_manager import ConversationManager
from app.infrastructure.document_store import DocumentStore


class TestConversationManager:
    """Test suite for ConversationManager."""

    @pytest.fixture
    def manager(self, tmp_dir):
        db_path = os.path.join(tmp_dir, "sqlite", "metadata.db")
        store = DocumentStore(db_path)
        return ConversationManager(store)

    def test_new_session(self, manager):
        session = manager.new_session("default")
        assert session is not None
        assert session.collection == "default"
        assert manager.current_session == session

    def test_save_user_message(self, manager):
        manager.new_session("default")
        msg = manager.save_user_message("What is RAG?")
        assert msg.role == "user"
        assert msg.content == "What is RAG?"

    def test_save_assistant_message(self, manager):
        manager.new_session("default")
        msg = manager.save_assistant_message(
            content="RAG is Retrieval-Augmented Generation.",
            sources=[{"file_name": "test.pdf", "page_num": 1}],
        )
        assert msg.role == "assistant"

    def test_get_history(self, manager):
        session = manager.new_session("default")
        manager.save_user_message("Q1")
        manager.save_assistant_message("A1")
        manager.save_user_message("Q2")

        history = manager.get_history()
        assert len(history) == 3
        assert history[0]["role"] == "user"
        assert history[0]["content"] == "Q1"
        assert history[1]["role"] == "assistant"

    def test_no_session_raises(self, manager):
        with pytest.raises(ValueError, match="No active session"):
            manager.save_user_message("test")

    def test_get_sessions(self, manager):
        manager.new_session("col1")
        manager.new_session("col1")
        sessions = manager.get_sessions("col1")
        assert len(sessions) == 2

    def test_delete_session(self, manager):
        session = manager.new_session("default")
        manager.save_user_message("test")
        assert manager.delete_session(session.id)
        assert manager.current_session is None

    def test_set_current_session(self, manager):
        s1 = manager.new_session("default")
        s2 = manager.new_session("default")
        manager.set_current_session(s1)
        assert manager.current_session == s1
