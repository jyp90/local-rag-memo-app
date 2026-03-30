"""Tests for F-10 MenuBarApp — TC-401~407"""
import sys
import pytest


@pytest.fixture(scope="module")
def qapp():
    from PyQt6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication(sys.argv)
    yield app


def test_menu_bar_app_import(qapp):
    """TC-401: MenuBarApp 클래스 존재"""
    from app.ui.menu_bar_app import MenuBarApp
    assert MenuBarApp is not None


def test_menu_bar_app_is_system_tray_icon(qapp):
    """TC-402: MenuBarApp은 QSystemTrayIcon 서브클래스"""
    from app.ui.menu_bar_app import MenuBarApp
    from PyQt6.QtWidgets import QSystemTrayIcon
    assert issubclass(MenuBarApp, QSystemTrayIcon)


def test_menu_bar_app_has_signals(qapp):
    """TC-403: show_window, quit_app 신호 존재"""
    from app.ui.menu_bar_app import MenuBarApp
    app = MenuBarApp()
    assert hasattr(app, "show_window")
    assert hasattr(app, "quit_app")


def test_menu_bar_app_show_window_signal(qapp):
    """TC-404: show_window 신호 emit 확인"""
    from app.ui.menu_bar_app import MenuBarApp
    tray = MenuBarApp()
    received = []
    tray.show_window.connect(lambda: received.append(True))
    tray.show_window.emit()
    assert received == [True]


def test_menu_bar_app_quit_signal(qapp):
    """TC-405: quit_app 신호 emit 확인"""
    from app.ui.menu_bar_app import MenuBarApp
    tray = MenuBarApp()
    received = []
    tray.quit_app.connect(lambda: received.append(True))
    tray.quit_app.emit()
    assert received == [True]


def test_menu_bar_app_context_menu(qapp):
    """TC-406: context menu에 '열기', '종료' 항목 포함"""
    from app.ui.menu_bar_app import MenuBarApp
    tray = MenuBarApp()
    menu = tray.contextMenu()
    assert menu is not None
    actions = [a.text() for a in menu.actions() if a.text()]
    assert any("열기" in t for t in actions)
    assert any("종료" in t for t in actions)


def test_menu_bar_app_update_status(qapp):
    """TC-407: update_status — tooltip 갱신"""
    from app.ui.menu_bar_app import MenuBarApp
    tray = MenuBarApp()
    tray.update_status("Ollama 연결됨")
    assert "Ollama 연결됨" in tray.toolTip()
