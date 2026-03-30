"""OllamaClient - Ollama LLM backend implementation.

Connects to local Ollama server for text generation.
Default: http://localhost:11434
"""
import json
import logging
from typing import Iterator

import requests

from app.infrastructure.llm_client import LlmClient

logger = logging.getLogger(__name__)


class OllamaClient(LlmClient):
    """Ollama local LLM client with streaming support."""

    def __init__(self, host: str = "http://localhost:11434", model: str = "gemma3:4b"):
        self._host = host.rstrip("/")
        self._model = model
        self._timeout = 120  # seconds

    @property
    def host(self) -> str:
        return self._host

    @host.setter
    def host(self, value: str):
        self._host = value.rstrip("/")

    @property
    def model(self) -> str:
        return self._model

    @model.setter
    def model(self, value: str):
        self._model = value

    def generate(self, prompt: str, context: str = "", system: str = "") -> Iterator[str]:
        """Stream tokens from Ollama API.

        Uses POST /api/generate with streaming enabled.
        """
        if not system:
            system = (
                "You are a helpful document assistant. "
                "Answer questions based on the provided context. "
                "If the context doesn't contain relevant information, say so honestly. "
                "Always respond in the same language as the question."
            )

        full_prompt = prompt
        if context:
            full_prompt = (
                f"Context:\n{context}\n\n"
                f"Question: {prompt}\n\n"
                f"Answer based on the context above:"
            )

        payload = {
            "model": self._model,
            "prompt": full_prompt,
            "system": system,
            "stream": True,
        }

        try:
            response = requests.post(
                f"{self._host}/api/generate",
                json=payload,
                stream=True,
                timeout=self._timeout,
            )
            response.raise_for_status()

            for line in response.iter_lines():
                if line:
                    try:
                        data = json.loads(line)
                        if "response" in data:
                            yield data["response"]
                        if data.get("done", False):
                            break
                    except json.JSONDecodeError:
                        continue

        except requests.ConnectionError:
            yield "[Error: Cannot connect to Ollama. Is it running at {}?]".format(self._host)
        except requests.Timeout:
            yield "[Error: Ollama request timed out]"
        except requests.HTTPError as e:
            yield f"[Error: Ollama returned {e.response.status_code}]"
        except Exception as e:
            logger.error(f"Ollama generate error: {e}")
            yield f"[Error: {str(e)}]"

    def is_available(self) -> bool:
        """Check Ollama server connectivity."""
        try:
            response = requests.get(f"{self._host}/api/tags", timeout=5)
            return response.status_code == 200
        except Exception:
            return False

    def list_models(self) -> list[str]:
        """List models installed in Ollama."""
        try:
            response = requests.get(f"{self._host}/api/tags", timeout=10)
            response.raise_for_status()
            data = response.json()
            models = data.get("models", [])
            return [m["name"] for m in models]
        except Exception as e:
            logger.error(f"Failed to list Ollama models: {e}")
            return []

    def get_model_name(self) -> str:
        return self._model
