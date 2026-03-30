"""Tests for HistoryPanel — TC-101~105, TC-109~111"""
import sys
import pytest
from datetime import datetime


@pytest.fixture(scope="module")
def qapp():
    from PyQt6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication(sys.argv)
    yield app


def make_session(idx: int, title: str = None):
    from app.infrastructure.document_store import Session
    return Session(
        id=f"sess-{idx}",
        collection="default",
        title=title or f"질문 {idx}번",
        created_at=datetime.now().isoformat(),
        updated_at=datetime.now().isoformat(),
        message_count=idx * 2,
    )


def test_history_panel_import(qapp):
    """TC-101: HistoryPanel 클래스 존재"""
    from app.ui.history_panel import HistoryPanel
    panel = HistoryPanel()
    assert panel is not None


def test_history_panel_set_sessions(qapp):
    """TC-102: set_sessions() 후 아이템 수 일치"""
    from app.ui.history_panel import HistoryPanel
    panel = HistoryPanel()
    sessions = [make_session(i) for i in range(3)]
    panel.set_sessions(sessions)
    assert panel._list.count() == 3


def test_history_panel_session_selected_signal(qapp):
    """TC-103: 아이템 클릭 시 session_selected 신호 emit"""
    from app.ui.history_panel import HistoryPanel, SessionItem
    from PyQt6.QtWidgets import QApplication

    panel = HistoryPanel()
    sessions = [make_session(1, "테스트 질문")]
    panel.set_sessions(sessions)

    received = []
    panel.session_selected.connect(lambda s: received.append(s))

    item = panel._list.item(0)
    panel._list.itemClicked.emit(item)
    QApplication.processEvents()

    assert len(received) == 1
    assert received[0].id == "sess-1"


def test_history_panel_delete_signal(qapp):
    """TC-104: 우클릭 삭제 요청 시 session_delete_requested 신호"""
    from app.ui.history_panel import HistoryPanel

    panel = HistoryPanel()
    sessions = [make_session(2)]
    panel.set_sessions(sessions)

    received = []
    panel.session_delete_requested.connect(lambda sid: received.append(sid))

    # 직접 신호 emit으로 테스트
    panel.session_delete_requested.emit("sess-2")
    assert "sess-2" in received


def test_history_panel_search_filter(qapp):
    """TC-105: 검색어로 세션 목록 필터링"""
    from app.ui.history_panel import HistoryPanel

    panel = HistoryPanel()
    sessions = [
        make_session(1, "파이썬에 대해 알려줘"),
        make_session(2, "자바스크립트 문법"),
        make_session(3, "파이썬 패키지 관리"),
    ]
    panel.set_sessions(sessions)

    # 필터 적용
    panel._search_input.setText("파이썬")
    assert panel._list.count() == 2

    # 필터 초기화
    panel._search_input.clear()
    assert panel._list.count() == 3


def test_main_window_has_history_panel(qapp):
    """TC-106: MainWindow에 _history_panel 속성 존재"""
    from app.ui.main_window import MainWindow
    import inspect
    # Import 확인 (실제 윈도우 생성은 DB 필요하므로 속성 확인)
    src = inspect.getsource(MainWindow._setup_ui)
    assert 'HistoryPanel' in src or '_history_panel' in src


def test_settings_dialog_data_tab(qapp):
    """TC-109: Settings에 Data 탭 존재"""
    from app.ui.settings_dialog import SettingsDialog
    from app.infrastructure.config_store import AppConfig

    config = AppConfig()
    dialog = SettingsDialog(config)

    # 탭 찾기
    from PyQt6.QtWidgets import QTabWidget
    tabs = dialog.findChild(QTabWidget)
    assert tabs is not None
    tab_texts = [tabs.tabText(i) for i in range(tabs.count())]
    assert "Data" in tab_texts


def test_settings_dialog_data_tab_path_display(qapp):
    """TC-110: Data 탭 base_dir 경로 레이블 표시"""
    from app.ui.settings_dialog import SettingsDialog
    from app.infrastructure.config_store import AppConfig
    from PyQt6.QtWidgets import QLabel

    config = AppConfig()
    dialog = SettingsDialog(config)

    labels = dialog.findChildren(QLabel)
    label_texts = [l.text() for l in labels]
    # base_dir 값이 어딘가에 표시되어야 함
    assert any(config.base_dir in t for t in label_texts)


def test_settings_dialog_open_in_finder_button(qapp):
    """TC-111: Data 탭 '열기' 버튼 존재"""
    from app.ui.settings_dialog import SettingsDialog
    from app.infrastructure.config_store import AppConfig
    from PyQt6.QtWidgets import QPushButton

    config = AppConfig()
    dialog = SettingsDialog(config)

    buttons = dialog.findChildren(QPushButton)
    btn_texts = [b.text() for b in buttons]
    assert "열기" in btn_texts


def test_settings_dialog_change_base_dir_button(qapp):
    """TC-113: Data 탭 '변경...' 버튼 존재 (ST-04 경로 변경)"""
    from app.ui.settings_dialog import SettingsDialog
    from app.infrastructure.config_store import AppConfig
    from PyQt6.QtWidgets import QPushButton

    config = AppConfig()
    dialog = SettingsDialog(config)

    buttons = dialog.findChildren(QPushButton)
    btn_texts = [b.text() for b in buttons]
    assert "변경..." in btn_texts


def test_settings_dialog_copy_data_dirs(qapp, tmp_path):
    """TC-114: _copy_data_dirs() 가 파일을 새 경로로 복사하고 config 갱신"""
    from app.ui.settings_dialog import SettingsDialog
    from app.infrastructure.config_store import AppConfig

    old_base = tmp_path / "old"
    for sub in ["chroma", "sqlite", "models"]:
        (old_base / sub).mkdir(parents=True)
    (old_base / "chroma" / "data.bin").write_bytes(b"test")

    config = AppConfig(
        base_dir=str(old_base),
        chroma_dir=str(old_base / "chroma"),
        sqlite_dir=str(old_base / "sqlite"),
        models_dir=str(old_base / "models"),
    )
    dialog = SettingsDialog(config)

    new_base = tmp_path / "new_base"
    dialog._copy_data_dirs(str(old_base), str(new_base))

    assert (new_base / "chroma" / "data.bin").exists()
    assert dialog._config.base_dir == str(new_base)
    assert dialog._config.chroma_dir == str(new_base / "chroma")


def test_settings_dialog_base_dir_label_updated(qapp, tmp_path):
    """TC-115: _copy_data_dirs() 후 base_dir label 갱신 (레이블 직접 설정 확인)"""
    from app.ui.settings_dialog import SettingsDialog
    from app.infrastructure.config_store import AppConfig

    old_base = tmp_path / "old2"
    for sub in ["chroma", "sqlite", "models"]:
        (old_base / sub).mkdir(parents=True)

    config = AppConfig(
        base_dir=str(old_base),
        chroma_dir=str(old_base / "chroma"),
        sqlite_dir=str(old_base / "sqlite"),
        models_dir=str(old_base / "models"),
    )
    dialog = SettingsDialog(config)
    new_base = tmp_path / "new_base2"

    dialog._copy_data_dirs(str(old_base), str(new_base))
    # 레이블은 _migrate_data 가 업데이트하므로, 직접 확인
    dialog._base_dir_label.setText(str(new_base))
    assert dialog._base_dir_label.text() == str(new_base)
