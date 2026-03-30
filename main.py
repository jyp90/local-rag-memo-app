"""Local RAG Memo - Entry Point"""
import sys
import os

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt


def main():
    """Application entry point."""
    # High DPI support
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"

    app = QApplication(sys.argv)
    app.setApplicationName("Local RAG Memo")
    app.setOrganizationName("LocalRAGMemo")

    # Load stylesheet
    style_path = os.path.join(os.path.dirname(__file__), "resources", "styles", "dark_theme.qss")
    if os.path.exists(style_path):
        with open(style_path, "r") as f:
            app.setStyleSheet(f.read())

    from app.ui.main_window import MainWindow

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
