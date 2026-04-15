from __future__ import annotations

from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication


def apply_fixed_light_theme(app: QApplication) -> None:
    app.setStyle("Fusion")

    palette = QPalette()
    palette.setColor(QPalette.Window, QColor("#f4f1e8"))
    palette.setColor(QPalette.WindowText, QColor("#2f2a22"))
    palette.setColor(QPalette.Base, QColor("#fffdf8"))
    palette.setColor(QPalette.AlternateBase, QColor("#f7f2e7"))
    palette.setColor(QPalette.ToolTipBase, QColor("#fffdf8"))
    palette.setColor(QPalette.ToolTipText, QColor("#2f2a22"))
    palette.setColor(QPalette.Text, QColor("#2f2a22"))
    palette.setColor(QPalette.Button, QColor("#efe8da"))
    palette.setColor(QPalette.ButtonText, QColor("#2f2a22"))
    palette.setColor(QPalette.BrightText, QColor("#ffffff"))
    palette.setColor(QPalette.Highlight, QColor("#d6b36d"))
    palette.setColor(QPalette.HighlightedText, QColor("#1f1a14"))
    palette.setColor(QPalette.PlaceholderText, QColor("#7d7468"))
    palette.setColor(QPalette.Light, QColor("#ffffff"))
    palette.setColor(QPalette.Midlight, QColor("#e5dccb"))
    palette.setColor(QPalette.Dark, QColor("#b7aa93"))
    palette.setColor(QPalette.Mid, QColor("#cdc2ad"))
    palette.setColor(QPalette.Shadow, QColor("#8d806b"))

    disabled_text = QColor("#9d9487")
    palette.setColor(QPalette.Disabled, QPalette.WindowText, disabled_text)
    palette.setColor(QPalette.Disabled, QPalette.Text, disabled_text)
    palette.setColor(QPalette.Disabled, QPalette.ButtonText, disabled_text)
    palette.setColor(QPalette.Disabled, QPalette.Highlight, QColor("#d8d1c5"))
    palette.setColor(QPalette.Disabled, QPalette.HighlightedText, QColor("#8f8679"))

    app.setPalette(palette)
    app.setStyleSheet(
        """
        QWidget {
            color: #2f2a22;
            background-color: #f4f1e8;
        }
        QMainWindow, QMenuBar, QMenu, QStatusBar {
            background-color: #f4f1e8;
        }
        QLineEdit, QComboBox, QListWidget, QScrollArea {
            background-color: #fffdf8;
            border: 1px solid #d7ccbb;
            border-radius: 8px;
        }
        QPushButton {
            background-color: #efe8da;
            border: 1px solid #cbbda7;
            border-radius: 8px;
            padding: 6px 10px;
        }
        QPushButton:disabled {
            background-color: #e5dfd3;
            color: #9d9487;
            border-color: #d0c7b8;
        }
        QListWidget::item:selected {
            background-color: #ead8b0;
            color: #1f1a14;
        }
        QMenu::item:selected {
            background-color: #ead8b0;
        }
        """
    )
