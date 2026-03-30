"""IndexingWorker - Background thread for document indexing.

Runs the full indexing pipeline: process -> chunk -> embed -> store
in a QThread to avoid UI blocking.
"""
import logging
import os
import uuid
from datetime import datetime

from PyQt6.QtCore import QThread, pyqtSignal

from app.domain.document_processor import DocumentProcessor
from app.domain.chunking_service import ChunkingService
from app.domain.embedding_service import EmbeddingService
from app.infrastructure.vector_store import VectorStore
from app.infrastructure.document_store import DocumentStore, DocumentMeta

logger = logging.getLogger(__name__)


class IndexingWorker(QThread):
    """Background worker for document indexing pipeline.

    Signals:
        progress(int, str): (progress_percent, status_message)
        chunk_done(int, int): (processed_chunks, total_chunks)
        file_done(str, int): (file_name, chunk_count)
        finished(bool, str): (success, summary_message)
        error(str): error message
    """

    progress = pyqtSignal(int, str)
    chunk_done = pyqtSignal(int, int)
    file_done = pyqtSignal(str, int)
    finished = pyqtSignal(bool, str)
    error = pyqtSignal(str)

    def __init__(
        self,
        files: list[str],
        collection: str,
        document_processor: DocumentProcessor,
        chunking_service: ChunkingService,
        embedding_service: EmbeddingService,
        vector_store: VectorStore,
        document_store: DocumentStore,
    ):
        super().__init__()
        self._files = files
        self._collection = collection
        self._doc_processor = document_processor
        self._chunking = chunking_service
        self._embedding = embedding_service
        self._vector_store = vector_store
        self._doc_store = document_store
        self._cancelled = False

    def cancel(self):
        """Request cancellation of the indexing process."""
        self._cancelled = True

    def run(self):
        """Execute the indexing pipeline."""
        total_files = len(self._files)
        total_chunks = 0
        processed_files = 0
        failed_files = []

        try:
            for i, file_path in enumerate(self._files):
                if self._cancelled:
                    self.progress.emit(
                        int((i / total_files) * 100),
                        "Indexing cancelled",
                    )
                    break

                file_name = os.path.basename(file_path)
                self.progress.emit(
                    int((i / total_files) * 100),
                    f"Processing {file_name} ({i + 1}/{total_files})...",
                )

                try:
                    # Step 1: Extract text
                    content = self._doc_processor.process(file_path)
                    if not content.full_text.strip():
                        logger.warning(f"No text extracted from {file_name}")
                        failed_files.append(file_name)
                        continue

                    # Step 2: Create document metadata
                    doc_id = str(uuid.uuid4())

                    # Step 3: Chunk the content
                    self.progress.emit(
                        int(((i + 0.3) / total_files) * 100),
                        f"Chunking {file_name}...",
                    )
                    chunks = self._chunking.chunk(content, doc_id)
                    if not chunks:
                        logger.warning(f"No chunks created from {file_name}")
                        failed_files.append(file_name)
                        continue

                    # Step 4: Generate embeddings
                    self.progress.emit(
                        int(((i + 0.5) / total_files) * 100),
                        f"Embedding {file_name} ({len(chunks)} chunks)...",
                    )
                    chunk_texts = [c.text for c in chunks]
                    embeddings = self._embedding.embed_texts(
                        chunk_texts,
                        progress_callback=lambda done, total: self.chunk_done.emit(done, total),
                    )

                    # Step 5: Store in vector DB
                    self.progress.emit(
                        int(((i + 0.8) / total_files) * 100),
                        f"Storing {file_name} vectors...",
                    )
                    self._vector_store.upsert(
                        collection_name=self._collection,
                        ids=[c.id for c in chunks],
                        documents=chunk_texts,
                        embeddings=embeddings,
                        metadatas=[c.metadata for c in chunks],
                    )

                    # Step 6: Save document metadata
                    doc_meta = DocumentMeta(
                        id=doc_id,
                        file_name=file_name,
                        file_path=file_path,
                        collection=self._collection,
                        chunk_count=len(chunks),
                        created_at=datetime.now().isoformat(),
                        file_size=content.file_size,
                        file_type=content.file_type,
                    )
                    self._doc_store.save_document(doc_meta)

                    total_chunks += len(chunks)
                    processed_files += 1
                    self.file_done.emit(file_name, len(chunks))

                except Exception as e:
                    logger.error(f"Failed to index {file_name}: {e}")
                    failed_files.append(file_name)
                    self.error.emit(f"Failed to index {file_name}: {str(e)}")
                    continue

            # Summary
            if self._cancelled:
                summary = f"Cancelled. Indexed {processed_files}/{total_files} files ({total_chunks} chunks)"
            elif failed_files:
                summary = (
                    f"Completed with errors. Indexed {processed_files}/{total_files} files "
                    f"({total_chunks} chunks). Failed: {', '.join(failed_files)}"
                )
            else:
                summary = f"Successfully indexed {processed_files} files ({total_chunks} chunks)"

            self.progress.emit(100, summary)
            self.finished.emit(len(failed_files) == 0, summary)

        except Exception as e:
            logger.error(f"Indexing worker fatal error: {e}")
            self.error.emit(f"Fatal error: {str(e)}")
            self.finished.emit(False, f"Fatal error: {str(e)}")
