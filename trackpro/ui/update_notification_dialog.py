from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QLabel, QFrame, QGraphicsDropShadowEffect)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QPropertyAnimation, QEasingCurve, QPoint
from PyQt6.QtGui import QFont, QPalette, QColor


class UpdateNotificationDialog(QFrame):
    """Modern update notification dialog with Cursor-like styling and animations."""
    
    download_clicked = pyqtSignal()
    cancel_clicked = pyqtSignal()
    
    def __init__(self, version_number, parent=None):
        super().__init__(parent)
        self.version_number = version_number
        self.setup_ui()
        self.setup_styling()
        self.setup_animations()
        
    def setup_ui(self):
        """Set up the dialog UI."""
        self.setWindowTitle("Update Available")
        self.setFixedSize(320, 120)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)
        
        # Header with title and version
        header_layout = QHBoxLayout()
        header_layout.setSpacing(8)
        
        # Update icon (using a simple dot for now)
        icon_label = QLabel("●")
        icon_label.setStyleSheet("color: #2a82da; font-size: 12px; font-weight: bold;")
        header_layout.addWidget(icon_label)
        
        # Title and version
        title_layout = QVBoxLayout()
        title_layout.setSpacing(2)
        
        title_label = QLabel("Update Available")
        title_font = QFont()
        title_font.setPointSize(13)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setStyleSheet("color: #ffffff;")
        title_layout.addWidget(title_label)
        
        version_label = QLabel(f"v{self.version_number}")
        version_font = QFont()
        version_font.setPointSize(11)
        version_label.setFont(version_font)
        version_label.setStyleSheet("color: #2a82da; font-weight: 600;")
        title_layout.addWidget(version_label)
        
        header_layout.addLayout(title_layout)
        header_layout.addStretch()
        
        # Close button (X)
        close_btn = QPushButton("×")
        close_btn.setFixedSize(20, 20)
        close_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                color: #888888;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                color: #ffffff;
            }
        """)
        close_btn.clicked.connect(self._on_cancel_clicked)
        header_layout.addWidget(close_btn)
        
        main_layout.addLayout(header_layout)
        
        # Button layout
        button_layout = QHBoxLayout()
        button_layout.setSpacing(8)
        
        # Download button
        self.download_btn = QPushButton("Download")
        self.download_btn.setFixedSize(80, 32)
        self.download_btn.clicked.connect(self._on_download_clicked)
        button_layout.addWidget(self.download_btn)
        
        # Cancel button
        self.cancel_btn = QPushButton("Later")
        self.cancel_btn.setFixedSize(60, 32)
        self.cancel_btn.clicked.connect(self._on_cancel_clicked)
        button_layout.addWidget(self.cancel_btn)
        
        button_layout.addStretch()
        main_layout.addLayout(button_layout)
        
    def setup_styling(self):
        """Apply modern dark theme styling with drop shadow."""
        # Create drop shadow effect
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 80))
        shadow.setOffset(0, 4)
        self.setGraphicsEffect(shadow)
        
        # Set modern styling - all elements share the same background container with border
        self.setStyleSheet("""
            QFrame {
                background-color: #1e1e1e;
                border: 1px solid #666666;
                border-radius: 8px;
            }
            
            QLabel {
                background-color: transparent;
                border: none;
            }
            
            QPushButton {
                border: none;
                border-radius: 6px;
                padding: 6px 12px;
                font-weight: 600;
                font-size: 11px;
                min-height: 20px;
            }
            
            QPushButton#download_btn {
                background-color: #2a82da;
                color: #ffffff;
            }
            
            QPushButton#download_btn:hover {
                background-color: #1e6bb8;
            }
            
            QPushButton#download_btn:pressed {
                background-color: #155a9e;
            }
            
            QPushButton#cancel_btn {
                background-color: #dc3545;
                color: #ffffff;
            }
            
            QPushButton#cancel_btn:hover {
                background-color: #c82333;
            }
            
            QPushButton#cancel_btn:pressed {
                background-color: #bd2130;
            }
        """)
        
        # Set object names for styling
        self.download_btn.setObjectName("download_btn")
        self.cancel_btn.setObjectName("cancel_btn")
        
    def _on_download_clicked(self):
        """Handle download button click - emit signal and close dialog."""
        self.download_clicked.emit()
        self.close()
        
    def _on_cancel_clicked(self):
        """Handle cancel button click - emit signal and close dialog immediately."""
        self.cancel_clicked.emit()
        # Close immediately without animation
        self.deleteLater()
        
    def setup_animations(self):
        """Set up slide-in animation from bottom-left corner."""
        # Position the notification in the bottom-left corner
        if self.parent():
            parent_rect = self.parent().geometry()
            self.move(
                60,  # 60px from left edge (moved further to the right to avoid account button)
                parent_rect.height() - self.height() - 20  # 20px from bottom
            )
        
        # Create slide-in animation
        self.slide_animation = QPropertyAnimation(self, b"geometry")
        self.slide_animation.setDuration(300)
        self.slide_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        # Start position (off-screen to the left)
        start_rect = self.geometry()
        start_rect.moveLeft(start_rect.left() - 50)
        
        # End position (current position)
        end_rect = self.geometry()
        
        self.slide_animation.setStartValue(start_rect)
        self.slide_animation.setEndValue(end_rect)
        
    def showEvent(self, event):
        """Override show event to start animation."""
        super().showEvent(event)
        self.slide_animation.start()
        
    def closeEvent(self, event):
        """Override close event to add slide-out animation."""
        # Create slide-out animation
        slide_out = QPropertyAnimation(self, b"geometry")
        slide_out.setDuration(200)
        slide_out.setEasingCurve(QEasingCurve.Type.InCubic)
        
        start_rect = self.geometry()
        end_rect = start_rect
        end_rect.moveLeft(end_rect.left() - 50)
        
        slide_out.setStartValue(start_rect)
        slide_out.setEndValue(end_rect)
        slide_out.finished.connect(super().close)
        slide_out.start()
        
        event.ignore()  # Don't close immediately, let animation finish 