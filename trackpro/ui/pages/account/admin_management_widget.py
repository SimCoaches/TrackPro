"""
Admin Management Widget for TrackPro.

Allows admins to manage dynamic admin users.
"""

import logging
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QPushButton, QListWidget, QListWidgetItem, QMessageBox,
    QFrame, QScrollArea
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

from ....auth.hierarchy_manager import hierarchy_manager
from ....auth.user_manager import get_current_user, is_current_user_dev

logger = logging.getLogger(__name__)

class AdminManagementWidget(QWidget):
    """Widget for managing admin users."""
    
    admin_updated = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.load_admin_list()
    
    def setup_ui(self):
        """Set up the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        # Ensure labels don't draw opaque bars over the page background
        self.setStyleSheet("""
            QLabel { background: transparent; }
        """)
        
        # Title
        title = QLabel("Admin Management")
        title.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        title.setStyleSheet("color: #ffffff; margin-bottom: 10px; background: transparent;")
        layout.addWidget(title)
        
        # Description
        desc = QLabel("Manage dynamic admin users. Only hardcoded admins can add/remove other admins.")
        desc.setStyleSheet("color: #b9bbbe; font-size: 14px; margin-bottom: 20px; background: transparent;")
        desc.setWordWrap(True)
        layout.addWidget(desc)
        
        # Current user info
        current_user = get_current_user()
        if current_user:
            user_info = QLabel(f"Current User: {current_user.email}")
            user_info.setStyleSheet("color: #5865f2; font-size: 12px; margin-bottom: 10px; background: transparent;")
            layout.addWidget(user_info)
        
        # Add admin section
        add_frame = QFrame()
        add_frame.setStyleSheet("""
            QFrame {
                background-color: #2f3136;
                border-radius: 8px;
                padding: 15px;
            }
            QLabel { background: transparent; }
        """)
        add_layout = QVBoxLayout(add_frame)
        
        add_title = QLabel("Add New Admin")
        add_title.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        add_title.setStyleSheet("color: #ffffff; margin-bottom: 10px; background: transparent;")
        add_layout.addWidget(add_title)
        
        # Email input
        input_layout = QHBoxLayout()
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("Enter email address")
        self.email_input.setStyleSheet("""
            QLineEdit {
                background-color: #40444b;
                border: 1px solid #202225;
                border-radius: 4px;
                padding: 8px 12px;
                color: #dcddde;
                font-size: 14px;
            }
            QLineEdit:focus {
                border: 1px solid #5865f2;
            }
        """)
        input_layout.addWidget(self.email_input)
        
        # Add button
        self.add_button = QPushButton("Add Admin")
        self.add_button.setStyleSheet("""
            QPushButton {
                background-color: #5865f2;
                color: #ffffff;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-size: 14px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #4752c4;
            }
            QPushButton:pressed {
                background-color: #3c45a5;
            }
            QPushButton:disabled {
                background-color: #40444b;
                color: #72767d;
            }
        """)
        self.add_button.clicked.connect(self.add_admin)
        input_layout.addWidget(self.add_button)
        
        add_layout.addLayout(input_layout)
        layout.addWidget(add_frame)
        
        # Admin list section
        list_frame = QFrame()
        list_frame.setStyleSheet("""
            QFrame {
                background-color: #2f3136;
                border-radius: 8px;
                padding: 15px;
            }
            QLabel { background: transparent; }
        """)
        list_layout = QVBoxLayout(list_frame)
        
        list_title = QLabel("Current Admins")
        list_title.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        list_title.setStyleSheet("color: #ffffff; margin-bottom: 10px; background: transparent;")
        list_layout.addWidget(list_title)
        
        # Admin list
        self.admin_list = QListWidget()
        self.admin_list.setStyleSheet("""
            QListWidget {
                background-color: #40444b;
                border: 1px solid #202225;
                border-radius: 4px;
                color: #dcddde;
                font-size: 14px;
                padding: 5px;
            }
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #2f3136;
            }
            QListWidget::item:selected {
                background-color: #5865f2;
                color: #ffffff;
            }
            QListWidget::item:hover {
                background-color: #40444b;
            }
        """)
        list_layout.addWidget(self.admin_list)
        
        # Remove button
        self.remove_button = QPushButton("Remove Selected Admin")
        self.remove_button.setStyleSheet("""
            QPushButton {
                background-color: #ed4245;
                color: #ffffff;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-size: 14px;
                font-weight: 500;
                margin-top: 10px;
            }
            QPushButton:hover {
                background-color: #c03537;
            }
            QPushButton:pressed {
                background-color: #a02826;
            }
            QPushButton:disabled {
                background-color: #40444b;
                color: #72767d;
            }
        """)
        self.remove_button.clicked.connect(self.remove_admin)
        list_layout.addWidget(self.remove_button)
        
        layout.addWidget(list_frame)
        
        # Refresh button
        self.refresh_button = QPushButton("Refresh List")
        self.refresh_button.setStyleSheet("""
            QPushButton {
                background-color: #40444b;
                color: #dcddde;
                border: 1px solid #202225;
                border-radius: 4px;
                padding: 8px 16px;
                font-size: 14px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #4f545c;
            }
        """)
        self.refresh_button.clicked.connect(self.load_admin_list)
        layout.addWidget(self.refresh_button)

        # Make the outer widget background transparent so it blends with page background
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(self.styleSheet() + "\nQWidget { background: transparent; }\n")
        
        # Set up connections
        self.email_input.returnPressed.connect(self.add_admin)
        self.admin_list.itemSelectionChanged.connect(self.update_remove_button)
        
        # Initial state
        self.update_remove_button()
    
    def load_admin_list(self):
        """Load the list of admin users."""
        try:
            self.admin_list.clear()
            
            # Get all admin emails
            admin_emails = hierarchy_manager.get_all_admin_emails()
            dynamic_admins = hierarchy_manager.get_dynamic_admin_emails()
            
            for email in admin_emails:
                item = QListWidgetItem()
                
                # Mark hardcoded admin
                if email == "lawrence@simcoaches.com":
                    item.setText(f"👑 {email} (Hardcoded Admin)")
                    item.setData(Qt.ItemDataRole.UserRole, {"email": email, "type": "hardcoded"})
                elif email in dynamic_admins:
                    item.setText(f"🔧 {email} (Dynamic Admin)")
                    item.setData(Qt.ItemDataRole.UserRole, {"email": email, "type": "dynamic"})
                else:
                    item.setText(f"⚙️ {email}")
                    item.setData(Qt.ItemDataRole.UserRole, {"email": email, "type": "unknown"})
                
                self.admin_list.addItem(item)
                
        except Exception as e:
            logger.error(f"Error loading admin list: {e}")
            QMessageBox.warning(self, "Error", f"Failed to load admin list: {e}")
    
    def add_admin(self):
        """Add a new admin user."""
        email = self.email_input.text().strip().lower()
        
        if not email:
            QMessageBox.warning(self, "Error", "Please enter an email address")
            return
        
        if not self.is_valid_email(email):
            QMessageBox.warning(self, "Error", "Please enter a valid email address")
            return
        
        current_user = get_current_user()
        if not current_user:
            QMessageBox.warning(self, "Error", "You must be logged in to add admins")
            return
        
        try:
            result = hierarchy_manager.add_dynamic_admin(email, current_user.email)
            
            if result["success"]:
                QMessageBox.information(self, "Success", result["message"])
                self.email_input.clear()
                self.load_admin_list()
                self.admin_updated.emit()
            else:
                QMessageBox.warning(self, "Error", result["message"])
                
        except Exception as e:
            logger.error(f"Error adding admin: {e}")
            QMessageBox.warning(self, "Error", f"Failed to add admin: {e}")
    
    def remove_admin(self):
        """Remove the selected admin user."""
        current_item = self.admin_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "Error", "Please select an admin to remove")
            return
        
        item_data = current_item.data(Qt.ItemDataRole.UserRole)
        email = item_data["email"]
        admin_type = item_data["type"]
        
        if admin_type == "hardcoded":
            QMessageBox.warning(self, "Error", "Cannot remove hardcoded admin")
            return
        
        # Confirm removal
        reply = QMessageBox.question(
            self, 
            "Confirm Removal", 
            f"Are you sure you want to remove {email} as an admin?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            current_user = get_current_user()
            if not current_user:
                QMessageBox.warning(self, "Error", "You must be logged in to remove admins")
                return
            
            try:
                result = hierarchy_manager.remove_dynamic_admin(email, current_user.email)
                
                if result["success"]:
                    QMessageBox.information(self, "Success", result["message"])
                    self.load_admin_list()
                    self.admin_updated.emit()
                else:
                    QMessageBox.warning(self, "Error", result["message"])
                    
            except Exception as e:
                logger.error(f"Error removing admin: {e}")
                QMessageBox.warning(self, "Error", f"Failed to remove admin: {e}")
    
    def update_remove_button(self):
        """Update the remove button state based on selection."""
        current_item = self.admin_list.currentItem()
        if current_item:
            item_data = current_item.data(Qt.ItemDataRole.UserRole)
            admin_type = item_data["type"]
            self.remove_button.setEnabled(admin_type == "dynamic")
        else:
            self.remove_button.setEnabled(False)
    
    def is_valid_email(self, email: str) -> bool:
        """Check if email is valid."""
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
    
    def showEvent(self, event):
        """Handle show event."""
        super().showEvent(event)
        # Only show if user is admin
        if not is_current_user_dev():
            self.hide()
        else:
            self.load_admin_list() 