"""ConversationManager - Chat session and message management.

Handles session creation, message saving, and history retrieval.
Uses DocumentStore for persistence.
"""
import json
import logging
import uuid
from datetime import datetime

from app.infrastructure.document_store import DocumentStore, Message, Session

logger = logging.getLogger(__name__)


class ConversationManager:
    """Manages chat sessions and conversation history."""

    def __init__(self, document_store: DocumentStore):
        self._store = document_store
        self._current_session: Session | None = None

    @property
    def current_session(self) -> Session | None:
        return self._current_session

    def new_session(self, collection: str) -> Session:
        """Create a new chat session.

        Args:
            collection: Collection name for this session.

        Returns:
            New Session object.
        """
        session = self._store.create_session(collection=collection)
        self._current_session = session
        logger.info(f"New session created: {session.id} for collection '{collection}'")
        return session

    def set_current_session(self, session: Session):
        """Set the active session."""
        self._current_session = session

    def save_user_message(
        self,
        content: str,
        session_id: str | None = None,
    ) -> Message:
        """Save a user message.

        Args:
            content: Message text.
            session_id: Session to save to (uses current if None).

        Returns:
            Saved Message object.
        """
        sid = session_id or (self._current_session.id if self._current_session else None)
        if not sid:
            raise ValueError("No active session. Create one first.")

        message = Message(
            id=str(uuid.uuid4()),
            session_id=sid,
            role="user",
            content=content,
            sources="[]",
            created_at=datetime.now().isoformat(),
        )
        self._store.save_message(message)
        return message

    def save_assistant_message(
        self,
        content: str,
        sources: list[dict] | None = None,
        session_id: str | None = None,
    ) -> Message:
        """Save an assistant (AI) message.

        Args:
            content: Full answer text.
            sources: Source reference dicts.
            session_id: Session to save to (uses current if None).

        Returns:
            Saved Message object.
        """
        sid = session_id or (self._current_session.id if self._current_session else None)
        if not sid:
            raise ValueError("No active session. Create one first.")

        message = Message(
            id=str(uuid.uuid4()),
            session_id=sid,
            role="assistant",
            content=content,
            sources=json.dumps(sources or [], ensure_ascii=False),
            created_at=datetime.now().isoformat(),
        )
        self._store.save_message(message)
        return message

    def get_history(self, session_id: str | None = None) -> list[dict]:
        """Get conversation history as simple dicts.

        Args:
            session_id: Session to retrieve (uses current if None).

        Returns:
            List of {"role": "user"|"assistant", "content": "..."} dicts.
        """
        sid = session_id or (self._current_session.id if self._current_session else None)
        if not sid:
            return []

        messages = self._store.get_messages(sid)
        return [
            {"role": msg.role, "content": msg.content}
            for msg in messages
        ]

    def get_sessions(self, collection: str) -> list[Session]:
        """Get all sessions for a collection."""
        return self._store.get_sessions(collection)

    def delete_session(self, session_id: str) -> bool:
        """Delete a session and its messages."""
        success = self._store.delete_session(session_id)
        if success and self._current_session and self._current_session.id == session_id:
            self._current_session = None
        return success

    def search_history(self, collection: str, keyword: str) -> list[Message]:
        """Search messages in a collection by keyword."""
        return self._store.search_messages(collection, keyword)
