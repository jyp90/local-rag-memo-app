"""DocumentPanel - Document list and drag-and-drop indexing widget.

Displays documents in the current collection and accepts
file drops for indexing.
"""
import logging
import os

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QListWidget, QListWidgetItem, QFileDialog,
    QMessageBox, QMenu,
)
from PyQt6.QtCore import Qt, pyqtSignal, QMimeData
from PyQt6.QtGui import QFont, QDragEnterEvent, QDropEvent, QAction

from app.domain.document_processor import SUPPORTED_EXTENSIONS

logger = logging.getLogger(__name__)


class DocumentListItem(QListWidgetItem):
    """Custom list item for documents with metadata."""

    def __init__(self, doc_meta):
        self.doc_meta = doc_meta
        display = f"{doc_meta.file_name}"
        size_kb = doc_meta.file_size / 1024
        if size_kb > 1024:
            size_str = f"{size_kb / 1024:.1f} MB"
        else:
            size_str = f"{size_kb:.0f} KB"
        display += f"\n  {size_str} | {doc_meta.chunk_count} chunks | {doc_meta.file_type.upper()}"
        super().__init__(display)
        self.setToolTip(doc_meta.file_path)


class DocumentPanel(QWidget):
    """Document list panel with drag-and-drop support.

    Signals:
        files_dropped(list[str]): Files dropped for indexing.
        document_delete_requested(str): doc_id to delete.
        add_files_clicked(): User clicked the add button.
    """

    files_dropped = pyqtSignal(list)
    document_delete_requested = pyqtSignal(str)
    add_files_clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        # Header
        header_layout = QHBoxLayout()
        title = QLabel("Documents")
        title.setObjectName("panelTitle")
        font = QFont()
        font.setBold(True)
        font.setPointSize(13)
        title.setFont(font)
        header_layout.addWidget(title)
        header_layout.addStretch()

        self._count_label = QLabel("0 docs")
        self._count_label.setObjectName("docCountLabel")
        header_layout.addWidget(self._count_label)

        layout.addLayout(header_layout)

        # Document list
        self._list_widget = QListWidget()
        self._list_widget.setObjectName("documentList")
        self._list_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._list_widget.customContextMenuRequested.connect(self._show_context_menu)
        self._list_widget.setAlternatingRowColors(True)
        self._list_widget.setSpacing(2)
        layout.addWidget(self._list_widget, stretch=1)

        # Drop zone hint
        self._drop_hint = QLabel("Drag & drop files here\n(.pdf, .md, .txt)")
        self._drop_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._drop_hint.setObjectName("dropHint")
        self._drop_hint.setMinimumHeight(60)
        layout.addWidget(self._drop_hint)

        # Add button
        btn_layout = QHBoxLayout()
        self._add_btn = QPushButton("+ Add Files")
        self._add_btn.setObjectName("addFilesButton")
        self._add_btn.clicked.connect(self._on_add_files)
        btn_layout.addWidget(self._add_btn)

        self._delete_btn = QPushButton("Delete")
        self._delete_btn.setObjectName("deleteButton")
        self._delete_btn.clicked.connect(self._on_delete)
        self._delete_btn.setEnabled(False)
        btn_layout.addWidget(self._delete_btn)

        layout.addLayout(btn_layout)

        # Selection change
        self._list_widget.itemSelectionChanged.connect(
            lambda: self._delete_btn.setEnabled(
                len(self._list_widget.selectedItems()) > 0
            )
        )

    def update_documents(self, documents: list):
        """Refresh the document list.

        Args:
            documents: List of DocumentMeta objects.
        """
        self._list_widget.clear()
        for doc in documents:
            item = DocumentListItem(doc)
            self._list_widget.addItem(item)
        self._count_label.setText(f"{len(documents)} docs")
        self._delete_btn.setEnabled(False)

    def _on_add_files(self):
        """Open file dialog for adding documents."""
        extensions = " ".join(f"*{ext}" for ext in SUPPORTED_EXTENSIONS)
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Select Documents",
            "",
            f"Documents ({extensions});;PDF (*.pdf);;Markdown (*.md);;Text (*.txt);;All Files (*)",
        )
        if files:
            self.files_dropped.emit(files)

    def _on_delete(self):
        """Handle delete button click."""
        items = self._list_widget.selectedItems()
        if not items:
            return

        item = items[0]
        if isinstance(item, DocumentListItem):
            reply = QMessageBox.question(
                self,
                "Delete Document",
                f"Delete '{item.doc_meta.file_name}' from collection?\n"
                "This will remove the document and all its indexed data.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.document_delete_requested.emit(item.doc_meta.id)

    def _show_context_menu(self, position):
        """Show right-click context menu."""
        item = self._list_widget.itemAt(position)
        if not item or not isinstance(item, DocumentListItem):
            return

        menu = QMenu(self)
        delete_action = QAction("Delete", self)
        delete_action.triggered.connect(lambda: self.document_delete_requested.emit(item.doc_meta.id))
        menu.addAction(delete_action)

        info_action = QAction("Info", self)
        info_action.triggered.connect(lambda: self._show_info(item.doc_meta))
        menu.addAction(info_action)

        menu.exec(self._list_widget.mapToGlobal(position))

    def _show_info(self, doc_meta):
        QMessageBox.information(
            self,
            "Document Info",
            f"Name: {doc_meta.file_name}\n"
            f"Path: {doc_meta.file_path}\n"
            f"Type: {doc_meta.file_type.upper()}\n"
            f"Size: {doc_meta.file_size / 1024:.1f} KB\n"
            f"Chunks: {doc_meta.chunk_count}\n"
            f"Indexed: {doc_meta.created_at}",
        )

    # --- Drag and Drop ---

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self._drop_hint.setStyleSheet("border: 2px dashed #4a9eff; background: rgba(74, 158, 255, 0.1);")
        else:
            event.ignore()

    def dragLeaveEvent(self, event):
        self._drop_hint.setStyleSheet("")

    def dropEvent(self, event: QDropEvent):
        self._drop_hint.setStyleSheet("")
        urls = event.mimeData().urls()
        files = []

        for url in urls:
            path = url.toLocalFile()
            if os.path.isfile(path):
                ext = os.path.splitext(path)[1].lower()
                if ext in SUPPORTED_EXTENSIONS:
                    files.append(path)
            elif os.path.isdir(path):
                # Recursively collect supported files from folder
                for root, _, filenames in os.walk(path):
                    for fname in filenames:
                        fpath = os.path.join(root, fname)
                        ext = os.path.splitext(fname)[1].lower()
                        if ext in SUPPORTED_EXTENSIONS:
                            files.append(fpath)

        if files:
            self.files_dropped.emit(files)
        else:
            QMessageBox.warning(
                self,
                "Unsupported Files",
                f"No supported files found.\nSupported: {', '.join(SUPPORTED_EXTENSIONS)}",
            )

        event.acceptProposedAction()
