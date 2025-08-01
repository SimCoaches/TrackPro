"""Authentication dialog widgets."""

from .shared_imports import *

class PasswordDialog(QDialog):
    """Dialog to request password before accessing protected features."""
    
    def __init__(self, parent=None, feature_name="Race Coach"):
        super().__init__(parent)
        self.feature_name = feature_name
        self.setWindowTitle("Password Required")
        self.setMinimumWidth(350)
        self.setModal(True)
        self.setup_ui()
        
    def setup_ui(self):
        """Set up the dialog UI with modern styling."""
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)
        
        # Title
        title_label = QLabel(f"🔒 {self.feature_name} Access")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("""
            QLabel {
                font-size: 18px;
                font-weight: bold;
                color: #77aaff;
                margin-bottom: 10px;
            }
        """)
        layout.addWidget(title_label)
        
        # Message label
        message_label = QLabel(f"Please enter the password to access {self.feature_name}:")
        message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        message_label.setWordWrap(True)
        message_label.setStyleSheet("""
            QLabel {
                color: #ddd;
                font-size: 14px;
                margin-bottom: 15px;
            }
        """)
        layout.addWidget(message_label)
        
        # Password field
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setPlaceholderText("Enter password...")
        self.password_input.setStyleSheet("""
            QLineEdit {
                background-color: #444;
                border: 2px solid #555;
                padding: 12px;
                border-radius: 6px;
                color: #ddd;
                font-size: 14px;
            }
            QLineEdit:focus {
                border: 2px solid #77aaff;
                background-color: #4a4a4a;
            }
        """)
        self.password_input.returnPressed.connect(self.validate_password)
        layout.addWidget(self.password_input)
        
        # Error label (initially hidden)
        self.error_label = QLabel("")
        self.error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.error_label.setStyleSheet("""
            QLabel {
                color: #ff6b6b;
                font-size: 12px;
                background-color: rgba(255, 107, 107, 0.1);
                border: 1px solid #ff6b6b;
                border-radius: 4px;
                padding: 8px;
            }
        """)
        self.error_label.hide()
        layout.addWidget(self.error_label)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(15)
        
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setStyleSheet("""
            QPushButton {
                background-color: #666;
                border: none;
                padding: 10px 20px;
                border-radius: 5px;
                color: white;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #777;
            }
        """)
        self.cancel_button.clicked.connect(self.reject)
        
        self.ok_button = QPushButton("Access")
        self.ok_button.setStyleSheet("""
            QPushButton {
                background-color: #77aaff;
                border: none;
                padding: 10px 20px;
                border-radius: 5px;
                color: white;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #6699ee;
            }
        """)
        self.ok_button.setDefault(True)
        self.ok_button.clicked.connect(self.validate_password)
        
        button_layout.addWidget(self.cancel_button)
        button_layout.addStretch()
        button_layout.addWidget(self.ok_button)
        layout.addLayout(button_layout)
        
        # Focus on password input
        self.password_input.setFocus()
    
    def validate_password(self):
        """Validate the entered password."""
        password = self.password_input.text().strip()
        
        if password == "lt":  # The required password
            self.accept()
        else:
            self.show_error("Incorrect password. Please try again.")
            self.password_input.clear()
            self.password_input.setFocus()
    
    def show_error(self, message):
        """Show an error message."""
        self.error_label.setText(message)
        self.error_label.show()
        
        # Flash the password field red briefly
        self.password_input.setStyleSheet("""
            QLineEdit {
                background-color: #554;
                border: 2px solid #ff6b6b;
                padding: 12px;
                border-radius: 6px;
                color: #ddd;
                font-size: 14px;
            }
        """)
        
        # Reset style after 1 second
        QTimer.singleShot(1000, self.reset_password_field_style)
    
    def reset_password_field_style(self):
        """Reset password field to normal style."""
        self.password_input.setStyleSheet("""
            QLineEdit {
                background-color: #444;
                border: 2px solid #555;
                padding: 12px;
                border-radius: 6px;
                color: #ddd;
                font-size: 14px;
            }
            QLineEdit:focus {
                border: 2px solid #77aaff;
                background-color: #4a4a4a;
            }
        """)
    
    def get_password(self):
        """Get the entered password."""
        return self.password_input.text() 