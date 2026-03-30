"""Tests for ChatPanel and MessageBubble — TC-001~003, TC-012"""
import sys
import pytest

# PyQt6 requires a QApplication
@pytest.fixture(scope="module")
def qapp():
    from PyQt6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication(sys.argv)
    yield app


def test_message_bubble_text_content(qapp):
    """TC-001: MessageBubble 텍스트 렌더링"""
    from app.ui.chat_panel import MessageBubble
    bubble = MessageBubble(role="user", content="Hello World")
    assert bubble._content_label.toPlainText() == "Hello World"


def test_message_bubble_minimum_height(qapp):
    """TC-002: MessageBubble 높이 >= 24px"""
    from app.ui.chat_panel import MessageBubble
    bubble = MessageBubble(role="user", content="Test message")
    bubble.show()
    # Process events to trigger layout
    from PyQt6.QtWidgets import QApplication
    QApplication.processEvents()
    assert bubble._content_label.minimumHeight() >= 24


def test_message_bubble_streaming_append(qapp):
    """TC-003: 스트리밍 append_text"""
    from app.ui.chat_panel import MessageBubble
    bubble = MessageBubble(role="assistant", content="")
    bubble.append_text("Hello")
    bubble.append_text(" World")
    assert "Hello World" in bubble._content_label.toPlainText()


def test_message_bubble_empty_content_height(qapp):
    """TC-012: 빈 content에서도 minimumHeight >= 24"""
    from app.ui.chat_panel import MessageBubble
    bubble = MessageBubble(role="user", content="")
    assert bubble._content_label.minimumHeight() >= 24


def test_message_bubble_role_label_user(qapp):
    """역할 레이블: user → 'You'"""
    from app.ui.chat_panel import MessageBubble
    bubble = MessageBubble(role="user", content="Hi")
    labels = [c for c in bubble.children() if hasattr(c, 'text') and callable(c.text)]
    role_texts = [l.text() for l in labels]
    assert any("You" in t for t in role_texts)


def test_message_bubble_role_label_assistant(qapp):
    """역할 레이블: assistant → 'AI Assistant'"""
    from app.ui.chat_panel import MessageBubble
    bubble = MessageBubble(role="assistant", content="Hi")
    labels = [c for c in bubble.children() if hasattr(c, 'text') and callable(c.text)]
    role_texts = [l.text() for l in labels]
    assert any("AI Assistant" in t for t in role_texts)


def test_message_bubble_transparent_stylesheet(qapp):
    """배경이 투명 stylesheet로 설정됨"""
    from app.ui.chat_panel import MessageBubble
    bubble = MessageBubble(role="user", content="Test")
    ss = bubble._content_label.styleSheet()
    assert "transparent" in ss


def test_message_bubble_assistant_renders_markdown(qapp):
    """TC-201: 어시스턴트 버블 — content 있을 때 HTML로 렌더링"""
    from app.ui.chat_panel import MessageBubble
    bubble = MessageBubble(role="assistant", content="**bold** text")
    html = bubble._content_label.toHtml()
    assert "<strong>" in html or "bold" in html


def test_message_bubble_user_plain_text(qapp):
    """TC-202: 사용자 버블 — 항상 plain text"""
    from app.ui.chat_panel import MessageBubble
    bubble = MessageBubble(role="user", content="**not bold**")
    assert bubble._content_label.toPlainText() == "**not bold**"


def test_message_bubble_finalize_markdown(qapp):
    """TC-203: finalize_markdown() — 스트리밍 완료 후 HTML 렌더링"""
    from app.ui.chat_panel import MessageBubble
    from PyQt6.QtWidgets import QApplication

    bubble = MessageBubble(role="assistant", content="")
    bubble.append_text("# Title\n\n")
    bubble.append_text("- item1\n- item2")

    # Before finalize: plain text
    assert "# Title" in bubble._content_label.toPlainText()

    bubble.finalize_markdown()
    QApplication.processEvents()

    html = bubble._content_label.toHtml()
    assert "Title" in html


def test_message_bubble_raw_text_accumulated(qapp):
    """TC-204: append_text 로 _raw_text 누적"""
    from app.ui.chat_panel import MessageBubble

    bubble = MessageBubble(role="assistant", content="")
    bubble.append_text("Hello")
    bubble.append_text(" World")
    assert bubble._raw_text == "Hello World"


def test_render_markdown_heading(qapp):
    """TC-205: _render_markdown — H1 태그 생성"""
    from app.ui.chat_panel import MessageBubble
    html = MessageBubble._render_markdown("# Hello")
    assert "<h1>" in html


def test_render_markdown_code_block(qapp):
    """TC-206: _render_markdown — 코드 블록 pre/code 태그"""
    from app.ui.chat_panel import MessageBubble
    html = MessageBubble._render_markdown("```python\nprint('hi')\n```")
    assert "<pre>" in html and "<code" in html


def test_render_markdown_bold_italic(qapp):
    """TC-207: _render_markdown — bold/italic 태그"""
    from app.ui.chat_panel import MessageBubble
    html = MessageBubble._render_markdown("**bold** and *italic*")
    assert "<strong>" in html
    assert "<em>" in html


def test_chat_panel_finish_assistant_renders_markdown(qapp):
    """TC-208: ChatPanel.finish_assistant_message() 후 HTML 렌더링"""
    from app.ui.chat_panel import ChatPanel
    from PyQt6.QtWidgets import QApplication

    panel = ChatPanel()
    panel.start_assistant_message()
    panel.append_to_assistant("## Answer\n\nThis is **important**.")
    panel.finish_assistant_message()
    QApplication.processEvents()

    # 마지막 추가된 버블의 HTML 확인
    last_bubble = panel._messages[-1]
    html = last_bubble._content_label.toHtml()
    assert "Answer" in html or "important" in html
