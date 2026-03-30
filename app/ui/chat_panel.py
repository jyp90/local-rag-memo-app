"""ChatPanel - Question input and answer display widget.

Handles user question input, streaming answer display,
source references, and conversation flow.
"""
import json
import logging

from markdown_it import MarkdownIt

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit,
    QPushButton, QLabel, QScrollArea, QFrame, QSizePolicy,
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QTextCursor, QKeyEvent

logger = logging.getLogger(__name__)


class MessageBubble(QFrame):
    """A single chat message bubble."""

    source_clicked = pyqtSignal(dict)

    _md = MarkdownIt()

    def __init__(self, role: str, content: str = "", sources: list | None = None, parent=None):
        super().__init__(parent)
        self._role = role
        self._sources = sources or []
        self._raw_text = content  # accumulates streaming tokens
        self._setup_ui(content)

    def _setup_ui(self, content: str):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)

        # Role label
        role_label = QLabel("You" if self._role == "user" else "AI Assistant")
        role_label.setObjectName("chatRoleLabel")
        font = QFont()
        font.setBold(True)
        font.setPointSize(11)
        role_label.setFont(font)
        layout.addWidget(role_label)

        # Content
        self._content_label = QTextEdit()
        self._content_label.setReadOnly(True)
        self._content_label.setFrameStyle(QFrame.Shape.NoFrame)
        self._content_label.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._content_label.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._content_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        # Transparent background so bubble color shows through
        self._content_label.setStyleSheet(
            "QTextEdit { background-color: transparent; border: none; padding: 2px; color: #cdd6f4; }"
        )
        if self._role == "assistant" and content:
            self._content_label.setHtml(self._render_markdown(content))
        else:
            self._content_label.setPlainText(content)
        self._content_label.document().setDocumentMargin(4)
        # Set initial height and schedule re-adjustment after layout
        self._content_label.setMinimumHeight(24)
        self._content_label.textChanged.connect(self._adjust_height)
        QTimer.singleShot(0, self._adjust_height)
        layout.addWidget(self._content_label)

        # Source references
        if self._sources:
            self._add_sources(layout)

        # Styling
        if self._role == "user":
            self.setObjectName("userBubble")
        else:
            self.setObjectName("assistantBubble")

    def _add_sources(self, layout: QVBoxLayout):
        sources_frame = QFrame()
        sources_frame.setObjectName("sourcesFrame")
        sources_layout = QVBoxLayout(sources_frame)
        sources_layout.setContentsMargins(8, 4, 8, 4)

        header = QLabel("Sources:")
        header.setObjectName("sourcesHeader")
        font = QFont()
        font.setPointSize(10)
        font.setBold(True)
        header.setFont(font)
        sources_layout.addWidget(header)

        for src in self._sources:
            source_btn = QPushButton()
            file_name = src.get("file_name", "Unknown")
            page = src.get("page_num")
            section = src.get("section", "")
            score = src.get("score", 0)

            label = f"  {file_name}"
            if page:
                label += f" (p.{page})"
            if section:
                label += f" - {section}"
            label += f"  [{score:.2f}]"

            source_btn.setText(label)
            source_btn.setObjectName("sourceButton")
            source_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            source_btn.clicked.connect(lambda checked, s=src: self.source_clicked.emit(s))
            sources_layout.addWidget(source_btn)

        layout.addWidget(sources_frame)

    def append_text(self, text: str):
        """Append text to the content (for streaming). Plain text during stream."""
        self._raw_text += text
        self._content_label.moveCursor(QTextCursor.MoveOperation.End)
        self._content_label.insertPlainText(text)
        QTimer.singleShot(0, self._adjust_height)

    def finalize_markdown(self):
        """Convert accumulated raw text to rendered Markdown HTML (call after streaming ends)."""
        if self._role != "assistant" or not self._raw_text:
            return
        self._content_label.setHtml(self._render_markdown(self._raw_text))
        QTimer.singleShot(50, self._adjust_height)

    @classmethod
    def _render_markdown(cls, text: str) -> str:
        """Render Markdown text to styled HTML."""
        html_body = cls._md.render(text)
        return (
            "<html><head><style>"
            "body { color: #cdd6f4; font-family: sans-serif; font-size: 14px; margin: 0; padding: 0; }"
            "h1,h2,h3 { color: #89b4fa; margin: 4px 0; }"
            "code { background: #313244; padding: 1px 4px; border-radius: 3px; font-family: monospace; }"
            "pre { background: #313244; padding: 8px; border-radius: 6px; overflow-x: auto; }"
            "pre code { background: transparent; padding: 0; }"
            "ul,ol { margin: 4px 0; padding-left: 20px; }"
            "li { margin: 2px 0; }"
            "blockquote { border-left: 3px solid #6c7086; padding-left: 8px; color: #a6adc8; margin: 4px 0; }"
            "strong { color: #f5c2e7; }"
            "em { color: #a6e3a1; }"
            "p { margin: 4px 0; }"
            "a { color: #89dceb; }"
            "</style></head><body>"
            + html_body
            + "</body></html>"
        )

    def set_sources(self, sources: list):
        """Set sources after streaming completes."""
        self._sources = sources
        if sources:
            self._add_sources(self.layout())

    def _adjust_height(self):
        doc = self._content_label.document()
        viewport_width = self._content_label.viewport().width()
        if viewport_width > 0:
            doc.setTextWidth(viewport_width)
        doc_height = int(doc.size().height())
        height = max(doc_height + 12, 24)
        self._content_label.setMinimumHeight(min(height, 600))
        self._content_label.setMaximumHeight(min(height, 600))


class ChatInput(QWidget):
    """Chat input area with text field and send button."""

    message_sent = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)

        self._input = QTextEdit()
        self._input.setPlaceholderText("Ask a question... (Cmd+Enter to send)")
        self._input.setMaximumHeight(100)
        self._input.setObjectName("chatInput")
        self._input.installEventFilter(self)
        layout.addWidget(self._input)

        btn_layout = QVBoxLayout()
        self._send_btn = QPushButton("Send")
        self._send_btn.setObjectName("sendButton")
        self._send_btn.setFixedWidth(80)
        self._send_btn.clicked.connect(self._on_send)
        btn_layout.addWidget(self._send_btn)

        self._cancel_btn = QPushButton("Cancel")
        self._cancel_btn.setObjectName("cancelButton")
        self._cancel_btn.setFixedWidth(80)
        self._cancel_btn.setVisible(False)
        btn_layout.addWidget(self._cancel_btn)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

    def eventFilter(self, obj, event):
        if obj == self._input and isinstance(event, QKeyEvent):
            if (
                event.key() == Qt.Key.Key_Return
                and event.modifiers() == Qt.KeyboardModifier.MetaModifier
            ):
                self._on_send()
                return True
        return super().eventFilter(obj, event)

    def _on_send(self):
        text = self._input.toPlainText().strip()
        if text:
            self.message_sent.emit(text)
            self._input.clear()

    def set_enabled(self, enabled: bool, show_cancel: bool = True):
        self._input.setEnabled(enabled)
        self._send_btn.setEnabled(enabled)
        if not enabled and show_cancel:
            # Query in-progress: hide Send, show Cancel
            self._send_btn.setVisible(False)
            self._cancel_btn.setVisible(True)
        else:
            # Idle or loading (no cancel): show Send, hide Cancel
            self._send_btn.setVisible(True)
            self._cancel_btn.setVisible(False)

    @property
    def cancel_button(self) -> QPushButton:
        return self._cancel_btn

    def focus_input(self):
        self._input.setFocus()


class ChatPanel(QWidget):
    """Main chat panel combining message display and input.

    Signals:
        question_submitted(str): User submitted a question.
        source_clicked(dict): User clicked a source reference.
    """

    question_submitted = pyqtSignal(str)
    source_clicked = pyqtSignal(dict)
    export_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._messages: list[MessageBubble] = []
        self._current_assistant_bubble: MessageBubble | None = None
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Messages scroll area
        self._scroll_area = QScrollArea()
        self._scroll_area.setWidgetResizable(True)
        self._scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll_area.setObjectName("chatScrollArea")

        self._messages_widget = QWidget()
        self._messages_layout = QVBoxLayout(self._messages_widget)
        self._messages_layout.setContentsMargins(8, 8, 8, 8)
        self._messages_layout.setSpacing(12)
        self._messages_layout.addStretch()

        self._scroll_area.setWidget(self._messages_widget)
        layout.addWidget(self._scroll_area, stretch=1)

        # Empty state
        self._empty_label = QLabel("Start by adding documents, then ask questions about them.")
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_label.setObjectName("emptyStateLabel")
        self._empty_label.setWordWrap(True)
        self._messages_layout.insertWidget(0, self._empty_label)

        # Toolbar (export button)
        toolbar = QHBoxLayout()
        toolbar.setContentsMargins(8, 2, 8, 0)
        toolbar.addStretch()
        self._export_btn = QPushButton("내보내기")
        self._export_btn.setObjectName("exportButton")
        self._export_btn.setFixedHeight(24)
        self._export_btn.setToolTip("대화 내용을 Markdown 또는 텍스트 파일로 저장")
        self._export_btn.clicked.connect(self.export_requested.emit)
        toolbar.addWidget(self._export_btn)
        layout.addLayout(toolbar)

        # Input area
        self._chat_input = ChatInput()
        self._chat_input.message_sent.connect(self._on_message_sent)
        layout.addWidget(self._chat_input)

    def _on_message_sent(self, text: str):
        self._empty_label.hide()
        self.question_submitted.emit(text)

    def add_user_message(self, content: str):
        """Add a user message bubble."""
        self._empty_label.hide()
        bubble = MessageBubble(role="user", content=content)
        self._messages.append(bubble)
        # Insert before the stretch
        self._messages_layout.insertWidget(
            self._messages_layout.count() - 1, bubble
        )
        self._scroll_to_bottom()

    def start_assistant_message(self) -> MessageBubble:
        """Start a new assistant message bubble for streaming."""
        bubble = MessageBubble(role="assistant")
        self._current_assistant_bubble = bubble
        self._messages.append(bubble)
        self._messages_layout.insertWidget(
            self._messages_layout.count() - 1, bubble
        )
        self._scroll_to_bottom()
        return bubble

    def append_to_assistant(self, token: str):
        """Append a token to the current assistant bubble."""
        if self._current_assistant_bubble:
            self._current_assistant_bubble.append_text(token)
            self._scroll_to_bottom()

    def finish_assistant_message(self, sources: list | None = None):
        """Finalize the current assistant message with Markdown rendering."""
        if self._current_assistant_bubble:
            self._current_assistant_bubble.finalize_markdown()
            if sources:
                self._current_assistant_bubble.set_sources(sources)
                self._current_assistant_bubble.source_clicked.connect(
                    self.source_clicked.emit
                )
        self._current_assistant_bubble = None

    def set_input_enabled(self, enabled: bool, show_cancel: bool = True):
        """Enable/disable chat input. show_cancel=False hides Cancel (e.g. during model loading)."""
        self._chat_input.set_enabled(enabled, show_cancel=show_cancel)

    @property
    def cancel_button(self) -> QPushButton:
        return self._chat_input.cancel_button

    def clear_messages(self):
        """Clear all messages."""
        for bubble in self._messages:
            bubble.deleteLater()
        self._messages.clear()
        self._current_assistant_bubble = None
        self._empty_label.show()

    def focus_input(self):
        self._chat_input.focus_input()

    def _scroll_to_bottom(self):
        scrollbar = self._scroll_area.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def get_messages_for_export(self) -> list[dict]:
        """Return raw message data for export (role + raw_text)."""
        result = []
        for bubble in self._messages:
            result.append({
                "role": bubble._role,
                "content": bubble._raw_text,
            })
        return result

    def load_history(self, messages: list[dict]):
        """Load conversation history into the panel."""
        self.clear_messages()
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            sources_json = msg.get("sources", "[]")

            try:
                sources = json.loads(sources_json) if isinstance(sources_json, str) else sources_json
            except (json.JSONDecodeError, TypeError):
                sources = []

            bubble = MessageBubble(role=role, content=content, sources=sources if role == "assistant" else None)
            if role == "assistant" and sources:
                bubble.source_clicked.connect(self.source_clicked.emit)

            self._messages.append(bubble)
            self._messages_layout.insertWidget(
                self._messages_layout.count() - 1, bubble
            )

        if messages:
            self._empty_label.hide()
        self._scroll_to_bottom()
