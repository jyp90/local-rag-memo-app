"""Tests for EmbeddingService.

NOTE: These tests require sentence-transformers to be installed
and will download the model on first run (~420MB).
Tests marked with @pytest.mark.slow can be skipped with: pytest -m "not slow"
"""
import pytest

from app.domain.embedding_service import EmbeddingService


@pytest.fixture(scope="module")
def embedding_service():
    """Module-scoped embedding service (avoids reloading model per test)."""
    service = EmbeddingService(
        model_name="paraphrase-multilingual-MiniLM-L12-v2",
    )
    success = service.load()
    if not success:
        pytest.skip("Embedding model not available")
    return service


class TestEmbeddingService:
    """Test suite for EmbeddingService."""

    def test_init_defaults(self):
        service = EmbeddingService()
        assert service.model_name == "paraphrase-multilingual-MiniLM-L12-v2"
        assert not service.is_loaded()

    def test_available_models(self):
        models = EmbeddingService.available_models()
        assert len(models) >= 3
        names = [m["name"] for m in models]
        assert "paraphrase-multilingual-MiniLM-L12-v2" in names

    @pytest.mark.slow
    def test_load(self, embedding_service):
        assert embedding_service.is_loaded()
        assert embedding_service.dimension is not None
        assert embedding_service.dimension > 0

    @pytest.mark.slow
    def test_embed_single_text(self, embedding_service):
        embedding = embedding_service.embed_text("Hello world")
        assert isinstance(embedding, list)
        assert len(embedding) == embedding_service.dimension
        assert all(isinstance(x, float) for x in embedding)

    @pytest.mark.slow
    def test_embed_multiple_texts(self, embedding_service):
        texts = ["First document", "Second document", "Third document"]
        embeddings = embedding_service.embed_texts(texts)
        assert len(embeddings) == 3
        for emb in embeddings:
            assert len(emb) == embedding_service.dimension

    @pytest.mark.slow
    def test_embed_korean(self, embedding_service):
        embedding = embedding_service.embed_text("RAG 시스템의 아키텍처를 설명합니다")
        assert len(embedding) == embedding_service.dimension

    @pytest.mark.slow
    def test_similar_texts_closer(self, embedding_service):
        """Similar texts should have closer embeddings."""
        import numpy as np

        e1 = embedding_service.embed_text("machine learning algorithms")
        e2 = embedding_service.embed_text("deep learning models")
        e3 = embedding_service.embed_text("cooking recipes for pasta")

        # Cosine similarity
        def cosine_sim(a, b):
            a, b = np.array(a), np.array(b)
            return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

        sim_related = cosine_sim(e1, e2)
        sim_unrelated = cosine_sim(e1, e3)

        assert sim_related > sim_unrelated, "Related texts should be more similar"

    @pytest.mark.slow
    def test_embed_query_alias(self, embedding_service):
        emb1 = embedding_service.embed_text("test query")
        emb2 = embedding_service.embed_query("test query")
        assert emb1 == emb2

    @pytest.mark.slow
    def test_progress_callback(self, embedding_service):
        progress_calls = []

        def on_progress(done, total):
            progress_calls.append((done, total))

        texts = ["text " + str(i) for i in range(10)]
        embedding_service.embed_texts(texts, progress_callback=on_progress)
        assert len(progress_calls) > 0

    def test_embed_without_load_raises(self):
        service = EmbeddingService()
        with pytest.raises(RuntimeError, match="not loaded"):
            service.embed_text("test")
