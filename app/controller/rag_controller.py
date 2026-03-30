"""RagController - Central application controller.

Orchestrates all services and provides a unified API for the UI layer.
Manages lifecycle of services, workers, and configuration.
"""
import logging
import os

from app.infrastructure.config_store import ConfigStore, AppConfig
from app.infrastructure.vector_store import VectorStore
from app.infrastructure.document_store import DocumentStore
from app.infrastructure.llm_client import LlmClient
from app.infrastructure.ollama_client import OllamaClient
from app.infrastructure.claude_client import ClaudeClient
from app.domain.document_processor import DocumentProcessor
from app.domain.chunking_service import ChunkingService
from app.domain.embedding_service import EmbeddingService
from app.domain.query_engine import QueryEngine
from app.domain.conversation_manager import ConversationManager
from app.controller.indexing_worker import IndexingWorker
from app.controller.query_worker import QueryWorker

logger = logging.getLogger(__name__)


class RagController:
    """Central controller orchestrating all RAG services.

    Provides a clean API for the UI layer to:
    - Index documents
    - Query with RAG
    - Manage collections
    - Switch LLM backends
    - Manage settings
    """

    def __init__(self, config_store: ConfigStore | None = None):
        # Configuration
        self._config_store = config_store or ConfigStore()
        self._config = self._config_store.load()

        # Infrastructure
        self._vector_store = VectorStore(self._config.chroma_dir)
        self._document_store = DocumentStore(
            os.path.join(self._config.sqlite_dir, "metadata.db")
        )

        # LLM clients
        self._ollama_client = OllamaClient(
            host=self._config.ollama_host,
            model=self._config.ollama_model,
        )
        self._claude_client = ClaudeClient(model=self._config.claude_model)

        # Active LLM client
        self._llm_client: LlmClient = (
            self._claude_client if self._config.llm_backend == "claude"
            else self._ollama_client
        )

        # Domain services
        self._doc_processor = DocumentProcessor()
        self._chunking = ChunkingService(
            chunk_size=self._config.default_chunk_size,
            overlap=self._config.default_chunk_overlap,
        )
        self._embedding = EmbeddingService(
            model_name=self._config.embedding_model,
            cache_dir=self._config.models_dir,
        )
        self._query_engine = QueryEngine(self._llm_client)
        self._conversation = ConversationManager(self._document_store)

        # Active workers
        self._indexing_worker: IndexingWorker | None = None
        self._query_worker: QueryWorker | None = None

        # Ensure default collection exists
        self._ensure_default_collection()

    # --- Properties ---

    @property
    def config(self) -> AppConfig:
        return self._config

    @property
    def vector_store(self) -> VectorStore:
        return self._vector_store

    @property
    def document_store(self) -> DocumentStore:
        return self._document_store

    @property
    def embedding_service(self) -> EmbeddingService:
        return self._embedding

    @property
    def conversation(self) -> ConversationManager:
        return self._conversation

    @property
    def llm_client(self) -> LlmClient:
        return self._llm_client

    @property
    def active_collection(self) -> str:
        return self._config.active_collection

    # --- Embedding Model ---

    def load_embedding_model(self, progress_callback=None) -> bool:
        """Load the embedding model (may download on first run)."""
        return self._embedding.load(progress_callback=progress_callback)

    def is_embedding_loaded(self) -> bool:
        return self._embedding.is_loaded()

    def reload_embedding_model(self, model_name: str) -> None:
        """Replace embedding service with a new model (unloads current)."""
        self._embedding = EmbeddingService(
            model_name=model_name,
            cache_dir=self._config.models_dir,
        )

    # --- Indexing ---

    def start_indexing(self, files: list[str], collection: str | None = None) -> IndexingWorker:
        """Start background document indexing.

        Args:
            files: List of file paths to index.
            collection: Target collection (uses active if None).

        Returns:
            IndexingWorker thread (already started).
        """
        target = collection or self._config.active_collection

        # Get collection-specific settings if available
        col_config = self._document_store.get_collection_config(target)
        if col_config:
            chunking = ChunkingService(
                chunk_size=col_config.get("chunk_size", self._config.default_chunk_size),
                overlap=col_config.get("chunk_overlap", self._config.default_chunk_overlap),
            )
        else:
            chunking = self._chunking

        worker = IndexingWorker(
            files=files,
            collection=target,
            document_processor=self._doc_processor,
            chunking_service=chunking,
            embedding_service=self._embedding,
            vector_store=self._vector_store,
            document_store=self._document_store,
        )
        self._indexing_worker = worker
        worker.start()
        return worker

    def is_indexing(self) -> bool:
        return self._indexing_worker is not None and self._indexing_worker.isRunning()

    def cancel_indexing(self):
        if self._indexing_worker:
            self._indexing_worker.cancel()

    # --- Querying ---

    def start_query(
        self,
        question: str,
        collection: str | None = None,
        session_id: str | None = None,
    ) -> QueryWorker:
        """Start background RAG query.

        Args:
            question: Natural language question.
            collection: Collection to search (uses active if None).
            session_id: Chat session ID.

        Returns:
            QueryWorker thread (already started).
        """
        target = collection or self._config.active_collection

        # Get conversation history
        history = self._conversation.get_history(session_id)

        # Get top_k from collection config
        col_config = self._document_store.get_collection_config(target)
        top_k = col_config.get("top_k", self._config.default_top_k) if col_config else self._config.default_top_k

        worker = QueryWorker(
            question=question,
            collection=target,
            history=history,
            embedding_service=self._embedding,
            vector_store=self._vector_store,
            query_engine=self._query_engine,
            top_k=top_k,
        )
        self._query_worker = worker
        worker.start()
        return worker

    def is_querying(self) -> bool:
        return self._query_worker is not None and self._query_worker.isRunning()

    def cancel_query(self):
        if self._query_worker:
            self._query_worker.cancel()

    # --- Collection Management ---

    def create_collection(self, name: str) -> bool:
        """Create a new collection."""
        try:
            self._vector_store.get_or_create_collection(name)
            self._document_store.save_collection_config(
                name=name,
                embedding_model=self._config.embedding_model,
                chunk_size=self._config.default_chunk_size,
                chunk_overlap=self._config.default_chunk_overlap,
                top_k=self._config.default_top_k,
                llm_backend=self._config.llm_backend,
                llm_model=self._llm_client.get_model_name(),
            )
            logger.info(f"Collection created: {name}")
            return True
        except Exception as e:
            logger.error(f"Failed to create collection '{name}': {e}")
            return False

    def delete_collection(self, name: str) -> bool:
        """Delete a collection and all its data."""
        # Prevent deleting last collection
        collections = self.list_collections()
        if len(collections) <= 1:
            logger.warning("Cannot delete the last collection")
            return False

        success = self._vector_store.delete_collection(name)
        if success:
            self._document_store.delete_collection_config(name)

            # Switch to another collection if active was deleted
            if self._config.active_collection == name:
                remaining = [c for c in collections if c != name]
                if remaining:
                    self.switch_collection(remaining[0])

        return success

    def switch_collection(self, name: str):
        """Switch active collection."""
        self._config.active_collection = name
        self._config_store.save(self._config)
        logger.info(f"Switched to collection: {name}")

    def list_collections(self) -> list[str]:
        """List all collections."""
        configs = self._document_store.list_collection_configs()
        if configs:
            return [c["name"] for c in configs]
        # Fallback to vector store
        return self._vector_store.list_collections() or ["default"]

    def get_collection_documents(self, collection: str | None = None):
        """Get documents in a collection."""
        target = collection or self._config.active_collection
        return self._document_store.get_documents(target)

    def get_document_count(self, collection: str | None = None) -> int:
        target = collection or self._config.active_collection
        return self._document_store.get_document_count(target)

    def delete_document(self, doc_id: str, collection: str | None = None) -> bool:
        """Delete a document from collection."""
        target = collection or self._config.active_collection
        # Delete from vector store
        self._vector_store.delete_documents(target, doc_id)
        # Delete metadata
        return self._document_store.delete_document(doc_id)

    def find_duplicate(self, file_name: str, collection: str | None = None):
        """Check if a document already exists in collection."""
        target = collection or self._config.active_collection
        return self._document_store.find_document(target, file_name)

    def set_document_tags(self, doc_id: str, tags: list[str]) -> None:
        """Save tags for a document (F-12)."""
        self._document_store.set_document_tags(doc_id, tags)

    # --- LLM Backend ---

    def switch_llm_backend(self, backend: str):
        """Switch LLM backend between 'ollama' and 'claude'.

        Args:
            backend: "ollama" or "claude"
        """
        if backend == "claude":
            self._llm_client = self._claude_client
        else:
            self._llm_client = self._ollama_client

        self._query_engine.llm_client = self._llm_client
        self._config.llm_backend = backend
        self._config_store.save(self._config)
        logger.info(f"LLM backend switched to: {backend}")

    def update_ollama_settings(self, host: str | None = None, model: str | None = None):
        """Update Ollama connection settings."""
        if host:
            self._ollama_client.host = host
            self._config.ollama_host = host
        if model:
            self._ollama_client.model = model
            self._config.ollama_model = model
        self._config_store.save(self._config)

    def update_claude_settings(self, model: str | None = None):
        """Update Claude API settings."""
        if model:
            self._claude_client.model = model
            self._config.claude_model = model
        self._config_store.save(self._config)

    def check_llm_status(self) -> tuple[bool, str]:
        """Check current LLM backend status.

        Returns:
            (is_available, status_message)
        """
        if self._config.llm_backend == "ollama":
            available = self._ollama_client.is_available()
            if available:
                return True, f"Ollama connected ({self._ollama_client.model})"
            return False, f"Ollama not reachable at {self._ollama_client.host}"
        else:
            available = self._claude_client.is_available()
            if available:
                return True, f"Claude API ready ({self._claude_client.model})"
            return False, "Claude API key not configured"

    def get_available_models(self) -> list[str]:
        """Get available models for the current backend."""
        return self._llm_client.list_models()

    # --- Settings ---

    def save_config(self):
        """Persist current configuration."""
        self._config_store.save(self._config)

    def update_config(self, **kwargs):
        """Update config fields."""
        self._config_store.update(**kwargs)
        self._config = self._config_store.get()

    # --- Private ---

    def _ensure_default_collection(self):
        """Ensure at least one collection exists."""
        collections = self._document_store.list_collection_configs()
        if not collections:
            self.create_collection("default")
            self._config.active_collection = "default"
            self._config_store.save(self._config)
