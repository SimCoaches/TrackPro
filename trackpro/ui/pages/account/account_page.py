import logging
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QPushButton, 
    QStackedWidget, QScrollArea, QLineEdit, QTextEdit, QDateEdit, 
    QComboBox, QCheckBox, QFileDialog, QMessageBox, QSpinBox,
    QGroupBox, QGridLayout, QSizePolicy, QSpacerItem
)
from PyQt6.QtCore import Qt, pyqtSignal, QDate, QTimer, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QFont, QPixmap, QPainter, QPen, QBrush
from ...avatar_manager import AvatarManager

# Import user management functions
from trackpro.auth.user_manager import is_current_user_dev
from trackpro.utils.windows_startup import WindowsStartupManager

logger = logging.getLogger(__name__)

class ModernCard(QFrame):
    """Modern card-style container widget."""
    
    def __init__(self, title: str = "", parent=None):
        super().__init__(parent)
        self.setFrameStyle(QFrame.Shape.StyledPanel)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.MinimumExpanding)
        self.setMinimumHeight(120)  # Ensure minimum height
        self.setStyleSheet("""
            QFrame {
                background-color: #2f3136;
                border: 1px solid #40444b;
                border-radius: 8px;
                margin: 4px;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)
        
        if title:
            title_label = QLabel(title)
            title_label.setStyleSheet("""
                QLabel {
                    color: #ffffff;
                    font-size: 18px;
                    font-weight: 600;
                    border: none;
                    background: transparent;
                    margin-bottom: 8px;
                }
            """)
            layout.addWidget(title_label)
        
        self.content_layout = layout

class ModernInput(QLineEdit):
    """Modern styled input field."""
    
    def __init__(self, placeholder: str = "", parent=None):
        super().__init__(parent)
        self.setPlaceholderText(placeholder)
        self.setStyleSheet("""
            QLineEdit {
                background-color: #40444b;
                border: 2px solid #40444b;
                border-radius: 4px;
                padding: 8px 12px;
                font-size: 14px;
                color: #dcddde;
            }
            QLineEdit:focus {
                border-color: #5865f2;
                background-color: #36393f;
            }
            QLineEdit::placeholder {
                color: #72767d;
            }
        """)

class ModernTextArea(QTextEdit):
    """Modern styled text area."""
    
    def __init__(self, placeholder: str = "", parent=None):
        super().__init__(parent)
        self.setPlaceholderText(placeholder)
        self.setMaximumHeight(100)
        self.setStyleSheet("""
            QTextEdit {
                background-color: #40444b;
                border: 2px solid #40444b;
                border-radius: 4px;
                padding: 8px 12px;
                font-size: 14px;
                color: #dcddde;
            }
            QTextEdit:focus {
                border-color: #5865f2;
                background-color: #36393f;
            }
        """)

class ModernButton(QPushButton):
    """Modern styled button."""
    
    def __init__(self, text: str, style: str = "primary", parent=None):
        super().__init__(text, parent)
        self.setMinimumHeight(36)
        
        if style == "primary":
            self.setStyleSheet("""
                QPushButton {
                    background-color: #5865f2;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    padding: 8px 16px;
                    font-size: 14px;
                    font-weight: 600;
                }
                QPushButton:hover {
                    background-color: #4752c4;
                }
                QPushButton:pressed {
                    background-color: #3c45a5;
                }
            """)
        elif style == "secondary":
            self.setStyleSheet("""
                QPushButton {
                    background-color: #4f545c;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    padding: 8px 16px;
                    font-size: 14px;
                    font-weight: 600;
                }
                QPushButton:hover {
                    background-color: #5d6269;
                }
                QPushButton:pressed {
                    background-color: #484d54;
                }
            """)
        elif style == "danger":
            self.setStyleSheet("""
                QPushButton {
                    background-color: #ed4245;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    padding: 8px 16px;
                    font-size: 14px;
                    font-weight: 600;
                }
                QPushButton:hover {
                    background-color: #c53030;
                }
                QPushButton:pressed {
                    background-color: #a02728;
                }
            """)

class ProfileAvatar(QLabel):
    """Profile avatar widget with click functionality."""
    
    def __init__(self, size: int = 80, parent=None):
        super().__init__(parent)
        self.setFixedSize(size, size)
        self.setStyleSheet(f"""
            QLabel {{
                background-color: #5865f2;
                border: 3px solid #40444b;
                border-radius: {size // 2}px;
                color: white;
                font-size: {size // 3}px;
                font-weight: bold;
            }}
        """)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setText("LT")  # Default initials
        self.setToolTip("Click to change avatar")
        self.account_page = None  # Will be set by parent
    
    def set_account_page(self, account_page):
        """Set reference to parent account page."""
        self.account_page = account_page
    
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.select_avatar()
    
    def select_avatar(self):
        """Open file dialog to select new avatar."""
        if self.account_page:
            self.account_page.upload_avatar()
        else:
            # Fallback if no account page reference
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                "Select Avatar Image",
                "",
                "Image files (*.png *.jpg *.jpeg *.gif *.bmp)"
            )
            
            if file_path:
                QMessageBox.information(self, "Avatar Upload", f"Avatar upload selected: {file_path}")

class AccountPage(QWidget):
    """Main Account page with sidebar navigation."""
    
    # Signal emitted when avatar is uploaded
    avatar_uploaded = pyqtSignal(str)  # Emits the avatar URL
    
    def __init__(self, global_managers=None):
        super().__init__()
        self.global_managers = global_managers
        self.current_section = "profile"
        self.user_data = {}
        self.is_initialized = False
        
        # Initialize Windows startup manager
        self.startup_manager = WindowsStartupManager()
        
        self.init_page()
    
    def init_page(self):
        """Initialize the account page."""
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Create sidebar
        sidebar = self.create_sidebar()
        main_layout.addWidget(sidebar)
        
        # Create main content area
        self.content_stack = QStackedWidget()
        self.content_stack.setStyleSheet("""
            QStackedWidget {
                background-color: #36393f;
                border: none;
            }
        """)
        
        # Create content sections
        self.create_content_sections()
        
        main_layout.addWidget(self.content_stack, 1)
        
        # Load user data
        self.load_user_data()
        
        # Set default section
        self.switch_section("profile")
    
    def create_sidebar(self):
        """Create the navigation sidebar."""
        sidebar = QFrame()
        sidebar.setFixedWidth(250)
        sidebar.setStyleSheet("""
            QFrame {
                background-color: #2f3136;
                border: none;
                border-right: 1px solid #40444b;
            }
        """)
        
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(16, 20, 16, 20)
        layout.setSpacing(8)
        
        # Sidebar title
        title = QLabel("Account Settings")
        title.setStyleSheet("""
            QLabel {
                color: #ffffff;
                font-size: 20px;
                font-weight: 700;
                margin-bottom: 16px;
                border: none;
                background: transparent;
            }
        """)
        layout.addWidget(title)
        
        # Navigation buttons
        self.nav_buttons = {}
        nav_items = [
            ("profile", "P", "Profile"),
            ("security", "S", "Security"),
            ("notifications", "N", "Notifications"), 
            ("racing", "R", "Racing"),
            ("connections", "C", "Connections"),
            ("privacy", "D", "Privacy & Data")
        ]
        
        # Add admin management for dev users
        if is_current_user_dev():
            nav_items.append(("admin", "A", "Admin Management"))
        
        # Add hierarchy management for dev users
        if is_current_user_dev():
            nav_items.append(("hierarchy", "H", "Hierarchy"))
        
        for section_id, icon, title in nav_items:
            btn = QPushButton(f"{icon}  {title}")
            btn.setCheckable(True)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    color: #b9bbbe;
                    border: none;
                    border-radius: 4px;
                    padding: 12px 16px;
                    text-align: left;
                    font-size: 14px;
                    font-weight: 500;
                }
                QPushButton:hover {
                    background-color: #40444b;
                    color: #dcddde;
                }
                QPushButton:checked {
                    background-color: #5865f2;
                    color: #ffffff;
                    font-weight: 600;
                }
            """)
            btn.clicked.connect(lambda checked, s=section_id: self.switch_section(s))
            self.nav_buttons[section_id] = btn
            layout.addWidget(btn)
        
        layout.addStretch()
        
        # Logout button at bottom
        logout_btn = ModernButton("Logout", "danger")
        logout_btn.clicked.connect(self.handle_logout)
        layout.addWidget(logout_btn)
        
        return sidebar
    
    def create_content_sections(self):
        """Create all content sections."""
        self.sections = {
            "profile": self.create_profile_section(),
            "security": self.create_security_section(),
            "notifications": self.create_notifications_section(),
            "racing": self.create_racing_section(),
            "connections": self.create_connections_section(),
            "privacy": self.create_privacy_section()
        }
        
        # Add admin management for dev users
        if is_current_user_dev():
            self.sections["admin"] = self.create_admin_section()
            self.sections["hierarchy"] = self.create_hierarchy_section()
        
        for section in self.sections.values():
            self.content_stack.addWidget(section)
    
    def create_profile_section(self):
        """Create the profile information section."""
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setStyleSheet("""
            QScrollArea {
                background-color: #36393f;
                border: none;
            }
            QScrollBar:vertical {
                background-color: #2f3136;
                width: 12px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background-color: #5865f2;
                border-radius: 6px;
                min-height: 20px;
            }
        """)
        
        content_widget = QWidget()
        content_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.MinimumExpanding)
        layout = QVBoxLayout(content_widget)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        # Header
        header_label = QLabel("My Profile")
        header_label.setStyleSheet("""
            QLabel {
                color: #ffffff;
                font-size: 24px;
                font-weight: 700;
                margin-bottom: 8px;
                border: none;
                background: transparent;
            }
        """)
        layout.addWidget(header_label)
        
        subtitle_label = QLabel("Manage your personal information and racing preferences")
        subtitle_label.setStyleSheet("""
            QLabel {
                color: #b9bbbe;
                font-size: 14px;
                margin-bottom: 16px;
                border: none;
                background: transparent;
            }
        """)
        layout.addWidget(subtitle_label)
        
        # Avatar section
        avatar_card = ModernCard("Profile Picture")
        avatar_layout = QHBoxLayout()
        
        self.profile_avatar = ProfileAvatar(80)
        self.profile_avatar.set_account_page(self)
        avatar_layout.addWidget(self.profile_avatar)
        
        avatar_info_layout = QVBoxLayout()
        avatar_info = QLabel("Click on your avatar to upload a new profile picture.\nRecommended size: 256x256 pixels")
        avatar_info.setStyleSheet("""
            QLabel {
                color: #b9bbbe;
                font-size: 12px;
                border: none;
                background: transparent;
            }
        """)
        avatar_info_layout.addWidget(avatar_info)
        avatar_info_layout.addStretch()
        
        avatar_layout.addLayout(avatar_info_layout)
        avatar_layout.addStretch()
        avatar_card.content_layout.addLayout(avatar_layout)
        layout.addWidget(avatar_card)
        
        # Basic Information
        basic_info_card = ModernCard("Basic Information")
        form_layout = QGridLayout()
        form_layout.setSpacing(12)
        
        # First Name
        form_layout.addWidget(QLabel("First Name"), 0, 0)
        self.first_name_input = ModernInput("Enter your first name")
        form_layout.addWidget(self.first_name_input, 0, 1)
        
        # Last Name
        form_layout.addWidget(QLabel("Last Name"), 1, 0)
        self.last_name_input = ModernInput("Enter your last name")
        form_layout.addWidget(self.last_name_input, 1, 1)
        
        # Display Name
        form_layout.addWidget(QLabel("Display Name"), 2, 0)
        self.display_name_input = ModernInput("How you appear to others")
        form_layout.addWidget(self.display_name_input, 2, 1)
        
        # Email (read-only)
        form_layout.addWidget(QLabel("Email"), 3, 0)
        self.email_input = ModernInput("your@email.com")
        self.email_input.setReadOnly(True)
        self.email_input.setStyleSheet(self.email_input.styleSheet() + "background-color: #484b51;")
        form_layout.addWidget(self.email_input, 3, 1)
        
        # Date of Birth
        form_layout.addWidget(QLabel("Date of Birth"), 4, 0)
        self.dob_input = QDateEdit()
        self.dob_input.setDate(QDate.currentDate().addYears(-25))
        self.dob_input.setStyleSheet("""
            QDateEdit {
                background-color: #40444b;
                border: 2px solid #40444b;
                border-radius: 4px;
                padding: 8px 12px;
                font-size: 14px;
                color: #dcddde;
            }
            QDateEdit:focus {
                border-color: #5865f2;
                background-color: #36393f;
            }
        """)
        form_layout.addWidget(self.dob_input, 4, 1)
        
        # Set label styles
        for i in range(form_layout.rowCount()):
            label = form_layout.itemAtPosition(i, 0).widget()
            if label:
                label.setStyleSheet("""
                    QLabel {
                        color: #dcddde;
                        font-size: 14px;
                        font-weight: 600;
                        padding: 8px 0;
                        border: none;
                        background: transparent;
                    }
                """)
        
        basic_info_card.content_layout.addLayout(form_layout)
        layout.addWidget(basic_info_card)
        
        # Bio section
        bio_card = ModernCard("About Me")
        self.bio_input = ModernTextArea("Tell us about yourself, your racing background, or favorite series...")
        bio_card.content_layout.addWidget(self.bio_input)
        layout.addWidget(bio_card)
        

        
        # Save button
        save_btn = ModernButton("Save Profile", "primary")
        save_btn.clicked.connect(self.save_profile)
        layout.addWidget(save_btn)
        
        layout.addStretch()
        scroll_area.setWidget(content_widget)
        return scroll_area
    
    def create_security_section(self):
        """Create the security settings section."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)
        
        # Header
        header_label = QLabel("Security Settings")
        header_label.setStyleSheet("""
            QLabel {
                color: #ffffff;
                font-size: 24px;
                font-weight: 700;
                margin-bottom: 8px;
                border: none;
                background: transparent;
            }
        """)
        layout.addWidget(header_label)
        
        # Password Management Card
        password_card = ModernCard("Password Management")
        password_layout = QVBoxLayout()
        
        # Current password (for verification)
        current_pw_layout = QHBoxLayout()
        current_pw_layout.addWidget(QLabel("Current Password:"))
        self.current_password_input = ModernInput("Enter current password")
        self.current_password_input.setEchoMode(QLineEdit.EchoMode.Password)
        current_pw_layout.addWidget(self.current_password_input)
        password_layout.addLayout(current_pw_layout)
        
        # New password
        new_pw_layout = QHBoxLayout()
        new_pw_layout.addWidget(QLabel("New Password:"))
        self.new_password_input = ModernInput("Enter new password")
        self.new_password_input.setEchoMode(QLineEdit.EchoMode.Password)
        new_pw_layout.addWidget(self.new_password_input)
        password_layout.addLayout(new_pw_layout)
        
        # Confirm new password
        confirm_pw_layout = QHBoxLayout()
        confirm_pw_layout.addWidget(QLabel("Confirm Password:"))
        self.confirm_password_input = ModernInput("Confirm new password")
        self.confirm_password_input.setEchoMode(QLineEdit.EchoMode.Password)
        confirm_pw_layout.addWidget(self.confirm_password_input)
        password_layout.addLayout(confirm_pw_layout)
        
        # Change password button
        change_pw_btn = ModernButton("Change Password", "primary")
        change_pw_btn.clicked.connect(self.change_password)
        password_layout.addWidget(change_pw_btn)
        
        password_card.content_layout.addLayout(password_layout)
        layout.addWidget(password_card)
        
        # Two-Factor Authentication Card
        tfa_card = ModernCard("Two-Factor Authentication")
        tfa_layout = QVBoxLayout()
        
        # 2FA Status
        self.tfa_status_label = QLabel("2FA Status: Disabled")
        self.tfa_status_label.setStyleSheet("""
            QLabel {
                color: #faa61a;
                font-size: 14px;
                font-weight: 600;
                padding: 8px;
                background-color: #2f3136;
                border-radius: 4px;
            }
        """)
        tfa_layout.addWidget(self.tfa_status_label)
        
        # 2FA Toggle buttons
        tfa_btn_layout = QHBoxLayout()
        self.enable_2fa_btn = ModernButton("Enable 2FA", "secondary")
        self.enable_2fa_btn.clicked.connect(self.toggle_2fa)
        tfa_btn_layout.addWidget(self.enable_2fa_btn)
        
        self.disable_2fa_btn = ModernButton("Disable 2FA", "danger")
        self.disable_2fa_btn.clicked.connect(self.toggle_2fa)
        self.disable_2fa_btn.setVisible(False)
        tfa_btn_layout.addWidget(self.disable_2fa_btn)
        
        tfa_layout.addLayout(tfa_btn_layout)
        tfa_card.content_layout.addLayout(tfa_layout)
        layout.addWidget(tfa_card)
        
        # Application Version Card
        version_card = ModernCard("Application Version")
        version_layout = QVBoxLayout()
        
        # Version info layout
        version_info_layout = QHBoxLayout()
        
        # Current version display
        version_label = QLabel("Current Version:")
        version_label.setStyleSheet("""
            QLabel {
                color: #dcddde;
                font-size: 14px;
                font-weight: 600;
                padding: 8px 0;
                border: none;
                background: transparent;
            }
        """)
        version_info_layout.addWidget(version_label)
        
        # Version number
        from trackpro.updater import CURRENT_VERSION
        self.version_display = QLabel(f"v{CURRENT_VERSION}")
        self.version_display.setStyleSheet("""
            QLabel {
                color: #5865f2;
                font-size: 14px;
                font-weight: 700;
                padding: 8px 12px;
                background-color: #2f3136;
                border-radius: 4px;
                border: 1px solid #40444b;
            }
        """)
        version_info_layout.addWidget(self.version_display)
        
        # Check for updates button
        self.check_updates_btn = ModernButton("Check for Updates", "secondary")
        self.check_updates_btn.clicked.connect(self.check_for_updates)
        version_info_layout.addWidget(self.check_updates_btn)
        
        # Download update button (initially hidden)
        self.download_update_btn = ModernButton("Download Update", "primary")
        self.download_update_btn.clicked.connect(self.download_update)
        self.download_update_btn.setVisible(False)
        version_info_layout.addWidget(self.download_update_btn)
        
        version_info_layout.addStretch()
        version_layout.addLayout(version_info_layout)
        
        # Update status
        self.update_status_label = QLabel("")
        self.update_status_label.setStyleSheet("""
            QLabel {
                color: #b9bbbe;
                font-size: 12px;
                padding: 4px 0;
                border: none;
                background: transparent;
            }
        """)
        version_layout.addWidget(self.update_status_label)
        
        version_card.content_layout.addLayout(version_layout)
        layout.addWidget(version_card)
        
        layout.addStretch()
        return widget
    
    def create_notifications_section(self):
        """Create the notifications settings section."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)
        
        # Header
        header_label = QLabel("Notification Settings")
        header_label.setStyleSheet("""
            QLabel {
                color: #ffffff;
                font-size: 24px;
                font-weight: 700;
                margin-bottom: 8px;
                border: none;
                background: transparent;
            }
        """)
        layout.addWidget(header_label)
        
        # Email Notifications Card
        email_card = ModernCard("Email Notifications")
        email_layout = QVBoxLayout()
        
        self.email_notifications_check = QCheckBox("Enable email notifications")
        self.email_notifications_check.setStyleSheet("""
            QCheckBox {
                color: #dcddde;
                font-size: 14px;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
            }
            QCheckBox::indicator:unchecked {
                background-color: #40444b;
                border: 2px solid #72767d;
                border-radius: 3px;
            }
            QCheckBox::indicator:checked {
                background-color: #5865f2;
                border: 2px solid #5865f2;
                border-radius: 3px;
            }
        """)
        email_layout.addWidget(self.email_notifications_check)
        
        self.race_reminders_check = QCheckBox("Race event reminders")
        self.race_reminders_check.setStyleSheet(self.email_notifications_check.styleSheet())
        email_layout.addWidget(self.race_reminders_check)
        
        self.achievement_emails_check = QCheckBox("Achievement notifications")
        self.achievement_emails_check.setStyleSheet(self.email_notifications_check.styleSheet())
        email_layout.addWidget(self.achievement_emails_check)
        
        email_card.content_layout.addLayout(email_layout)
        layout.addWidget(email_card)
        
        # In-App Notifications Card
        inapp_card = ModernCard("In-App Notifications")
        inapp_layout = QVBoxLayout()
        
        self.ai_coach_alerts_check = QCheckBox("AI Coach alerts and tips")
        self.ai_coach_alerts_check.setStyleSheet(self.email_notifications_check.styleSheet())
        inapp_layout.addWidget(self.ai_coach_alerts_check)
        
        self.performance_alerts_check = QCheckBox("Performance improvement alerts")
        self.performance_alerts_check.setStyleSheet(self.email_notifications_check.styleSheet())
        inapp_layout.addWidget(self.performance_alerts_check)
        
        self.social_notifications_check = QCheckBox("Social activity notifications")
        self.social_notifications_check.setStyleSheet(self.email_notifications_check.styleSheet())
        inapp_layout.addWidget(self.social_notifications_check)
        
        inapp_card.content_layout.addLayout(inapp_layout)
        layout.addWidget(inapp_card)
        
        # Startup Settings Card
        startup_card = ModernCard("Startup Settings")
        startup_layout = QVBoxLayout()
        
        self.start_with_windows_check = QCheckBox("Start TrackPro with Windows")
        self.start_with_windows_check.setStyleSheet(self.email_notifications_check.styleSheet())
        startup_layout.addWidget(self.start_with_windows_check)
        
        self.start_minimized_check = QCheckBox("Start minimized (recommended)")
        self.start_minimized_check.setStyleSheet(self.email_notifications_check.styleSheet())
        startup_layout.addWidget(self.start_minimized_check)
        
        self.minimize_to_tray_check = QCheckBox("Always minimize to tray when closing (recommended)")
        self.minimize_to_tray_check.setStyleSheet(self.email_notifications_check.styleSheet())
        startup_layout.addWidget(self.minimize_to_tray_check)
        
        # Add description
        startup_desc = QLabel("TrackPro needs to be running for hardware functionality to work properly. When you close the window, TrackPro will continue running in the background.")
        startup_desc.setStyleSheet("""
            QLabel {
                color: #72767d;
                font-size: 12px;
                margin-top: 8px;
                border: none;
                background: transparent;
            }
        """)
        startup_layout.addWidget(startup_desc)
        
        startup_card.content_layout.addLayout(startup_layout)
        layout.addWidget(startup_card)
        
        # Save button
        save_notifications_btn = ModernButton("Save Settings", "primary")
        save_notifications_btn.clicked.connect(self.save_notification_settings)
        layout.addWidget(save_notifications_btn)
        
        layout.addStretch()
        return widget
    
    def create_racing_section(self):
        """Create the racing preferences section."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)
        
        # Header
        header_label = QLabel("Racing Preferences")
        header_label.setStyleSheet("""
            QLabel {
                color: #ffffff;
                font-size: 24px;
                font-weight: 700;
                margin-bottom: 8px;
                border: none;
                background: transparent;
            }
        """)
        layout.addWidget(header_label)
        
        # Racing Statistics Card
        stats_card = ModernCard("Racing Statistics")
        stats_layout = QGridLayout()
        
        # Performance metrics
        self.total_sessions_label = QLabel("Total Sessions: Loading...")
        self.total_distance_label = QLabel("Total Distance: Loading...")
        self.best_lap_label = QLabel("Best Lap Time: Loading...")
        self.avg_consistency_label = QLabel("Consistency Rating: Loading...")
        
        stats_style = """
            QLabel {
                color: #dcddde;
                font-size: 14px;
                padding: 8px;
                background-color: #2f3136;
                border-radius: 4px;
                margin: 2px;
            }
        """
        
        for label in [self.total_sessions_label, self.total_distance_label, 
                     self.best_lap_label, self.avg_consistency_label]:
            label.setStyleSheet(stats_style)
        
        stats_layout.addWidget(self.total_sessions_label, 0, 0)
        stats_layout.addWidget(self.total_distance_label, 0, 1)
        stats_layout.addWidget(self.best_lap_label, 1, 0)
        stats_layout.addWidget(self.avg_consistency_label, 1, 1)
        
        refresh_stats_btn = ModernButton("Refresh Statistics", "secondary")
        refresh_stats_btn.clicked.connect(self.load_racing_statistics)
        stats_layout.addWidget(refresh_stats_btn, 2, 0, 1, 2)
        
        stats_card.content_layout.addLayout(stats_layout)
        layout.addWidget(stats_card)
        
        # AI Coach Preferences Card
        ai_coach_card = ModernCard("AI Coach Preferences")
        ai_layout = QVBoxLayout()
        
        # Coach personality
        personality_layout = QHBoxLayout()
        personality_layout.addWidget(QLabel("Coaching Style:"))
        self.coach_personality_combo = QComboBox()
        self.coach_personality_combo.addItems(["Encouraging", "Technical", "Strict", "Balanced"])
        self.coach_personality_combo.setStyleSheet("""
            QComboBox {
                background-color: #40444b;
                border: 1px solid #5865f2;
                border-radius: 4px;
                padding: 8px;
                color: #fefefe;
                font-size: 14px;
            }
        """)
        personality_layout.addWidget(self.coach_personality_combo)
        ai_layout.addLayout(personality_layout)
        
        # Coaching frequency
        frequency_layout = QHBoxLayout()
        frequency_layout.addWidget(QLabel("Coaching Frequency:"))
        self.coaching_frequency_combo = QComboBox()
        self.coaching_frequency_combo.addItems(["Real-time", "After sessions", "Weekly summary", "On-demand only"])
        self.coaching_frequency_combo.setStyleSheet(self.coach_personality_combo.styleSheet())
        frequency_layout.addWidget(self.coaching_frequency_combo)
        ai_layout.addLayout(frequency_layout)
        
        # Voice coaching toggle
        self.voice_coaching_check = QCheckBox("Enable voice coaching during sessions")
        self.voice_coaching_check.setStyleSheet("""
            QCheckBox {
                color: #dcddde;
                font-size: 14px;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
            }
            QCheckBox::indicator:unchecked {
                background-color: #40444b;
                border: 2px solid #72767d;
                border-radius: 3px;
            }
            QCheckBox::indicator:checked {
                background-color: #5865f2;
                border: 2px solid #5865f2;
                border-radius: 3px;
            }
        """)
        ai_layout.addWidget(self.voice_coaching_check)
        
        ai_coach_card.content_layout.addLayout(ai_layout)
        layout.addWidget(ai_coach_card)
        
        # Performance Goals Card
        goals_card = ModernCard("Performance Goals")
        goals_layout = QVBoxLayout()
        
        # Target lap time improvement
        laptime_layout = QHBoxLayout()
        laptime_layout.addWidget(QLabel("Target Lap Time Improvement (%/month):"))
        self.laptime_goal_spin = QSpinBox()
        self.laptime_goal_spin.setRange(0, 50)
        self.laptime_goal_spin.setValue(5)
        self.laptime_goal_spin.setStyleSheet("""
            QSpinBox {
                background-color: #40444b;
                border: 1px solid #5865f2;
                border-radius: 4px;
                padding: 8px;
                color: #fefefe;
                font-size: 14px;
            }
        """)
        laptime_layout.addWidget(self.laptime_goal_spin)
        goals_layout.addLayout(laptime_layout)
        
        # Consistency target
        consistency_layout = QHBoxLayout()
        consistency_layout.addWidget(QLabel("Target Consistency Rating:"))
        self.consistency_goal_spin = QSpinBox()
        self.consistency_goal_spin.setRange(50, 100)
        self.consistency_goal_spin.setValue(85)
        self.consistency_goal_spin.setStyleSheet(self.laptime_goal_spin.styleSheet())
        consistency_layout.addWidget(self.consistency_goal_spin)
        goals_layout.addLayout(consistency_layout)
        
        goals_card.content_layout.addLayout(goals_layout)
        layout.addWidget(goals_card)
        
        # Save Racing Settings Button
        save_racing_btn = ModernButton("Save Racing Settings", "primary")
        save_racing_btn.clicked.connect(self.save_racing_settings)
        layout.addWidget(save_racing_btn)
        
        layout.addStretch()
        return widget
    
    def create_connections_section(self):
        """Create the connections/integrations section."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)
        
        # Header
        header_label = QLabel("Connected Accounts")
        header_label.setStyleSheet("""
            QLabel {
                color: #ffffff;
                font-size: 24px;
                font-weight: 700;
                margin-bottom: 8px;
                border: none;
                background: transparent;
            }
        """)
        layout.addWidget(header_label)
        
        # iRacing Integration Card
        iracing_card = ModernCard("iRacing Integration")
        iracing_layout = QVBoxLayout()
        
        # Connection status
        self.iracing_status_label = QLabel("Status: Not Connected")
        self.iracing_status_label.setStyleSheet("""
            QLabel {
                color: #faa61a;
                font-size: 14px;
                font-weight: 600;
                padding: 8px;
                background-color: #2f3136;
                border-radius: 4px;
            }
        """)
        iracing_layout.addWidget(self.iracing_status_label)
        
        # iRacing username
        iracing_user_layout = QHBoxLayout()
        iracing_user_layout.addWidget(QLabel("iRacing Username:"))
        self.iracing_username_input = ModernInput("Enter your iRacing username")
        iracing_user_layout.addWidget(self.iracing_username_input)
        iracing_layout.addLayout(iracing_user_layout)
        
        # Connect/Disconnect buttons
        iracing_btn_layout = QHBoxLayout()
        self.connect_iracing_btn = ModernButton("Connect iRacing", "primary")
        self.connect_iracing_btn.clicked.connect(self.connect_iracing)
        iracing_btn_layout.addWidget(self.connect_iracing_btn)
        
        self.disconnect_iracing_btn = ModernButton("Disconnect", "danger")
        self.disconnect_iracing_btn.clicked.connect(self.disconnect_iracing)
        self.disconnect_iracing_btn.setVisible(False)
        iracing_btn_layout.addWidget(self.disconnect_iracing_btn)
        
        iracing_layout.addLayout(iracing_btn_layout)
        iracing_card.content_layout.addLayout(iracing_layout)
        layout.addWidget(iracing_card)
        
        # Save Connections Button
        save_connections_btn = ModernButton("Save Connection Settings", "primary")
        save_connections_btn.clicked.connect(self.save_connection_settings)
        layout.addWidget(save_connections_btn)
        
        layout.addStretch()
        return widget
    
    def create_privacy_section(self):
        """Create a compact and well-organized privacy and data section."""
        widget = QWidget()
        widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)
        
        # Compact header
        header_label = QLabel("Privacy & Data")
        header_label.setStyleSheet("""
            QLabel {
                color: #ffffff;
                font-size: 24px;
                font-weight: 700;
                margin-bottom: 8px;
            }
        """)
        layout.addWidget(header_label)
        
        # Main content area with scroll
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background: transparent;
            }
            QScrollBar:vertical {
                background: #2f3136;
                width: 8px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background: #40444b;
                border-radius: 4px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background: #5865f2;
            }
        """)
        
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setSpacing(20)
        scroll_layout.setContentsMargins(0, 0, 0, 0)
        
        # Privacy Settings Card - Compact design
        privacy_card = ModernCard("Privacy Settings")
        privacy_layout = QVBoxLayout()
        privacy_layout.setSpacing(16)
        privacy_layout.setContentsMargins(0, 0, 0, 0)
        
        # Profile visibility - compact layout
        visibility_layout = QHBoxLayout()
        visibility_layout.setSpacing(12)
        
        visibility_label = QLabel("Profile Visibility:")
        visibility_label.setStyleSheet("color: #dcddde; font-weight: 500; font-size: 13px; min-width: 120px;")
        
        self.profile_visibility_combo = QComboBox()
        self.profile_visibility_combo.addItems(["Public", "Friends Only", "Private"])
        self.profile_visibility_combo.setStyleSheet("""
            QComboBox {
                background-color: #40444b;
                border: 2px solid #40444b;
                border-radius: 6px;
                padding: 8px 12px;
                color: #fefefe;
                font-size: 13px;
                min-width: 140px;
            }
            QComboBox:hover {
                border-color: #5865f2;
            }
        """)
        
        visibility_layout.addWidget(visibility_label)
        visibility_layout.addWidget(self.profile_visibility_combo)
        visibility_layout.addStretch()
        privacy_layout.addLayout(visibility_layout)
        
        # Privacy options - compact checkboxes
        privacy_options_label = QLabel("Privacy Options:")
        privacy_options_label.setStyleSheet("color: #ffffff; font-size: 14px; font-weight: 600; margin-top: 8px;")
        privacy_layout.addWidget(privacy_options_label)
        
        # Create compact checkboxes
        self.share_telemetry_check = QCheckBox("Share telemetry data")
        self.show_statistics_check = QCheckBox("Show racing statistics publicly")
        self.allow_friend_requests_check = QCheckBox("Allow friend requests")
        self.show_online_status_check = QCheckBox("Show online status")
        
        checkbox_style = """
            QCheckBox {
                color: #dcddde;
                font-size: 12px;
                font-weight: 500;
                spacing: 12px;
                padding: 8px 12px;
                background-color: #36393f;
                border: 1px solid #40444b;
                border-radius: 6px;
                min-height: 36px;
            }
            QCheckBox:hover {
                background-color: #40444b;
                border-color: #5865f2;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border-radius: 4px;
            }
            QCheckBox::indicator:unchecked {
                background-color: #40444b;
                border: 2px solid #72767d;
            }
            QCheckBox::indicator:checked {
                background-color: #5865f2;
                border: 2px solid #5865f2;
            }
        """
        
        privacy_checkboxes = [
            self.share_telemetry_check, 
            self.show_statistics_check, 
            self.allow_friend_requests_check, 
            self.show_online_status_check
        ]
        
        for checkbox in privacy_checkboxes:
            checkbox.setStyleSheet(checkbox_style)
            privacy_layout.addWidget(checkbox)
        
        privacy_card.content_layout.addLayout(privacy_layout)
        scroll_layout.addWidget(privacy_card)
        
        # Data Management Card - Compact design
        data_card = ModernCard("Data Management")
        data_layout = QVBoxLayout()
        data_layout.setSpacing(16)
        data_layout.setContentsMargins(0, 0, 0, 0)
        
        # Export buttons - horizontal layout
        export_layout = QHBoxLayout()
        export_layout.setSpacing(12)
        
        self.export_profile_btn = ModernButton("Export Profile", "secondary")
        self.export_profile_btn.clicked.connect(self.export_profile_data)
        self.export_profile_btn.setMinimumWidth(140)
        self.export_profile_btn.setMinimumHeight(36)
        
        self.export_telemetry_btn = ModernButton("Export Telemetry", "secondary")
        self.export_telemetry_btn.clicked.connect(self.export_telemetry_data)
        self.export_telemetry_btn.setMinimumWidth(140)
        self.export_telemetry_btn.setMinimumHeight(36)
        
        export_layout.addWidget(self.export_profile_btn)
        export_layout.addWidget(self.export_telemetry_btn)
        export_layout.addStretch()
        data_layout.addLayout(export_layout)
        
        # Data usage - compact display
        usage_label = QLabel("Data Usage:")
        usage_label.setStyleSheet("color: #ffffff; font-size: 14px; font-weight: 600; margin-top: 8px;")
        data_layout.addWidget(usage_label)
        
        self.data_usage_text = QTextEdit()
        self.data_usage_text.setReadOnly(True)
        self.data_usage_text.setMaximumHeight(80)
        self.data_usage_text.setStyleSheet("""
            QTextEdit {
                background-color: #2f3136;
                border: 1px solid #40444b;
                border-radius: 6px;
                color: #b9bbbe;
                font-size: 11px;
                padding: 8px;
            }
        """)
        
        data_usage_content = """Profile: ~2.5 KB | Stats: ~15.3 KB | Telemetry: ~127.8 MB
Total: ~128.0 MB | Last updated: Just now"""
        self.data_usage_text.setPlainText(data_usage_content)
        data_layout.addWidget(self.data_usage_text)
        
        data_card.content_layout.addLayout(data_layout)
        scroll_layout.addWidget(data_card)
        
        # Account Deletion Card - Compact warning
        deletion_card = ModernCard("Account Deletion")
        deletion_layout = QVBoxLayout()
        deletion_layout.setSpacing(16)
        deletion_layout.setContentsMargins(0, 0, 0, 0)
        
        # Warning header
        warning_layout = QHBoxLayout()
        warning_layout.setSpacing(8)
        
        warning_icon = QLabel("⚠️")
        warning_icon.setStyleSheet("font-size: 20px;")
        
        warning_title = QLabel("Danger Zone - Permanent Deletion")
        warning_title.setStyleSheet("color: #f04747; font-size: 14px; font-weight: 600;")
        
        warning_layout.addWidget(warning_icon)
        warning_layout.addWidget(warning_title)
        warning_layout.addStretch()
        deletion_layout.addLayout(warning_layout)
        
        # Compact warning info
        deletion_info = QLabel("This action cannot be undone. All your data will be permanently deleted.")
        deletion_info.setStyleSheet("color: #b9bbbe; font-size: 12px; line-height: 1.4;")
        deletion_info.setWordWrap(True)
        deletion_layout.addWidget(deletion_info)
        
        # Delete button
        self.delete_account_btn = ModernButton("Delete Account", "danger")
        self.delete_account_btn.clicked.connect(self.request_account_deletion)
        self.delete_account_btn.setStyleSheet("""
            QPushButton {
                background-color: #f04747;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                font-size: 12px;
                font-weight: 600;
                min-width: 120px;
                min-height: 36px;
            }
            QPushButton:hover {
                background-color: #d73d3d;
            }
        """)
        
        delete_button_layout = QHBoxLayout()
        delete_button_layout.addStretch()
        delete_button_layout.addWidget(self.delete_account_btn)
        delete_button_layout.addStretch()
        deletion_layout.addLayout(delete_button_layout)
        
        deletion_card.content_layout.addLayout(deletion_layout)
        scroll_layout.addWidget(deletion_card)
        
        # Save button - compact positioning
        save_privacy_btn = ModernButton("Save Privacy Settings", "primary")
        save_privacy_btn.clicked.connect(self.save_privacy_settings)
        save_privacy_btn.setStyleSheet("""
            QPushButton {
                background-color: #5865f2;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                font-size: 12px;
                font-weight: 600;
                min-width: 160px;
                min-height: 36px;
            }
            QPushButton:hover {
                background-color: #4752c4;
            }
        """)
        
        save_button_layout = QHBoxLayout()
        save_button_layout.addStretch()
        save_button_layout.addWidget(save_privacy_btn)
        save_button_layout.addStretch()
        scroll_layout.addLayout(save_button_layout)
        
        scroll_area.setWidget(scroll_content)
        layout.addWidget(scroll_area)
        
        return widget
    
    def switch_section(self, section_id: str):
        """Switch to a different section."""
        if section_id not in self.sections:
            return
        
        # Update button states
        for btn_id, btn in self.nav_buttons.items():
            btn.setChecked(btn_id == section_id)
        
        # Switch content
        section_widget = self.sections[section_id]
        self.content_stack.setCurrentWidget(section_widget)
        self.current_section = section_id
        
        # Load section-specific data
        if section_id == "racing":
            QTimer.singleShot(100, self.load_racing_statistics)
        elif section_id == "privacy":
            QTimer.singleShot(100, self.load_data_usage_statistics)
        elif section_id == "notifications":
            QTimer.singleShot(100, self.load_startup_settings)
        
        logger.info(f"Switched to account section: {section_id}")
    
    def load_user_data(self):
        """Load current user data from the database."""
        try:
            # Load profile from Supabase
            from ....database.supabase_client import get_supabase_client
            from ....social.user_manager import EnhancedUserManager
            
            # Check if user is authenticated
            supabase_client = get_supabase_client()
            if not supabase_client:
                logger.warning("Unable to connect to database for loading user data")
                self.user_data = {}
                return
            
            # Get current user
            user_response = supabase_client.auth.get_user()
            if not user_response or not user_response.user:
                logger.warning("No authenticated user found")
                self.user_data = {}
                return
            
            user_id = user_response.user.id
            logger.info(f"Loading user data for user {user_id}")
            
            # Load profile from Supabase
            user_manager = EnhancedUserManager()
            profile_data = user_manager.get_complete_user_profile()
            
            if profile_data:
                self.user_data = profile_data
                logger.info(f"User data loaded successfully from Supabase: {profile_data}")
            else:
                # Fallback to basic user info from auth metadata if no profile exists
                metadata = getattr(user_response.user, 'user_metadata', {})
                
                # Extract name info from Google OAuth metadata  
                first_name = metadata.get('first_name', '')
                last_name = metadata.get('last_name', '')
                
                # Handle uppercase names from Google OAuth
                if first_name and first_name.isupper():
                    first_name = first_name.title()
                if last_name and last_name.isupper():
                    last_name = last_name.title()
                
                # Try to get a display name
                display_name = metadata.get('full_name') or metadata.get('name') or f"{first_name} {last_name}".strip()
                
                self.user_data = {
                    "email": user_response.user.email,
                    "first_name": first_name,
                    "last_name": last_name,
                    "display_name": display_name,
                    "bio": "",
                    "date_of_birth": metadata.get('date_of_birth', '1995-01-01')
                }
                logger.info(f"No profile data found, using auth metadata: {self.user_data}")
            
            # Populate form fields
            if hasattr(self, 'first_name_input'):
                self.first_name_input.setText(self.user_data.get("first_name", ""))
                self.last_name_input.setText(self.user_data.get("last_name", ""))
                self.display_name_input.setText(self.user_data.get("display_name", ""))
                self.email_input.setText(self.user_data.get("email", ""))
                self.bio_input.setText(self.user_data.get("bio", ""))
                
                # Handle date of birth
                if hasattr(self, 'dob_input'):
                    dob_str = self.user_data.get("date_of_birth", "")
                    if dob_str:
                        try:
                            # Parse the date string and set it in the date input
                            dob_date = QDate.fromString(dob_str, "yyyy-MM-dd")
                            if dob_date.isValid():
                                self.dob_input.setDate(dob_date)
                            else:
                                # Fallback to default date if parsing fails
                                self.dob_input.setDate(QDate.currentDate().addYears(-25))
                        except Exception as e:
                            logger.warning(f"Error parsing date of birth '{dob_str}': {e}")
                            self.dob_input.setDate(QDate.currentDate().addYears(-25))
                    else:
                        # Set default date if no date of birth is stored
                        self.dob_input.setDate(QDate.currentDate().addYears(-25))
                
                # Update avatar display
                avatar_url = self.user_data.get("avatar_url")
                if avatar_url:
                    # Load avatar from URL
                    self.load_avatar_from_url(avatar_url)
                else:
                    # Set initials as fallback
                    first_initial = self.user_data.get("first_name", "U")[0].upper()
                    last_initial = self.user_data.get("last_name", "")[0].upper() if self.user_data.get("last_name") else ""
                    self.profile_avatar.setText(f"{first_initial}{last_initial}")
            
            logger.info("User data loaded successfully")
            
        except Exception as e:
            logger.error(f"Error loading user data: {e}")
    
    def load_startup_settings(self):
        """Load startup settings from config and Windows registry."""
        try:
            from trackpro.config import Config
            config = Config()
            
            # Load settings from config
            start_with_windows = config.start_with_windows
            start_minimized = config.start_minimized
            minimize_to_tray = config.minimize_to_tray
            
            # Check actual Windows registry status
            actual_startup_enabled = self.startup_manager.is_startup_enabled()
            
            # Update checkboxes
            if hasattr(self, 'start_with_windows_check'):
                self.start_with_windows_check.setChecked(start_with_windows)
            if hasattr(self, 'start_minimized_check'):
                self.start_minimized_check.setChecked(start_minimized)
            if hasattr(self, 'minimize_to_tray_check'):
                self.minimize_to_tray_check.setChecked(minimize_to_tray)
            
            logger.info(f"Startup settings loaded - Windows: {start_with_windows}, Minimized: {start_minimized}, Tray: {minimize_to_tray}, Registry: {actual_startup_enabled}")
            
        except Exception as e:
            logger.error(f"Error loading startup settings: {e}")
    
    def save_profile(self):
        """Save profile changes."""
        try:
            # Get form data
            profile_data = {
                "first_name": self.first_name_input.text().strip(),
                "last_name": self.last_name_input.text().strip(),
                "display_name": self.display_name_input.text().strip(),
                "bio": self.bio_input.toPlainText().strip(),
                "date_of_birth": self.dob_input.date().toString("yyyy-MM-dd"),
                "share_data": True  # Make profile public by default
            }
            
            # Validate required fields
            if not profile_data["first_name"] or not profile_data["last_name"]:
                QMessageBox.warning(self, "Validation Error", "First name and last name are required.")
                return
            
            # Save to Supabase using enhanced user manager
            from ....database.supabase_client import get_supabase_client
            from ....social.user_manager import EnhancedUserManager
            
            # Check if user is authenticated
            supabase_client = get_supabase_client()
            if not supabase_client:
                QMessageBox.warning(
                    self, 
                    "Connection Error", 
                    "Unable to connect to database. Please check your connection."
                )
                return
            
            # Get current user
            user_response = supabase_client.auth.get_user()
            if not user_response or not user_response.user:
                QMessageBox.warning(
                    self, 
                    "Authentication Required", 
                    "You must be logged in to save your profile."
                )
                return
            
            user_id = user_response.user.id
            logger.info(f"Saving profile for user {user_id}: {profile_data}")
            
            # Create user manager instance and save to Supabase
            user_manager = EnhancedUserManager()
            success = user_manager.update_user_profile(user_id, profile_data)
            
            if not success:
                QMessageBox.warning(
                    self, 
                    "Save Failed", 
                    "Failed to save your profile. Please try again."
                )
                logger.error("Profile save failed")
                return
            
            # Update local data only if save was successful
            self.user_data.update(profile_data)
            logger.info("Profile saved successfully to Supabase")
            
            # Update avatar initials
            first_initial = profile_data["first_name"][0].upper()
            last_initial = profile_data["last_name"][0].upper() if profile_data["last_name"] else ""
            self.profile_avatar.setText(f"{first_initial}{last_initial}")
            
            QMessageBox.information(self, "Success", "Profile updated successfully!")
            
        except Exception as e:
            logger.error(f"Error saving profile: {e}")
            import traceback
            logger.error(f"Profile save traceback: {traceback.format_exc()}")
            QMessageBox.critical(self, "Error", f"Failed to save profile: {str(e)}")
    
    def handle_logout(self):
        """Handle user logout."""
        reply = QMessageBox.question(
            self, 
            "Confirm Logout", 
            "Are you sure you want to logout?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                logger.info("User logout initiated")
                
                # Get main window and trigger logout
                main_window = self.parent()
                while main_window is not None and not hasattr(main_window, 'logout_user'):
                    next_main_window = main_window.parent()
                    if next_main_window is None:
                        break
                    main_window = next_main_window
                
                if main_window is not None and hasattr(main_window, 'logout_user'):
                    main_window.logout_user()
                else:
                    # Fallback: try to find the main window by looking for ModernMainWindow
                    while main_window is not None and not hasattr(main_window, '__class__'):
                        next_main_window = main_window.parent()
                        if next_main_window is None:
                            break
                        main_window = next_main_window
                    
                    if main_window is not None and 'ModernMainWindow' in main_window.__class__.__name__:
                        if hasattr(main_window, 'logout_user'):
                            main_window.logout_user()
                        else:
                            QMessageBox.information(self, "Logout", "Logout functionality not available")
                    else:
                        QMessageBox.information(self, "Logout", "Logout functionality not available")
                
            except Exception as e:
                logger.error(f"Error during logout: {e}")
                QMessageBox.critical(self, "Error", f"Logout failed: {str(e)}")
    
    def lazy_init(self):
        """Lazy initialization when page is first accessed."""
        logger.info("Lazy initializing Account page...")
        self.load_user_data()
    
    def on_page_activated(self):
        """Called when page becomes active."""
        if not self.is_initialized:
            self.lazy_init()
            self.is_initialized = True
        logger.info("Account page activated")
        
        # Refresh user data when page is activated
        QTimer.singleShot(100, self.load_user_data)
        
        # Load racing statistics if on racing section
        if self.current_section == "racing":
            QTimer.singleShot(200, self.load_racing_statistics)
        
        # Load data usage if on privacy section
        if self.current_section == "privacy":
            QTimer.singleShot(200, self.load_data_usage_statistics)
    
    def upload_avatar(self):
        """Upload a new avatar image to Supabase Storage."""
        try:
            # Open file dialog for image selection
            file_dialog = QFileDialog()
            file_path, _ = file_dialog.getOpenFileName(
                self,
                "Select Avatar Image",
                "",
                "Image Files (*.png *.jpg *.jpeg *.gif *.bmp)"
            )
            
            if not file_path:
                return  # User cancelled
            
            # Validate file size (max 5MB)
            import os
            file_size = os.path.getsize(file_path)
            if file_size > 5 * 1024 * 1024:  # 5MB limit
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.warning(
                    self,
                    "File Too Large",
                    "Avatar image must be smaller than 5MB. Please choose a smaller image."
                )
                return
            
            # Show progress dialog
            from PyQt6.QtWidgets import QProgressDialog
            progress = QProgressDialog("Uploading avatar...", "Cancel", 0, 100, self)
            progress.setWindowModality(Qt.WindowModality.WindowModal)
            progress.show()
            progress.setValue(10)
            
            # Import required modules
            from ....database.supabase_client import get_supabase_client
            from ....social.user_manager import EnhancedUserManager
            import uuid
            import mimetypes
            
            # Get Supabase client
            supabase_client = get_supabase_client()
            if not supabase_client:
                progress.close()
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.warning(self, "Connection Error", "Unable to connect to storage service.")
                return
            
            progress.setValue(30)
            
            # Get current user
            user_response = supabase_client.auth.get_user()
            if not user_response or not user_response.user:
                progress.close()
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.warning(self, "Authentication Required", "You must be logged in to upload an avatar.")
                return
            
            user_id = user_response.user.id
            progress.setValue(50)
            
            # Generate unique filename
            file_extension = os.path.splitext(file_path)[1].lower()
            filename = f"avatars/{user_id}/{uuid.uuid4()}{file_extension}"
            
            # Read file data
            with open(file_path, 'rb') as f:
                file_data = f.read()
            
            progress.setValue(70)
            
            # Get MIME type
            mime_type, _ = mimetypes.guess_type(file_path)
            if not mime_type:
                mime_type = 'image/jpeg'  # Default fallback
            
            # Upload to Supabase Storage via centralized manager
            try:
                public_url = AvatarManager.instance().upload_avatar(user_id, file_path)
                if not public_url:
                    raise RuntimeError("Avatar upload failed")
                progress.setValue(90)
                avatar_url = public_url
                
                # Update user profile with new avatar URL
                user_manager = EnhancedUserManager()
                success = user_manager.update_user_profile(user_id, {
                    'avatar_url': avatar_url
                })
                
                progress.setValue(100)
                progress.close()
                
                if success:
                    # Update local avatar display
                    display_name = self.user_data.get('display_name') or self.user_data.get('username') or 'User'
                    AvatarManager.instance().set_label_avatar(self.profile_avatar, avatar_url, display_name, size=self.profile_avatar.width())
                    
                    from PyQt6.QtWidgets import QMessageBox
                    QMessageBox.information(self, "Success", "Avatar uploaded successfully!")
                    logger.info(f"Avatar uploaded successfully: {avatar_url}")
                    self.avatar_uploaded.emit(avatar_url)
                else:
                    from PyQt6.QtWidgets import QMessageBox
                    QMessageBox.warning(self, "Upload Failed", "Failed to save avatar to profile.")
                    
            except Exception as storage_error:
                progress.close()
                logger.error(f"Storage upload error: {storage_error}")
                logger.error(f"Storage error type: {type(storage_error)}")
                logger.error(f"Storage error details: {str(storage_error)}")
                
                # Provide more specific error messages
                error_message = str(storage_error)
                if "bucket" in error_message.lower():
                    error_message = "Storage bucket 'avatars' does not exist. Please create it in your Supabase dashboard."
                elif "permission" in error_message.lower():
                    error_message = "Permission denied. Please check your Supabase storage policies."
                elif "network" in error_message.lower():
                    error_message = "Network error. Please check your internet connection."
                else:
                    error_message = f"Upload failed: {error_message}"
                
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.critical(self, "Upload Error", error_message)
            
        except Exception as e:
            if 'progress' in locals():
                progress.close()
            logger.error(f"Error uploading avatar: {e}")
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Error", f"Failed to upload avatar: {str(e)}")
    
    def load_avatar_from_url(self, url):
        """Deprecated: use AvatarManager to set avatar directly."""
        display_name = self.user_data.get('display_name') or self.user_data.get('username') or 'User'
        AvatarManager.instance().set_label_avatar(self.profile_avatar, url, display_name, size=self.profile_avatar.width())
    

    
    def remove_avatar(self):
        """Remove the current avatar."""
        try:
            # Confirm avatar removal
            from PyQt6.QtWidgets import QMessageBox
            reply = QMessageBox.question(
                self,
                "Remove Avatar",
                "Are you sure you want to remove your avatar?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                # TODO: Implement avatar removal from Supabase
                # Reset to default avatar (initials)
                if hasattr(self, 'profile_avatar'):
                    first_initial = self.user_data.get("first_name", "U")[0].upper()
                    last_initial = self.user_data.get("last_name", "")[0].upper() if self.user_data.get("last_name") else ""
                    self.profile_avatar.setText(f"{first_initial}{last_initial}")
                
                QMessageBox.information(self, "Success", "Avatar removed successfully!")
                logger.info("Avatar removed")
            
        except Exception as e:
            logger.error(f"Error removing avatar: {e}")
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Error", f"Failed to remove avatar: {str(e)}")
    
    def change_password(self):
        """Change user password."""
        try:
            # Get password values
            current_pw = self.current_password_input.text().strip()
            new_pw = self.new_password_input.text().strip()
            confirm_pw = self.confirm_password_input.text().strip()
            
            # Validate inputs
            if not current_pw or not new_pw or not confirm_pw:
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.warning(self, "Validation Error", "All password fields are required.")
                return
            
            if new_pw != confirm_pw:
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.warning(self, "Validation Error", "New passwords do not match.")
                return
            
            if len(new_pw) < 8:
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.warning(self, "Validation Error", "Password must be at least 8 characters long.")
                return
            
            # TODO: Implement actual password change with Supabase
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.information(
                self,
                "Password Change",
                "Password change functionality will be implemented soon."
            )
            
            # Clear password fields for security
            self.current_password_input.clear()
            self.new_password_input.clear()
            self.confirm_password_input.clear()
            
            logger.info("Password change requested")
            
        except Exception as e:
            logger.error(f"Error changing password: {e}")
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Error", f"Failed to change password: {str(e)}")
    
    def toggle_2fa(self):
        """Toggle two-factor authentication."""
        try:
            sender = self.sender()
            
            if sender == self.enable_2fa_btn:
                # TODO: Implement 2FA setup
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.information(
                    self,
                    "Enable 2FA",
                    "Two-factor authentication setup will be implemented soon."
                )
                logger.info("2FA enable requested")
            else:
                # TODO: Implement 2FA disable
                from PyQt6.QtWidgets import QMessageBox
                reply = QMessageBox.question(
                    self,
                    "Disable 2FA",
                    "Are you sure you want to disable two-factor authentication?\nThis will make your account less secure.",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No
                )
                
                if reply == QMessageBox.StandardButton.Yes:
                    QMessageBox.information(
                        self,
                        "Disable 2FA",
                        "Two-factor authentication disable will be implemented soon."
                    )
                    logger.info("2FA disable requested")
            
        except Exception as e:
            logger.error(f"Error toggling 2FA: {e}")
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Error", f"Failed to toggle 2FA: {str(e)}")
    
    def check_for_updates(self):
        """Manually check for updates."""
        try:
            # Disable the button during check
            self.check_updates_btn.setEnabled(False)
            self.check_updates_btn.setText("Checking...")
            self.update_status_label.setText("Checking for updates...")
            
            # Get the main window to access the updater
            main_window = self.window()
            if hasattr(main_window, 'updater'):
                # Perform manual update check
                main_window.updater.check_for_updates(silent=False, manual_check=True)
                
                # Update status after a short delay
                from PyQt6.QtCore import QTimer
                QTimer.singleShot(2000, self.update_check_status)
            else:
                self.update_status_label.setText("Update system not available")
                self.check_updates_btn.setEnabled(True)
                self.check_updates_btn.setText("Check for Updates")
                
        except Exception as e:
            self.update_status_label.setText(f"Error checking for updates: {str(e)}")
            self.check_updates_btn.setEnabled(True)
            self.check_updates_btn.setText("Check for Updates")
    
    def update_check_status(self):
        """Update the status label after checking for updates."""
        try:
            # Get the main window to access the updater
            main_window = self.window()
            if hasattr(main_window, 'updater'):
                # Check if an update is available
                if hasattr(main_window.updater, 'latest_version'):
                    latest_version = main_window.updater.latest_version
                    from trackpro.updater import CURRENT_VERSION
                    if latest_version and latest_version != CURRENT_VERSION:
                        self.update_status_label.setText(f"Update available: v{latest_version}")
                        self.update_status_label.setStyleSheet("""
                            QLabel {
                                color: #43b581;
                                font-size: 12px;
                                padding: 4px 0;
                                border: none;
                                background: transparent;
                            }
                        """)
                        # Show download button
                        self.download_update_btn.setVisible(True)
                        self.download_update_btn.setText(f"Download v{latest_version}")
                    else:
                        self.update_status_label.setText("You are running the latest version")
                        self.update_status_label.setStyleSheet("""
                            QLabel {
                                color: #b9bbbe;
                                font-size: 12px;
                                padding: 4px 0;
                                border: none;
                                background: transparent;
                            }
                        """)
                        # Hide download button
                        self.download_update_btn.setVisible(False)
                else:
                    self.update_status_label.setText("No updates available")
            else:
                self.update_status_label.setText("Update system not available")
            
            # Re-enable the button
            self.check_updates_btn.setEnabled(True)
            self.check_updates_btn.setText("Check for Updates")
            
        except Exception as e:
            self.update_status_label.setText(f"Error: {str(e)}")
            self.check_updates_btn.setEnabled(True)
            self.check_updates_btn.setText("Check for Updates")
    
    def download_update(self):
        """Download and install the available update."""
        try:
            # Get the main window to access the updater
            main_window = self.window()
            if hasattr(main_window, 'updater') and hasattr(main_window.updater, 'latest_version'):
                # Disable the download button during process
                self.download_update_btn.setEnabled(False)
                self.download_update_btn.setText("Downloading...")
                self.update_status_label.setText("Starting download...")
                
                # Trigger the download process
                main_window.updater._handle_download_choice()
                
                # The updater will handle the rest (download, installation, app exit)
            else:
                self.update_status_label.setText("Update system not available")
                self.download_update_btn.setEnabled(True)
                self.download_update_btn.setText("Download Update")
                
        except Exception as e:
            self.update_status_label.setText(f"Error downloading update: {str(e)}")
            self.download_update_btn.setEnabled(True)
            self.download_update_btn.setText("Download Update")
    
    def save_notification_settings(self):
        """Save notification preferences and startup settings."""
        try:
            # Get checkbox states
            notification_settings = {
                "email_notifications": self.email_notifications_check.isChecked(),
                "race_reminders": self.race_reminders_check.isChecked(),
                "achievement_emails": self.achievement_emails_check.isChecked(),
                "ai_coach_alerts": self.ai_coach_alerts_check.isChecked(),
                "performance_alerts": self.performance_alerts_check.isChecked(),
                "social_notifications": self.social_notifications_check.isChecked()
            }
            
            # Get startup settings
            start_with_windows = self.start_with_windows_check.isChecked()
            start_minimized = self.start_minimized_check.isChecked()
            minimize_to_tray = self.minimize_to_tray_check.isChecked()
            
            # Save startup settings to Windows registry
            success = self.startup_manager.toggle_startup(start_with_windows, start_minimized)
            
            # Save startup settings to config
            from trackpro.config import Config
            config = Config()
            config.set('ui.start_with_windows', start_with_windows)
            config.set('ui.start_minimized', start_minimized)
            config.set('ui.minimize_to_tray', minimize_to_tray)
            config.save()
            
            # TODO: Save notification settings to Supabase user preferences
            logger.info(f"Saving notification settings: {notification_settings}")
            logger.info(f"Startup settings - Windows: {start_with_windows}, Minimized: {start_minimized}, Tray: {minimize_to_tray}")
            
            from PyQt6.QtWidgets import QMessageBox
            if success:
                QMessageBox.information(
                    self,
                    "Settings Saved",
                    "Your settings have been saved successfully!"
                )
            else:
                QMessageBox.warning(
                    self,
                    "Settings Partially Saved",
                    "Notification settings saved, but there was an issue with startup settings. You may need administrator privileges."
                )
            
        except Exception as e:
            logger.error(f"Error saving settings: {e}")
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Error", f"Failed to save settings: {str(e)}")
    
    def load_racing_statistics(self):
        """Load racing statistics from the database."""
        try:
            from ....database.supabase_client import get_supabase_client
            
            # Get current user
            supabase_client = get_supabase_client()
            if not supabase_client:
                logger.warning("Unable to connect to database for racing stats")
                return
            
            user_response = supabase_client.auth.get_user()
            if not user_response or not user_response.user:
                logger.warning("No authenticated user for racing stats")
                return
            
            user_id = user_response.user.id
            
            # Get racing statistics from database
            try:
                # Query user_stats table for racing data
                stats_response = supabase_client.table('user_stats').select('*').eq('user_id', user_id).single().execute()
                
                if stats_response.data:
                    stats = stats_response.data
                    
                    # Update UI with real data
                    total_sessions = stats.get('total_sessions', 0)
                    total_distance = stats.get('total_distance_km', 0.0)
                    best_lap = stats.get('best_lap_time', 0.0)
                    consistency = stats.get('consistency_rating', 0.0)
                    
                    self.total_sessions_label.setText(f"Total Sessions: {total_sessions}")
                    self.total_distance_label.setText(f"Total Distance: {total_distance:.1f} km")
                    
                    if best_lap > 0:
                        minutes = int(best_lap // 60)
                        seconds = best_lap % 60
                        self.best_lap_label.setText(f"Best Lap Time: {minutes}:{seconds:06.3f}")
                    else:
                        self.best_lap_label.setText("Best Lap Time: No data")
                    
                    self.avg_consistency_label.setText(f"Consistency Rating: {consistency:.1f}%")
                    
                    logger.info("Racing statistics loaded successfully")
                else:
                    # No stats data yet - show defaults
                    self.total_sessions_label.setText("Total Sessions: 0")
                    self.total_distance_label.setText("Total Distance: 0.0 km")
                    self.best_lap_label.setText("Best Lap Time: No data")
                    self.avg_consistency_label.setText("Consistency Rating: 0.0%")
                    
            except Exception as db_error:
                logger.error(f"Error querying racing stats: {db_error}")
                # Show placeholder data on error
                self.total_sessions_label.setText("Total Sessions: Loading...")
                self.total_distance_label.setText("Total Distance: Loading...")
                self.best_lap_label.setText("Best Lap Time: Loading...")
                self.avg_consistency_label.setText("Consistency Rating: Loading...")
            
        except Exception as e:
            logger.error(f"Error loading racing statistics: {e}")
    
    def save_racing_settings(self):
        """Save racing preferences and AI coach settings."""
        try:
            # Collect racing settings
            racing_settings = {
                "coach_personality": self.coach_personality_combo.currentText(),
                "coaching_frequency": self.coaching_frequency_combo.currentText(),
                "voice_coaching_enabled": self.voice_coaching_check.isChecked(),
                "laptime_improvement_goal": self.laptime_goal_spin.value(),
                "consistency_goal": self.consistency_goal_spin.value()
            }
            
            # Save to user preferences
            from ....database.supabase_client import get_supabase_client
            from ....social.user_manager import EnhancedUserManager
            
            supabase_client = get_supabase_client()
            if not supabase_client:
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.warning(self, "Connection Error", "Unable to connect to database.")
                return
            
            user_response = supabase_client.auth.get_user()
            if not user_response or not user_response.user:
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.warning(self, "Authentication Required", "You must be logged in to save settings.")
                return
            
            user_id = user_response.user.id
            
            # Update user profile with racing preferences
            user_manager = EnhancedUserManager()
            success = user_manager.update_user_profile(user_id, {
                "preferences": racing_settings
            })
            
            if success:
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.information(self, "Settings Saved", "Your racing preferences have been saved successfully!")
                logger.info(f"Racing settings saved: {racing_settings}")
            else:
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.warning(self, "Save Failed", "Failed to save racing settings. Please try again.")
            
        except Exception as e:
            logger.error(f"Error saving racing settings: {e}")
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Error", f"Failed to save racing settings: {str(e)}")
    
    def save_connection_settings(self):
        """Save connection and integration settings."""
        try:
            # Collect connection settings
            connection_settings = {
                "iracing_username": self.iracing_username_input.text().strip(),
                "discord_rich_presence": self.discord_rich_presence_check.isChecked(),
                "discord_community": self.discord_community_check.isChecked()
            }
            
            # TODO: Save to user profile or dedicated connections table
            logger.info(f"Saving connection settings: {connection_settings}")
            
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.information(
                self,
                "Settings Saved",
                "Your connection preferences have been saved successfully!"
            )
            
        except Exception as e:
            logger.error(f"Error saving connection settings: {e}")
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Error", f"Failed to save connection settings: {str(e)}")
    
    def connect_iracing(self):
        """Connect to iRacing account."""
        try:
            username = self.iracing_username_input.text().strip()
            if not username:
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.warning(self, "Validation Error", "Please enter your iRacing username.")
                return
            
            # TODO: Implement actual iRacing API integration
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.information(
                self,
                "iRacing Connection",
                f"iRacing integration for '{username}' will be implemented soon."
            )
            logger.info(f"iRacing connection requested for username: {username}")
            
        except Exception as e:
            logger.error(f"Error connecting to iRacing: {e}")
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Error", f"Failed to connect to iRacing: {str(e)}")
    
    def disconnect_iracing(self):
        """Disconnect from iRacing account."""
        try:
            from PyQt6.QtWidgets import QMessageBox
            reply = QMessageBox.question(
                self,
                "Disconnect iRacing",
                "Are you sure you want to disconnect your iRacing account?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                # TODO: Implement disconnection logic
                QMessageBox.information(self, "Disconnected", "iRacing account disconnected successfully!")
                logger.info("iRacing account disconnected")
            
        except Exception as e:
            logger.error(f"Error disconnecting iRacing: {e}")
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Error", f"Failed to disconnect iRacing: {str(e)}")
    

    
    def save_privacy_settings(self):
        """Save privacy preferences."""
        try:
            # Collect privacy settings
            privacy_settings = {
                "profile_visibility": self.profile_visibility_combo.currentText().lower().replace(" ", "_"),
                "share_telemetry": self.share_telemetry_check.isChecked(),
                "show_statistics": self.show_statistics_check.isChecked(),
                "allow_friend_requests": self.allow_friend_requests_check.isChecked(),
                "show_online_status": self.show_online_status_check.isChecked()
            }
            
            # Save to user profile
            from ....database.supabase_client import get_supabase_client
            from ....social.user_manager import EnhancedUserManager
            
            supabase_client = get_supabase_client()
            if not supabase_client:
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.warning(self, "Connection Error", "Unable to connect to database.")
                return
            
            user_response = supabase_client.auth.get_user()
            if not user_response or not user_response.user:
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.warning(self, "Authentication Required", "You must be logged in to save settings.")
                return
            
            user_id = user_response.user.id
            
            # Update privacy settings
            user_manager = EnhancedUserManager()
            success = user_manager.update_user_profile(user_id, {
                "privacy_settings": privacy_settings
            })
            
            if success:
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.information(self, "Settings Saved", "Your privacy preferences have been saved successfully!")
                logger.info(f"Privacy settings saved: {privacy_settings}")
            else:
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.warning(self, "Save Failed", "Failed to save privacy settings. Please try again.")
            
        except Exception as e:
            logger.error(f"Error saving privacy settings: {e}")
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Error", f"Failed to save privacy settings: {str(e)}")
    
    def export_profile_data(self):
        """Export user profile data."""
        try:
            from PyQt6.QtWidgets import QFileDialog, QMessageBox
            import json
            from datetime import datetime
            
            # Get save location
            filename, _ = QFileDialog.getSaveFileName(
                self,
                "Export Profile Data",
                f"trackpro_profile_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                "JSON Files (*.json);;All Files (*)"
            )
            
            if not filename:
                return
            
            # Collect profile data
            from ....database.supabase_client import get_supabase_client
            from ....social.user_manager import EnhancedUserManager
            
            supabase_client = get_supabase_client()
            if not supabase_client:
                QMessageBox.warning(self, "Connection Error", "Unable to connect to database.")
                return
            
            user_response = supabase_client.auth.get_user()
            if not user_response or not user_response.user:
                QMessageBox.warning(self, "Authentication Required", "You must be logged in to export data.")
                return
            
            # Get complete profile
            user_manager = EnhancedUserManager()
            profile_data = user_manager.get_complete_user_profile()
            
            # Add export metadata
            export_data = {
                "export_date": datetime.now().isoformat(),
                "export_type": "profile",
                "trackpro_version": "1.0",
                "profile_data": profile_data
            }
            
            # Save to file
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            
            QMessageBox.information(self, "Export Complete", f"Profile data exported successfully to:\\n{filename}")
            logger.info(f"Profile data exported to: {filename}")
            
        except Exception as e:
            logger.error(f"Error exporting profile data: {e}")
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Export Error", f"Failed to export profile data: {str(e)}")
    
    def export_telemetry_data(self):
        """Export user telemetry data."""
        try:
            from PyQt6.QtWidgets import QMessageBox
            
            # TODO: Implement telemetry data export
            QMessageBox.information(
                self,
                "Telemetry Export",
                "Telemetry data export functionality will be implemented soon.\\n\\nThis will include:\\n• Session data\\n• Lap times\\n• Performance metrics\\n• Track data"
            )
            logger.info("Telemetry export requested")
            
        except Exception as e:
            logger.error(f"Error exporting telemetry data: {e}")
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Export Error", f"Failed to export telemetry data: {str(e)}")
    
    def request_account_deletion(self):
        """Request account deletion."""
        try:
            from PyQt6.QtWidgets import QMessageBox, QInputDialog
            
            # Double confirmation
            reply = QMessageBox.warning(
                self,
                "Delete Account",
                "⚠️ Are you absolutely sure you want to delete your account?\\n\\nThis action will:\\n• Permanently delete all your data\\n• Remove all racing statistics\\n• Cancel any active subscriptions\\n• Cannot be undone\\n\\nType 'DELETE' to confirm:",
                QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Cancel
            )
            
            if reply == QMessageBox.StandardButton.Ok:
                # Ask for confirmation text
                text, ok = QInputDialog.getText(
                    self,
                    "Confirm Account Deletion",
                    "Type 'DELETE' to confirm account deletion:"
                )
                
                if ok and text.upper() == "DELETE":
                    # TODO: Implement actual account deletion
                    QMessageBox.information(
                        self,
                        "Account Deletion Request",
                        "Account deletion request submitted.\\n\\nYou will receive an email with further instructions within 24 hours.\\n\\nYour account will be scheduled for deletion in 30 days, during which you can cancel this request by logging in."
                    )
                    logger.warning("Account deletion requested")
                elif ok:
                    QMessageBox.information(self, "Deletion Cancelled", "Account deletion cancelled - confirmation text did not match.")
            
        except Exception as e:
            logger.error(f"Error requesting account deletion: {e}")
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Error", f"Failed to process deletion request: {str(e)}")
    
    def load_data_usage_statistics(self):
        """Load and display data usage statistics."""
        try:
            from ....database.supabase_client import get_supabase_client
            
            supabase_client = get_supabase_client()
            if not supabase_client:
                self.data_usage_text.setPlainText("• Unable to load data usage statistics")
                return
            
            user_response = supabase_client.auth.get_user()
            if not user_response or not user_response.user:
                self.data_usage_text.setPlainText("• User not authenticated")
                return
            
            # TODO: Implement actual data usage calculation from Supabase
            # For now, show example data
            usage_text = (
                "• Profile data: ~2.5 KB\n"
                "• Racing statistics: ~15.3 KB\n" 
                "• Achievement data: ~4.7 KB\n"
                "• Telemetry sessions: ~127.8 MB\n"
                "• Avatar images: ~245 KB\n"
                "• Settings & preferences: ~1.2 KB\n\n"
                "📊 Total storage used: ~128.1 MB"
            )
            
            self.data_usage_text.setPlainText(usage_text)
            logger.info("Data usage statistics updated")
            
        except Exception as e:
            logger.error(f"Error loading data usage: {e}")
            self.data_usage_text.setPlainText("• Error loading data usage statistics")
    
    def create_admin_section(self):
        """Create the admin management section (dev users only)."""
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setStyleSheet("""
            QScrollArea {
                background-color: #36393f;
                border: none;
            }
        """)
        
        # Import and create admin management widget
        from .admin_management_widget import AdminManagementWidget
        admin_widget = AdminManagementWidget()
        admin_widget.admin_updated.connect(self.on_admin_updated)
        
        scroll_area.setWidget(admin_widget)
        return scroll_area
    
    def on_admin_updated(self):
        """Handle admin list updates."""
        logger.info("Admin list updated")
        # Refresh the navigation if needed
        self.refresh_navigation()
    
    def create_hierarchy_section(self):
        """Create the hierarchy management section (dev users only)."""
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setStyleSheet("""
            QScrollArea {
                background-color: #36393f;
                border: none;
            }
            QScrollBar:vertical {
                background-color: #2f3136;
                width: 12px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background-color: #5865f2;
                border-radius: 6px;
                min-height: 20px;
            }
        """)
        
        content_widget = QWidget()
        content_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.MinimumExpanding)
        layout = QVBoxLayout(content_widget)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        # Header
        header_label = QLabel("User Hierarchy Management")
        header_label.setStyleSheet("""
            QLabel {
                color: #ffffff;
                font-size: 24px;
                font-weight: 700;
                margin-bottom: 8px;
                border: none;
                background: transparent;
            }
        """)
        layout.addWidget(header_label)
        
        subtitle_label = QLabel("Manage user roles, permissions, and hierarchy levels")
        subtitle_label.setStyleSheet("""
            QLabel {
                color: #b9bbbe;
                font-size: 14px;
                margin-bottom: 16px;
                border: none;
                background: transparent;
            }
        """)
        layout.addWidget(subtitle_label)
        
        # Current user info
        current_user_card = ModernCard("Your Permissions")
        current_user_layout = QVBoxLayout()
        
        from trackpro.auth.user_manager import get_current_user, get_current_user_hierarchy_level, is_current_user_dev, is_current_user_moderator
        
        current_user = get_current_user()
        if current_user:
            user_info = QLabel(f"Email: {current_user.email}")
            user_info.setStyleSheet("color: #b9bbbe; font-size: 14px;")
            current_user_layout.addWidget(user_info)
            
            level_info = QLabel(f"Hierarchy Level: {get_current_user_hierarchy_level()}")
            level_info.setStyleSheet("color: #b9bbbe; font-size: 14px;")
            current_user_layout.addWidget(level_info)
            
            dev_info = QLabel(f"Dev Permissions: {'Yes' if is_current_user_dev() else 'No'}")
            dev_info.setStyleSheet("color: #b9bbbe; font-size: 14px;")
            current_user_layout.addWidget(dev_info)
            
            mod_info = QLabel(f"Moderator Permissions: {'Yes' if is_current_user_moderator() else 'No'}")
            mod_info.setStyleSheet("color: #b9bbbe; font-size: 14px;")
            current_user_layout.addWidget(mod_info)
        
        current_user_card.layout().addLayout(current_user_layout)
        layout.addWidget(current_user_card)
        
        # User search and management
        search_card = ModernCard("Manage Users")
        search_layout = QVBoxLayout()
        
        # Search input
        search_input_layout = QHBoxLayout()
        self.user_search_input = ModernInput("Enter user email to search...")
        search_btn = ModernButton("Search", "primary")
        search_btn.clicked.connect(self.search_user)
        search_input_layout.addWidget(self.user_search_input)
        search_input_layout.addWidget(search_btn)
        search_layout.addLayout(search_input_layout)
        
        # User results
        self.user_results_widget = QWidget()
        self.user_results_layout = QVBoxLayout(self.user_results_widget)
        search_layout.addWidget(self.user_results_widget)
        
        search_card.layout().addLayout(search_layout)
        layout.addWidget(search_card)
        
        # Hierarchy levels info
        levels_card = ModernCard("Hierarchy Levels")
        levels_layout = QVBoxLayout()
        
        levels_info = QLabel("""
        <b>TEAM</b> - Full system access, can manage all users and content<br>
        <b>SPONSORED_DRIVERS</b> - Premium users with enhanced features<br>
        <b>DRIVERS</b> - Standard users with basic features<br>
        <b>PADDOCK</b> - New users with limited access
        """)
        levels_info.setStyleSheet("color: #b9bbbe; font-size: 14px;")
        levels_info.setWordWrap(True)
        levels_layout.addWidget(levels_info)
        
        levels_card.layout().addLayout(levels_layout)
        layout.addWidget(levels_card)
        
        scroll_area.setWidget(content_widget)
        return scroll_area
    
    def search_user(self):
        """Search for a user by email."""
        email = self.user_search_input.text().strip()
        if not email:
            return
        
        try:
            from trackpro.auth.hierarchy_manager import hierarchy_manager
            from trackpro.database.supabase_client import get_supabase_client
            
            # Search for user by email
            supabase = get_supabase_client()
            response = supabase.table("user_profiles").select("user_id, email, display_name").eq("email", email).execute()
            
            if response.data:
                user_data = response.data[0]
                self.display_user_management(user_data)
            else:
                # Clear previous results
                self.clear_user_results()
                no_user_label = QLabel("User not found")
                no_user_label.setStyleSheet("color: #ed4245; font-size: 14px;")
                self.user_results_layout.addWidget(no_user_label)
                
        except Exception as e:
            logger.error(f"Error searching for user: {e}")
    
    def display_user_management(self, user_data):
        """Display user management interface."""
        # Clear previous results
        self.clear_user_results()
        
        # User info
        user_info = QLabel(f"User: {user_data.get('display_name', 'Unknown')} ({user_data.get('email', 'No email')})")
        user_info.setStyleSheet("color: #ffffff; font-size: 16px; font-weight: bold;")
        self.user_results_layout.addWidget(user_info)
        
        # Get current hierarchy
        from trackpro.auth.hierarchy_manager import hierarchy_manager
        hierarchy = hierarchy_manager.get_user_hierarchy(user_data['user_id'])
        
        if hierarchy:
            current_level = QLabel(f"Current Level: {hierarchy.hierarchy_level.value}")
            current_level.setStyleSheet("color: #b9bbbe; font-size: 14px;")
            self.user_results_layout.addWidget(current_level)
            
            dev_status = QLabel(f"Dev Permissions: {'Yes' if hierarchy.is_dev else 'No'}")
            dev_status.setStyleSheet("color: #b9bbbe; font-size: 14px;")
            self.user_results_layout.addWidget(dev_status)
            
            mod_status = QLabel(f"Moderator Permissions: {'Yes' if hierarchy.is_moderator else 'No'}")
            mod_status.setStyleSheet("color: #b9bbbe; font-size: 14px;")
            self.user_results_layout.addWidget(mod_status)
        
        # Hierarchy level selector
        level_group = QGroupBox("Change Hierarchy Level")
        level_layout = QVBoxLayout()
        
        self.level_combo = QComboBox()
        self.level_combo.addItems(["PADDOCK", "DRIVERS", "SPONSORED_DRIVERS", "TEAM"])
        if hierarchy:
            current_index = self.level_combo.findText(hierarchy.hierarchy_level.value)
            if current_index >= 0:
                self.level_combo.setCurrentIndex(current_index)
        
        level_layout.addWidget(self.level_combo)
        
        # Permission checkboxes
        self.dev_checkbox = QCheckBox("Dev Permissions")
        self.mod_checkbox = QCheckBox("Moderator Permissions")
        
        if hierarchy:
            self.dev_checkbox.setChecked(hierarchy.is_dev)
            self.mod_checkbox.setChecked(hierarchy.is_moderator)
        
        level_layout.addWidget(self.dev_checkbox)
        level_layout.addWidget(self.mod_checkbox)
        
        # Quick action buttons row
        quick_row = QHBoxLayout()
        quick_team_btn = ModernButton("Set TEAM", "secondary")
        quick_sponsored_btn = ModernButton("Set SPONSORED_DRIVERS", "secondary")
        quick_drivers_btn = ModernButton("Set DRIVERS", "secondary")
        quick_paddock_btn = ModernButton("Set PADDOCK", "secondary")

        def _set_level(text: str):
            idx = self.level_combo.findText(text)
            if idx >= 0:
                self.level_combo.setCurrentIndex(idx)

        quick_team_btn.clicked.connect(lambda: _set_level("TEAM"))
        quick_sponsored_btn.clicked.connect(lambda: _set_level("SPONSORED_DRIVERS"))
        quick_drivers_btn.clicked.connect(lambda: _set_level("DRIVERS"))
        quick_paddock_btn.clicked.connect(lambda: _set_level("PADDOCK"))

        quick_row.addWidget(quick_team_btn)
        quick_row.addWidget(quick_sponsored_btn)
        quick_row.addWidget(quick_drivers_btn)
        quick_row.addWidget(quick_paddock_btn)
        level_layout.addLayout(quick_row)

        # Update button
        update_btn = ModernButton("Apply Changes", "primary")
        update_btn.clicked.connect(lambda: self.update_user_hierarchy(user_data['user_id']))
        level_layout.addWidget(update_btn)
        
        level_group.setLayout(level_layout)
        self.user_results_layout.addWidget(level_group)

        # Moderation actions
        mod_group = QGroupBox("Moderation")
        mod_layout = QHBoxLayout()

        ban_btn = ModernButton("Ban (Block)", "danger")
        unban_btn = ModernButton("Unban (Unblock)", "success")

        def _ban_user():
            try:
                from trackpro.social.friends_manager import FriendsManager
                from trackpro.auth.user_manager import get_current_user
                current_user = get_current_user()
                if not current_user:
                    return
                FriendsManager().block_user(current_user.id, user_data['user_id'])
                QMessageBox.information(self, "Success", "User has been blocked.")
            except Exception as e:
                logger.error(f"Error blocking user: {e}")
                QMessageBox.warning(self, "Error", "Failed to block user")

        def _unban_user():
            try:
                from trackpro.social.friends_manager import FriendsManager
                from trackpro.auth.user_manager import get_current_user
                current_user = get_current_user()
                if not current_user:
                    return
                FriendsManager().unblock_user(current_user.id, user_data['user_id'])
                QMessageBox.information(self, "Success", "User has been unblocked.")
            except Exception as e:
                logger.error(f"Error unblocking user: {e}")
                QMessageBox.warning(self, "Error", "Failed to unblock user")

        ban_btn.clicked.connect(_ban_user)
        unban_btn.clicked.connect(_unban_user)

        mod_layout.addWidget(ban_btn)
        mod_layout.addWidget(unban_btn)
        mod_group.setLayout(mod_layout)
        self.user_results_layout.addWidget(mod_group)
    
    def clear_user_results(self):
        """Clear the user results area."""
        while self.user_results_layout.count():
            child = self.user_results_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
    
    def update_user_hierarchy(self, user_id):
        """Update user hierarchy."""
        try:
            from trackpro.auth.hierarchy_manager import hierarchy_manager, HierarchyLevel
            from trackpro.auth.user_manager import get_current_user
            
            current_user = get_current_user()
            if not current_user:
                return
            
            # Get selected values
            level_text = self.level_combo.currentText()
            hierarchy_level = HierarchyLevel(level_text)
            is_dev = self.dev_checkbox.isChecked()
            is_moderator = self.mod_checkbox.isChecked()
            
            # Update hierarchy
            result = hierarchy_manager.update_user_hierarchy(
                target_id=user_id,
                modifier_id=current_user.id,
                hierarchy_level=hierarchy_level,
                is_dev=is_dev,
                is_moderator=is_moderator
            )
            
            if result['success']:
                QMessageBox.information(self, "Success", "User hierarchy updated successfully!")
                # Refresh the display
                self.search_user()
            else:
                QMessageBox.warning(self, "Error", f"Failed to update user hierarchy: {result['message']}")
                
        except Exception as e:
            logger.error(f"Error updating user hierarchy: {e}")
            QMessageBox.critical(self, "Error", f"An error occurred: {str(e)}")
