"""OnboardingDialog - First-run setup wizard.

Guides the user through:
1. Ollama installation check
2. Embedding model download
3. First collection creation
"""
import logging

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QProgressBar, QStackedWidget, QWidget,
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread
from PyQt6.QtGui import QFont

logger = logging.getLogger(__name__)


class ModelDownloadWorker(QThread):
    """Background worker to load/download embedding model."""

    progress = pyqtSignal(str, int)  # (message, percent)
    finished = pyqtSignal(bool, str)  # (success, message)

    def __init__(self, embedding_service):
        super().__init__()
        self._embedding = embedding_service

    def run(self):
        def on_progress(msg, pct):
            self.progress.emit(msg, pct)

        success = self._embedding.load(progress_callback=on_progress)
        if success:
            self.finished.emit(True, "Embedding model loaded successfully!")
        else:
            self.finished.emit(False, "Failed to load embedding model.")


class OnboardingDialog(QDialog):
    """First-run onboarding wizard.

    Signals:
        onboarding_complete(): All setup steps completed.
    """

    onboarding_complete = pyqtSignal()

    def __init__(self, rag_controller, parent=None):
        super().__init__(parent)
        self._controller = rag_controller
        self._download_worker = None
        self.setWindowTitle("Welcome to Local RAG Memo")
        self.setMinimumSize(500, 350)
        self.setModal(True)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)

        # Title
        title = QLabel("Welcome to Local RAG Memo")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = QFont()
        font.setPointSize(18)
        font.setBold(True)
        title.setFont(font)
        layout.addWidget(title)

        subtitle = QLabel("Let's set up your local AI document assistant")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle)

        # Stacked pages
        self._stack = QStackedWidget()
        self._stack.addWidget(self._create_ollama_page())
        self._stack.addWidget(self._create_embedding_page())
        self._stack.addWidget(self._create_ready_page())
        layout.addWidget(self._stack, stretch=1)

        # Navigation
        nav_layout = QHBoxLayout()
        nav_layout.addStretch()

        self._next_btn = QPushButton("Next")
        self._next_btn.setObjectName("onboardingNext")
        self._next_btn.clicked.connect(self._next_page)
        nav_layout.addWidget(self._next_btn)

        layout.addLayout(nav_layout)

    def _create_ollama_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)

        header = QLabel("Step 1: LLM Backend")
        font = QFont()
        font.setBold(True)
        font.setPointSize(14)
        header.setFont(font)
        layout.addWidget(header)

        info = QLabel(
            "Local RAG Memo uses a Large Language Model to answer your questions.\n\n"
            "Option A (Recommended): Install Ollama for free, local LLM\n"
            "  - Visit https://ollama.ai to download\n"
            "  - Run: ollama pull gemma3:4b\n\n"
            "Option B: Use Claude API (requires API key & internet)\n"
            "  - Configure in Settings after setup"
        )
        info.setWordWrap(True)
        layout.addWidget(info)

        # Ollama status check
        self._ollama_status = QLabel("Checking Ollama...")
        layout.addWidget(self._ollama_status)

        check_btn = QPushButton("Check Ollama")
        check_btn.clicked.connect(self._check_ollama)
        layout.addWidget(check_btn)

        layout.addStretch()

        # Initial check
        self._check_ollama()

        return page

    def _create_embedding_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)

        header = QLabel("Step 2: Embedding Model")
        font = QFont()
        font.setBold(True)
        font.setPointSize(14)
        header.setFont(font)
        layout.addWidget(header)

        info = QLabel(
            "The embedding model converts text to vectors for search.\n"
            "This is a one-time download (~420MB).\n\n"
            "Model: paraphrase-multilingual-MiniLM-L12-v2\n"
            "Supports: Korean, English, and 50+ languages"
        )
        info.setWordWrap(True)
        layout.addWidget(info)

        self._embed_progress = QProgressBar()
        self._embed_progress.setRange(0, 100)
        self._embed_progress.setValue(0)
        layout.addWidget(self._embed_progress)

        self._embed_status = QLabel("Click 'Download' to start")
        layout.addWidget(self._embed_status)

        self._download_btn = QPushButton("Download Embedding Model")
        self._download_btn.clicked.connect(self._start_download)
        layout.addWidget(self._download_btn)

        layout.addStretch()
        return page

    def _create_ready_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)

        header = QLabel("Ready!")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = QFont()
        font.setBold(True)
        font.setPointSize(16)
        header.setFont(font)
        layout.addWidget(header)

        info = QLabel(
            "Setup is complete!\n\n"
            "To get started:\n"
            "1. Drag & drop PDF, Markdown, or text files into the document panel\n"
            "2. Wait for indexing to complete\n"
            "3. Ask questions about your documents\n\n"
            "Tip: Use Cmd+, to open Settings anytime"
        )
        info.setWordWrap(True)
        info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(info)

        layout.addStretch()
        return page

    def _check_ollama(self):
        from app.infrastructure.ollama_client import OllamaClient

        client = OllamaClient()
        if client.is_available():
            models = client.list_models()
            self._ollama_status.setText(
                f"Ollama is running. Available models: {', '.join(models) if models else 'none'}"
            )
            self._ollama_status.setStyleSheet("color: green;")
        else:
            self._ollama_status.setText(
                "Ollama not detected. You can still use Claude API.\n"
                "Install from https://ollama.ai"
            )
            self._ollama_status.setStyleSheet("color: orange;")

    def _start_download(self):
        self._download_btn.setEnabled(False)
        self._embed_status.setText("Downloading...")

        self._download_worker = ModelDownloadWorker(self._controller.embedding_service)
        self._download_worker.progress.connect(self._on_download_progress)
        self._download_worker.finished.connect(self._on_download_finished)
        self._download_worker.start()

    def _on_download_progress(self, message: str, percent: int):
        self._embed_status.setText(message)
        if percent >= 0:
            self._embed_progress.setValue(percent)

    def _on_download_finished(self, success: bool, message: str):
        self._embed_status.setText(message)
        if success:
            self._embed_progress.setValue(100)
            self._embed_status.setStyleSheet("color: green;")
            self._next_btn.setText("Finish")
        else:
            self._embed_status.setStyleSheet("color: red;")
            self._download_btn.setEnabled(True)

    def _next_page(self):
        current = self._stack.currentIndex()
        if current < self._stack.count() - 1:
            self._stack.setCurrentIndex(current + 1)
            if current + 1 == self._stack.count() - 1:
                self._next_btn.setText("Start")
        else:
            self.onboarding_complete.emit()
            self.accept()
