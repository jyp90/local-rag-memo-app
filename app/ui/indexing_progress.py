"""IndexingProgressDialog - Document indexing progress display.

Shows progress bar, current file, and chunk processing status
during background indexing.
"""
import logging

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QProgressBar,
    QPushButton, QHBoxLayout,
)
from PyQt6.QtCore import Qt

logger = logging.getLogger(__name__)


class IndexingProgressDialog(QDialog):
    """Modal progress dialog for document indexing."""

    def __init__(self, file_count: int, parent=None):
        super().__init__(parent)
        self._file_count = file_count
        self._cancelled = False
        self.setWindowTitle("Indexing Documents")
        self.setMinimumWidth(450)
        self.setModal(True)
        self.setWindowFlags(
            self.windowFlags() & ~Qt.WindowType.WindowCloseButtonHint
        )
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # Status message
        self._status_label = QLabel(f"Preparing to index {self._file_count} files...")
        self._status_label.setObjectName("indexingStatus")
        self._status_label.setWordWrap(True)
        layout.addWidget(self._status_label)

        # Main progress bar
        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(0)
        self._progress_bar.setTextVisible(True)
        layout.addWidget(self._progress_bar)

        # Chunk progress
        self._chunk_label = QLabel("")
        self._chunk_label.setObjectName("chunkProgress")
        layout.addWidget(self._chunk_label)

        # File completion log
        self._log_label = QLabel("")
        self._log_label.setObjectName("indexingLog")
        self._log_label.setWordWrap(True)
        self._log_label.setMaximumHeight(80)
        layout.addWidget(self._log_label)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self._cancel_btn = QPushButton("Cancel")
        self._cancel_btn.clicked.connect(self._on_cancel)
        btn_layout.addWidget(self._cancel_btn)

        self._close_btn = QPushButton("Close")
        self._close_btn.clicked.connect(self.accept)
        self._close_btn.setVisible(False)
        btn_layout.addWidget(self._close_btn)

        layout.addLayout(btn_layout)

    def update_progress(self, percent: int, message: str):
        """Update progress bar and status message."""
        self._progress_bar.setValue(percent)
        self._status_label.setText(message)

    def update_chunk_progress(self, done: int, total: int):
        """Update chunk-level progress."""
        self._chunk_label.setText(f"Embedding: {done}/{total} chunks")

    def file_completed(self, file_name: str, chunk_count: int):
        """Log a completed file."""
        current = self._log_label.text()
        line = f"  {file_name}: {chunk_count} chunks"
        if current:
            self._log_label.setText(f"{current}\n{line}")
        else:
            self._log_label.setText(line)

    def on_finished(self, success: bool, message: str):
        """Called when indexing completes."""
        self._status_label.setText(message)
        self._progress_bar.setValue(100)
        self._cancel_btn.setVisible(False)
        self._close_btn.setVisible(True)

    def on_error(self, error_message: str):
        """Display an error."""
        current = self._log_label.text()
        self._log_label.setText(f"{current}\n  ERROR: {error_message}")

    def _on_cancel(self):
        """Handle cancel request."""
        self._cancelled = True
        self._status_label.setText("Cancelling...")
        self._cancel_btn.setEnabled(False)

    @property
    def is_cancelled(self) -> bool:
        return self._cancelled
