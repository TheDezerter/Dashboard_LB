# app/styles.py

from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QPalette, QColor


def apply_dark_theme():
    """
    Globalny ciemny motyw aplikacji.
    """
    app = QApplication.instance()
    palette = QPalette()

    # Tła
    palette.setColor(QPalette.Window, QColor(40, 40, 40))
    palette.setColor(QPalette.Base, QColor(30, 30, 30))
    palette.setColor(QPalette.AlternateBase, QColor(40, 40, 40))

    # Teksty
    palette.setColor(QPalette.WindowText, QColor(230, 230, 230))
    palette.setColor(QPalette.Text, QColor(230, 230, 230))
    palette.setColor(QPalette.ToolTipText, QColor(230, 230, 230))

    # Przyciski
    palette.setColor(QPalette.Button, QColor(60, 60, 60))
    palette.setColor(QPalette.ButtonText, QColor(230, 230, 230))

    # Akcenty
    palette.setColor(QPalette.Highlight, QColor(0, 120, 215))
    palette.setColor(QPalette.HighlightedText, QColor(0, 0, 0))

    # ustaw PALETĘ
    app.setPalette(palette)

    # CSS aplikacji
    app.setStyleSheet(
        """
        QWidget {
            color: #E6E6E6;
            background-color: #282828;
            font-size: 13px;
        }

        QLabel {
            color: #FFFFFF;
            font-size: 13px;
        }

        QLineEdit, QSpinBox, QDoubleSpinBox {
            background-color: #1E1E1E;
            color: #FFFFFF;
            border: 2px solid #444;
            border-radius: 6px;
            padding: 3px;
        }

        QPushButton {
            background-color: #3a6ea5;
            color: white;
            border-radius: 8px;
            padding: 6px 14px;
            font-weight: bold;
        }

        QPushButton:hover {
            background-color: #4d8bc9;
        }

        QPushButton:pressed {
            background-color: #2c5682;
        }

        QScrollBar:vertical {
            background: #202020;
            width: 12px;
        }

        QScrollBar::handle:vertical {
            background: #555;
            border-radius: 5px;
        }

        QScrollBar:horizontal {
            background: #202020;
            height: 12px;
        }

        QScrollBar::handle:horizontal {
            background: #555;
            border-radius: 5px;
        }

        QTableWidget {
            gridline-color: #444;
        }

        QHeaderView::section {
            background-color: #303030;
            color: #FFFFFF;
            padding: 4px;
            border: none;
        }
        """
    )
