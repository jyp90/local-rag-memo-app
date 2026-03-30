"""CollectionPanel - Collection management widget.

Provides collection creation, switching, and deletion UI.
"""
import logging

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QComboBox, QPushButton, QInputDialog, QMessageBox,
)
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QFont

logger = logging.getLogger(__name__)


class CollectionPanel(QWidget):
    """Collection management toolbar.

    Signals:
        collection_changed(str): Active collection changed.
        collection_created(str): New collection created.
        collection_deleted(str): Collection deleted.
    """

    collection_changed = pyqtSignal(str)
    collection_created = pyqtSignal(str)
    collection_deleted = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)

        label = QLabel("Collection:")
        label.setObjectName("collectionLabel")
        font = QFont()
        font.setBold(True)
        label.setFont(font)
        layout.addWidget(label)

        self._combo = QComboBox()
        self._combo.setObjectName("collectionCombo")
        self._combo.setMinimumWidth(200)
        self._combo.currentTextChanged.connect(self._on_collection_changed)
        layout.addWidget(self._combo, stretch=1)

        self._new_btn = QPushButton("+ New")
        self._new_btn.setObjectName("newCollectionButton")
        self._new_btn.clicked.connect(self._on_new_collection)
        layout.addWidget(self._new_btn)

        self._delete_btn = QPushButton("Delete")
        self._delete_btn.setObjectName("deleteCollectionButton")
        self._delete_btn.clicked.connect(self._on_delete_collection)
        layout.addWidget(self._delete_btn)

    def set_collections(self, names: list[str], active: str = ""):
        """Update the collection list.

        Args:
            names: List of collection names.
            active: Currently active collection.
        """
        self._combo.blockSignals(True)
        self._combo.clear()
        self._combo.addItems(names)
        if active and active in names:
            self._combo.setCurrentText(active)
        self._combo.blockSignals(False)

        # Disable delete if only one collection
        self._delete_btn.setEnabled(len(names) > 1)

    def current_collection(self) -> str:
        return self._combo.currentText()

    def _on_collection_changed(self, name: str):
        if name:
            self.collection_changed.emit(name)

    def _on_new_collection(self):
        name, ok = QInputDialog.getText(
            self,
            "New Collection",
            "Collection name:",
        )
        if ok and name.strip():
            name = name.strip()
            # Check for duplicates
            existing = [self._combo.itemText(i) for i in range(self._combo.count())]
            if name in existing:
                QMessageBox.warning(self, "Duplicate", f"Collection '{name}' already exists.")
                return
            self.collection_created.emit(name)

    def _on_delete_collection(self):
        name = self._combo.currentText()
        if not name:
            return

        if self._combo.count() <= 1:
            QMessageBox.warning(
                self, "Cannot Delete",
                "Cannot delete the last remaining collection.",
            )
            return

        # Require typing the collection name to confirm
        confirm, ok = QInputDialog.getText(
            self,
            "Delete Collection",
            f"Type '{name}' to confirm deletion.\n"
            "This will delete ALL documents and data in this collection.",
        )
        if ok and confirm == name:
            self.collection_deleted.emit(name)
        elif ok:
            QMessageBox.warning(
                self, "Mismatch",
                "Collection name did not match. Deletion cancelled.",
            )
