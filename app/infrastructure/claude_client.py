"""ClaudeClient - Anthropic Claude API backend implementation.

API key is stored in macOS Keychain via keyring library (NF-S-01).
Never stores API key in plaintext.
"""
import logging
from typing import Iterator

from app.infrastructure.llm_client import LlmClient

logger = logging.getLogger(__name__)

KEYCHAIN_SERVICE = "local-rag-memo"
KEYCHAIN_ACCOUNT = "claude-api-key"


class ClaudeClient(LlmClient):
    """Claude API client with streaming support and Keychain integration."""

    def __init__(self, model: str = "claude-sonnet-4-20250514"):
        self._model = model
        self._client = None

    @property
    def model(self) -> str:
        return self._model

    @model.setter
    def model(self, value: str):
        self._model = value
        self._client = None  # Force re-init on model change

    def _get_api_key(self) -> str | None:
        """Retrieve API key from macOS Keychain."""
        try:
            import keyring
            return keyring.get_password(KEYCHAIN_SERVICE, KEYCHAIN_ACCOUNT)
        except Exception as e:
            logger.error(f"Failed to retrieve API key from Keychain: {e}")
            return None

    @staticmethod
    def save_api_key(api_key: str) -> bool:
        """Save API key to macOS Keychain."""
        try:
            import keyring
            keyring.set_password(KEYCHAIN_SERVICE, KEYCHAIN_ACCOUNT, api_key)
            return True
        except Exception as e:
            logger.error(f"Failed to save API key to Keychain: {e}")
            return False

    @staticmethod
    def delete_api_key() -> bool:
        """Delete API key from macOS Keychain."""
        try:
            import keyring
            keyring.delete_password(KEYCHAIN_SERVICE, KEYCHAIN_ACCOUNT)
            return True
        except Exception as e:
            logger.error(f"Failed to delete API key from Keychain: {e}")
            return False

    def _ensure_client(self):
        """Initialize Anthropic client with Keychain API key."""
        if self._client is not None:
            return

        api_key = self._get_api_key()
        if not api_key:
            raise ValueError("Claude API key not found in Keychain. Please set it in Settings.")

        try:
            import anthropic
            self._client = anthropic.Anthropic(api_key=api_key)
        except ImportError:
            raise ImportError("anthropic package not installed. Run: pip install anthropic")

    def generate(self, prompt: str, context: str = "", system: str = "") -> Iterator[str]:
        """Stream tokens from Claude API using server-sent events."""
        try:
            self._ensure_client()
        except (ValueError, ImportError) as e:
            yield f"[Error: {str(e)}]"
            return

        if not system:
            system = (
                "You are a helpful document assistant. "
                "Answer questions based on the provided context. "
                "If the context doesn't contain relevant information, say so honestly. "
                "Always respond in the same language as the question."
            )

        user_message = prompt
        if context:
            user_message = (
                f"Context:\n{context}\n\n"
                f"Question: {prompt}\n\n"
                f"Answer based on the context above:"
            )

        try:
            with self._client.messages.stream(
                model=self._model,
                max_tokens=4096,
                system=system,
                messages=[{"role": "user", "content": user_message}],
            ) as stream:
                for text in stream.text_stream:
                    yield text

        except Exception as e:
            logger.error(f"Claude API error: {e}")
            yield f"[Error: Claude API - {str(e)}]"

    def is_available(self) -> bool:
        """Check if Claude API key exists and client can be initialized."""
        api_key = self._get_api_key()
        if not api_key:
            return False
        try:
            self._ensure_client()
            return True
        except Exception:
            return False

    def list_models(self) -> list[str]:
        """Return available Claude models."""
        return [
            "claude-sonnet-4-20250514",
            "claude-haiku-35-20241022",
            "claude-opus-4-20250514",
        ]

    def get_model_name(self) -> str:
        return self._model
