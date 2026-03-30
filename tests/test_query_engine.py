"""Tests for QueryEngine."""
import pytest
from unittest.mock import MagicMock

from app.domain.query_engine import QueryEngine, MAX_CONTEXT_CHARS, MAX_HISTORY_MESSAGES
from app.infrastructure.vector_store import SearchResult


class TestQueryEngine:
    """Test suite for QueryEngine prompt building and answer streaming."""

    @pytest.fixture
    def mock_llm(self):
        mock = MagicMock()
        mock.generate.return_value = iter(["Hello", " world", "!"])
        return mock

    @pytest.fixture
    def engine(self, mock_llm):
        return QueryEngine(mock_llm)

    def test_build_prompt_no_context(self, engine):
        prompt = engine.build_prompt("What is RAG?", [], None)
        assert "What is RAG?" in prompt

    def test_build_prompt_with_results(self, engine):
        results = [
            SearchResult(
                chunk_id="c1",
                text="RAG combines retrieval and generation.",
                score=0.95,
                metadata={"file_name": "rag.pdf", "page_num": 1, "doc_id": "d1"},
            ),
        ]
        prompt = engine.build_prompt("What is RAG?", results)
        assert "Retrieved Documents" in prompt
        assert "rag.pdf" in prompt
        assert "RAG combines" in prompt

    def test_build_prompt_with_history(self, engine):
        history = [
            {"role": "user", "content": "Tell me about AI"},
            {"role": "assistant", "content": "AI is artificial intelligence."},
        ]
        prompt = engine.build_prompt("More details?", [], history)
        assert "Conversation History" in prompt
        assert "Tell me about AI" in prompt

    def test_context_length_limit(self, engine):
        """Context should be truncated beyond MAX_CONTEXT_CHARS."""
        results = []
        for i in range(50):
            results.append(SearchResult(
                chunk_id=f"c{i}",
                text="X" * 500,
                score=0.9,
                metadata={"file_name": "big.pdf", "page_num": i, "doc_id": "d1"},
            ))

        prompt = engine.build_prompt("test?", results)
        # The context portion shouldn't be unreasonably large
        context_section = prompt.split("--- End of Retrieved Documents ---")[0]
        assert len(context_section) <= MAX_CONTEXT_CHARS + 2000  # Allow some overhead

    def test_history_limit(self, engine):
        """Only recent N history messages should be included."""
        history = [
            {"role": "user", "content": f"question {i}"}
            for i in range(20)
        ]
        prompt = engine.build_prompt("current?", [], history)
        # Should not include all 20 messages
        count = prompt.count("question ")
        assert count <= MAX_HISTORY_MESSAGES

    def test_stream_answer(self, engine, mock_llm):
        results = [
            SearchResult(
                chunk_id="c1",
                text="test context",
                score=0.9,
                metadata={"file_name": "t.txt", "doc_id": "d1"},
            ),
        ]
        tokens = list(engine.stream_answer("question?", results))
        assert len(tokens) > 0
        mock_llm.generate.assert_called_once()

    def test_format_sources_for_display(self, engine):
        results = [
            SearchResult(
                chunk_id="c1",
                text="Some content here",
                score=0.95,
                metadata={
                    "file_name": "doc.pdf",
                    "page_num": 5,
                    "section": "Intro",
                    "doc_id": "d1",
                },
            ),
            SearchResult(
                chunk_id="c2",
                text="More content",
                score=0.88,
                metadata={
                    "file_name": "doc.pdf",
                    "page_num": 5,
                    "doc_id": "d1",
                },
            ),
        ]
        sources = engine.format_sources_for_display(results)
        # Should deduplicate by doc_id + page
        assert len(sources) == 1
        assert sources[0]["file_name"] == "doc.pdf"
        assert sources[0]["page_num"] == 5
        assert sources[0]["score"] == 0.95

    def test_format_sources_different_pages(self, engine):
        results = [
            SearchResult(
                chunk_id="c1", text="A", score=0.9,
                metadata={"file_name": "a.pdf", "page_num": 1, "doc_id": "d1"},
            ),
            SearchResult(
                chunk_id="c2", text="B", score=0.8,
                metadata={"file_name": "a.pdf", "page_num": 2, "doc_id": "d1"},
            ),
        ]
        sources = engine.format_sources_for_display(results)
        assert len(sources) == 2  # Different pages = different sources

    def test_llm_client_swap(self, engine):
        new_mock = MagicMock()
        new_mock.generate.return_value = iter(["New", " response"])
        engine.llm_client = new_mock
        assert engine.llm_client == new_mock
