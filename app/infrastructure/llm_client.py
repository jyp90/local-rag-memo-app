"""LlmClient - Abstract base class for LLM backends.

Defines the interface for Ollama and Claude API implementations.
Supports streaming token generation.
"""
from abc import ABC, abstractmethod
from typing import Iterator


class LlmClient(ABC):
    """LLM backend abstraction -- enables Ollama/Claude API runtime swap."""

    @abstractmethod
    def generate(self, prompt: str, context: str = "", system: str = "") -> Iterator[str]:
        """Stream tokens from LLM.

        Args:
            prompt: The user query/prompt.
            context: RAG context (retrieved chunks).
            system: System prompt for LLM behavior.

        Yields:
            Individual tokens as strings.
        """
        ...

    @abstractmethod
    def is_available(self) -> bool:
        """Check if the LLM backend is reachable and operational.

        Returns:
            True if the backend is available, False otherwise.
        """
        ...

    @abstractmethod
    def list_models(self) -> list[str]:
        """List available models for this backend.

        Returns:
            List of model name strings.
        """
        ...

    @abstractmethod
    def get_model_name(self) -> str:
        """Get the currently configured model name.

        Returns:
            Model name string.
        """
        ...
