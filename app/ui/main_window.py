"""MainWindow - Primary application window.

Orchestrates all UI panels and connects them to the RagController.
Layout: Left sidebar (documents) | Right main area (chat).
Top toolbar: Collection selector + settings.
"""
import json
import logging
import os

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QSplitter, QStatusBar, QLabel, QMessageBox,
    QToolBar, QPushButton,
)
from PyQt6.QtCore import Qt, QSize, QThread, pyqtSignal
from PyQt6.QtGui import QAction, QKeySequence

from app.controller.rag_controller import RagController
from app.infrastructure.config_store import ConfigStore
from app.ui.chat_panel import ChatPanel
from app.ui.document_panel import DocumentPanel
from app.ui.collection_panel import CollectionPanel
from app.ui.history_panel import HistoryPanel
from app.ui.settings_dialog import SettingsDialog
from app.ui.indexing_progress import IndexingProgressDialog
from app.ui.source_viewer import SourceViewer
from app.ui.onboarding_dialog import OnboardingDialog

logger = logging.getLogger(__name__)


class EmbeddingLoadWorker(QThread):
    """Background worker to load embedding model on startup."""
    progress = pyqtSignal(str)   # status message
    finished = pyqtSignal(bool)  # success

    def __init__(self, controller):
        super().__init__()
        self._controller = controller

    def run(self):
        success = self._controller.load_embedding_model()
        self.finished.emit(success)


class MainWindow(QMainWindow):
    """Main application window."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Local RAG Memo")
        self.setMinimumSize(900, 600)

        # Initialize controller
        self._controller = RagController()

        # Setup UI
        self._setup_ui()
        self._setup_menubar()
        self._setup_statusbar()
        self._connect_signals()

        # Restore window size
        config = self._controller.config
        self.resize(config.window_width, config.window_height)

        # Load initial data
        self._refresh_collections()
        self._refresh_documents()
        self._refresh_history()

        # Load embedding model in background — disable input until ready
        self._embedding_worker = None
        if not self._controller.is_embedding_loaded():
            self._chat_panel.set_input_enabled(False, show_cancel=False)
            self._start_embedding_load()
        else:
            self._chat_panel.set_input_enabled(True)

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Collection toolbar
        self._collection_panel = CollectionPanel()
        main_layout.addWidget(self._collection_panel)

        # Main splitter: left sidebar | chat panel
        self._splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left sidebar: document panel (top) + history panel (bottom)
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(0)

        self._left_splitter = QSplitter(Qt.Orientation.Vertical)

        self._document_panel = DocumentPanel()
        self._document_panel.setMinimumWidth(200)
        self._left_splitter.addWidget(self._document_panel)

        self._history_panel = HistoryPanel()
        self._left_splitter.addWidget(self._history_panel)

        self._left_splitter.setSizes([350, 250])
        self._left_splitter.setStretchFactor(0, 1)
        self._left_splitter.setStretchFactor(1, 0)

        left_layout.addWidget(self._left_splitter)
        left_widget.setMinimumWidth(200)
        left_widget.setMaximumWidth(400)
        self._splitter.addWidget(left_widget)

        self._chat_panel = ChatPanel()
        self._splitter.addWidget(self._chat_panel)

        self._splitter.setSizes([280, 720])
        self._splitter.setStretchFactor(0, 0)
        self._splitter.setStretchFactor(1, 1)

        main_layout.addWidget(self._splitter, stretch=1)

    def _setup_menubar(self):
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu("File")

        add_action = QAction("Add Documents...", self)
        add_action.setShortcut(QKeySequence("Ctrl+O"))
        add_action.triggered.connect(self._document_panel._on_add_files)
        file_menu.addAction(add_action)

        new_session_action = QAction("New Session", self)
        new_session_action.setShortcut(QKeySequence("Ctrl+K"))
        new_session_action.triggered.connect(self._new_session)
        file_menu.addAction(new_session_action)

        file_menu.addSeparator()

        settings_action = QAction("Settings...", self)
        settings_action.setShortcut(QKeySequence("Ctrl+,"))
        settings_action.triggered.connect(self._show_settings)
        file_menu.addAction(settings_action)

        # View menu
        view_menu = menubar.addMenu("View")

        toggle_docs = QAction("Toggle Document Panel", self)
        toggle_docs.setShortcut(QKeySequence("Ctrl+B"))
        toggle_docs.triggered.connect(
            lambda: self._document_panel.setVisible(not self._document_panel.isVisible())
        )
        view_menu.addAction(toggle_docs)

    def _setup_statusbar(self):
        self._status_bar = QStatusBar()
        self.setStatusBar(self._status_bar)

        self._llm_status_label = QLabel("")
        self._status_bar.addPermanentWidget(self._llm_status_label)

        self._update_llm_status()

    def _connect_signals(self):
        # Document panel
        self._document_panel.files_dropped.connect(self._on_files_dropped)
        self._document_panel.document_delete_requested.connect(self._on_delete_document)

        # Chat panel
        self._chat_panel.question_submitted.connect(self._on_question)
        self._chat_panel.source_clicked.connect(self._on_source_clicked)

        # Collection panel
        self._collection_panel.collection_changed.connect(self._on_collection_changed)
        self._collection_panel.collection_created.connect(self._on_create_collection)
        self._collection_panel.collection_deleted.connect(self._on_delete_collection)

        # History panel
        self._history_panel.session_selected.connect(self._on_history_session_selected)
        self._history_panel.session_delete_requested.connect(self._on_delete_session)

    # --- Event Handlers ---

    def _on_files_dropped(self, files: list[str]):
        """Handle files dropped or selected for indexing."""
        if not self._controller.is_embedding_loaded():
            QMessageBox.warning(
                self, "Model Not Loaded",
                "Embedding model is not loaded. Please complete the setup first.",
            )
            self._show_onboarding()
            return

        if self._controller.is_indexing():
            QMessageBox.warning(
                self, "Indexing in Progress",
                "Please wait for the current indexing to complete.",
            )
            return

        # Check for duplicates
        collection = self._controller.active_collection
        new_files = []
        for f in files:
            fname = os.path.basename(f)
            existing = self._controller.find_duplicate(fname, collection)
            if existing:
                reply = QMessageBox.question(
                    self, "Duplicate Document",
                    f"'{fname}' already exists in this collection.\nRe-index it?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                )
                if reply == QMessageBox.StandardButton.Yes:
                    self._controller.delete_document(existing.id, collection)
                    new_files.append(f)
            else:
                new_files.append(f)

        if not new_files:
            return

        # Start indexing with progress dialog
        progress = IndexingProgressDialog(len(new_files), self)

        worker = self._controller.start_indexing(new_files)
        worker.progress.connect(progress.update_progress)
        worker.chunk_done.connect(progress.update_chunk_progress)
        worker.file_done.connect(progress.file_completed)
        worker.finished.connect(progress.on_finished)
        worker.error.connect(progress.on_error)
        worker.finished.connect(lambda s, m: self._refresh_documents())

        # Cancel button
        progress._cancel_btn.clicked.connect(worker.cancel)

        progress.exec()

    def _on_delete_document(self, doc_id: str):
        """Handle document deletion."""
        if self._controller.delete_document(doc_id):
            self._refresh_documents()
            self._status_bar.showMessage("Document deleted", 3000)
        else:
            QMessageBox.warning(self, "Error", "Failed to delete document.")

    def _on_question(self, question: str):
        """Handle user question submission."""
        if not self._controller.is_embedding_loaded():
            QMessageBox.warning(
                self, "Model Not Loaded",
                "Embedding model is not loaded.",
            )
            return

        # Check if collection has documents
        doc_count = self._controller.get_document_count()
        if doc_count == 0:
            self._chat_panel.add_user_message(question)
            from app.ui.chat_panel import MessageBubble
            bubble = self._chat_panel.start_assistant_message()
            self._chat_panel.append_to_assistant(
                "This collection has no documents yet. "
                "Please add documents first by dragging files into the document panel."
            )
            self._chat_panel.finish_assistant_message()
            return

        # Ensure we have an active session
        session = self._controller.conversation.current_session
        if not session:
            session = self._controller.conversation.new_session(
                self._controller.active_collection
            )

        # Save user message
        self._controller.conversation.save_user_message(question)

        # Update UI
        self._chat_panel.add_user_message(question)
        self._chat_panel.set_input_enabled(False)
        self._chat_panel.start_assistant_message()

        # Start query
        self._sources = []
        worker = self._controller.start_query(
            question=question,
            session_id=session.id,
        )
        worker.token_received.connect(self._chat_panel.append_to_assistant)
        worker.sources_ready.connect(self._on_sources_ready)
        worker.finished.connect(self._on_query_finished)
        worker.error.connect(self._on_query_error)

        # Cancel support
        self._chat_panel.cancel_button.clicked.connect(worker.cancel)

    def _on_sources_ready(self, sources: list):
        """Store sources for later use."""
        self._sources = sources

    def _on_query_finished(self):
        """Handle query completion."""
        self._chat_panel.finish_assistant_message(self._sources)
        self._chat_panel.set_input_enabled(True)
        self._chat_panel.focus_input()

        # Save assistant message
        if hasattr(self, '_sources') and self._controller.conversation.current_session:
            worker = self._controller._query_worker
            if worker:
                self._controller.conversation.save_assistant_message(
                    content=worker.full_answer,
                    sources=self._sources,
                )
        # Refresh history panel to show updated session
        self._refresh_history()

    def _on_query_error(self, error: str):
        """Handle query error."""
        self._chat_panel.append_to_assistant(f"\n\n[Error: {error}]")
        self._chat_panel.finish_assistant_message()
        self._chat_panel.set_input_enabled(True)
        self._status_bar.showMessage(f"Query error: {error}", 5000)

    def _on_source_clicked(self, source: dict):
        """Show source viewer dialog."""
        viewer = SourceViewer(
            file_name=source.get("file_name", "Unknown"),
            page_num=source.get("page_num"),
            section=source.get("section", ""),
            text_preview=source.get("text_preview", ""),
            score=source.get("score", 0),
            parent=self,
        )
        viewer.exec()

    def _on_history_session_selected(self, session):
        """Load a past session into the chat panel."""
        self._controller.conversation.set_current_session(session)
        messages = self._controller.document_store.get_messages(session.id)
        msg_dicts = [
            {"role": m.role, "content": m.content, "sources": m.sources}
            for m in messages
        ]
        self._chat_panel.load_history(msg_dicts)
        self._history_panel.highlight_session(session.id)
        self._status_bar.showMessage(f"대화 기록 로드: {session.title or '새 대화'}", 3000)

    def _on_delete_session(self, session_id: str):
        """Handle session deletion from history panel."""
        if self._controller.conversation.delete_session(session_id):
            self._refresh_history()
            self._status_bar.showMessage("대화 기록 삭제됨", 3000)
        else:
            QMessageBox.warning(self, "Error", "Failed to delete session.")

    def _on_collection_changed(self, name: str):
        """Handle collection switch."""
        self._controller.switch_collection(name)
        self._refresh_documents()
        self._refresh_history()
        self._chat_panel.clear_messages()
        self._controller.conversation._current_session = None
        self._status_bar.showMessage(f"Switched to collection: {name}", 3000)

    def _on_create_collection(self, name: str):
        """Handle new collection creation."""
        if self._controller.create_collection(name):
            self._refresh_collections()
            self._controller.switch_collection(name)
            self._collection_panel.set_collections(
                self._controller.list_collections(),
                active=name,
            )
            self._refresh_documents()
            self._refresh_history()
            self._chat_panel.clear_messages()
            self._status_bar.showMessage(f"Collection '{name}' created", 3000)
        else:
            QMessageBox.warning(self, "Error", f"Failed to create collection '{name}'.")

    def _on_delete_collection(self, name: str):
        """Handle collection deletion."""
        if self._controller.delete_collection(name):
            self._refresh_collections()
            self._refresh_documents()
            self._refresh_history()
            self._chat_panel.clear_messages()
            self._status_bar.showMessage(f"Collection '{name}' deleted", 3000)
        else:
            QMessageBox.warning(self, "Error", f"Failed to delete collection '{name}'.")

    # --- Settings ---

    def _show_settings(self):
        dialog = SettingsDialog(self._controller.config, self)
        dialog.settings_changed.connect(self._on_settings_changed)
        dialog.exec()

    def _on_settings_changed(self, changes: dict):
        """Apply settings changes."""
        # Capture old values before updating
        old_backend = self._controller.config.llm_backend
        old_embedding = self._controller.config.embedding_model

        # LLM backend switch
        new_backend = changes.get("llm_backend", old_backend)
        if new_backend != old_backend:
            self._controller.switch_llm_backend(new_backend)

        # Ollama settings
        self._controller.update_ollama_settings(
            host=changes.get("ollama_host"),
            model=changes.get("ollama_model"),
        )

        # Claude settings
        self._controller.update_claude_settings(
            model=changes.get("claude_model"),
        )

        # Other config updates
        self._controller.update_config(
            embedding_model=changes.get("embedding_model", old_embedding),
            default_chunk_size=changes.get("default_chunk_size", self._controller.config.default_chunk_size),
            default_chunk_overlap=changes.get("default_chunk_overlap", self._controller.config.default_chunk_overlap),
            default_top_k=changes.get("default_top_k", self._controller.config.default_top_k),
            theme=changes.get("theme", self._controller.config.theme),
            font_size=changes.get("font_size", self._controller.config.font_size),
            language=changes.get("language", self._controller.config.language),
        )

        # Reload embedding model if changed
        new_embedding = changes.get("embedding_model")
        if new_embedding and new_embedding != old_embedding:
            self._controller.reload_embedding_model(new_embedding)
            self._start_embedding_load()

        self._update_llm_status()
        self._status_bar.showMessage("Settings saved", 3000)

    # --- Embedding Load ---

    def _start_embedding_load(self):
        """Load embedding model in background thread on startup."""
        self._chat_panel.set_input_enabled(False, show_cancel=False)
        self._status_bar.showMessage("Loading embedding model... (please wait)", 0)
        self._embedding_worker = EmbeddingLoadWorker(self._controller)
        self._embedding_worker.finished.connect(self._on_embedding_load_done)
        self._embedding_worker.start()

    def _on_embedding_load_done(self, success: bool):
        if success:
            self._chat_panel.set_input_enabled(True)
            self._status_bar.showMessage("Embedding model ready. You can now ask questions.", 4000)
        else:
            self._status_bar.showMessage(
                "Failed to load embedding model. Open Settings → Embedding to fix.", 0
            )

    # --- Onboarding ---

    def _show_onboarding(self):
        dialog = OnboardingDialog(self._controller, self)
        dialog.onboarding_complete.connect(self._on_onboarding_complete)
        dialog.exec()

    def _on_onboarding_complete(self):
        self._update_llm_status()
        self._status_bar.showMessage("Setup complete! Add documents to get started.", 5000)

    # --- Session Management ---

    def _new_session(self):
        """Create a new chat session."""
        self._chat_panel.clear_messages()
        self._controller.conversation.new_session(self._controller.active_collection)
        self._chat_panel.focus_input()
        self._status_bar.showMessage("New session started", 3000)

    # --- Refresh Helpers ---

    def _refresh_collections(self):
        collections = self._controller.list_collections()
        self._collection_panel.set_collections(
            collections,
            active=self._controller.active_collection,
        )

    def _refresh_documents(self):
        docs = self._controller.get_collection_documents()
        self._document_panel.update_documents(docs)

    def _refresh_history(self):
        sessions = self._controller.conversation.get_sessions(
            self._controller.active_collection
        )
        self._history_panel.set_sessions(sessions)

    def _update_llm_status(self):
        available, message = self._controller.check_llm_status()
        self._llm_status_label.setText(message)
        if available:
            self._llm_status_label.setStyleSheet("color: green;")
        else:
            self._llm_status_label.setStyleSheet("color: orange;")

    # --- Window Events ---

    def closeEvent(self, event):
        """Save window state on close."""
        self._controller.update_config(
            window_width=self.width(),
            window_height=self.height(),
        )
        event.accept()
