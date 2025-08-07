#!/usr/bin/env python3
"""
Test script to verify avatar manager thread safety.
"""

import sys
import logging
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QLabel
from PyQt6.QtCore import QTimer, QThread, pyqtSignal
from PyQt6.QtGui import QPixmap

# Add the trackpro directory to the path
sys.path.insert(0, '.')

from trackpro.ui.avatar_manager import get_avatar_manager, AvatarSize
from trackpro.ui.avatar_widget import AvatarWidget

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class TestThread(QThread):
    """Test thread that loads avatars from background."""
    avatar_loaded = pyqtSignal(str)
    
    def run(self):
        """Load avatars from background thread."""
        try:
            avatar_manager = get_avatar_manager()
            
            # Test loading avatars from background thread
            test_urls = [
                "https://via.placeholder.com/100x100/3498db/ffffff?text=Test1",
                "https://via.placeholder.com/100x100/e74c3c/ffffff?text=Test2",
                "https://via.placeholder.com/100x100/f39c12/ffffff?text=Test3"
            ]
            
            for i, url in enumerate(test_urls):
                logger.info(f"Loading avatar {i+1} from background thread: {url}")
                avatar_manager.get_avatar(
                    url=url,
                    size=AvatarSize.MEDIUM,
                    callback=lambda pixmap, url=url: self._on_avatar_loaded(pixmap, url),
                    user_name=f"TestUser{i+1}"
                )
                
                # Small delay between requests
                self.msleep(500)
                
        except Exception as e:
            logger.error(f"Error in test thread: {e}")

    def _on_avatar_loaded(self, pixmap, url):
        """Handle avatar loaded from background thread."""
        logger.info(f"Avatar loaded from background thread: {url}")
        self.avatar_loaded.emit(url)

class TestWindow(QMainWindow):
    """Test window for avatar thread safety."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Avatar Thread Safety Test")
        self.setGeometry(100, 100, 400, 300)
        
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Create avatar widgets
        self.avatar1 = AvatarWidget(AvatarSize.MEDIUM)
        self.avatar2 = AvatarWidget(AvatarSize.MEDIUM)
        self.avatar3 = AvatarWidget(AvatarSize.MEDIUM)
        
        # Create test button
        self.test_button = QPushButton("Test Avatar Loading from Background Thread")
        self.test_button.clicked.connect(self.start_test)
        
        # Create status label
        self.status_label = QLabel("Ready to test avatar thread safety")
        
        # Add widgets to layout
        layout.addWidget(self.avatar1)
        layout.addWidget(self.avatar2)
        layout.addWidget(self.avatar3)
        layout.addWidget(self.test_button)
        layout.addWidget(self.status_label)
        
        # Initialize test thread
        self.test_thread = TestThread()
        self.test_thread.avatar_loaded.connect(self.on_avatar_loaded)
        
        # Initialize avatar manager
        self.avatar_manager = get_avatar_manager()
        
        logger.info("Test window initialized")
    
    def start_test(self):
        """Start the avatar loading test."""
        logger.info("Starting avatar thread safety test")
        self.status_label.setText("Testing avatar loading from background thread...")
        self.test_button.setEnabled(False)
        
        # Start test thread
        self.test_thread.start()
    
    def on_avatar_loaded(self, url):
        """Handle avatar loaded signal."""
        logger.info(f"Avatar loaded signal received: {url}")
        self.status_label.setText(f"Avatar loaded: {url}")
        self.test_button.setEnabled(True)

def main():
    """Main function."""
    app = QApplication(sys.argv)
    
    # Create and show test window
    window = TestWindow()
    window.show()
    
    logger.info("Avatar thread safety test started")
    
    # Run the application
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
