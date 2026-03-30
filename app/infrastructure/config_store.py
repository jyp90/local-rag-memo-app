"""ConfigStore - Application configuration management.

Manages app-wide settings in a JSON file at ~/.local-rag-memo/config.json.
"""
import json
import os
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any


DEFAULT_BASE_DIR = os.path.expanduser("~/.local-rag-memo")


@dataclass
class AppConfig:
    """Application-wide configuration."""

    # Paths
    base_dir: str = DEFAULT_BASE_DIR
    chroma_dir: str = ""
    sqlite_dir: str = ""
    models_dir: str = ""

    # LLM settings
    llm_backend: str = "ollama"  # "ollama" | "claude"
    ollama_host: str = "http://localhost:11434"
    ollama_model: str = "gemma3:4b"
    claude_model: str = "claude-sonnet-4-20250514"

    # Embedding settings
    embedding_model: str = "paraphrase-multilingual-MiniLM-L12-v2"

    # RAG defaults
    default_chunk_size: int = 500
    default_chunk_overlap: int = 50
    default_top_k: int = 5

    # UI settings
    theme: str = "dark"
    font_size: int = 14
    language: str = "ko"

    # Window state
    window_width: int = 1200
    window_height: int = 800

    # Active collection
    active_collection: str = "default"

    def __post_init__(self):
        if not self.chroma_dir:
            self.chroma_dir = os.path.join(self.base_dir, "chroma")
        if not self.sqlite_dir:
            self.sqlite_dir = os.path.join(self.base_dir, "sqlite")
        if not self.models_dir:
            self.models_dir = os.path.join(self.base_dir, "models")


class ConfigStore:
    """Manages persistent configuration stored as JSON."""

    def __init__(self, base_dir: str | None = None):
        self._base_dir = base_dir or DEFAULT_BASE_DIR
        self._config_path = os.path.join(self._base_dir, "config.json")
        self._config: AppConfig | None = None

    def _ensure_dirs(self):
        """Create required directories if they don't exist."""
        os.makedirs(self._base_dir, exist_ok=True)

    def load(self) -> AppConfig:
        """Load configuration from disk. Creates defaults if not found."""
        self._ensure_dirs()

        if os.path.exists(self._config_path):
            try:
                with open(self._config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self._config = AppConfig(**{
                    k: v for k, v in data.items()
                    if k in AppConfig.__dataclass_fields__
                })
            except (json.JSONDecodeError, TypeError):
                self._config = AppConfig(base_dir=self._base_dir)
        else:
            self._config = AppConfig(base_dir=self._base_dir)

        # Ensure sub-directories exist
        os.makedirs(self._config.chroma_dir, exist_ok=True)
        os.makedirs(self._config.sqlite_dir, exist_ok=True)
        os.makedirs(self._config.models_dir, exist_ok=True)

        return self._config

    def save(self, config: AppConfig | None = None):
        """Save configuration to disk."""
        if config:
            self._config = config
        if not self._config:
            return

        self._ensure_dirs()
        with open(self._config_path, "w", encoding="utf-8") as f:
            json.dump(asdict(self._config), f, indent=2, ensure_ascii=False)

    def get(self) -> AppConfig:
        """Get current config (loads if needed)."""
        if not self._config:
            return self.load()
        return self._config

    def update(self, **kwargs):
        """Update specific config fields and save."""
        config = self.get()
        for key, value in kwargs.items():
            if hasattr(config, key):
                setattr(config, key, value)
        self.save(config)

    @property
    def config_path(self) -> str:
        return self._config_path
