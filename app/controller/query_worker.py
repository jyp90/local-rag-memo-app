"""QueryWorker - Background thread for question processing.

Handles: embed query -> similarity search -> LLM streaming -> save history.
Runs in QThread to keep UI responsive.
"""
import logging

from PyQt6.QtCore import QThread, pyqtSignal

from app.domain.embedding_service import EmbeddingService
from app.domain.query_engine import QueryEngine
from app.infrastructure.vector_store import VectorStore

logger = logging.getLogger(__name__)


class QueryWorker(QThread):
    """Background worker for RAG query pipeline.

    Signals:
        token_received(str): Individual streaming token.
        sources_ready(list): Source reference dicts for display.
        finished(): Query complete.
        error(str): Error message.
    """

    token_received = pyqtSignal(str)
    sources_ready = pyqtSignal(list)
    finished = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(
        self,
        question: str,
        collection: str,
        history: list[dict],
        embedding_service: EmbeddingService,
        vector_store: VectorStore,
        query_engine: QueryEngine,
        top_k: int = 5,
    ):
        super().__init__()
        self._question = question
        self._collection = collection
        self._history = history
        self._embedding = embedding_service
        self._vector_store = vector_store
        self._query_engine = query_engine
        self._top_k = top_k
        self._cancelled = False
        self._full_answer = ""

    @property
    def full_answer(self) -> str:
        """Get the complete accumulated answer text."""
        return self._full_answer

    def cancel(self):
        """Request cancellation of the query."""
        self._cancelled = True

    def run(self):
        """Execute the RAG query pipeline."""
        try:
            # Step 1: Embed the question
            query_embedding = self._embedding.embed_query(self._question)

            # Step 2: Similarity search
            search_results = self._vector_store.similarity_search(
                collection_name=self._collection,
                query_embedding=query_embedding,
                top_k=self._top_k,
            )

            # Step 3: Emit sources
            sources = self._query_engine.format_sources_for_display(search_results)
            self.sources_ready.emit(sources)

            # Step 4: Stream LLM answer
            self._full_answer = ""
            for token in self._query_engine.stream_answer(
                question=self._question,
                search_results=search_results,
                history=self._history,
            ):
                if self._cancelled:
                    break
                self._full_answer += token
                self.token_received.emit(token)

            self.finished.emit()

        except Exception as e:
            logger.error(f"Query worker error: {e}")
            self.error.emit(str(e))
