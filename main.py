"""Local RAG Memo - Entry Point"""
import sys
import os

from PyQt6.QtWidgets import QApplication, QSystemTrayIcon
from PyQt6.QtCore import Qt


def main():
    """Application entry point."""
    # High DPI support
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"

    app = QApplication(sys.argv)
    app.setApplicationName("Local RAG Memo")
    app.setOrganizationName("LocalRAGMemo")
    # Keep app alive when window is hidden (tray mode)
    app.setQuitOnLastWindowClosed(False)

    # Load stylesheet
    style_path = os.path.join(os.path.dirname(__file__), "resources", "styles", "dark_theme.qss")
    if os.path.exists(style_path):
        with open(style_path, "r") as f:
            app.setStyleSheet(f.read())

    from app.ui.main_window import MainWindow
    from app.ui.menu_bar_app import MenuBarApp

    window = MainWindow()

    # F-10: System tray / menu bar integration
    if QSystemTrayIcon.isSystemTrayAvailable():
        tray = MenuBarApp()
        tray.show()
        tray.show_window.connect(lambda: (window.show(), window.raise_(), window.activateWindow()))
        tray.quit_app.connect(app.quit)
        # Close → hide to tray instead of quitting
        window.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, False)
        window.closeEvent = lambda event: (event.ignore(), window.hide(),
                                           tray.showMessage("Local RAG Memo", "메뉴바에서 다시 열 수 있습니다.",
                                                            QSystemTrayIcon.MessageIcon.Information, 2000))

    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
