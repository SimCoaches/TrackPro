"""Theme setup for UI components."""

from .shared_imports import *


def setup_dark_theme(window):
    """Set up dark theme colors and styling for a window."""
    # Set up dark palette
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(53, 53, 53))
    palette.setColor(QPalette.WindowText, QColor(255, 255, 255))
    palette.setColor(QPalette.Base, QColor(35, 35, 35))
    palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
    palette.setColor(QPalette.ToolTipBase, QColor(255, 255, 255))
    palette.setColor(QPalette.ToolTipText, QColor(255, 255, 255))
    palette.setColor(QPalette.Text, QColor(255, 255, 255))
    palette.setColor(QPalette.Button, QColor(53, 53, 53))
    palette.setColor(QPalette.ButtonText, QColor(255, 255, 255))
    palette.setColor(QPalette.BrightText, QColor(255, 0, 0))
    palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
    palette.setColor(QPalette.HighlightedText, QColor(255, 255, 255))
    window.setPalette(palette)
    
    # Set stylesheet for custom styling
    window.setStyleSheet("""
        QMainWindow {
            background-color: #353535;
        }
        QWidget {
            background-color: #353535;
            color: #ffffff;
        }
        QGroupBox {
            border: 1px solid #555555;
            border-radius: 3px;
            padding: 2px;
            margin-top: 3px;
            margin-bottom: 3px;
            font-size: 11px;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 7px;
            padding: 0px 3px 0px 3px;
            top: -2px;
        }
        QPushButton {
            background-color: #444444;
            border: 1px solid #555555;
            border-radius: 3px;
            padding: 5px 15px;
            color: white;
        }
        QPushButton:hover {
            background-color: #4f4f4f;
        }
        QPushButton:pressed {
            background-color: #3a3a3a;
        }
        QProgressBar {
            border: 1px solid #555555;
            border-radius: 2px;
            text-align: center;
            background-color: #2d2d2d;
        }
        QProgressBar::chunk {
            background-color: #2a82da;
        }
        QComboBox {
            background-color: #444444;
            border: 1px solid #555555;
            border-radius: 3px;
            padding: 5px 10px;
            color: white;
        }
        QComboBox::drop-down {
            border: none;
        }
        QComboBox::down-arrow {
            image: none;
            border-width: 0px;
        }
        QComboBox QAbstractItemView {
            background-color: #444444;
            selection-background-color: #2a82da;
            min-width: 200px;
            padding: 5px;
        }
        QLabel {
            color: white;
        }
    """) 