"""Fixed Support page for opening support tickets and getting help."""

import logging
from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QTextEdit, QPushButton, QComboBox,
    QLineEdit, QFrame, QScrollArea, QWidget, QMessageBox, QTabWidget,
    QCheckBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread, pyqtSignal as Signal
from PyQt6.QtGui import QFont
from ...modern.shared.base_page import BasePage
from .emailjs_client import EmailJSConfig, EmailJSClient

logger = logging.getLogger(__name__)


class EmailSendWorker(QThread):
    """Worker thread for sending emails to avoid blocking the UI."""
    
    email_sent = Signal(bool, str)  # success, message
    
    def __init__(self, emailjs_client, subject, priority, category, description, user_email=None, user_name=None):
        super().__init__()
        self.emailjs_client = emailjs_client
        self.subject = subject
        self.priority = priority
        self.category = category
        self.description = description
        self.user_email = user_email
        self.user_name = user_name
    
    def run(self):
        """Send the email in background thread."""
        try:
            logger.info("🧵 [EMAIL DEBUG] Email worker thread started")
            logger.info(f"🧵 [EMAIL DEBUG] Sending ticket with:")
            logger.info(f"🧵 [EMAIL DEBUG]   Subject: '{self.subject}'")
            logger.info(f"🧵 [EMAIL DEBUG]   Priority: '{self.priority}'")
            logger.info(f"🧵 [EMAIL DEBUG]   Category: '{self.category}'")
            logger.info(f"🧵 [EMAIL DEBUG]   Description: {len(self.description)} chars")
            logger.info(f"🧵 [EMAIL DEBUG]   User email: '{self.user_email}'")
            logger.info(f"🧵 [EMAIL DEBUG]   User name: '{self.user_name}'")
            
            logger.info("🧵 [EMAIL DEBUG] Calling emailjs_client.send_support_ticket()...")
            success = self.emailjs_client.send_support_ticket(
                subject=self.subject,
                priority=self.priority,
                category=self.category,
                description=self.description,
                user_email=self.user_email,
                user_name=self.user_name
            )
            
            logger.info(f"🧵 [EMAIL DEBUG] EmailJS send result: {success}")
            
            if success:
                logger.info("🧵 [EMAIL DEBUG] Emitting success signal")
                self.email_sent.emit(True, "Support ticket sent successfully!")
            else:
                logger.error("🧵 [EMAIL DEBUG] Emitting failure signal")
                self.email_sent.emit(False, "Failed to send support ticket. Please try again.")
                
        except Exception as e:
            logger.error(f"❌ [EMAIL DEBUG] Error in email worker thread: {e}")
            import traceback
            logger.error(f"❌ [EMAIL DEBUG] Worker thread traceback: {traceback.format_exc()}")
            self.email_sent.emit(False, f"Error sending ticket: {str(e)}")

class SupportPage(BasePage):
    """Fixed Support page for user assistance and ticket submission."""
    
    def __init__(self, global_managers=None):
        # Initialize instance variables first to avoid AttributeError
        self.tab_widget = None
        self.subject_input = None
        self.priority_combo = None
        self.category_combo = None
        self.description_input = None
        self.user_email_input = None
        self.user_name_input = None
        self.include_user_info_checkbox = None
        
        # Initialize EmailJS with debugging
        logger.info("🔧 [EMAIL DEBUG] Initializing EmailJS configuration...")
        self.emailjs_config = EmailJSConfig()
        logger.info(f"🔧 [EMAIL DEBUG] EmailJS configured: {self.emailjs_config.is_configured()}")
        
        if self.emailjs_config.is_configured():
            logger.info(f"🔧 [EMAIL DEBUG] Service ID: {self.emailjs_config.service_id}")
            logger.info(f"🔧 [EMAIL DEBUG] Template ID: {self.emailjs_config.template_id}")
            logger.info(f"🔧 [EMAIL DEBUG] Public Key: {self.emailjs_config.public_key[:10]}..." if self.emailjs_config.public_key else "None")
        
        self.emailjs_client = self.emailjs_config.get_client()
        logger.info(f"🔧 [EMAIL DEBUG] EmailJS client created: {self.emailjs_client is not None}")
        
        super().__init__("support", global_managers)
    
    def init_page(self):
        """Initialize the support page layout with proper scrolling."""
        try:
            # Main layout for the page
            main_layout = QVBoxLayout()
            main_layout.setContentsMargins(0, 0, 0, 0)
            main_layout.setSpacing(0)
            self.setLayout(main_layout)
            
            # Content layout directly in main layout
            content_layout = QVBoxLayout()
            content_layout.setContentsMargins(15, 10, 15, 10)  # Reduced margins
            content_layout.setSpacing(8)  # Even more reduced spacing
            
            # Create header
            self.create_header(content_layout)
            
            # Create tab widget for different support sections
            self.create_tab_widget()
            
            # Create support tabs with error handling
            self.create_support_tabs_safe()
            
            # Add tab widget to content layout
            content_layout.addWidget(self.tab_widget)
            content_layout.addStretch()  # Add stretch to push content to top
            
            # Add content layout directly to main layout
            main_layout.addLayout(content_layout)
            
            logger.info("✅ Support page initialized successfully")
            
        except Exception as e:
            logger.error(f"❌ Error in Support page init_page: {e}")
            # Create a minimal fallback UI
            self.create_fallback_ui()
    
    def create_tab_widget(self):
        """Create the tab widget with compact styling."""
        self.tab_widget = QTabWidget()
        
        # Compact, reliable styling
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
                padding: 10px 16px;
                margin-right: 2px;
                border-radius: 4px;
                font-size: 13px;
                min-height: 20px;
                max-height: 35px;
            }
            QTabBar::tab:selected {
                background-color: #2a82da;
                color: white;
            }
        """)
    
    def create_header(self, layout):
        """Create a minimal header section."""
        try:
            header_frame = QFrame()
            header_frame.setMaximumHeight(50)  # Even more compact
            header_frame.setStyleSheet("""
                QFrame {
                    background-color: #252525;
                    border-radius: 6px;
                    padding: 8px 15px;
                    max-height: 50px;
                }
            """)
            header_layout = QHBoxLayout(header_frame)  # Horizontal layout
            header_layout.setContentsMargins(10, 5, 10, 5)
            header_layout.setSpacing(15)
            
            # Title
            title_label = QLabel("Support Center")
            title_label.setFont(QFont("Arial", 16, QFont.Weight.Bold))
            title_label.setStyleSheet("color: white; margin: 0;")
            header_layout.addWidget(title_label)
            
            # Description (inline)
            desc_label = QLabel("Get help, report issues, or submit feature requests")
            desc_label.setFont(QFont("Arial", 11))
            desc_label.setStyleSheet("color: #b0b0b0; margin: 0;")
            header_layout.addWidget(desc_label)
            header_layout.addStretch()  # Push content to left
            
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
            
        except Exception as e:
            logger.error(f"❌ Error creating support tabs: {e}")
            # Create minimal fallback tab
            self.create_minimal_support_tab()
    
    def create_submit_ticket_tab_safe(self):
        """Create the submit ticket tab with proper scrolling."""
        try:
            ticket_widget = QWidget()
            ticket_main_layout = QVBoxLayout(ticket_widget)
            ticket_main_layout.setContentsMargins(0, 0, 0, 0)
            ticket_main_layout.setSpacing(0)
            
            # Form layout directly in ticket widget
            form_layout = QVBoxLayout()
            form_layout.setContentsMargins(15, 15, 15, 15)  # Reduced margins
            form_layout.setSpacing(8)  # Even more reduced spacing
            
            # Ticket form
            self.create_ticket_form_safe(form_layout)
            form_layout.addStretch()  # Add stretch at the bottom
            
            # Add form layout directly to ticket main layout
            ticket_main_layout.addLayout(form_layout)
            
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
            
            # EmailJS status indicator
            if self.emailjs_client:
                status_label = QLabel("✅ Email delivery enabled")
                status_label.setStyleSheet("color: #27ae60; font-size: 12px; margin-bottom: 10px;")
            else:
                status_label = QLabel("⚠️ Email delivery not configured - tickets will be shown locally")
                status_label.setStyleSheet("color: #f39c12; font-size: 12px; margin-bottom: 10px;")
            layout.addWidget(status_label)
            
            # User profile info status
            profile_status_label = QLabel("👤 Your contact information will be automatically included from your profile")
            profile_status_label.setStyleSheet("color: #3498db; font-size: 12px; margin-bottom: 10px; padding: 8px; background-color: rgba(52, 152, 219, 0.1); border-radius: 4px;")
            layout.addWidget(profile_status_label)
            
            # Subject field
            subject_label = QLabel("Subject:")
            subject_label.setStyleSheet("color: white; font-weight: bold; font-size: 14px; margin-top: 8px; margin-bottom: 4px;")
            layout.addWidget(subject_label)
            
            self.subject_input = QLineEdit()
            self.subject_input.setPlaceholderText("Brief description of your issue...")
            self.subject_input.setMinimumHeight(35)
            self.subject_input.setStyleSheet("""
                QLineEdit {
                    background-color: #252525;
                    border: 2px solid #34495e;
                    border-radius: 6px;
                    padding: 10px;
                    color: white;
                    font-size: 14px;
                    min-height: 35px;
                }
                QLineEdit:focus {
                    border-color: #3498db;
                }
            """)
            layout.addWidget(self.subject_input)
            
            # Priority selection
            priority_label = QLabel("Priority:")
            priority_label.setStyleSheet("color: white; font-weight: bold; font-size: 14px; margin-top: 8px; margin-bottom: 4px;")
            layout.addWidget(priority_label)
            
            self.priority_combo = QComboBox()
            self.priority_combo.addItems(["Low", "Medium", "High", "Critical"])
            self.priority_combo.setCurrentText("Medium")
            self.priority_combo.setMinimumHeight(35)
            self.priority_combo.setStyleSheet("""
                QComboBox {
                    background-color: #252525;
                    border: 2px solid #34495e;
                    border-radius: 6px;
                    padding: 10px;
                    color: white;
                    font-size: 14px;
                    min-height: 35px;
                }
                QComboBox:focus {
                    border-color: #3498db;
                }
            """)
            layout.addWidget(self.priority_combo)
            
            # Category selection
            category_label = QLabel("Category:")
            category_label.setStyleSheet("color: white; font-weight: bold; font-size: 14px; margin-top: 8px; margin-bottom: 4px;")
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
            self.category_combo.setMinimumHeight(35)
            self.category_combo.setStyleSheet("""
                QComboBox {
                    background-color: #252525;
                    border: 2px solid #34495e;
                    border-radius: 6px;
                    padding: 10px;
                    color: white;
                    font-size: 14px;
                    min-height: 35px;
                }
                QComboBox:focus {
                    border-color: #3498db;
                }
            """)
            layout.addWidget(self.category_combo)
            
            # Description field
            description_label = QLabel("Description:")
            description_label.setStyleSheet("color: white; font-weight: bold; font-size: 14px; margin-top: 8px; margin-bottom: 4px;")
            layout.addWidget(description_label)
            
            self.description_input = QTextEdit()
            self.description_input.setPlaceholderText("Please provide a detailed description of your issue...")
            self.description_input.setMinimumHeight(80)
            self.description_input.setMaximumHeight(120)
            self.description_input.setStyleSheet("""
                QTextEdit {
                    background-color: #252525;
                    border: 2px solid #34495e;
                    border-radius: 6px;
                    padding: 10px;
                    color: white;
                    font-size: 14px;
                    line-height: 1.3;
                    min-height: 80px;
                }
                QTextEdit:focus {
                    border-color: #3498db;
                }
            """)
            layout.addWidget(self.description_input)
            
            # Submit button
            submit_button = QPushButton("Submit Ticket")
            submit_button.setMinimumHeight(40)
            submit_button.setStyleSheet("""
                QPushButton {
                    background-color: #27ae60;
                    color: white;
                    border: none;
                    border-radius: 6px;
                    padding: 12px 24px;
                    font-size: 15px;
                    font-weight: bold;
                    min-height: 40px;
                    margin-top: 10px;
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
    
    # User info section removed - now gets info from authenticated user profile automatically
    
    # Toggle method removed - no longer needed since user info comes from profile
    
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
            logger.info("🎫 [EMAIL DEBUG] Submit ticket clicked!")
            
            # First check if user is authenticated via Supabase
            try:
                from trackpro.database.supabase_client import get_supabase_client
                supabase_client = get_supabase_client()
                user_response = supabase_client.auth.get_user() if supabase_client else None
                
                if not user_response or not user_response.user:
                    QMessageBox.warning(self, "Authentication Required", 
                                      "You must be signed in to submit support tickets.\n\n"
                                      "Please sign in from the Account page and try again.")
                    logger.warning("🎫 [EMAIL DEBUG] User not authenticated - blocking submission")
                    return
                    
            except Exception as e:
                logger.error(f"🎫 [EMAIL DEBUG] Error checking authentication: {e}")
                QMessageBox.warning(self, "Authentication Error", 
                                  "Unable to verify authentication status.\n\n"
                                  "Please try signing in again.")
                return
            
            if not self.subject_input or not self.description_input:
                logger.error("🎫 [EMAIL DEBUG] Form not properly initialized")
                QMessageBox.warning(self, "Error", "Support form not properly initialized.")
                return
            
            subject = self.subject_input.text().strip()
            priority = self.priority_combo.currentText() if self.priority_combo else "Medium"
            category = self.category_combo.currentText() if self.category_combo else "General Question"
            description = self.description_input.toPlainText().strip()
            
            logger.info(f"🎫 [EMAIL DEBUG] Form data collected:")
            logger.info(f"🎫 [EMAIL DEBUG]   Subject: '{subject}'")
            logger.info(f"🎫 [EMAIL DEBUG]   Priority: '{priority}'")
            logger.info(f"🎫 [EMAIL DEBUG]   Category: '{category}'")
            logger.info(f"🎫 [EMAIL DEBUG]   Description length: {len(description)} chars")
            
            # Get user info from authenticated profile
            user_name = None
            user_email = None
            
            # Get user info from authenticated Supabase session
            try:
                from trackpro.database.supabase_client import get_supabase_client
                supabase_client = get_supabase_client()
                user_response = supabase_client.auth.get_user() if supabase_client else None
                
                if user_response and user_response.user:
                    # Get user info from Supabase profile
                    user_email = user_response.user.email or 'No email on file'
                    user_name = (user_response.user.user_metadata.get('full_name') or 
                               user_response.user.user_metadata.get('name') or 
                               'TrackPro User')
                    logger.info(f"🎫 [EMAIL DEBUG]   Using authenticated user: {user_name} ({user_email})")
                else:
                    # User not authenticated - shouldn't happen since we checked above
                    user_email = "Anonymous User"
                    user_name = "TrackPro User"
                    logger.warning(f"🎫 [EMAIL DEBUG]   User not authenticated - this shouldn't happen!")
                    
            except Exception as e:
                logger.error(f"🎫 [EMAIL DEBUG]   Error getting user info: {e}")
                user_email = "Error retrieving email"
                user_name = "TrackPro User"
            
            if not subject:
                logger.warning("🎫 [EMAIL DEBUG] Missing subject")
                QMessageBox.warning(self, "Missing Subject", "Please enter a subject for your ticket.")
                return
            
            if not description:
                logger.warning("🎫 [EMAIL DEBUG] Missing description")
                QMessageBox.warning(self, "Missing Description", "Please provide a description of your issue.")
                return
            
            # Email validation removed - user email comes from authenticated profile
            
            # Try to send via EmailJS if configured
            logger.info(f"🎫 [EMAIL DEBUG] EmailJS client available: {self.emailjs_client is not None}")
            if self.emailjs_client:
                logger.info("🎫 [EMAIL DEBUG] Attempting to send via EmailJS...")
                self.send_ticket_via_email(subject, priority, category, description, user_email, user_name)
            else:
                logger.info("🎫 [EMAIL DEBUG] No EmailJS client, using fallback...")
                # Fallback to local confirmation
                self.show_local_ticket_confirmation(subject, priority, category, description, user_email, user_name)
            
        except Exception as e:
            logger.error(f"❌ [EMAIL DEBUG] Error submitting ticket: {e}")
            import traceback
            logger.error(f"❌ [EMAIL DEBUG] Traceback: {traceback.format_exc()}")
            QMessageBox.critical(self, "Error", f"Failed to submit ticket: {e}")
    
    # Email validation method removed - no longer needed
    
    def send_ticket_via_email(self, subject, priority, category, description, user_email, user_name):
        """Send support ticket via EmailJS."""
        try:
            logger.info("📧 [EMAIL DEBUG] Starting email sending process...")
            
            # Disable submit button to prevent double submission
            submit_buttons = self.findChildren(QPushButton)
            button_found = False
            for btn in submit_buttons:
                if "submit" in btn.text().lower():
                    btn.setEnabled(False)
                    btn.setText("Sending...")
                    button_found = True
                    logger.info("📧 [EMAIL DEBUG] Submit button disabled and text changed")
                    break
            
            if not button_found:
                logger.warning("📧 [EMAIL DEBUG] Submit button not found!")
            
            # Create and start email worker thread
            logger.info("📧 [EMAIL DEBUG] Creating EmailSendWorker...")
            self.email_worker = EmailSendWorker(
                self.emailjs_client, subject, priority, category, description, user_email, user_name
            )
            logger.info("📧 [EMAIL DEBUG] Connecting email_sent signal...")
            self.email_worker.email_sent.connect(self.on_email_sent)
            logger.info("📧 [EMAIL DEBUG] Starting email worker thread...")
            self.email_worker.start()
            logger.info("📧 [EMAIL DEBUG] Email worker thread started successfully")
            
        except Exception as e:
            logger.error(f"❌ [EMAIL DEBUG] Error starting email worker: {e}")
            import traceback
            logger.error(f"❌ [EMAIL DEBUG] Traceback: {traceback.format_exc()}")
            QMessageBox.critical(self, "Error", f"Failed to send ticket: {e}")
            self.reset_submit_button()
    
    def on_email_sent(self, success, message):
        """Handle email send result."""
        try:
            logger.info(f"📧 [EMAIL DEBUG] Email send result received: success={success}, message='{message}'")
            self.reset_submit_button()
            
            if success:
                logger.info("✅ [EMAIL DEBUG] Email sent successfully!")
                # Show success message
                QMessageBox.information(self, "Ticket Sent", 
                    f"{message}\n\nYour support ticket has been sent to our team. "
                    f"We'll get back to you as soon as possible!")
                
                # Clear the form
                self.clear_form()
                logger.info("✅ [EMAIL DEBUG] Support ticket sent successfully via EmailJS")
            else:
                logger.error(f"❌ [EMAIL DEBUG] Email send failed: {message}")
                # Show error and fallback option
                reply = QMessageBox.question(self, "Send Failed", 
                    f"{message}\n\nWould you like to see the ticket details for manual submission?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                
                if reply == QMessageBox.StandardButton.Yes:
                    logger.info("📧 [EMAIL DEBUG] User chose to see ticket details for manual submission")
                    self.show_local_ticket_confirmation()
                else:
                    logger.info("📧 [EMAIL DEBUG] User chose not to see ticket details")
                    
        except Exception as e:
            logger.error(f"❌ [EMAIL DEBUG] Error handling email send result: {e}")
            import traceback
            logger.error(f"❌ [EMAIL DEBUG] Traceback: {traceback.format_exc()}")
            QMessageBox.critical(self, "Error", "An unexpected error occurred.")
    
    def reset_submit_button(self):
        """Reset submit button state."""
        try:
            submit_buttons = self.findChildren(QPushButton)
            for btn in submit_buttons:
                if "sending" in btn.text().lower() or "submit" in btn.text().lower():
                    btn.setEnabled(True)
                    btn.setText("Submit Ticket")
                    break
        except Exception as e:
            logger.error(f"❌ Error resetting submit button: {e}")
    
    def show_local_ticket_confirmation(self, subject=None, priority=None, category=None, description=None, user_email=None, user_name=None):
        """Show local ticket confirmation as fallback."""
        try:
            # Get current form values if not provided
            if subject is None:
                subject = self.subject_input.text().strip()
                priority = self.priority_combo.currentText() if self.priority_combo else "Medium"
                category = self.category_combo.currentText() if self.category_combo else "General Question"
                description = self.description_input.toPlainText().strip()
                
                if (self.include_user_info_checkbox and 
                    self.include_user_info_checkbox.isChecked() and
                    self.user_name_input and self.user_email_input):
                    user_name = self.user_name_input.text().strip() or None
                    user_email = self.user_email_input.text().strip() or None
            
            # Build ticket info message
            ticket_info = f"""Ticket Details (Please send manually):

Subject: {subject}
Priority: {priority}
Category: {category}

Description:
{description}"""
            
            if user_name or user_email:
                ticket_info += f"\n\nContact Information:"
                if user_name:
                    ticket_info += f"\nName: {user_name}"
                if user_email:
                    ticket_info += f"\nEmail: {user_email}"
            
            ticket_info += f"\n\nPlease send this information to: support@simcoaches.com"
            
            QMessageBox.information(self, "Ticket Information", ticket_info)
            self.clear_form()
            
        except Exception as e:
            logger.error(f"❌ Error showing local ticket confirmation: {e}")
    
    def clear_form(self):
        """Clear the support form."""
        try:
            if self.subject_input:
                self.subject_input.clear()
            if self.priority_combo:
                self.priority_combo.setCurrentText("Medium")
            if self.category_combo:
                self.category_combo.setCurrentIndex(0)
            if self.description_input:
                self.description_input.clear()
            if self.include_user_info_checkbox:
                self.include_user_info_checkbox.setChecked(False)
            if self.user_name_input:
                self.user_name_input.clear()
            if self.user_email_input:
                self.user_email_input.clear()
        except Exception as e:
            logger.error(f"❌ Error clearing form: {e}")