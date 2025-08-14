from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QFrame, QLineEdit

class ModernCard(QFrame):
    """A styled card widget."""
    def __init__(self, title, parent=None):
        super().__init__(parent)
        self.setObjectName("modernCard")
        
        main_layout = QVBoxLayout(self)
        
        title_label = QLabel(title)
        title_label.setObjectName("modernCardTitle")
        
        main_layout.addWidget(title_label)

class ModernInput(QLineEdit):
    """A styled input field."""
    def __init__(self, placeholder_text, parent=None):
        super().__init__(parent)
        self.setPlaceholderText(placeholder_text)
        self.setObjectName("modernInput")

class ModernButton(QPushButton):
    """A styled button."""
    def __init__(self, text, button_type="primary", parent=None):
        super().__init__(text, parent)
        self.setObjectName(f"modernButton-{button_type}")
