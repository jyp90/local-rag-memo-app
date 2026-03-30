"""QueryEngine - Search result assembly and prompt construction.

Combines retrieved chunks with conversation history to build
LLM prompts. Manages context window limits.
"""
import logging
from typing import Iterator

from app.infrastructure.llm_client import LlmClient
from app.infrastructure.vector_store import SearchResult

logger = logging.getLogger(__name__)

# Default RAG system prompt
DEFAULT_SYSTEM_PROMPT = """You are a helpful document assistant for Local RAG Memo.
Answer questions based on the provided context from the user's documents.
Important rules:
1. Only answer based on the provided context. Do not make up information.
2. If the context doesn't contain relevant information, clearly state that.
3. When citing information, reference the source document and page/section.
4. Respond in the same language as the user's question.
5. Be concise but thorough."""

MAX_CONTEXT_CHARS = 8000  # Max characters for context window
MAX_HISTORY_MESSAGES = 6  # Max conversation history messages to include


class QueryEngine:
    """Assembles search results + history into LLM prompts and streams answers."""

    def __init__(self, llm_client: LlmClient):
        self._llm_client = llm_client

    @property
    def llm_client(self) -> LlmClient:
        return self._llm_client

    @llm_client.setter
    def llm_client(self, client: LlmClient):
        self._llm_client = client

    def build_prompt(
        self,
        question: str,
        search_results: list[SearchResult],
        history: list[dict] | None = None,
    ) -> str:
        """Build a prompt from question, search results, and history.

        Args:
            question: User's natural language question.
            search_results: Retrieved similar chunks.
            history: Previous conversation messages [{"role": "user"|"assistant", "content": "..."}].

        Returns:
            Formatted prompt string ready for LLM.
        """
        parts = []

        # Build context from search results
        context = self._build_context(search_results)
        if context:
            parts.append(context)

        # Build conversation history
        if history:
            history_text = self._build_history(history)
            if history_text:
                parts.append(history_text)

        # The question
        parts.append(f"Question: {question}")

        return "\n\n".join(parts)

    def _build_context(self, search_results: list[SearchResult]) -> str:
        """Build context string from search results with source attribution."""
        if not search_results:
            return ""

        context_parts = ["--- Retrieved Documents ---"]
        total_chars = 0

        for i, result in enumerate(search_results, 1):
            source_info = self._format_source(result)
            chunk_text = f"[Source {i}] {source_info}\n{result.text}"

            if total_chars + len(chunk_text) > MAX_CONTEXT_CHARS:
                # Truncate to fit
                remaining = MAX_CONTEXT_CHARS - total_chars
                if remaining > 100:
                    chunk_text = chunk_text[:remaining] + "..."
                    context_parts.append(chunk_text)
                break

            context_parts.append(chunk_text)
            total_chars += len(chunk_text)

        context_parts.append("--- End of Retrieved Documents ---")
        return "\n\n".join(context_parts)

    def _build_history(self, history: list[dict]) -> str:
        """Build conversation history string."""
        # Take only recent messages
        recent = history[-MAX_HISTORY_MESSAGES:]

        if not recent:
            return ""

        parts = ["--- Conversation History ---"]
        for msg in recent:
            role = "User" if msg.get("role") == "user" else "Assistant"
            content = msg.get("content", "")
            # Truncate long messages in history
            if len(content) > 500:
                content = content[:500] + "..."
            parts.append(f"{role}: {content}")

        return "\n".join(parts)

    @staticmethod
    def _format_source(result: SearchResult) -> str:
        """Format source attribution for a search result."""
        meta = result.metadata
        parts = []

        file_name = meta.get("file_name", "Unknown")
        parts.append(file_name)

        page_num = meta.get("page_num")
        if page_num:
            parts.append(f"p.{page_num}")

        section = meta.get("section")
        if section:
            parts.append(f"'{section}'")

        score = f"(relevance: {result.score:.2f})"
        return " | ".join(parts) + f" {score}"

    def stream_answer(
        self,
        question: str,
        search_results: list[SearchResult],
        history: list[dict] | None = None,
    ) -> Iterator[str]:
        """Stream answer tokens from LLM.

        Args:
            question: User's question.
            search_results: Retrieved chunks.
            history: Conversation history.

        Yields:
            Individual tokens as strings.
        """
        prompt = self.build_prompt(question, search_results, history)
        context = self._build_context(search_results)

        yield from self._llm_client.generate(
            prompt=question,
            context=context,
            system=DEFAULT_SYSTEM_PROMPT,
        )

    def format_sources_for_display(
        self, search_results: list[SearchResult]
    ) -> list[dict]:
        """Format search results for UI source reference display.

        Returns:
            List of source dicts with display-ready information.
        """
        sources = []
        seen = set()  # Deduplicate by doc_id + page

        for result in search_results:
            meta = result.metadata
            doc_id = meta.get("doc_id", "")
            page_num = meta.get("page_num")
            key = f"{doc_id}:{page_num}"

            if key in seen:
                continue
            seen.add(key)

            sources.append({
                "file_name": meta.get("file_name", "Unknown"),
                "page_num": page_num,
                "section": meta.get("section", ""),
                "score": round(result.score, 3),
                "text_preview": result.text[:200] + "..." if len(result.text) > 200 else result.text,
                "chunk_id": result.chunk_id,
                "doc_id": doc_id,
            })

        return sources
