"""Authentication dialog widgets."""

from .shared_imports import *

class PasswordDialog(QDialog):
    """Dialog to request password before accessing protected features."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Password Required")
        self.setMinimumWidth(300)
        
        # Create layout
        layout = QVBoxLayout()
        
        # Add message label
        message_label = QLabel("Please enter the password to access Race Coach:")
        layout.addWidget(message_label)
        
        # Add password field
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        layout.addWidget(self.password_input)
        
        # Add buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        self.setLayout(layout)
    
    def get_password(self):
        """Get the entered password."""
        return self.password_input.text() 