"""MenuBarApp - macOS 메뉴바 상주 및 시스템 트레이 아이콘 (F-10).

앱을 닫아도 메뉴바에 상주하며 언제든 빠르게 열 수 있음.
QSystemTrayIcon 기반 구현 (PyQt6 통합, rumps 불필요).
"""
import logging

from PyQt6.QtWidgets import QSystemTrayIcon, QMenu, QApplication
from PyQt6.QtGui import QIcon, QPixmap, QColor, QPainter
from PyQt6.QtCore import Qt, pyqtSignal, QObject

logger = logging.getLogger(__name__)


def _make_tray_icon() -> QIcon:
    """Create a simple colored circle icon for the tray."""
    px = QPixmap(22, 22)
    px.fill(Qt.GlobalColor.transparent)
    painter = QPainter(px)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setBrush(QColor("#89b4fa"))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawEllipse(2, 2, 18, 18)
    painter.end()
    return QIcon(px)


class MenuBarApp(QSystemTrayIcon):
    """macOS 메뉴바 상주 아이콘 및 빠른 접근 메뉴.

    MainWindow를 닫으면 숨기고 트레이에 상주.
    트레이 아이콘 클릭 또는 '열기' 메뉴로 복원.

    Signals:
        show_window(): 창을 보여달라는 요청.
        quit_app(): 완전 종료 요청.
    """

    show_window = pyqtSignal()
    quit_app = pyqtSignal()

    def __init__(self, parent=None):
        icon = _make_tray_icon()
        super().__init__(icon, parent)
        self.setToolTip("Local RAG Memo")
        self._build_menu()
        self.activated.connect(self._on_activated)

    def _build_menu(self):
        menu = QMenu()

        open_action = menu.addAction("📂 Local RAG Memo 열기")
        open_action.triggered.connect(self.show_window.emit)

        menu.addSeparator()

        quit_action = menu.addAction("종료")
        quit_action.triggered.connect(self.quit_app.emit)

        self.setContextMenu(menu)

    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason):
        if reason in (
            QSystemTrayIcon.ActivationReason.Trigger,
            QSystemTrayIcon.ActivationReason.DoubleClick,
        ):
            self.show_window.emit()

    def update_status(self, text: str):
        """Update tooltip with current app status."""
        self.setToolTip(f"Local RAG Memo — {text}")
