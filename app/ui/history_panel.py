"""HistoryPanel - Chat session history list and search.

Displays past sessions for the active collection.
Allows clicking to reload a session and searching messages.
Implements CH-02 (history view) and CH-03 (history search).
"""
import logging
from datetime import datetime

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QLabel, QLineEdit, QPushButton, QFrame, QSizePolicy,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

from app.infrastructure.document_store import Session

logger = logging.getLogger(__name__)


class SessionItem(QListWidgetItem):
    """List item representing a chat session."""

    def __init__(self, session: Session):
        super().__init__()
        self._session = session
        self._update_display()

    def _update_display(self):
        title = self._session.title or "새 대화"
        # Truncate long titles
        if len(title) > 40:
            title = title[:38] + "..."
        try:
            dt = datetime.fromisoformat(self._session.updated_at)
            date_str = dt.strftime("%m/%d %H:%M")
        except (ValueError, TypeError):
            date_str = ""

        count = self._session.message_count
        display = f"{title}\n{date_str}  •  {count}개 메시지"
        self.setText(display)
        self.setToolTip(f"ID: {self._session.id}\n{self._session.title}")

    @property
    def session(self) -> Session:
        return self._session


class HistoryPanel(QWidget):
    """Left-panel widget showing past chat sessions.

    Signals:
        session_selected(Session): User clicked a session to load.
        session_delete_requested(str): User requested deletion of session_id.
    """

    session_selected = pyqtSignal(object)       # Session
    session_delete_requested = pyqtSignal(str)  # session_id

    def __init__(self, parent=None):
        super().__init__(parent)
        self._sessions: list[Session] = []
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        # Header
        header = QLabel("대화 기록")
        header.setObjectName("panelHeader")
        font = QFont()
        font.setBold(True)
        font.setPointSize(12)
        header.setFont(font)
        layout.addWidget(header)

        # Search bar (CH-03)
        search_row = QHBoxLayout()
        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText("기록 검색...")
        self._search_input.setObjectName("historySearchInput")
        self._search_input.textChanged.connect(self._on_search_changed)
        search_row.addWidget(self._search_input)

        clear_btn = QPushButton("×")
        clear_btn.setFixedWidth(28)
        clear_btn.setObjectName("clearSearchButton")
        clear_btn.clicked.connect(self._search_input.clear)
        search_row.addWidget(clear_btn)
        layout.addLayout(search_row)

        # Session list
        self._list = QListWidget()
        self._list.setObjectName("historyList")
        self._list.setSpacing(2)
        self._list.itemClicked.connect(self._on_item_clicked)
        self._list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._list.customContextMenuRequested.connect(self._on_context_menu)
        layout.addWidget(self._list, stretch=1)

        # Empty state label
        self._empty_label = QLabel("아직 대화 기록이 없습니다.\n질문을 시작하면 여기에 저장됩니다.")
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_label.setWordWrap(True)
        self._empty_label.setObjectName("emptyStateLabel")
        self._empty_label.hide()
        layout.addWidget(self._empty_label)

    def set_sessions(self, sessions: list[Session]):
        """Update session list (call when collection changes or new session added)."""
        self._sessions = sessions
        self._apply_filter(self._search_input.text())

    def _apply_filter(self, keyword: str):
        self._list.clear()
        keyword_lower = keyword.strip().lower()

        filtered = [
            s for s in self._sessions
            if not keyword_lower or keyword_lower in (s.title or "").lower()
        ]

        for session in filtered:
            item = SessionItem(session)
            self._list.addItem(item)

        has_items = self._list.count() > 0
        self._list.setVisible(has_items)
        self._empty_label.setVisible(not has_items and not self._sessions)

    def _on_search_changed(self, text: str):
        self._apply_filter(text)

    def _on_item_clicked(self, item: QListWidgetItem):
        if isinstance(item, SessionItem):
            self.session_selected.emit(item.session)

    def _on_context_menu(self, pos):
        from PyQt6.QtWidgets import QMenu
        item = self._list.itemAt(pos)
        if not isinstance(item, SessionItem):
            return

        menu = QMenu(self)
        delete_action = menu.addAction("삭제")
        action = menu.exec(self._list.mapToGlobal(pos))
        if action == delete_action:
            self.session_delete_requested.emit(item.session.id)

    def highlight_session(self, session_id: str):
        """Highlight the currently active session in the list."""
        for i in range(self._list.count()):
            item = self._list.item(i)
            if isinstance(item, SessionItem):
                item.setSelected(item.session.id == session_id)
