"""SettingsDialog - Application settings configuration.

Manages LLM backend settings, embedding model selection,
and UI preferences. Claude API key stored in macOS Keychain.
"""
import logging

import os

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget,
    QLabel, QLineEdit, QComboBox, QPushButton, QSpinBox,
    QFormLayout, QGroupBox, QMessageBox, QRadioButton,
    QButtonGroup, QFileDialog, QProgressDialog,
)
from PyQt6.QtCore import pyqtSignal

from app.infrastructure.config_store import AppConfig

logger = logging.getLogger(__name__)


class SettingsDialog(QDialog):
    """Application settings dialog.

    Signals:
        settings_changed(dict): Emitted when settings are saved.
    """

    settings_changed = pyqtSignal(dict)

    def __init__(self, config: AppConfig, parent=None):
        super().__init__(parent)
        self._config = config
        self.setWindowTitle("Settings")
        self.setMinimumSize(550, 450)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        tabs = QTabWidget()
        tabs.addTab(self._create_llm_tab(), "LLM")
        tabs.addTab(self._create_embedding_tab(), "Embedding")
        tabs.addTab(self._create_ui_tab(), "UI")
        tabs.addTab(self._create_data_tab(), "Data")
        layout.addWidget(tabs)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        save_btn = QPushButton("Save")
        save_btn.setObjectName("saveButton")
        save_btn.clicked.connect(self._on_save)
        btn_layout.addWidget(save_btn)

        layout.addLayout(btn_layout)

    def _create_llm_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Backend selection
        backend_group = QGroupBox("LLM Backend")
        backend_layout = QVBoxLayout(backend_group)

        self._backend_group = QButtonGroup()
        self._ollama_radio = QRadioButton("Ollama (Local)")
        self._claude_radio = QRadioButton("Claude API")
        self._backend_group.addButton(self._ollama_radio)
        self._backend_group.addButton(self._claude_radio)

        if self._config.llm_backend == "claude":
            self._claude_radio.setChecked(True)
        else:
            self._ollama_radio.setChecked(True)

        backend_layout.addWidget(self._ollama_radio)
        backend_layout.addWidget(self._claude_radio)
        layout.addWidget(backend_group)

        # Ollama settings
        ollama_group = QGroupBox("Ollama Settings")
        ollama_layout = QFormLayout(ollama_group)

        self._ollama_host = QLineEdit(self._config.ollama_host)
        self._ollama_host.setPlaceholderText("http://localhost:11434")
        ollama_layout.addRow("Host:", self._ollama_host)

        self._ollama_model = QComboBox()
        self._ollama_model.setEditable(True)
        self._ollama_model.addItems([
            "gemma3:4b", "llama3.2:3b", "qwen2.5:7b", "exaone3.5:7.8b",
        ])
        self._ollama_model.setCurrentText(self._config.ollama_model)
        ollama_layout.addRow("Model:", self._ollama_model)

        self._ollama_test_btn = QPushButton("Test Connection")
        self._ollama_test_btn.clicked.connect(self._test_ollama)
        ollama_layout.addRow("", self._ollama_test_btn)

        self._ollama_status = QLabel("")
        ollama_layout.addRow("Status:", self._ollama_status)

        layout.addWidget(ollama_group)

        # Claude settings
        claude_group = QGroupBox("Claude API Settings")
        claude_layout = QFormLayout(claude_group)

        self._claude_key = QLineEdit()
        self._claude_key.setEchoMode(QLineEdit.EchoMode.Password)
        self._claude_key.setPlaceholderText("sk-ant-... (stored in macOS Keychain)")
        claude_layout.addRow("API Key:", self._claude_key)

        key_btn_layout = QHBoxLayout()
        self._save_key_btn = QPushButton("Save Key")
        self._save_key_btn.clicked.connect(self._save_api_key)
        key_btn_layout.addWidget(self._save_key_btn)

        self._delete_key_btn = QPushButton("Delete Key")
        self._delete_key_btn.clicked.connect(self._delete_api_key)
        key_btn_layout.addWidget(self._delete_key_btn)
        claude_layout.addRow("", key_btn_layout)

        self._claude_model = QComboBox()
        self._claude_model.addItems([
            "claude-sonnet-4-20250514",
            "claude-haiku-35-20241022",
            "claude-opus-4-20250514",
        ])
        self._claude_model.setCurrentText(self._config.claude_model)
        claude_layout.addRow("Model:", self._claude_model)

        self._claude_status = QLabel("")
        claude_layout.addRow("Status:", self._claude_status)

        layout.addWidget(claude_group)
        layout.addStretch()

        return widget

    def _create_embedding_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        group = QGroupBox("Embedding Model")
        form = QFormLayout(group)

        self._embedding_model = QComboBox()
        self._embedding_model.addItems([
            "paraphrase-multilingual-MiniLM-L12-v2",
            "all-MiniLM-L6-v2",
            "jhgan/ko-sroberta-multitask",
        ])
        self._embedding_model.setCurrentText(self._config.embedding_model)
        form.addRow("Model:", self._embedding_model)

        warning = QLabel(
            "Warning: Changing the embedding model requires\n"
            "re-indexing all documents in all collections."
        )
        warning.setStyleSheet("color: orange;")
        form.addRow("", warning)

        layout.addWidget(group)

        # RAG defaults
        rag_group = QGroupBox("RAG Defaults")
        rag_form = QFormLayout(rag_group)

        self._chunk_size = QSpinBox()
        self._chunk_size.setRange(200, 2000)
        self._chunk_size.setValue(self._config.default_chunk_size)
        self._chunk_size.setSuffix(" chars")
        rag_form.addRow("Chunk Size:", self._chunk_size)

        self._chunk_overlap = QSpinBox()
        self._chunk_overlap.setRange(0, 200)
        self._chunk_overlap.setValue(self._config.default_chunk_overlap)
        self._chunk_overlap.setSuffix(" chars")
        rag_form.addRow("Chunk Overlap:", self._chunk_overlap)

        self._top_k = QSpinBox()
        self._top_k.setRange(1, 10)
        self._top_k.setValue(self._config.default_top_k)
        rag_form.addRow("Top-K Results:", self._top_k)

        layout.addWidget(rag_group)
        layout.addStretch()

        return widget

    def _create_ui_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        group = QGroupBox("Appearance")
        form = QFormLayout(group)

        self._theme = QComboBox()
        self._theme.addItems(["dark", "light"])
        self._theme.setCurrentText(self._config.theme)
        form.addRow("Theme:", self._theme)

        self._font_size = QSpinBox()
        self._font_size.setRange(10, 24)
        self._font_size.setValue(self._config.font_size)
        self._font_size.setSuffix(" pt")
        form.addRow("Font Size:", self._font_size)

        self._language = QComboBox()
        self._language.addItems(["ko", "en"])
        self._language.setCurrentText(self._config.language)
        form.addRow("Language:", self._language)

        layout.addWidget(group)
        layout.addStretch()

        return widget

    def _create_data_tab(self) -> QWidget:
        """ST-04: Data storage path settings with change + migration."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Base directory (changeable)
        base_group = QGroupBox("기본 데이터 디렉토리")
        base_layout = QVBoxLayout(base_group)

        base_row = QHBoxLayout()
        self._base_dir_label = QLabel(self._config.base_dir)
        self._base_dir_label.setObjectName("pathLabel")
        self._base_dir_label.setWordWrap(True)
        base_row.addWidget(self._base_dir_label, stretch=1)

        open_base_btn = QPushButton("열기")
        open_base_btn.setFixedWidth(50)
        open_base_btn.clicked.connect(
            lambda: self._open_in_finder(self._base_dir_label.text())
        )
        base_row.addWidget(open_base_btn)

        change_btn = QPushButton("변경...")
        change_btn.setFixedWidth(60)
        change_btn.setObjectName("changeBaseDirButton")
        change_btn.clicked.connect(self._change_base_dir)
        base_row.addWidget(change_btn)
        base_layout.addLayout(base_row)

        warning_label = QLabel(
            "⚠ 변경 시 기존 데이터를 새 위치로 복사합니다. 앱 재시작이 필요합니다."
        )
        warning_label.setStyleSheet("color: orange; font-size: 11px;")
        warning_label.setWordWrap(True)
        base_layout.addWidget(warning_label)
        layout.addWidget(base_group)

        # Sub-directories (read-only, derived from base_dir)
        sub_group = QGroupBox("하위 데이터 경로")
        form = QFormLayout(sub_group)
        form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)

        sub_paths = [
            ("벡터 DB (ChromaDB)", self._config.chroma_dir, "chromaDirLabel"),
            ("메타데이터 (SQLite)", self._config.sqlite_dir, "sqliteDirLabel"),
            ("임베딩 모델 캐시", self._config.models_dir, "modelsDirLabel"),
        ]

        self._sub_dir_labels = {}
        for label_text, path_value, obj_name in sub_paths:
            row_widget = QWidget()
            row_layout = QHBoxLayout(row_widget)
            row_layout.setContentsMargins(0, 0, 0, 0)

            path_label = QLabel(path_value)
            path_label.setObjectName(obj_name)
            path_label.setWordWrap(True)
            row_layout.addWidget(path_label, stretch=1)
            self._sub_dir_labels[obj_name] = path_label

            open_btn = QPushButton("열기")
            open_btn.setFixedWidth(50)
            open_btn.clicked.connect(
                lambda checked, p=path_value: self._open_in_finder(p)
            )
            row_layout.addWidget(open_btn)
            form.addRow(label_text + ":", row_widget)

        layout.addWidget(sub_group)

        # Disk usage
        usage_group = QGroupBox("디스크 사용량")
        usage_layout = QVBoxLayout(usage_group)
        self._usage_label = QLabel("계산 중...")
        usage_layout.addWidget(self._usage_label)

        refresh_btn = QPushButton("새로고침")
        refresh_btn.clicked.connect(self._update_disk_usage)
        usage_layout.addWidget(refresh_btn)
        layout.addWidget(usage_group)

        layout.addStretch()
        self._update_disk_usage()
        return widget

    def _change_base_dir(self):
        """ST-04: Change base data directory with migration."""
        new_dir = QFileDialog.getExistingDirectory(
            self,
            "새 데이터 디렉토리 선택",
            os.path.expanduser("~"),
            QFileDialog.Option.ShowDirsOnly,
        )
        if not new_dir:
            return

        old_dir = os.path.expanduser(self._config.base_dir)
        if os.path.abspath(new_dir) == os.path.abspath(old_dir):
            QMessageBox.information(self, "알림", "현재와 동일한 경로입니다.")
            return

        # Check if new dir already has data
        new_base = os.path.join(new_dir, ".local-rag-memo")
        if os.path.exists(new_base):
            reply = QMessageBox.question(
                self,
                "디렉토리 확인",
                f"{new_base}\n\n위 경로에 이미 데이터가 존재합니다.\n덮어쓰시겠습니까?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

        reply = QMessageBox.question(
            self,
            "데이터 이전 확인",
            f"기존 데이터를 다음 위치로 복사합니다:\n\n"
            f"  이전: {old_dir}\n"
            f"  이후: {new_base}\n\n"
            f"진행하시겠습니까?\n(기존 데이터는 삭제되지 않습니다)",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        self._migrate_data(old_dir, new_base)

    def _copy_data_dirs(self, old_base: str, new_base: str):
        """Copy chroma/sqlite/models subdirs and update config fields. No UI calls."""
        import shutil, json, dataclasses

        os.makedirs(new_base, exist_ok=True)
        for sub in ["chroma", "sqlite", "models"]:
            src = os.path.join(old_base, sub)
            dst = os.path.join(new_base, sub)
            if os.path.exists(src):
                if os.path.exists(dst):
                    shutil.rmtree(dst)
                shutil.copytree(src, dst)
            else:
                os.makedirs(dst, exist_ok=True)

        self._config.base_dir = new_base
        self._config.chroma_dir = os.path.join(new_base, "chroma")
        self._config.sqlite_dir = os.path.join(new_base, "sqlite")
        self._config.models_dir = os.path.join(new_base, "models")

        old_cfg = os.path.join(old_base, "config.json")
        if os.path.exists(old_cfg):
            with open(os.path.join(new_base, "config.json"), "w") as f:
                json.dump(dataclasses.asdict(self._config), f, indent=2)

    def _migrate_data(self, old_base: str, new_base: str):
        """Copy data directories to new location and update config."""
        from PyQt6.QtWidgets import QApplication

        progress = QProgressDialog("데이터 이전 중...", None, 0, 0, self)
        progress.setWindowTitle("데이터 이전")
        progress.setMinimumDuration(0)
        progress.setValue(0)
        progress.show()
        QApplication.processEvents()

        try:
            self._copy_data_dirs(old_base, new_base)

            self._base_dir_label.setText(new_base)
            self._update_disk_usage()

            progress.close()
            QMessageBox.information(
                self,
                "이전 완료",
                f"데이터가 복사되었습니다:\n{new_base}\n\n"
                f"앱을 재시작하면 새 경로가 적용됩니다.\n"
                f"기존 데이터: {old_base}",
            )
            self.settings_changed.emit({
                "base_dir": new_base,
                "chroma_dir": self._config.chroma_dir,
                "sqlite_dir": self._config.sqlite_dir,
                "models_dir": self._config.models_dir,
            })

        except Exception as e:
            progress.close()
            logger.exception("Data migration failed")
            QMessageBox.critical(
                self, "이전 실패", f"데이터 이전 중 오류가 발생했습니다:\n{e}"
            )

    def _open_in_finder(self, path: str):
        """Open path in Finder."""
        import subprocess
        expanded = os.path.expanduser(path)
        if os.path.exists(expanded):
            subprocess.run(["open", expanded])
        else:
            QMessageBox.information(self, "경로 없음", f"경로가 존재하지 않습니다:\n{path}")

    def _update_disk_usage(self):
        """Calculate and display disk usage."""
        import shutil
        base = os.path.expanduser(self._config.base_dir)
        if not os.path.exists(base):
            self._usage_label.setText("데이터 없음")
            return

        total = 0
        for dirpath, _, filenames in os.walk(base):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                try:
                    total += os.path.getsize(fp)
                except OSError:
                    pass

        def fmt(b):
            if b < 1024:
                return f"{b} B"
            if b < 1024 ** 2:
                return f"{b/1024:.1f} KB"
            if b < 1024 ** 3:
                return f"{b/1024**2:.1f} MB"
            return f"{b/1024**3:.2f} GB"

        disk = shutil.disk_usage(base)
        self._usage_label.setText(
            f"앱 데이터: {fmt(total)}\n"
            f"디스크 여유 공간: {fmt(disk.free)}"
        )

    def _test_ollama(self):
        """Test Ollama connection."""
        from app.infrastructure.ollama_client import OllamaClient

        host = self._ollama_host.text().strip()
        client = OllamaClient(host=host)

        if client.is_available():
            models = client.list_models()
            self._ollama_status.setText(f"Connected. Models: {len(models)}")
            self._ollama_status.setStyleSheet("color: green;")
            # Update model combo
            if models:
                current = self._ollama_model.currentText()
                self._ollama_model.clear()
                self._ollama_model.addItems(models)
                if current in models:
                    self._ollama_model.setCurrentText(current)
        else:
            self._ollama_status.setText("Connection failed")
            self._ollama_status.setStyleSheet("color: red;")

    def _save_api_key(self):
        """Save Claude API key to Keychain."""
        key = self._claude_key.text().strip()
        if not key:
            QMessageBox.warning(self, "Empty Key", "Please enter an API key.")
            return

        from app.infrastructure.claude_client import ClaudeClient

        if ClaudeClient.save_api_key(key):
            self._claude_status.setText("API key saved to Keychain")
            self._claude_status.setStyleSheet("color: green;")
            self._claude_key.clear()
        else:
            self._claude_status.setText("Failed to save key")
            self._claude_status.setStyleSheet("color: red;")

    def _delete_api_key(self):
        """Delete Claude API key from Keychain."""
        from app.infrastructure.claude_client import ClaudeClient

        reply = QMessageBox.question(
            self, "Delete Key",
            "Delete Claude API key from Keychain?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            if ClaudeClient.delete_api_key():
                self._claude_status.setText("API key deleted")
                self._claude_status.setStyleSheet("color: orange;")
            else:
                self._claude_status.setText("Failed to delete key")
                self._claude_status.setStyleSheet("color: red;")

    def _on_save(self):
        """Save all settings and emit signal."""
        changes = {
            "llm_backend": "claude" if self._claude_radio.isChecked() else "ollama",
            "ollama_host": self._ollama_host.text().strip(),
            "ollama_model": self._ollama_model.currentText(),
            "claude_model": self._claude_model.currentText(),
            "embedding_model": self._embedding_model.currentText(),
            "default_chunk_size": self._chunk_size.value(),
            "default_chunk_overlap": self._chunk_overlap.value(),
            "default_top_k": self._top_k.value(),
            "theme": self._theme.currentText(),
            "font_size": self._font_size.value(),
            "language": self._language.currentText(),
        }
        self.settings_changed.emit(changes)
        self.accept()
