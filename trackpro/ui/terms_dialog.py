from pathlib import Path
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QTextEdit, QPushButton, QHBoxLayout

class TermsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("User Agreement")
        self.setModal(True)
        self.setMinimumSize(600, 500)

        self.accepted = False

        layout = QVBoxLayout(self)

        self.terms_text_edit = QTextEdit()
        self.terms_text_edit.setReadOnly(True)
        layout.addWidget(self.terms_text_edit)

        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.agree_button = QPushButton("I Agree")
        self.agree_button.clicked.connect(self.on_agree)
        button_layout.addWidget(self.agree_button)

        self.decline_button = QPushButton("Decline")
        self.decline_button.clicked.connect(self.reject)
        button_layout.addWidget(self.decline_button)

        layout.addLayout(button_layout)

        self.load_terms()

    def load_terms(self):
        try:
            terms_file_path = Path(__file__).parent.parent / 'resources' / 'terms_of_service.txt'
            if not terms_file_path.exists():
                raise FileNotFoundError("Terms of Service file not found.")

            with open(terms_file_path, 'r', encoding='utf-8') as f:
                terms_text = f.read()
            self.terms_text_edit.setMarkdown(terms_text)
        except Exception as e:
            self.terms_text_edit.setText(f"Could not load terms of service: {e}")
            self.agree_button.setEnabled(False)

    def on_agree(self):
        self.accepted = True
        self.accept() 