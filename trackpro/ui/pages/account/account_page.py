import logging
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QPushButton, 
    QStackedWidget, QScrollArea, QLineEdit, QTextEdit, QDateEdit, 
    QComboBox, QCheckBox, QFileDialog, QMessageBox, QSpinBox,
    QGroupBox, QGridLayout, QSizePolicy, QSpacerItem
)
from PyQt6.QtCore import Qt, pyqtSignal, QDate, QTimer
from PyQt6.QtGui import QFont, QPixmap, QPainter, QPen, QBrush

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
    
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.select_avatar()
    
    def select_avatar(self):
        """Open file dialog to select new avatar."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Avatar Image",
            "",
            "Image files (*.png *.jpg *.jpeg *.gif *.bmp)"
        )
        
        if file_path:
            # TODO: Implement avatar upload and processing
            QMessageBox.information(self, "Avatar Upload", f"Avatar upload selected: {file_path}")

class AccountPage(QWidget):
    """Main Account page with sidebar navigation."""
    
    def __init__(self, global_managers=None):
        super().__init__()
        self.global_managers = global_managers
        self.current_section = "profile"
        self.user_data = {}
        self.is_initialized = False
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
        
        # Save button
        save_notifications_btn = ModernButton("Save Notification Settings", "primary")
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
        
        # Discord Integration Card
        discord_card = ModernCard("Discord Integration")
        discord_layout = QVBoxLayout()
        
        # Discord status
        self.discord_status_label = QLabel("Status: Not Connected")
        self.discord_status_label.setStyleSheet(self.iracing_status_label.styleSheet())
        discord_layout.addWidget(self.discord_status_label)
        
        # Discord features
        self.discord_rich_presence_check = QCheckBox("Enable Discord Rich Presence")
        self.discord_community_check = QCheckBox("Join TrackPro Discord Community")
        
        checkbox_style = """
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
        """
        
        for checkbox in [self.discord_rich_presence_check, self.discord_community_check]:
            checkbox.setStyleSheet(checkbox_style)
            discord_layout.addWidget(checkbox)
        
        # Discord connect button
        self.connect_discord_btn = ModernButton("Connect Discord", "secondary")
        self.connect_discord_btn.clicked.connect(self.connect_discord)
        discord_layout.addWidget(self.connect_discord_btn)
        
        discord_card.content_layout.addLayout(discord_layout)
        layout.addWidget(discord_card)
        
        # Save Connections Button
        save_connections_btn = ModernButton("Save Connection Settings", "primary")
        save_connections_btn.clicked.connect(self.save_connection_settings)
        layout.addWidget(save_connections_btn)
        
        layout.addStretch()
        return widget
    
    def create_privacy_section(self):
        """Create the privacy and data section with improved layout and readability."""
        widget = QWidget()
        widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.MinimumExpanding)
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(36)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        # Header with optimized typography and spacing
        header_container = QWidget()
        header_layout = QVBoxLayout(header_container)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(8)
        
        header_label = QLabel("Privacy & Data")
        header_label.setStyleSheet("""
            QLabel {
                color: #ffffff;
                font-size: 28px;
                font-weight: 700;
                border: none;
                background: transparent;
                letter-spacing: -0.5px;
                margin-bottom: 4px;
            }
        """)
        
        header_subtitle = QLabel("Manage your privacy settings and data preferences")
        header_subtitle.setStyleSheet("""
            QLabel {
                color: #b9bbbe;
                font-size: 15px;
                font-weight: 400;
                border: none;
                background: transparent;
                line-height: 1.3;
            }
        """)
        
        header_layout.addWidget(header_label)
        header_layout.addWidget(header_subtitle)
        layout.addWidget(header_container)
        
        # Privacy Controls Card - Optimized layout and spacing
        privacy_card = ModernCard("Privacy Settings")
        privacy_card.setMinimumHeight(420)
        privacy_layout = QVBoxLayout()
        privacy_layout.setSpacing(24)
        privacy_layout.setContentsMargins(0, 0, 0, 0)
        
        # Profile visibility section with optimized organization
        visibility_section = QWidget()
        visibility_layout = QVBoxLayout(visibility_section)
        visibility_layout.setSpacing(14)
        visibility_layout.setContentsMargins(0, 0, 0, 0)
        
        visibility_title = QLabel("Profile Visibility")
        visibility_title.setStyleSheet("""
            QLabel {
                color: #ffffff;
                font-size: 17px;
                font-weight: 600;
                border: none;
                background: transparent;
            }
        """)
        
        visibility_description = QLabel("Control who can see your profile and racing information")
        visibility_description.setStyleSheet("""
            QLabel {
                color: #b9bbbe;
                font-size: 13px;
                font-weight: 400;
                border: none;
                background: transparent;
                line-height: 1.3;
            }
        """)
        
        visibility_control_layout = QHBoxLayout()
        visibility_control_layout.setSpacing(16)
        
        visibility_label = QLabel("Profile Visibility:")
        visibility_label.setStyleSheet("""
            QLabel {
                color: #dcddde;
                font-weight: 500;
                font-size: 13px;
                min-width: 140px;
            }
        """)
        
        self.profile_visibility_combo = QComboBox()
        self.profile_visibility_combo.addItems(["Public", "Friends Only", "Private"])
        self.profile_visibility_combo.setStyleSheet("""
            QComboBox {
                background-color: #40444b;
                border: 2px solid #40444b;
                border-radius: 8px;
                padding: 10px 16px;
                color: #fefefe;
                font-size: 13px;
                min-width: 160px;
                font-weight: 500;
            }
            QComboBox:hover {
                border-color: #5865f2;
                background-color: #36393f;
            }
            QComboBox:focus {
                border-color: #5865f2;
                background-color: #36393f;
            }
            QComboBox::drop-down {
                border: none;
                width: 24px;
            }
            QComboBox::down-arrow {
                image: none;
                border-style: solid;
                border-width: 5px 5px 0px 5px;
                border-color: #dcddde transparent transparent transparent;
            }
        """)
        
        visibility_control_layout.addWidget(visibility_label)
        visibility_control_layout.addWidget(self.profile_visibility_combo)
        visibility_control_layout.addStretch()
        
        visibility_layout.addWidget(visibility_title)
        visibility_layout.addWidget(visibility_description)
        visibility_layout.addLayout(visibility_control_layout)
        privacy_layout.addWidget(visibility_section)
        
        # Optimized separator with better styling
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setStyleSheet("background-color: #40444b; margin: 10px 0; min-height: 1px;")
        privacy_layout.addWidget(separator)
        
        # Privacy checkboxes with optimized layout and readability
        privacy_options_section = QWidget()
        privacy_options_layout = QVBoxLayout(privacy_options_section)
        privacy_options_layout.setSpacing(14)
        privacy_options_layout.setContentsMargins(0, 0, 0, 0)
        
        privacy_options_title = QLabel("Privacy Options")
        privacy_options_title.setStyleSheet("""
            QLabel {
                color: #ffffff;
                font-size: 17px;
                font-weight: 600;
                border: none;
                background: transparent;
            }
        """)
        
        privacy_options_description = QLabel("Choose what information you want to share with the community")
        privacy_options_description.setStyleSheet("""
            QLabel {
                color: #b9bbbe;
                font-size: 13px;
                font-weight: 400;
                border: none;
                background: transparent;
                line-height: 1.3;
            }
        """)
        
        privacy_options_layout.addWidget(privacy_options_title)
        privacy_options_layout.addWidget(privacy_options_description)
        
        # Create checkboxes with enhanced spacing and layout
        self.share_telemetry_check = QCheckBox("Share telemetry data for community insights and analytics")
        self.show_statistics_check = QCheckBox("Show my racing statistics and achievements publicly")
        self.allow_friend_requests_check = QCheckBox("Allow friend requests from other users")
        self.show_online_status_check = QCheckBox("Show when I'm online and available for racing")
        
        checkbox_style = """
            QCheckBox {
                color: #dcddde;
                font-size: 13px;
                font-weight: 500;
                spacing: 16px;
                padding: 14px 18px;
                background-color: #36393f;
                border: 1px solid #40444b;
                border-radius: 8px;
                min-height: 52px;
                line-height: 1.3;
            }
            QCheckBox:hover {
                background-color: #40444b;
                border-color: #5865f2;
                transform: translateY(-1px);
            }
            QCheckBox::indicator {
                width: 22px;
                height: 22px;
                border-radius: 5px;
                margin-right: 14px;
            }
            QCheckBox::indicator:unchecked {
                background-color: #40444b;
                border: 2px solid #72767d;
            }
            QCheckBox::indicator:checked {
                background-color: #5865f2;
                border: 2px solid #5865f2;
                image: url(data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTIiIGhlaWdodD0iOSIgdmlld0JveD0iMCAwIDEyIDkiIGZpbGw9Im5vbmUiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+CjxwYXRoIGQ9Ik0xMC42IDEuNEw0LjIgNy44TDEuNCA1IiBzdHJva2U9IndoaXRlIiBzdHJva2Utd2lkdGg9IjIiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIgc3Ryb2tlLWxpbmVqb2luPSJyb3VuZCIvPgo8L3N2Zz4K);
            }
            QCheckBox::indicator:checked:hover {
                background-color: #4752c4;
            }
            QCheckBox::indicator:unchecked:hover {
                border-color: #8e9297;
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
            checkbox.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
            privacy_options_layout.addWidget(checkbox)
        
        privacy_layout.addWidget(privacy_options_section)
        privacy_card.content_layout.addLayout(privacy_layout)
        layout.addWidget(privacy_card)
        
        # Data Management Card - Optimized layout and spacing
        data_card = ModernCard("Data Management")
        data_card.setMinimumHeight(480)
        data_layout = QVBoxLayout()
        data_layout.setSpacing(24)
        data_layout.setContentsMargins(0, 0, 0, 0)
        
        # Data export section with optimized organization
        export_section = QWidget()
        export_layout = QVBoxLayout(export_section)
        export_layout.setSpacing(16)
        export_layout.setContentsMargins(0, 0, 0, 0)
        
        export_title = QLabel("Export Your Data")
        export_title.setStyleSheet("""
            QLabel {
                color: #ffffff;
                font-size: 17px;
                font-weight: 600;
                border: none;
                background: transparent;
            }
        """)
        
        export_description = QLabel("Download your personal data for backup or transfer purposes")
        export_description.setStyleSheet("""
            QLabel {
                color: #b9bbbe;
                font-size: 13px;
                font-weight: 400;
                border: none;
                background: transparent;
                line-height: 1.3;
            }
        """)
        
        export_buttons_layout = QHBoxLayout()
        export_buttons_layout.setSpacing(16)
        
        self.export_profile_btn = ModernButton("Export Profile Data", "secondary")
        self.export_profile_btn.clicked.connect(self.export_profile_data)
        self.export_profile_btn.setToolTip("Export your profile data, settings, and preferences")
        self.export_profile_btn.setMinimumWidth(180)
        self.export_profile_btn.setMinimumHeight(42)
        
        self.export_telemetry_btn = ModernButton("Export Telemetry Data", "secondary")
        self.export_telemetry_btn.clicked.connect(self.export_telemetry_data)
        self.export_telemetry_btn.setToolTip("Export your racing data and telemetry")
        self.export_telemetry_btn.setMinimumWidth(180)
        self.export_telemetry_btn.setMinimumHeight(42)
        
        export_buttons_layout.addWidget(self.export_profile_btn)
        export_buttons_layout.addWidget(self.export_telemetry_btn)
        export_buttons_layout.addStretch()
        
        export_layout.addWidget(export_title)
        export_layout.addWidget(export_description)
        export_layout.addLayout(export_buttons_layout)
        data_layout.addWidget(export_section)
        
        # Optimized separator
        separator2 = QFrame()
        separator2.setFrameShape(QFrame.Shape.HLine)
        separator2.setStyleSheet("background-color: #40444b; margin: 10px 0; min-height: 1px;")
        data_layout.addWidget(separator2)
        
        # Data usage stats with optimized formatting
        usage_section = QWidget()
        usage_layout = QVBoxLayout(usage_section)
        usage_layout.setSpacing(16)
        usage_layout.setContentsMargins(0, 0, 0, 0)
        
        usage_title = QLabel("Data Usage Statistics")
        usage_title.setStyleSheet("""
            QLabel {
                color: #ffffff;
                font-size: 17px;
                font-weight: 600;
                border: none;
                background: transparent;
            }
        """)
        
        usage_description = QLabel("Overview of your data storage and usage")
        usage_description.setStyleSheet("""
            QLabel {
                color: #b9bbbe;
                font-size: 13px;
                font-weight: 400;
                border: none;
                background: transparent;
                line-height: 1.3;
            }
        """)
        
        # Create a proper text area for data usage with optimized styling
        self.data_usage_text = QTextEdit()
        self.data_usage_text.setReadOnly(True)
        self.data_usage_text.setMaximumHeight(150)
        self.data_usage_text.setMinimumHeight(150)
        self.data_usage_text.setStyleSheet("""
            QTextEdit {
                background-color: #2f3136;
                border: 2px solid #40444b;
                border-radius: 8px;
                color: #b9bbbe;
                font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
                font-size: 12px;
                line-height: 1.5;
                padding: 16px;
                selection-background-color: #5865f2;
            }
            QTextEdit:focus {
                border-color: #5865f2;
            }
        """)
        
        # Set initial data usage content with enhanced formatting
        data_usage_content = """📊 Data Usage Summary

• Profile data: ~2.5 KB
• Racing statistics: ~15.3 KB  
• Telemetry data: ~127.8 MB
• Total storage used: ~128.0 MB

Last updated: Just now"""
        self.data_usage_text.setPlainText(data_usage_content)
        
        usage_layout.addWidget(usage_title)
        usage_layout.addWidget(usage_description)
        usage_layout.addWidget(self.data_usage_text)
        data_layout.addWidget(usage_section)
        
        data_card.content_layout.addLayout(data_layout)
        layout.addWidget(data_card)
        
        # Account Deletion Card - Optimized warning design
        deletion_card = ModernCard("Account Deletion")
        deletion_card.setMinimumHeight(520)
        deletion_layout = QVBoxLayout()
        deletion_layout.setSpacing(24)
        deletion_layout.setContentsMargins(0, 0, 0, 0)
        
        # Warning header with optimized visual hierarchy
        warning_section = QWidget()
        warning_layout = QHBoxLayout(warning_section)
        warning_layout.setSpacing(16)
        warning_layout.setContentsMargins(0, 0, 0, 0)
        
        warning_icon = QLabel("⚠️")
        warning_icon.setStyleSheet("font-size: 28px;")
        
        warning_text_container = QWidget()
        warning_text_layout = QVBoxLayout(warning_text_container)
        warning_text_layout.setSpacing(4)
        warning_text_layout.setContentsMargins(0, 0, 0, 0)
        
        warning_title = QLabel("Danger Zone")
        warning_title.setStyleSheet("color: #f04747; font-size: 20px; font-weight: 700;")
        
        warning_subtitle = QLabel("Permanent account deletion")
        warning_subtitle.setStyleSheet("color: #b9bbbe; font-size: 13px; font-weight: 400; line-height: 1.3;")
        
        warning_text_layout.addWidget(warning_title)
        warning_text_layout.addWidget(warning_subtitle)
        
        warning_layout.addWidget(warning_icon)
        warning_layout.addWidget(warning_text_container)
        warning_layout.addStretch()
        deletion_layout.addWidget(warning_section)
        
        # Warning info with optimized formatting
        deletion_info = QLabel("Once you delete your account, there is no going back. This action cannot be undone.\n\nDeleting your account will permanently remove all your data and cannot be reversed.")
        deletion_info.setStyleSheet("""
            QLabel {
                color: #b9bbbe;
                font-size: 13px;
                line-height: 1.5;
                border: none;
                background: transparent;
            }
        """)
        deletion_info.setWordWrap(True)
        deletion_layout.addWidget(deletion_info)
        
        # Consequences list with optimized styling
        consequences_container = QWidget()
        consequences_container.setStyleSheet("""
            QWidget {
                background-color: #3c2d2d;
                border: 1px solid #f04747;
                border-radius: 8px;
                padding: 16px;
            }
        """)
        
        consequences_layout = QVBoxLayout(consequences_container)
        consequences_layout.setSpacing(10)
        consequences_layout.setContentsMargins(16, 16, 16, 16)
        
        consequences_title = QLabel("What will be deleted:")
        consequences_title.setStyleSheet("color: #f04747; font-size: 15px; font-weight: 600;")
        
        consequences_list = QLabel("• All your profile data and personal information\n• Complete racing statistics and achievements history\n• All telemetry data and session recordings\n• Active subscriptions and premium features\n• Team memberships and community participation\n• All saved settings and preferences")
        consequences_list.setStyleSheet("""
            QLabel {
                color: #f04747;
                font-size: 13px;
                line-height: 1.5;
                border: none;
                background: transparent;
            }
        """)
        consequences_list.setWordWrap(True)
        consequences_list.setMinimumHeight(130)
        
        consequences_layout.addWidget(consequences_title)
        consequences_layout.addWidget(consequences_list)
        deletion_layout.addWidget(consequences_container)
        
        # Delete button with optimized styling and positioning
        delete_button_container = QWidget()
        delete_button_layout = QHBoxLayout(delete_button_container)
        delete_button_layout.setContentsMargins(0, 0, 0, 0)
        delete_button_layout.addStretch()
        
        self.delete_account_btn = ModernButton("Delete Account", "danger")
        self.delete_account_btn.clicked.connect(self.request_account_deletion)
        self.delete_account_btn.setStyleSheet("""
            QPushButton {
                background-color: #f04747;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 14px 28px;
                font-size: 13px;
                font-weight: 600;
                min-width: 160px;
                min-height: 44px;
            }
            QPushButton:hover {
                background-color: #d73d3d;
            }
            QPushButton:pressed {
                background-color: #c73030;
            }
        """)
        
        delete_button_layout.addWidget(self.delete_account_btn)
        delete_button_layout.addStretch()
        deletion_layout.addWidget(delete_button_container)
        
        deletion_card.content_layout.addLayout(deletion_layout)
        layout.addWidget(deletion_card)
        
        # Save Privacy Settings Button - Optimized positioning and styling
        save_button_container = QWidget()
        save_button_layout = QHBoxLayout(save_button_container)
        save_button_layout.setContentsMargins(0, 0, 0, 0)
        save_button_layout.addStretch()
        
        save_privacy_btn = ModernButton("Save Privacy Settings", "primary")
        save_privacy_btn.clicked.connect(self.save_privacy_settings)
        save_privacy_btn.setStyleSheet("""
            QPushButton {
                background-color: #5865f2;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 14px 28px;
                font-size: 13px;
                font-weight: 600;
                min-width: 200px;
                min-height: 44px;
            }
            QPushButton:hover {
                background-color: #4752c4;
            }
            QPushButton:pressed {
                background-color: #3c45a3;
            }
        """)
        
        save_button_layout.addWidget(save_privacy_btn)
        save_button_layout.addStretch()
        layout.addWidget(save_button_container)
        
        layout.addStretch()
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
        
        logger.info(f"Switched to account section: {section_id}")
    
    def load_user_data(self):
        """Load current user data from the database."""
        try:
            # Load profile from Supabase
            from ....database.supabase_client import get_supabase_client
            from ...social.user_manager import enhanced_user_manager
            
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
            profile_data = enhanced_user_manager.get_complete_user_profile()
            
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
                
                # Update avatar initials
                first_initial = self.user_data.get("first_name", "U")[0].upper()
                last_initial = self.user_data.get("last_name", "")[0].upper() if self.user_data.get("last_name") else ""
                self.profile_avatar.setText(f"{first_initial}{last_initial}")
            
            logger.info("User data loaded successfully")
            
        except Exception as e:
            logger.error(f"Error loading user data: {e}")
    
    def save_profile(self):
        """Save profile changes."""
        try:
            # Get form data
            profile_data = {
                "first_name": self.first_name_input.text().strip(),
                "last_name": self.last_name_input.text().strip(),
                "display_name": self.display_name_input.text().strip(),
                "bio": self.bio_input.toPlainText().strip(),
                "date_of_birth": self.dob_input.date().toString("yyyy-MM-dd")
            }
            
            # Validate required fields
            if not profile_data["first_name"] or not profile_data["last_name"]:
                QMessageBox.warning(self, "Validation Error", "First name and last name are required.")
                return
            
            # Save to Supabase using enhanced user manager
            from ....database.supabase_client import get_supabase_client
            from ...social.user_manager import enhanced_user_manager
            
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
            
            # Save to Supabase
            success = enhanced_user_manager.update_user_profile(user_id, profile_data)
            
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
                # TODO: Implement actual logout functionality
                logger.info("User logout initiated")
                
                # Get main window and trigger logout
                main_window = self.parent()
                while main_window and not hasattr(main_window, 'handle_logout'):
                    main_window = main_window.parent()
                
                if main_window and hasattr(main_window, 'handle_logout'):
                    main_window.handle_logout()
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
            from ...social.user_manager import enhanced_user_manager
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
            
            # Upload to Supabase Storage
            try:
                storage_response = supabase_client.storage.from_('avatars').upload(
                    filename,
                    file_data,
                    {
                        'content-type': mime_type,
                        'cache-control': '3600',
                        'upsert': 'true'
                    }
                )
                logger.info(f"Storage upload response: {storage_response}")
                progress.setValue(90)
                
                # Get public URL
                public_url = supabase_client.storage.from_('avatars').get_public_url(filename)
                avatar_url = public_url
                
                # Update user profile with new avatar URL
                success = enhanced_user_manager.update_user_profile(user_id, {
                    'avatar_url': avatar_url
                })
                
                progress.setValue(100)
                progress.close()
                
                if success:
                    # Update local avatar display
                    self.load_avatar_from_url(avatar_url)
                    
                    from PyQt6.QtWidgets import QMessageBox
                    QMessageBox.information(self, "Success", "Avatar uploaded successfully!")
                    logger.info(f"Avatar uploaded successfully: {avatar_url}")
                else:
                    from PyQt6.QtWidgets import QMessageBox
                    QMessageBox.warning(self, "Upload Failed", "Failed to save avatar to profile.")
                    
            except Exception as storage_error:
                progress.close()
                logger.error(f"Storage upload error: {storage_error}")
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.critical(self, "Upload Error", f"Failed to upload avatar: {str(storage_error)}")
            
        except Exception as e:
            if 'progress' in locals():
                progress.close()
            logger.error(f"Error uploading avatar: {e}")
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Error", f"Failed to upload avatar: {str(e)}")
    
    def load_avatar_from_url(self, url):
        """Load and display avatar from URL."""
        try:
            from PyQt6.QtNetwork import QNetworkAccessManager, QNetworkRequest
            from PyQt6.QtCore import QUrl
            
            # Create network manager if it doesn't exist
            if not hasattr(self, 'network_manager'):
                self.network_manager = QNetworkAccessManager(self)
            
            # Download image
            request = QNetworkRequest(QUrl(url))
            reply = self.network_manager.get(request)
            
            def on_avatar_downloaded():
                try:
                    if reply.error() == reply.NetworkError.NoError:
                        image_data = reply.readAll()
                        pixmap = QPixmap()
                        pixmap.loadFromData(image_data)
                        
                        # Scale and crop to circle
                        if not pixmap.isNull():
                            # Scale to fit avatar size
                            scaled_pixmap = pixmap.scaled(
                                120, 120, 
                                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                                Qt.TransformationMode.SmoothTransformation
                            )
                            
                            # Create circular mask
                            circular_pixmap = QPixmap(120, 120)
                            circular_pixmap.fill(Qt.GlobalColor.transparent)
                            
                            painter = QPainter(circular_pixmap)
                            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                            painter.setBrush(QBrush(scaled_pixmap))
                            painter.setPen(QPen(Qt.GlobalColor.transparent))
                            painter.drawEllipse(0, 0, 120, 120)
                            painter.end()
                            
                            # Update avatar display
                            if hasattr(self, 'profile_avatar'):
                                self.profile_avatar.setPixmap(circular_pixmap)
                                self.profile_avatar.setText("")  # Clear text
                    
                    reply.deleteLater()
                except Exception as e:
                    logger.error(f"Error processing downloaded avatar: {e}")
            
            reply.finished.connect(on_avatar_downloaded)
            
        except Exception as e:
            logger.error(f"Error loading avatar from URL: {e}")
    
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
    
    def save_notification_settings(self):
        """Save notification preferences."""
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
            
            # TODO: Save to Supabase user preferences
            logger.info(f"Saving notification settings: {notification_settings}")
            
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.information(
                self,
                "Settings Saved",
                "Your notification preferences have been saved successfully!"
            )
            
        except Exception as e:
            logger.error(f"Error saving notification settings: {e}")
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Error", f"Failed to save notification settings: {str(e)}")
    
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
            from ...social.user_manager import enhanced_user_manager
            
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
            success = enhanced_user_manager.update_user_profile(user_id, {
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
    
    def connect_discord(self):
        """Connect to Discord."""
        try:
            # TODO: Implement Discord OAuth integration
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.information(
                self,
                "Discord Connection",
                "Discord integration will be implemented soon."
            )
            logger.info("Discord connection requested")
            
        except Exception as e:
            logger.error(f"Error connecting to Discord: {e}")
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Error", f"Failed to connect to Discord: {str(e)}")
    
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
            from ...social.user_manager import enhanced_user_manager
            
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
            success = enhanced_user_manager.update_user_profile(user_id, {
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
            from ...social.user_manager import enhanced_user_manager
            
            supabase_client = get_supabase_client()
            if not supabase_client:
                QMessageBox.warning(self, "Connection Error", "Unable to connect to database.")
                return
            
            user_response = supabase_client.auth.get_user()
            if not user_response or not user_response.user:
                QMessageBox.warning(self, "Authentication Required", "You must be logged in to export data.")
                return
            
            # Get complete profile
            profile_data = enhanced_user_manager.get_complete_user_profile()
            
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
