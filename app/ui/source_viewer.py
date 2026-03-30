"""SourceViewer - Document source preview dialog.

Shows the original text around a referenced chunk
with the chunk text highlighted.
"""
import logging

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QTextEdit, QPushButton, QHBoxLayout,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QTextCharFormat, QColor, QTextCursor

logger = logging.getLogger(__name__)


class SourceViewer(QDialog):
    """Dialog to display source document text with chunk highlight."""

    def __init__(
        self,
        file_name: str,
        page_num: int | None,
        section: str,
        text_preview: str,
        score: float,
        parent=None,
    ):
        super().__init__(parent)
        self.setWindowTitle(f"Source: {file_name}")
        self.setMinimumSize(600, 400)
        self._setup_ui(file_name, page_num, section, text_preview, score)

    def _setup_ui(
        self,
        file_name: str,
        page_num: int | None,
        section: str,
        text_preview: str,
        score: float,
    ):
        layout = QVBoxLayout(self)

        # Header info
        info_parts = [f"File: {file_name}"]
        if page_num:
            info_parts.append(f"Page: {page_num}")
        if section:
            info_parts.append(f"Section: {section}")
        info_parts.append(f"Relevance: {score:.3f}")

        info_label = QLabel(" | ".join(info_parts))
        info_label.setObjectName("sourceInfoLabel")
        font = QFont()
        font.setBold(True)
        info_label.setFont(font)
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

        # Text content
        self._text_edit = QTextEdit()
        self._text_edit.setReadOnly(True)
        self._text_edit.setObjectName("sourceTextEdit")
        self._text_edit.setPlainText(text_preview)

        # Highlight the chunk text
        self._highlight_text(text_preview)

        layout.addWidget(self._text_edit, stretch=1)

        # Close button
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.close)
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)

    def _highlight_text(self, text: str):
        """Apply highlight formatting to the entire text (it's the chunk itself)."""
        cursor = self._text_edit.textCursor()
        cursor.select(QTextCursor.SelectionType.Document)

        fmt = QTextCharFormat()
        fmt.setBackground(QColor(255, 255, 150, 80))  # Soft yellow highlight
        cursor.mergeCharFormat(fmt)

        self._text_edit.setTextCursor(cursor)
        cursor.clearSelection()
        self._text_edit.setTextCursor(cursor)
