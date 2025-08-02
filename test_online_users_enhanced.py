#!/usr/bin/env python3
"""Test script for the enhanced online users sidebar with friends prioritization and online status indicators."""

import sys
import os
from pathlib import Path
from PyQt6.QtWidgets import QApplication, QMainWindow, QHBoxLayout, QWidget, QVBoxLayout, QLabel

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from trackpro.ui.online_users_sidebar import OnlineUsersSidebar


class TestMainWindow(QMainWindow):
    """Test window for the enhanced online users sidebar."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Enhanced Online Users Sidebar Test")
        self.setGeometry(100, 100, 800, 600)
        
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Create layout
        layout = QHBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Create main content area
        main_content = QWidget()
        main_content.setStyleSheet("background-color: #252525;")
        main_layout = QVBoxLayout(main_content)
        
        # Add title
        title = QLabel("Enhanced Online Users Sidebar Test")
        title.setStyleSheet("""
            QLabel {
                color: #ffffff;
                font-size: 24px;
                font-weight: bold;
                padding: 20px;
            }
        """)
        main_layout.addWidget(title)
        
        # Add description
        description = QLabel("""
        This test demonstrates the enhanced online users sidebar with the following features:
        
        • ALL users are shown (not just online ones)
        • Friends are prioritized at the top
        • Online users have a green dot on their avatar
        • Offline users have a gray dot on their avatar
        • Users are sorted: Friends online > Friends offline > Others online > Others offline
        • Shows online count in the format "X/Y online"
        • "Add a Friend" search bar at the top (when expanded)
        • Send friend requests by username
        • Click any user to see their profile popup with:
          - Profile picture with online status
          - Display name and username
          - Member since date
          - Friendship status
          - "View Profile" and "Send Friend Request" buttons
        
        Click the toggle button (👥 or ▶) to expand/collapse the sidebar.
        When expanded, you can use the "Add a Friend" bar to send friend requests.
        Click on any user to see their profile popup!
        """)
        description.setStyleSheet("""
            QLabel {
                color: #dcddde;
                font-size: 14px;
                padding: 20px;
                line-height: 1.6;
            }
        """)
        main_layout.addWidget(description)
        
        main_layout.addStretch()
        layout.addWidget(main_content, 1)
        
        # Create and add the enhanced online users sidebar
        self.sidebar = OnlineUsersSidebar()
        self.sidebar.user_selected.connect(self.on_user_selected)
        layout.addWidget(self.sidebar)
        
        # Apply Discord-like styling to the main window
        self.setStyleSheet("""
            QMainWindow {
                background-color: #252525;
            }
        """)
    
    def on_user_selected(self, user_data):
        """Handle user selection."""
        user_name = user_data.get('display_name') or user_data.get('username', 'Unknown User')
        is_friend = user_data.get('is_friend', False)
        is_online = user_data.get('is_online', False)
        status = user_data.get('status', 'Unknown')
        
        friend_text = " (Friend)" if is_friend else ""
        online_text = "Online" if is_online else "Offline"
        
        print(f"Selected user: {user_name}{friend_text} - {online_text} - {status}")


def main():
    """Run the test application."""
    app = QApplication(sys.argv)
    
    # Set application style
    app.setStyle('Fusion')
    
    # Create and show the test window
    window = TestMainWindow()
    window.show()
    
    # Start the event loop
    sys.exit(app.exec())


if __name__ == "__main__":
    main()