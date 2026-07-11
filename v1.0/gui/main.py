from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication, QStyleFactory

from gui.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    available_styles = {str(name).lower(): str(name) for name in QStyleFactory.keys()}
    for preferred in ("windows11", "windowsvista", "windows"):
        style_name = available_styles.get(preferred)
        if style_name:
            app.setStyle(style_name)
            break
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
