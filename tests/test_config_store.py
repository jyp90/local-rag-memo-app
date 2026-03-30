"""Tests for ConfigStore."""
import os
import json
import pytest

from app.infrastructure.config_store import ConfigStore, AppConfig, DEFAULT_BASE_DIR


class TestConfigStore:
    """Test suite for ConfigStore configuration management."""

    @pytest.fixture
    def store(self, tmp_dir):
        return ConfigStore(base_dir=tmp_dir)

    def test_load_creates_defaults(self, store, tmp_dir):
        config = store.load()
        assert config.base_dir == tmp_dir
        assert config.llm_backend == "ollama"
        assert config.embedding_model == "paraphrase-multilingual-MiniLM-L12-v2"

    def test_save_and_reload(self, store, tmp_dir):
        config = store.load()
        config.llm_backend = "claude"
        config.font_size = 18
        store.save(config)

        # Reload
        store2 = ConfigStore(base_dir=tmp_dir)
        config2 = store2.load()
        assert config2.llm_backend == "claude"
        assert config2.font_size == 18

    def test_update_fields(self, store):
        store.load()
        store.update(theme="light", font_size=16)
        config = store.get()
        assert config.theme == "light"
        assert config.font_size == 16

    def test_directories_created(self, store, tmp_dir):
        config = store.load()
        assert os.path.isdir(config.chroma_dir)
        assert os.path.isdir(config.sqlite_dir)
        assert os.path.isdir(config.models_dir)

    def test_config_file_exists_after_save(self, store, tmp_dir):
        store.load()
        store.save()
        assert os.path.exists(os.path.join(tmp_dir, "config.json"))

    def test_corrupted_config_falls_back(self, tmp_dir):
        # Write invalid JSON
        config_path = os.path.join(tmp_dir, "config.json")
        os.makedirs(tmp_dir, exist_ok=True)
        with open(config_path, "w") as f:
            f.write("not valid json{{{")

        store = ConfigStore(base_dir=tmp_dir)
        config = store.load()
        assert config.llm_backend == "ollama"  # Default value

    def test_app_config_post_init(self):
        config = AppConfig(base_dir="/tmp/test")
        assert config.chroma_dir == "/tmp/test/chroma"
        assert config.sqlite_dir == "/tmp/test/sqlite"
        assert config.models_dir == "/tmp/test/models"

    def test_get_without_load(self, store):
        config = store.get()  # Should auto-load
        assert config is not None
        assert config.llm_backend == "ollama"
