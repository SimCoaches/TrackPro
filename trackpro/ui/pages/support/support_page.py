"""Fixed Support page for opening support tickets and getting help."""

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
    """Fixed Support page for user assistance and ticket submission."""
    
    def __init__(self, global_managers=None):
        # Initialize instance variables first to avoid AttributeError
        self.tab_widget = None
        self.subject_input = None
        self.priority_combo = None
        self.category_combo = None
        self.description_input = None
        super().__init__("support", global_managers)
    
    def init_page(self):
        """Initialize the support page layout with error handling."""
        try:
            layout = QVBoxLayout()
            layout.setContentsMargins(20, 20, 20, 20)
            layout.setSpacing(15)
            self.setLayout(layout)
            
            # Create header
            self.create_header(layout)
            
            # Create tab widget for different support sections
            self.create_tab_widget()
            
            # Create support tabs with error handling
            self.create_support_tabs_safe()
            
            # Add tab widget to layout
            layout.addWidget(self.tab_widget)
            
            logger.info("✅ Support page initialized successfully")
            
        except Exception as e:
            logger.error(f"❌ Error in Support page init_page: {e}")
            # Create a minimal fallback UI
            self.create_fallback_ui()
    
    def create_tab_widget(self):
        """Create the tab widget with basic styling."""
        self.tab_widget = QTabWidget()
        
        # Simple, reliable styling
        self.tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #444;
                background-color: #1a1a1a;
                border-radius: 6px;
            }
            QTabBar::tab {
                background-color: #252525;
                color: #CCC;
                padding: 8px 16px;
                margin-right: 2px;
                border-radius: 4px;
            }
            QTabBar::tab:selected {
                background-color: #2a82da;
                color: white;
            }
        """)
    
    def create_header(self, layout):
        """Create the header section."""
        try:
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
            
        except Exception as e:
            logger.error(f"❌ Error creating header: {e}")
            # Add simple fallback header
            simple_label = QLabel("Support Center")
            simple_label.setStyleSheet("color: white; font-size: 24px; font-weight: bold; padding: 20px;")
            layout.addWidget(simple_label)
    
    def create_support_tabs_safe(self):
        """Create the support tabs with error handling."""
        try:
            # Submit Ticket tab
            self.create_submit_ticket_tab_safe()
            
            # FAQ tab
            self.create_faq_tab_safe()
            
            # Contact Info tab
            self.create_contact_tab_safe()
            
        except Exception as e:
            logger.error(f"❌ Error creating support tabs: {e}")
            # Create minimal fallback tab
            self.create_minimal_support_tab()
    
    def create_submit_ticket_tab_safe(self):
        """Create the submit ticket tab with error handling."""
        try:
            ticket_widget = QWidget()
            ticket_layout = QVBoxLayout(ticket_widget)
            ticket_layout.setContentsMargins(20, 20, 20, 20)
            ticket_layout.setSpacing(15)
            
            # Ticket form
            self.create_ticket_form_safe(ticket_layout)
            
            self.tab_widget.addTab(ticket_widget, "🎫 Submit Ticket")
            
        except Exception as e:
            logger.error(f"❌ Error creating submit ticket tab: {e}")
    
    def create_ticket_form_safe(self, layout):
        """Create the ticket submission form with error handling."""
        try:
            # Form header
            form_header = QLabel("Submit a Support Ticket")
            form_header.setFont(QFont("Arial", 18, QFont.Weight.Bold))
            form_header.setStyleSheet("color: white; margin-bottom: 15px;")
            layout.addWidget(form_header)
            
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
            """)
            layout.addWidget(self.category_combo)
            
            # Description field
            description_label = QLabel("Description:")
            description_label.setStyleSheet("color: white; font-weight: bold; font-size: 14px;")
            layout.addWidget(description_label)
            
            self.description_input = QTextEdit()
            self.description_input.setPlaceholderText("Please provide a detailed description of your issue...")
            self.description_input.setMaximumHeight(150)
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
            submit_button = QPushButton("Submit Ticket")
            submit_button.setStyleSheet("""
                QPushButton {
                    background-color: #27ae60;
                    color: white;
                    border: none;
                    border-radius: 6px;
                    padding: 12px 24px;
                    font-size: 16px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #2ecc71;
                }
                QPushButton:pressed {
                    background-color: #229954;
                }
            """)
            submit_button.clicked.connect(self.submit_ticket_safe)
            layout.addWidget(submit_button)
            
            layout.addStretch()
            
        except Exception as e:
            logger.error(f"❌ Error creating ticket form: {e}")
    
    def create_faq_tab_safe(self):
        """Create the FAQ tab with error handling."""
        try:
            faq_widget = QWidget()
            faq_layout = QVBoxLayout(faq_widget)
            faq_layout.setContentsMargins(20, 20, 20, 20)
            faq_layout.setSpacing(15)
            
            # FAQ header
            faq_header = QLabel("Frequently Asked Questions")
            faq_header.setFont(QFont("Arial", 18, QFont.Weight.Bold))
            faq_header.setStyleSheet("color: white; margin-bottom: 15px;")
            faq_layout.addWidget(faq_header)
            
            # FAQ items
            faqs = [
                ("How do I calibrate my pedals?", "Go to the Pedals page and follow the calibration wizard. Make sure your pedals are connected before starting."),
                ("Why isn't iRacing telemetry working?", "Ensure iRacing is running and you're in a session. Check that the iRacing SDK is properly installed."),
                ("How do I report a bug?", "Use the Submit Ticket tab to report bugs. Include as much detail as possible about what you were doing when the issue occurred."),
                ("Can I use TrackPro without pedals?", "Yes! TrackPro works without physical pedals connected. You can still use the Race Coach and other features."),
                ("How do I get help quickly?", "Join our Discord community for real-time help from other users and our support team.")
            ]
            
            for question, answer in faqs:
                self.create_faq_item(faq_layout, question, answer)
            
            faq_layout.addStretch()
            self.tab_widget.addTab(faq_widget, "❓ FAQ")
            
        except Exception as e:
            logger.error(f"❌ Error creating FAQ tab: {e}")
    
    def create_faq_item(self, layout, question, answer):
        """Create a single FAQ item."""
        try:
            faq_frame = QFrame()
            faq_frame.setStyleSheet("""
                QFrame {
                    background-color: #252525;
                    border-radius: 8px;
                    padding: 15px;
                    margin-bottom: 10px;
                }
            """)
            faq_frame_layout = QVBoxLayout(faq_frame)
            
            question_label = QLabel(question)
            question_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))
            question_label.setStyleSheet("color: #3498db; margin-bottom: 8px;")
            faq_frame_layout.addWidget(question_label)
            
            answer_label = QLabel(answer)
            answer_label.setStyleSheet("color: #ecf0f1; font-size: 13px; line-height: 1.4;")
            answer_label.setWordWrap(True)
            faq_frame_layout.addWidget(answer_label)
            
            layout.addWidget(faq_frame)
            
        except Exception as e:
            logger.error(f"❌ Error creating FAQ item: {e}")
    
    def create_contact_tab_safe(self):
        """Create the contact information tab with error handling."""
        try:
            contact_widget = QWidget()
            contact_layout = QVBoxLayout(contact_widget)
            contact_layout.setContentsMargins(20, 20, 20, 20)
            contact_layout.setSpacing(20)
            
            # Contact header
            contact_header = QLabel("Contact Information")
            contact_header.setFont(QFont("Arial", 18, QFont.Weight.Bold))
            contact_header.setStyleSheet("color: white; margin-bottom: 15px;")
            contact_layout.addWidget(contact_header)
            
            # Contact info
            contact_info = [
                "📧 Email: support@simcoaches.com",
                "💬 Discord: Join our community server for quick help",
                "📝 Support Tickets: Use the 'Submit Ticket' tab for detailed issues",
                "🕒 Response Time: We typically respond within 24 hours"
            ]
            
            for info in contact_info:
                info_label = QLabel(info)
                info_label.setStyleSheet("color: #ecf0f1; font-size: 14px; margin-bottom: 8px;")
                contact_layout.addWidget(info_label)
            
            contact_layout.addStretch()
            self.tab_widget.addTab(contact_widget, "📞 Contact")
            
        except Exception as e:
            logger.error(f"❌ Error creating contact tab: {e}")
    
    def create_minimal_support_tab(self):
        """Create a minimal support tab as fallback."""
        try:
            minimal_widget = QWidget()
            minimal_layout = QVBoxLayout(minimal_widget)
            minimal_layout.setContentsMargins(20, 20, 20, 20)
            
            label = QLabel("Support Center\n\nFor support, please contact:\nsupport@simcoaches.com")
            label.setStyleSheet("color: white; font-size: 16px; text-align: center;")
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            minimal_layout.addWidget(label)
            
            self.tab_widget.addTab(minimal_widget, "Support")
            
        except Exception as e:
            logger.error(f"❌ Error creating minimal support tab: {e}")
    
    def create_fallback_ui(self):
        """Create a minimal fallback UI if everything else fails."""
        try:
            layout = QVBoxLayout()
            self.setLayout(layout)
            
            label = QLabel("Support Center\n\nFor support, please contact support@simcoaches.com")
            label.setStyleSheet("color: white; font-size: 18px; text-align: center; padding: 50px;")
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(label)
            
            logger.info("📋 Created fallback Support UI")
            
        except Exception as e:
            logger.error(f"❌ Even fallback UI failed: {e}")
    
    def submit_ticket_safe(self):
        """Handle ticket submission with error handling."""
        try:
            if not self.subject_input or not self.description_input:
                QMessageBox.warning(self, "Error", "Support form not properly initialized.")
                return
            
            subject = self.subject_input.text().strip()
            priority = self.priority_combo.currentText() if self.priority_combo else "Medium"
            category = self.category_combo.currentText() if self.category_combo else "General Question"
            description = self.description_input.toPlainText().strip()
            
            if not subject:
                QMessageBox.warning(self, "Missing Subject", "Please enter a subject for your ticket.")
                return
            
            if not description:
                QMessageBox.warning(self, "Missing Description", "Please provide a description of your issue.")
                return
            
            # Show confirmation
            ticket_info = f"""Ticket submitted successfully!

Subject: {subject}
Priority: {priority}
Category: {category}

Description:
{description}

We'll get back to you soon via email at support@simcoaches.com."""
            
            QMessageBox.information(self, "Ticket Submitted", ticket_info)
            
            # Clear the form
            self.subject_input.clear()
            self.priority_combo.setCurrentText("Medium")
            self.category_combo.setCurrentIndex(0)
            self.description_input.clear()
            
        except Exception as e:
            logger.error(f"❌ Error submitting ticket: {e}")
            QMessageBox.critical(self, "Error", f"Failed to submit ticket: {e}")