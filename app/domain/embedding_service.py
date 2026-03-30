"""EmbeddingService - Local embedding model management.

Uses sentence-transformers for embedding generation.
Default model: paraphrase-multilingual-MiniLM-L12-v2
Supports progress callbacks for first-time model download.
"""
import logging
import os
from typing import Callable

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Manages sentence-transformer embedding model for vectorization."""

    def __init__(
        self,
        model_name: str = "paraphrase-multilingual-MiniLM-L12-v2",
        cache_dir: str | None = None,
    ):
        self._model_name = model_name
        self._cache_dir = cache_dir
        self._model = None
        self._dimension: int | None = None

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def dimension(self) -> int | None:
        """Embedding vector dimension (available after load)."""
        return self._dimension

    def is_loaded(self) -> bool:
        """Check if model is loaded."""
        return self._model is not None

    def load(self, progress_callback: Callable[[str, int], None] | None = None) -> bool:
        """Load the embedding model.

        Args:
            progress_callback: Optional callback(status_message, progress_percent).
                              Called during model download/initialization.

        Returns:
            True if successfully loaded, False otherwise.
        """
        try:
            if progress_callback:
                progress_callback("Loading embedding model...", 10)

            from sentence_transformers import SentenceTransformer

            kwargs = {"model_name_or_path": self._model_name}
            if self._cache_dir:
                kwargs["cache_folder"] = self._cache_dir

            if progress_callback:
                progress_callback(f"Downloading/loading {self._model_name}...", 30)

            self._model = SentenceTransformer(**kwargs)

            if progress_callback:
                progress_callback("Model loaded successfully", 100)

            # Get dimension from a test embedding
            test_embedding = self._model.encode(["test"], show_progress_bar=False)
            self._dimension = len(test_embedding[0])
            logger.info(
                f"Embedding model loaded: {self._model_name} "
                f"(dim={self._dimension})"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            if progress_callback:
                progress_callback(f"Error: {str(e)}", -1)
            return False

    def embed_text(self, text: str) -> list[float]:
        """Generate embedding for a single text.

        Args:
            text: Input text to embed.

        Returns:
            Embedding vector as list of floats.
        """
        if not self._model:
            raise RuntimeError("Embedding model not loaded. Call load() first.")

        embedding = self._model.encode([text], show_progress_bar=False)
        return embedding[0].tolist()

    def embed_texts(
        self,
        texts: list[str],
        batch_size: int = 32,
        progress_callback: Callable[[int, int], None] | None = None,
    ) -> list[list[float]]:
        """Generate embeddings for multiple texts in batches.

        Args:
            texts: List of texts to embed.
            batch_size: Batch size for processing.
            progress_callback: Optional callback(processed_count, total_count).

        Returns:
            List of embedding vectors.
        """
        if not self._model:
            raise RuntimeError("Embedding model not loaded. Call load() first.")

        all_embeddings: list[list[float]] = []
        total = len(texts)

        for i in range(0, total, batch_size):
            batch = texts[i : i + batch_size]
            embeddings = self._model.encode(batch, show_progress_bar=False)

            for emb in embeddings:
                all_embeddings.append(emb.tolist())

            if progress_callback:
                progress_callback(min(i + batch_size, total), total)

        return all_embeddings

    def embed_query(self, query: str) -> list[float]:
        """Embed a query text (alias for embed_text for semantic clarity)."""
        return self.embed_text(query)

    @staticmethod
    def available_models() -> list[dict[str, str]]:
        """List available embedding models."""
        return [
            {
                "name": "paraphrase-multilingual-MiniLM-L12-v2",
                "size": "420MB",
                "korean": "Yes",
                "speed": "Medium",
            },
            {
                "name": "all-MiniLM-L6-v2",
                "size": "80MB",
                "korean": "Limited",
                "speed": "Fast",
            },
            {
                "name": "jhgan/ko-sroberta-multitask",
                "size": "430MB",
                "korean": "Optimal",
                "speed": "Medium",
            },
        ]
