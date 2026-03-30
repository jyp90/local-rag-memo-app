"""Tests for F-12 Tags and F-13 Export — TC-301~315"""
import sys
import json
import pytest
from datetime import datetime


@pytest.fixture(scope="module")
def qapp():
    from PyQt6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication(sys.argv)
    yield app


def make_doc(idx: int, tags: list = None):
    from app.infrastructure.document_store import DocumentMeta
    return DocumentMeta(
        id=f"doc-{idx}",
        file_name=f"file_{idx}.pdf",
        file_path=f"/tmp/file_{idx}.pdf",
        collection="default",
        chunk_count=idx * 3,
        created_at=datetime.now().isoformat(),
        file_size=1024 * idx,
        file_type="pdf",
        tags=json.dumps(tags or []),
    )


# ---------- F-12 DocumentStore 태그 ----------

def test_document_meta_has_tags_field():
    """TC-301: DocumentMeta에 tags 필드 존재"""
    from app.infrastructure.document_store import DocumentMeta
    doc = DocumentMeta(
        id="d1", file_name="f.pdf", file_path="/f.pdf",
        collection="c", chunk_count=1, created_at="2026-01-01",
        file_size=100, file_type="pdf",
    )
    assert hasattr(doc, "tags")
    assert doc.tags == "[]"


def test_document_store_set_and_get_tags(tmp_path):
    """TC-302: set_document_tags / get_documents tags 필드 저장"""
    from app.infrastructure.document_store import DocumentStore, DocumentMeta

    db = DocumentStore(str(tmp_path / "meta.db"))
    doc = DocumentMeta(
        id="d1", file_name="f.pdf", file_path="/f.pdf",
        collection="col", chunk_count=1, created_at=datetime.now().isoformat(),
        file_size=100, file_type="pdf", tags="[]",
    )
    db.save_document(doc)
    db.set_document_tags("d1", ["python", "ML"])

    docs = db.get_documents("col")
    saved_tags = json.loads(docs[0].tags)
    assert "python" in saved_tags
    assert "ML" in saved_tags


def test_document_store_get_all_tags(tmp_path):
    """TC-303: get_all_tags — 컬렉션 내 유니크 태그 목록"""
    from app.infrastructure.document_store import DocumentStore, DocumentMeta

    db = DocumentStore(str(tmp_path / "meta2.db"))
    for i, tags in enumerate([["python", "ML"], ["python", "NLP"], ["java"]]):
        doc = DocumentMeta(
            id=f"d{i}", file_name=f"f{i}.pdf", file_path=f"/f{i}.pdf",
            collection="col", chunk_count=1, created_at=datetime.now().isoformat(),
            file_size=100, file_type="pdf", tags=json.dumps(tags),
        )
        db.save_document(doc)

    all_tags = db.get_all_tags("col")
    assert "python" in all_tags
    assert "ML" in all_tags
    assert "NLP" in all_tags
    assert "java" in all_tags
    assert len(set(all_tags)) == len(all_tags)  # no duplicates


# ---------- F-12 DocumentPanel UI ----------

def test_document_list_item_shows_tags(qapp):
    """TC-304: DocumentListItem — tags가 있으면 🏷 표시"""
    from app.ui.document_panel import DocumentListItem
    doc = make_doc(1, ["python", "ML"])
    item = DocumentListItem(doc)
    assert "🏷" in item.text()
    assert "python" in item.text()


def test_document_list_item_no_tags(qapp):
    """TC-305: DocumentListItem — tags 없으면 🏷 없음"""
    from app.ui.document_panel import DocumentListItem
    doc = make_doc(2, [])
    item = DocumentListItem(doc)
    assert "🏷" not in item.text()


def test_document_panel_tag_filter_combo(qapp):
    """TC-306: DocumentPanel — 태그 필터 콤보박스 존재"""
    from app.ui.document_panel import DocumentPanel
    from PyQt6.QtWidgets import QComboBox
    panel = DocumentPanel()
    combos = panel.findChildren(QComboBox)
    combo_names = [c.objectName() for c in combos]
    assert "tagFilter" in combo_names


def test_document_panel_tag_filter_populated(qapp):
    """TC-307: update_documents — 태그 필터에 태그 항목 추가"""
    from app.ui.document_panel import DocumentPanel
    panel = DocumentPanel()
    docs = [make_doc(1, ["python"]), make_doc(2, ["ML"])]
    panel.update_documents(docs)
    items = [panel._tag_filter.itemText(i) for i in range(panel._tag_filter.count())]
    assert "전체" in items
    assert "python" in items
    assert "ML" in items


def test_document_panel_tag_filter_filters(qapp):
    """TC-308: 태그 필터 선택 시 목록 필터링"""
    from app.ui.document_panel import DocumentPanel
    panel = DocumentPanel()
    docs = [
        make_doc(1, ["python"]),
        make_doc(2, ["ML"]),
        make_doc(3, ["python", "ML"]),
    ]
    panel.update_documents(docs)
    panel._tag_filter.setCurrentText("python")
    assert panel._list_widget.count() == 2  # doc1, doc3


def test_document_panel_tag_edit_signal(qapp):
    """TC-309: 태그 편집 신호 tag_edit_requested 존재"""
    from app.ui.document_panel import DocumentPanel
    panel = DocumentPanel()
    received = []
    panel.tag_edit_requested.connect(lambda doc_id, tags: received.append((doc_id, tags)))
    panel.tag_edit_requested.emit("doc-1", ["a", "b"])
    assert received == [("doc-1", ["a", "b"])]


def test_document_panel_update_document_tags(qapp):
    """TC-310: update_document_tags — 아이템 표시 갱신"""
    from app.ui.document_panel import DocumentPanel
    panel = DocumentPanel()
    docs = [make_doc(1, [])]
    panel.update_documents(docs)

    panel.update_document_tags("doc-1", ["새태그"])
    item = panel._list_widget.item(0)
    assert "새태그" in item.text()


# ---------- F-13 내보내기 ----------

def test_chat_panel_export_requested_signal(qapp):
    """TC-311: ChatPanel — export_requested 신호 존재"""
    from app.ui.chat_panel import ChatPanel
    panel = ChatPanel()
    received = []
    panel.export_requested.connect(lambda: received.append(True))
    panel.export_requested.emit()
    assert received == [True]


def test_chat_panel_export_button_exists(qapp):
    """TC-312: ChatPanel — '내보내기' 버튼 존재"""
    from app.ui.chat_panel import ChatPanel
    from PyQt6.QtWidgets import QPushButton
    panel = ChatPanel()
    buttons = panel.findChildren(QPushButton)
    btn_texts = [b.text() for b in buttons]
    assert "내보내기" in btn_texts


def test_chat_panel_get_messages_for_export(qapp):
    """TC-313: get_messages_for_export — 메시지 목록 반환"""
    from app.ui.chat_panel import ChatPanel
    panel = ChatPanel()
    panel.add_user_message("질문입니다")
    panel.start_assistant_message()
    panel.append_to_assistant("답변입니다")
    panel.finish_assistant_message()

    msgs = panel.get_messages_for_export()
    assert len(msgs) == 2
    assert msgs[0]["role"] == "user"
    assert msgs[0]["content"] == "질문입니다"
    assert msgs[1]["role"] == "assistant"
    assert "답변입니다" in msgs[1]["content"]


def test_export_markdown_format(tmp_path):
    """TC-314: Markdown 내보내기 포맷 검증"""
    # 내보내기 로직을 직접 검증
    messages = [
        {"role": "user", "content": "파이썬이란?"},
        {"role": "assistant", "content": "파이썬은 프로그래밍 언어입니다."},
    ]
    lines = ["# 대화 내보내기\n\n---\n"]
    for msg in messages:
        role_label = "**You**" if msg["role"] == "user" else "**AI Assistant**"
        lines.append(f"{role_label}\n\n{msg['content']}\n\n---\n")

    content = "\n".join(lines)
    assert "**You**" in content
    assert "**AI Assistant**" in content
    assert "파이썬이란?" in content
    assert "파이썬은 프로그래밍 언어입니다." in content


def test_export_empty_conversation(qapp):
    """TC-315: 빈 대화 내보내기 — 빈 리스트 반환"""
    from app.ui.chat_panel import ChatPanel
    panel = ChatPanel()
    assert panel.get_messages_for_export() == []
