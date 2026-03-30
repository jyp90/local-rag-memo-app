"""DocumentStore - SQLite metadata and conversation history management.

Stores document metadata, chunk info, sessions, and messages.
Database: ~/.local-rag-memo/sqlite/metadata.db
"""
import json
import logging
import os
import sqlite3
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class DocumentMeta:
    """Document metadata stored in SQLite."""
    id: str
    file_name: str
    file_path: str
    collection: str
    chunk_count: int
    created_at: str  # ISO format
    file_size: int
    file_type: str  # "pdf" | "md" | "txt"


@dataclass
class Message:
    """Chat message."""
    id: str
    session_id: str
    role: str  # "user" | "assistant"
    content: str
    sources: str  # JSON-serialized list of source references
    created_at: str  # ISO format


@dataclass
class Session:
    """Chat session metadata."""
    id: str
    collection: str
    title: str  # First question preview
    created_at: str
    updated_at: str
    message_count: int = 0


class DocumentStore:
    """SQLite-based document metadata and conversation manager."""

    def __init__(self, db_path: str):
        self._db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def _init_db(self):
        """Create tables if they don't exist."""
        conn = self._get_conn()
        try:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS documents (
                    id TEXT PRIMARY KEY,
                    file_name TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    collection TEXT NOT NULL,
                    chunk_count INTEGER DEFAULT 0,
                    created_at TEXT NOT NULL,
                    file_size INTEGER DEFAULT 0,
                    file_type TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_documents_collection
                    ON documents(collection);

                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY,
                    collection TEXT NOT NULL,
                    title TEXT DEFAULT '',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    message_count INTEGER DEFAULT 0
                );

                CREATE INDEX IF NOT EXISTS idx_sessions_collection
                    ON sessions(collection);

                CREATE TABLE IF NOT EXISTS messages (
                    id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    sources TEXT DEFAULT '[]',
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_messages_session
                    ON messages(session_id);

                CREATE TABLE IF NOT EXISTS collections (
                    name TEXT PRIMARY KEY,
                    embedding_model TEXT DEFAULT 'paraphrase-multilingual-MiniLM-L12-v2',
                    chunk_size INTEGER DEFAULT 500,
                    chunk_overlap INTEGER DEFAULT 50,
                    top_k INTEGER DEFAULT 5,
                    llm_backend TEXT DEFAULT 'ollama',
                    llm_model TEXT DEFAULT 'gemma3:4b',
                    created_at TEXT NOT NULL
                );
            """)
            conn.commit()
        finally:
            conn.close()

    # --- Document CRUD ---

    def save_document(self, doc: DocumentMeta) -> None:
        """Insert or replace document metadata."""
        conn = self._get_conn()
        try:
            conn.execute(
                """INSERT OR REPLACE INTO documents
                   (id, file_name, file_path, collection, chunk_count, created_at, file_size, file_type)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (doc.id, doc.file_name, doc.file_path, doc.collection,
                 doc.chunk_count, doc.created_at, doc.file_size, doc.file_type),
            )
            conn.commit()
        finally:
            conn.close()

    def get_documents(self, collection: str) -> list[DocumentMeta]:
        """Get all documents in a collection, sorted by created_at DESC."""
        conn = self._get_conn()
        try:
            rows = conn.execute(
                "SELECT * FROM documents WHERE collection = ? ORDER BY created_at DESC",
                (collection,),
            ).fetchall()
            return [DocumentMeta(**dict(row)) for row in rows]
        finally:
            conn.close()

    def get_document_by_id(self, doc_id: str) -> Optional[DocumentMeta]:
        """Get a single document by ID."""
        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT * FROM documents WHERE id = ?", (doc_id,)
            ).fetchone()
            return DocumentMeta(**dict(row)) if row else None
        finally:
            conn.close()

    def find_document(self, collection: str, file_name: str) -> Optional[DocumentMeta]:
        """Find document by collection and file_name (duplicate check)."""
        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT * FROM documents WHERE collection = ? AND file_name = ?",
                (collection, file_name),
            ).fetchone()
            return DocumentMeta(**dict(row)) if row else None
        finally:
            conn.close()

    def delete_document(self, doc_id: str) -> bool:
        """Delete a document by ID."""
        conn = self._get_conn()
        try:
            conn.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to delete document {doc_id}: {e}")
            return False
        finally:
            conn.close()

    def get_document_count(self, collection: str) -> int:
        """Count documents in a collection."""
        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT COUNT(*) as cnt FROM documents WHERE collection = ?",
                (collection,),
            ).fetchone()
            return row["cnt"] if row else 0
        finally:
            conn.close()

    # --- Session CRUD ---

    def create_session(self, collection: str, session_id: str | None = None) -> Session:
        """Create a new chat session."""
        now = datetime.now().isoformat()
        session = Session(
            id=session_id or str(uuid.uuid4()),
            collection=collection,
            title="",
            created_at=now,
            updated_at=now,
            message_count=0,
        )
        conn = self._get_conn()
        try:
            conn.execute(
                """INSERT INTO sessions (id, collection, title, created_at, updated_at, message_count)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (session.id, session.collection, session.title,
                 session.created_at, session.updated_at, session.message_count),
            )
            conn.commit()
        finally:
            conn.close()
        return session

    def get_sessions(self, collection: str) -> list[Session]:
        """Get sessions for a collection, sorted by updated_at DESC."""
        conn = self._get_conn()
        try:
            rows = conn.execute(
                "SELECT * FROM sessions WHERE collection = ? ORDER BY updated_at DESC",
                (collection,),
            ).fetchall()
            return [Session(**dict(row)) for row in rows]
        finally:
            conn.close()

    def delete_session(self, session_id: str) -> bool:
        """Delete a session and its messages (CASCADE)."""
        conn = self._get_conn()
        try:
            conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to delete session {session_id}: {e}")
            return False
        finally:
            conn.close()

    # --- Message CRUD ---

    def save_message(self, message: Message) -> None:
        """Save a message and update session."""
        conn = self._get_conn()
        try:
            conn.execute(
                """INSERT INTO messages (id, session_id, role, content, sources, created_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (message.id, message.session_id, message.role,
                 message.content, message.sources, message.created_at),
            )
            # Update session title (first user message) and updated_at
            conn.execute(
                """UPDATE sessions SET
                   updated_at = ?,
                   message_count = message_count + 1,
                   title = CASE WHEN title = '' AND ? = 'user'
                           THEN substr(?, 1, 80) ELSE title END
                   WHERE id = ?""",
                (message.created_at, message.role, message.content, message.session_id),
            )
            conn.commit()
        finally:
            conn.close()

    def get_messages(self, session_id: str) -> list[Message]:
        """Get all messages in a session, sorted by created_at ASC."""
        conn = self._get_conn()
        try:
            rows = conn.execute(
                "SELECT * FROM messages WHERE session_id = ? ORDER BY created_at ASC",
                (session_id,),
            ).fetchall()
            return [Message(**dict(row)) for row in rows]
        finally:
            conn.close()

    def search_messages(self, collection: str, keyword: str) -> list[Message]:
        """Search messages by keyword across sessions in a collection."""
        conn = self._get_conn()
        try:
            rows = conn.execute(
                """SELECT m.* FROM messages m
                   JOIN sessions s ON m.session_id = s.id
                   WHERE s.collection = ?
                   AND (m.content LIKE ? OR m.content LIKE ?)
                   ORDER BY m.created_at DESC
                   LIMIT 50""",
                (collection, f"%{keyword}%", f"%{keyword}%"),
            ).fetchall()
            return [Message(**dict(row)) for row in rows]
        finally:
            conn.close()

    # --- Collection Config ---

    def save_collection_config(
        self,
        name: str,
        embedding_model: str = "paraphrase-multilingual-MiniLM-L12-v2",
        chunk_size: int = 500,
        chunk_overlap: int = 50,
        top_k: int = 5,
        llm_backend: str = "ollama",
        llm_model: str = "gemma3:4b",
    ) -> None:
        """Save or update collection configuration."""
        conn = self._get_conn()
        try:
            conn.execute(
                """INSERT OR REPLACE INTO collections
                   (name, embedding_model, chunk_size, chunk_overlap, top_k,
                    llm_backend, llm_model, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (name, embedding_model, chunk_size, chunk_overlap, top_k,
                 llm_backend, llm_model, datetime.now().isoformat()),
            )
            conn.commit()
        finally:
            conn.close()

    def get_collection_config(self, name: str) -> dict | None:
        """Get collection configuration as dict."""
        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT * FROM collections WHERE name = ?", (name,)
            ).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def list_collection_configs(self) -> list[dict]:
        """List all collection configs."""
        conn = self._get_conn()
        try:
            rows = conn.execute(
                "SELECT * FROM collections ORDER BY created_at"
            ).fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()

    def delete_collection_config(self, name: str) -> bool:
        """Delete collection config."""
        conn = self._get_conn()
        try:
            conn.execute("DELETE FROM collections WHERE name = ?", (name,))
            # Also delete related documents and sessions
            conn.execute("DELETE FROM documents WHERE collection = ?", (name,))
            # Get session IDs first for message cascade
            sessions = conn.execute(
                "SELECT id FROM sessions WHERE collection = ?", (name,)
            ).fetchall()
            for s in sessions:
                conn.execute("DELETE FROM messages WHERE session_id = ?", (s["id"],))
            conn.execute("DELETE FROM sessions WHERE collection = ?", (name,))
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to delete collection config '{name}': {e}")
            return False
        finally:
            conn.close()
