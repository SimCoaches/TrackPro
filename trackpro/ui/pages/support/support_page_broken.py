"""Support page for opening support tickets and getting help."""

import logging
from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QTextEdit, QPushButton, QComboBox,
    QLineEdit, QFrame, QScrollArea, QWidget, QMessageBox, QTabWidget
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from ...modern.shared.base_page import BasePage

logger = logging.getLogger(__name__)

class SupportPage(BasePage):
    """Support page for user assistance and ticket submission."""
    
    def __init__(self, global_managers=None):
        super().__init__("support", global_managers)
    
    def init_page(self):
        """Initialize the support page layout."""
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        self.setLayout(layout)
        
        # Create header
        self.create_header(layout)
        
        # Create tab widget for different support sections
        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #444;
                background-color: #1a1a1a;
                border-radius: 6px;
                margin-top: 5px;
            }
            QTabBar::tab {
                background-color: #2d2d2d;
                color: #CCC;
                padding: 12px 20px;
                margin-right: 2px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                font-size: 14px;
                font-weight: 500;
                min-width: 100px;
            }
            QTabBar::tab:selected {
                background-color: #2a82da;
                color: white;
                font-weight: bold;
            }
            QTabBar::tab:hover:!selected {
                background-color: #3a3a3a;
                border-bottom: 2px solid #2a82da;
            }
        """)
        
        # Create support tabs
        self.create_support_tabs()
        
        layout.addWidget(self.tab_widget)
    
    def create_header(self, layout):
        """Create the header section."""
        header_frame = QFrame()
        header_frame.setStyleSheet("""
            QFrame {
                background-color: #252525;
                border-radius: 12px;
                padding: 20px;
            }
        """)
        header_layout = QVBoxLayout(header_frame)
        
        # Title
        title_label = QLabel("Support Center")
        title_label.setFont(QFont("Arial", 24, QFont.Weight.Bold))
        title_label.setStyleSheet("color: white; margin-bottom: 10px;")
        header_layout.addWidget(title_label)
        
        # Description
        desc_label = QLabel("Get help with TrackPro, report issues, or submit feature requests")
        desc_label.setFont(QFont("Arial", 14))
        desc_label.setStyleSheet("color: #b0b0b0;")
        header_layout.addWidget(desc_label)
        
        layout.addWidget(header_frame)
    
    def create_support_tabs(self):
        """Create the support tabs."""
        # Submit Ticket tab
        self.create_submit_ticket_tab()
        
        # FAQ tab
        self.create_faq_tab()
        
        # Contact Info tab
        self.create_contact_tab()
    
    def create_submit_ticket_tab(self):
        """Create the submit ticket tab."""
        ticket_widget = QWidget()
        ticket_layout = QVBoxLayout(ticket_widget)
        ticket_layout.setContentsMargins(20, 20, 20, 20)
        ticket_layout.setSpacing(15)
        
        # Create scroll area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollBar:vertical {
                background-color: #2c3e50;
                width: 12px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background-color: #3498db;
                border-radius: 6px;
                min-height: 20px;
            }
        """)
        
        form_widget = QWidget()
        form_layout = QVBoxLayout(form_widget)
        form_layout.setSpacing(15)
        
        # Ticket form
        self.create_ticket_form(form_layout)
        
        scroll_area.setWidget(form_widget)
        ticket_layout.addWidget(scroll_area)
        
        self.tab_widget.addTab(ticket_widget, "📝 Submit Ticket")
    
    def create_ticket_form(self, layout):
        """Create the ticket submission form."""
        # Subject field
        subject_label = QLabel("Subject:")
        subject_label.setStyleSheet("color: white; font-weight: bold; font-size: 14px;")
        layout.addWidget(subject_label)
        
        self.subject_input = QLineEdit()
        self.subject_input.setPlaceholderText("Brief description of your issue...")
        self.subject_input.setStyleSheet("""
            QLineEdit {
                background-color: #2c3e50;
                border: 2px solid #34495e;
                border-radius: 6px;
                padding: 10px;
                color: white;
                font-size: 14px;
            }
            QLineEdit:focus {
                border-color: #3498db;
            }
        """)
        layout.addWidget(self.subject_input)
        
        # Priority selection
        priority_label = QLabel("Priority:")
        priority_label.setStyleSheet("color: white; font-weight: bold; font-size: 14px;")
        layout.addWidget(priority_label)
        
        self.priority_combo = QComboBox()
        self.priority_combo.addItems(["Low", "Medium", "High", "Critical"])
        self.priority_combo.setCurrentText("Medium")
        self.priority_combo.setStyleSheet("""
            QComboBox {
                background-color: #2c3e50;
                border: 2px solid #34495e;
                border-radius: 6px;
                padding: 10px;
                color: white;
                font-size: 14px;
            }
            QComboBox:focus {
                border-color: #3498db;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox QAbstractItemView {
                background-color: #2c3e50;
                color: white;
                selection-background-color: #3498db;
            }
        """)
        layout.addWidget(self.priority_combo)
        
        # Category selection
        category_label = QLabel("Category:")
        category_label.setStyleSheet("color: white; font-weight: bold; font-size: 14px;")
        layout.addWidget(category_label)
        
        self.category_combo = QComboBox()
        self.category_combo.addItems([
            "General Question",
            "Bug Report", 
            "Feature Request",
            "Pedal Calibration Issue",
            "Race Coach Problem",
            "Community Feature",
            "Account/Login Issue",
            "Performance Issue",
            "Hardware Compatibility",
            "Other"
        ])
        self.category_combo.setStyleSheet("""
            QComboBox {
                background-color: #2c3e50;
                border: 2px solid #34495e;
                border-radius: 6px;
                padding: 10px;
                color: white;
                font-size: 14px;
            }
            QComboBox:focus {
                border-color: #3498db;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox QAbstractItemView {
                background-color: #2c3e50;
                color: white;
                selection-background-color: #3498db;
            }
        """)
        layout.addWidget(self.category_combo)
        
        # Description field
        description_label = QLabel("Description:")
        description_label.setStyleSheet("color: white; font-weight: bold; font-size: 14px;")
        layout.addWidget(description_label)
        
        self.description_input = QTextEdit()
        self.description_input.setPlaceholderText("Please provide detailed information about your issue, including:\n\n• What you were trying to do\n• What happened instead\n• Steps to reproduce the issue\n• Any error messages you saw\n• Your system information (Windows version, hardware, etc.)")
        self.description_input.setMinimumHeight(200)
        self.description_input.setStyleSheet("""
            QTextEdit {
                background-color: #2c3e50;
                border: 2px solid #34495e;
                border-radius: 6px;
                padding: 10px;
                color: white;
                font-size: 14px;
            }
            QTextEdit:focus {
                border-color: #3498db;
            }
        """)
        layout.addWidget(self.description_input)
        
        # Submit button
        submit_button = QPushButton("Submit Support Ticket")
        submit_button.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                border: none;
                padding: 15px 30px;
                border-radius: 6px;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #229954;
            }
            QPushButton:pressed {
                background-color: #1e8449;
            }
        """)
        submit_button.clicked.connect(self.submit_ticket)
        layout.addWidget(submit_button)
    
    def create_faq_tab(self):
        """Create the FAQ tab."""
        faq_widget = QWidget()
        faq_layout = QVBoxLayout(faq_widget)
        faq_layout.setContentsMargins(20, 20, 20, 20)
        
        # FAQ content
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollBar:vertical {
                background-color: #2c3e50;
                width: 12px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background-color: #3498db;
                border-radius: 6px;
                min-height: 20px;
            }
        """)
        
        faq_content = QWidget()
        content_layout = QVBoxLayout(faq_content)
        
        faqs = [
            {
                "question": "How do I calibrate my pedals?",
                "answer": "Go to the Pedals section and click the 'Calibration Wizard' button. Follow the on-screen instructions to calibrate each pedal by pressing them fully and releasing them."
            },
            {
                "question": "My pedals aren't being detected, what should I do?",
                "answer": "1. Make sure your pedals are properly connected\n2. Check if they appear in Windows Game Controllers\n3. Try restarting TrackPro\n4. Check if HidHide is blocking the device\n5. Contact support if the issue persists"
            },
            {
                "question": "How do I use the Race Coach feature?",
                "answer": "The Race Coach analyzes your driving and provides feedback. Connect to iRacing, complete some laps, and check the Race Coach section for analysis and improvement suggestions."
            },
            {
                "question": "What is the Race Pass?",
                "answer": "The Race Pass is TrackPro's progression system with challenges, rewards, and achievements to help you improve your racing skills over time."
            },
            {
                "question": "How do I reset my calibration?",
                "answer": "In the Pedals section, you can reset individual pedal calibrations or use the Calibration Wizard to start fresh with all pedals."
            },
            {
                "question": "Can I use multiple controllers/pedal sets?",
                "answer": "Yes, TrackPro supports multiple input devices. You can configure different pedal sets and switch between them as needed."
            }
        ]
        
        for faq in faqs:
            faq_frame = QFrame()
            faq_frame.setStyleSheet("""
                QFrame {
                    background-color: #252525;
                    border-radius: 8px;
                    padding: 15px;
                    margin-bottom: 10px;
                }
            """)
            faq_layout = QVBoxLayout(faq_frame)
            
            question_label = QLabel(f"Q: {faq['question']}")
            question_label.setStyleSheet("color: #3498db; font-weight: bold; font-size: 14px;")
            question_label.setWordWrap(True)
            faq_layout.addWidget(question_label)
            
            answer_label = QLabel(f"A: {faq['answer']}")
            answer_label.setStyleSheet("color: #ecf0f1; font-size: 13px; margin-top: 5px;")
            answer_label.setWordWrap(True)
            faq_layout.addWidget(answer_label)
            
            content_layout.addWidget(faq_frame)
        
        content_layout.addStretch()
        scroll_area.setWidget(faq_content)
        faq_layout.addWidget(scroll_area)
        
        self.tab_widget.addTab(faq_widget, "❓ FAQ")
    
    def create_contact_tab(self):
        """Create the contact information tab."""
        contact_widget = QWidget()
        contact_layout = QVBoxLayout(contact_widget)
        contact_layout.setContentsMargins(20, 20, 20, 20)
        contact_layout.setSpacing(20)
        
        # Contact info
        contact_frame = QFrame()
        contact_frame.setStyleSheet("""
            QFrame {
                background-color: #252525;
                border-radius: 12px;
                padding: 20px;
            }
        """)
        contact_frame_layout = QVBoxLayout(contact_frame)
        
        title_label = QLabel("Contact Information")
        title_label.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        title_label.setStyleSheet("color: white; margin-bottom: 15px;")
        contact_frame_layout.addWidget(title_label)
        
        contact_info = [
            "📧 Email: support@simcoaches.com",
            "💬 Discord: Join our community server for quick help",
            "📝 Support Tickets: Use the 'Submit Ticket' tab for detailed issues",
            "🔔 Coming Soon: Built-in messaging system for faster support",
            "🕒 Response Time: We typically respond within 24 hours"
        ]
        
        for info in contact_info:
            info_label = QLabel(info)
            info_label.setStyleSheet("color: #ecf0f1; font-size: 14px; margin-bottom: 8px;")
            contact_frame_layout.addWidget(info_label)
        
        contact_layout.addWidget(contact_frame)
        
        # Quick tips
        tips_frame = QFrame()
        tips_frame.setStyleSheet("""
            QFrame {
                background-color: #252525;
                border-radius: 12px;
                padding: 20px;
            }
        """)
        tips_frame_layout = QVBoxLayout(tips_frame)
        
        tips_title = QLabel("Tips for Better Support")
        tips_title.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        tips_title.setStyleSheet("color: white; margin-bottom: 15px;")
        tips_frame_layout.addWidget(tips_title)
        
        tips = [
            "• Include detailed steps to reproduce the issue",
            "• Mention your Windows version and hardware specs",
            "• Attach screenshots if relevant",
            "• Check the FAQ section first for common questions",
            "• Be as specific as possible about error messages"
        ]
        
        for tip in tips:
            tip_label = QLabel(tip)
            tip_label.setStyleSheet("color: #ecf0f1; font-size: 13px; margin-bottom: 5px;")
            tips_frame_layout.addWidget(tip_label)
        
        contact_layout.addWidget(tips_frame)
        contact_layout.addStretch()
        
        self.tab_widget.addTab(contact_widget, "📞 Contact")
    
    def submit_ticket(self):
        """Handle ticket submission."""
        subject = self.subject_input.text().strip()
        priority = self.priority_combo.currentText()
        category = self.category_combo.currentText()
        description = self.description_input.toPlainText().strip()
        
        if not subject:
            QMessageBox.warning(self, "Missing Subject", "Please enter a subject for your ticket.")
            return
        
        if not description:
            QMessageBox.warning(self, "Missing Description", "Please provide a description of your issue.")
            return
        
        # For now, show a confirmation message
        # In a real implementation, this would send the ticket to a support system
        ticket_info = f"""
Ticket submitted successfully!

Subject: {subject}
Priority: {priority}
Category: {category}

Description:
{description}

We'll get back to you soon via email at support@simcoaches.com.

Note: We're building an integrated messaging system that will allow you to track and respond to tickets directly within TrackPro. Stay tuned for this exciting update!
        """.strip()
        
        QMessageBox.information(self, "Ticket Submitted", ticket_info)
        
        # Clear the form
        self.subject_input.clear()
        self.priority_combo.setCurrentText("Medium")
        self.category_combo.setCurrentIndex(0)
        self.description_input.clear()
        
        logger.info(f"Support ticket submitted - Subject: {subject}, Category: {category}, Priority: {priority}")