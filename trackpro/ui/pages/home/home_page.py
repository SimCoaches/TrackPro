"""Homepage with user welcome, date, and announcements."""

import logging
from datetime import datetime
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QScrollArea, QFrame, QGridLayout, QPushButton, QSizePolicy)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QGuiApplication
from PyQt6.QtGui import QFont, QPixmap, QPainter, QBrush, QColor, QPen
from ...avatar_manager import AvatarManager
from ...modern.shared.base_page import BasePage

logger = logging.getLogger(__name__)

class HomePage(BasePage):
    """Home page with welcome message, date, and announcements."""
    
    def __init__(self, global_managers=None):
        super().__init__("home", global_managers)
        self._auth_check_completed = False
        self._cached_auth_state = None
        self.setup_ui()
        
    def init_page(self):
        """Initialize the page - called by BasePage."""
        # This is called by BasePage, but we do our setup in setup_ui
        pass
        
    def setup_ui(self):
        """Set up the home page UI."""
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)
        
        # Main content area with two columns
        main_content = QHBoxLayout()
        main_content.setSpacing(30)
        
        # Left column - User welcome section
        left_column = self.create_welcome_section()
        main_content.addWidget(left_column)
        
        # Right column - Dashboard + Events
        right_column = self.create_right_column()
        main_content.addWidget(right_column)
        
        layout.addLayout(main_content)
        
        # Add stretch to push content to top
        layout.addStretch()
        
        self.setLayout(layout)
        
        # Update date and events
        self.update_date()
        self.load_events()
        
        # Initialize avatar with default or current user
        self.initialize_avatar()
        
        # Set up timer to update date every minute
        self.date_timer = QTimer()
        self.date_timer.timeout.connect(self.update_date)
        self.date_timer.start(60000)  # Update every minute

        # Readiness/metrics refresh (Phase 2 minimal wiring)
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self.update_readiness)
        self.status_timer.start(2500)
        
    def create_welcome_section(self):
        """Create the left column welcome section."""
        welcome_frame = QFrame()
        welcome_frame.setFrameStyle(QFrame.Shape.StyledPanel)
        welcome_frame.setStyleSheet("""
            QFrame {
                background-color: #2a2a2a;
                border-radius: 15px;
                border: 1px solid #3a3a3a;
            }
        """)
        welcome_frame.setFixedWidth(400)
        
        welcome_layout = QVBoxLayout(welcome_frame)
        welcome_layout.setContentsMargins(30, 30, 30, 30)
        welcome_layout.setSpacing(20)
        
        # User avatar - optimized sizing
        self.avatar_label = QLabel()
        self.avatar_label.setFixedSize(100, 100)  # Reduced from 120x120
        self.avatar_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # Styling kept minimal so loaded pixmap is not tinted/overdrawn
        self.avatar_label.setStyleSheet("QLabel { border: none; background-color: transparent; }")
        # Don't set default text - will be replaced by dynamic avatar
        welcome_layout.addWidget(self.avatar_label, alignment=Qt.AlignmentFlag.AlignCenter)
        
        # Welcome message
        self.welcome_label = QLabel("Welcome to TrackPro!")
        self.welcome_label.setFont(QFont("Arial", 22, QFont.Weight.Bold))  # Slightly smaller
        self.welcome_label.setStyleSheet("color: #ffffff; margin: 10px;")
        self.welcome_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.welcome_label.setWordWrap(True)
        welcome_layout.addWidget(self.welcome_label)
        
        # Date and time
        self.date_label = QLabel()
        self.date_label.setFont(QFont("Arial", 13))  # Slightly smaller
        self.date_label.setStyleSheet("color: #cccccc; margin: 5px;")
        self.date_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        welcome_layout.addWidget(self.date_label)
        
        # Authentication buttons container (initially hidden)
        self.auth_buttons_container = QWidget()
        self.auth_buttons_container.setStyleSheet("""
            QWidget {
                background-color: transparent;
            }
        """)
        auth_buttons_layout = QVBoxLayout(self.auth_buttons_container)
        auth_buttons_layout.setSpacing(10)
        auth_buttons_layout.setContentsMargins(0, 10, 0, 0)
        
        # Sign Up button
        self.signup_button = QPushButton("Sign Up")
        self.signup_button.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        self.signup_button.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                border: none;
                padding: 12px;
                border-radius: 6px;
                color: white;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QPushButton:pressed {
                background-color: #21618c;
            }
        """)
        self.signup_button.clicked.connect(self.show_signup_dialog)
        auth_buttons_layout.addWidget(self.signup_button)
        
        # Log In button
        self.login_button = QPushButton("Log In")
        self.login_button.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        self.login_button.setStyleSheet("""
            QPushButton {
                background-color: #2ecc71;
                border: none;
                padding: 12px;
                border-radius: 6px;
                color: white;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #27ae60;
            }
            QPushButton:pressed {
                background-color: #1e8449;
            }
        """)
        self.login_button.clicked.connect(self.show_login_dialog)
        auth_buttons_layout.addWidget(self.login_button)
        
        # Add auth buttons to welcome layout
        welcome_layout.addWidget(self.auth_buttons_container)
        
        # Show auth buttons by default for non-authenticated users
        self.auth_buttons_container.setVisible(True)
        
        return welcome_frame

    def create_right_column(self):
        container = QFrame()
        container.setFrameStyle(QFrame.Shape.StyledPanel)
        container.setStyleSheet("""
            QFrame {
                background-color: transparent;
                border: none;
            }
        """)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(20)

        # Dashboard grid (cards)
        dashboard = self.create_dashboard_section()
        layout.addWidget(dashboard)

        # Events below
        events = self.create_events_section()
        layout.addWidget(events)

        return container

    def create_dashboard_section(self):
        frame = QFrame()
        frame.setFrameStyle(QFrame.Shape.StyledPanel)
        frame.setStyleSheet("""
            QFrame {
                background-color: #1f1f1f;
                border-radius: 12px;
                border: 1px solid #2e2e2e;
            }
        """)
        grid = QGridLayout(frame)
        grid.setContentsMargins(20, 20, 20, 20)
        grid.setHorizontalSpacing(16)
        grid.setVerticalSpacing(16)

        # Create cards
        quick_actions = self.create_quick_actions_card()
        readiness = self.create_readiness_card()
        performance = self.create_performance_card()
        ai_coach = self.create_ai_coach_card()
        race_pass = self.create_race_pass_card()
        community = self.create_community_card()

        # Store for reflow
        self._dashboard_frame = frame
        self._dashboard_grid = grid
        self._dashboard_cards = [quick_actions, readiness, performance, ai_coach, race_pass, community]
        self._dashboard_columns = self._compute_dashboard_columns()
        self._layout_dashboard_cards()

        return frame

    def _compute_dashboard_columns(self) -> int:
        screen = QGuiApplication.primaryScreen()
        width = screen.size().width() if screen else 1280
        if width >= 1700:
            return 3
        return 2

    def _layout_dashboard_cards(self):
        # Clear existing items from grid
        while self._dashboard_grid.count():
            item = self._dashboard_grid.takeAt(0)
            if item and item.widget():
                self._dashboard_grid.removeWidget(item.widget())
        # Re-add based on columns
        for index, card in enumerate(self._dashboard_cards):
            row = index // self._dashboard_columns
            col = index % self._dashboard_columns
            self._dashboard_grid.addWidget(card, row, col)

    def create_card(self, title: str) -> QFrame:
        card = QFrame()
        card.setFrameStyle(QFrame.Shape.StyledPanel)
        card.setStyleSheet("""
            QFrame {
                background-color: #2a2a2a;
                border-radius: 10px;
                border: 1px solid #3a3a3a;
            }
            QFrame:hover {
                background-color: #313131;
                border: 1px solid #4a4a4a;
            }
            QLabel[role="title"] {
                color: #ffffff;
                font-size: 16px;
                font-weight: bold;
            }
            QLabel[role="chip"] {
                border-radius: 10px;
                padding: 4px 8px;
                font-size: 11px;
                font-weight: 600;
            }
        """)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        title_label = QLabel(title)
        title_label.setProperty("role", "title")
        layout.addWidget(title_label)

        return card

    def create_quick_actions_card(self) -> QFrame:
        card = self.create_card("Quick Actions")

        def make_btn(text: str, color: str):
            btn = QPushButton(text)
            btn.setMinimumWidth(120)
            btn.setFixedHeight(34)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {color};
                    color: white;
                    border: none;
                    padding: 6px 10px;
                    border-radius: 6px;
                    font-weight: bold;
                    font-size: 13px;
                }}
                QPushButton:hover {{ filter: brightness(1.1); }}
            """)
            return btn

        # Short labels for readability in compact width
        calibrate_btn = make_btn("Calibrate", "#2a82da")
        coach_btn = make_btn("Coach", "#27ae60")
        voice_btn = make_btn("Voice", "#8e44ad")
        race_pass_btn = make_btn("Race Pass", "#f39c12")

        calibrate_btn.clicked.connect(lambda: self.navigate_to_page("pedals"))
        coach_btn.clicked.connect(lambda: self.navigate_to_page("race_coach"))
        voice_btn.clicked.connect(self.on_launch_voice_chat)
        race_pass_btn.clicked.connect(lambda: self.navigate_to_page("race_pass"))

        grid = QGridLayout()
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(8)
        grid.addWidget(calibrate_btn, 0, 0)
        grid.addWidget(coach_btn, 0, 1)
        grid.addWidget(voice_btn, 1, 0)
        grid.addWidget(race_pass_btn, 1, 1)
        card.layout().addLayout(grid)
        return card

    def create_status_chip(self, text: str, status: str = "unknown") -> QLabel:
        color_map = {
            "ok": ("#1e824c", "#2ecc71"),
            "warn": ("#7f6a00", "#f1c40f"),
            "error": ("#7e1d1d", "#e74c3c"),
            "unknown": ("#3a3a3a", "#7f8c8d"),
        }
        bg, fg = color_map.get(status, color_map["unknown"])
        chip = QLabel(text)
        chip.setProperty("role", "chip")
        chip.setStyleSheet(f"""
            QLabel[role="chip"] {{
                background-color: {bg};
                color: {fg};
            }}
        """)
        return chip

    def create_readiness_card(self) -> QFrame:
        card = self.create_card("System Readiness")
        grid = QGridLayout()
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(8)

        self.pedals_chip = self.create_status_chip("Pedals", "unknown")
        self.voice_chip = self.create_status_chip("Voice", "unknown")
        self.auth_chip = self.create_status_chip("Auth", "unknown")
        self.perf_chip = self.create_status_chip("UI Perf", "unknown")

        grid.addWidget(self.pedals_chip, 0, 0)
        grid.addWidget(self.voice_chip, 0, 1)
        grid.addWidget(self.auth_chip, 1, 0)
        grid.addWidget(self.perf_chip, 1, 1)

        card.layout().addLayout(grid)
        return card

    def create_performance_card(self) -> QFrame:
        card = self.create_card("Last Session Snapshot")
        self.perf_label = QLabel("Avg UI: — ms | Dropped: —")
        self.perf_label.setStyleSheet("color: #cccccc;")
        card.layout().addWidget(self.perf_label)
        return card

    def create_ai_coach_card(self) -> QFrame:
        card = self.create_card("AI Coach")
        subtitle = QLabel("Quick toggle and last insights")
        subtitle.setStyleSheet("color: #cccccc;")
        card.layout().addWidget(subtitle)

        btn_row = QHBoxLayout()
        toggle_btn = QPushButton("Coming Soon")
        toggle_btn.setEnabled(False)
        toggle_btn.setStyleSheet("""
            QPushButton {
                background-color: #555555;
                color: #dddddd;
                border: none;
                padding: 8px 12px;
                border-radius: 6px;
                font-weight: bold;
            }
        """)
        btn_row.addWidget(toggle_btn)
        btn_row.addStretch()
        card.layout().addLayout(btn_row)
        return card

    def create_race_pass_card(self) -> QFrame:
        card = self.create_card("Race Pass")
        label = QLabel("Season progress and next challenge")
        label.setStyleSheet("color: #cccccc;")
        open_btn = QPushButton("Coming Soon")
        open_btn.setStyleSheet("""
            QPushButton {
                background-color: #7f6a00;
                color: #f1c40f;
                border: 1px solid #9a8500;
                padding: 8px 12px;
                border-radius: 6px;
                font-weight: bold;
            }
            QPushButton:hover { filter: brightness(1.1); }
        """)
        open_btn.setEnabled(False)
        card.layout().addWidget(label)
        card.layout().addWidget(open_btn)
        return card

    def create_community_card(self) -> QFrame:
        card = self.create_card("Community")
        self.community_label = QLabel("Friends online: — | Unread DMs: —")
        self.community_label.setStyleSheet("color: #cccccc;")
        open_btn = QPushButton("Open Community")
        open_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                padding: 8px 12px;
                border-radius: 6px;
                font-weight: bold;
            }
            QPushButton:hover { filter: brightness(1.1); }
        """)
        open_btn.clicked.connect(lambda: self.navigate_to_page("community"))
        card.layout().addWidget(self.community_label)
        card.layout().addWidget(open_btn)
        return card

    def update_readiness(self):
        try:
            # Auth
            try:
                from trackpro.auth.user_manager import get_current_user
                current_user = get_current_user()
                if current_user and current_user.is_authenticated:
                    self.set_chip(self.auth_chip, "Auth: OK", "ok")
                else:
                    self.set_chip(self.auth_chip, "Auth: Sign-in", "warn")
            except Exception:
                self.set_chip(self.auth_chip, "Auth: Unknown", "unknown")

            # Voice server
            try:
                from trackpro.voice_server_manager import is_voice_server_running
                is_running = is_voice_server_running()
                self.set_chip(self.voice_chip, "Voice: On" if is_running else "Voice: Off", "ok" if is_running else "error")
            except Exception:
                self.set_chip(self.voice_chip, "Voice: Unknown", "unknown")

            # Pedals (actual connection status when available)
            try:
                hw = getattr(self.global_managers, 'hardware', None)
                if hw is None:
                    self.set_chip(self.pedals_chip, "Pedals: —", "warn")
                else:
                    if getattr(hw, 'pedals_connected', False):
                        self.set_chip(self.pedals_chip, "Pedals: OK", "ok")
                    else:
                        self.set_chip(self.pedals_chip, "Pedals: Off", "error")
            except Exception:
                self.set_chip(self.pedals_chip, "Pedals: Unknown", "unknown")

            # Performance (avg UI time)
            try:
                pm = getattr(self, 'performance_manager', None) or getattr(self.global_managers, 'performance', None)
                if pm and getattr(pm, 'performance_stats', None):
                    avg_ms = pm.performance_stats.get('avg_ui_time', 0.0) * 1000.0
                    dropped = pm.performance_stats.get('dropped_frames', 0)
                    timers_started = getattr(pm, '_timers_started', False)
                    if not timers_started:
                        self.perf_label.setText("Avg UI: — ms | Dropped: —")
                        self.set_chip(self.perf_chip, "UI: —", "unknown")
                    else:
                        self.perf_label.setText(f"Avg UI: {avg_ms:.1f} ms | Dropped: {dropped}")
                        status = "ok" if avg_ms <= 8.0 else ("warn" if avg_ms <= 16.0 else "error")
                        self.set_chip(self.perf_chip, f"UI: {avg_ms:.1f}ms", status)
                else:
                    self.perf_label.setText("Avg UI: — ms | Dropped: —")
                    self.set_chip(self.perf_chip, "UI: —", "unknown")
            except Exception:
                self.set_chip(self.perf_chip, "UI: —", "unknown")

            # Community metrics (friends online, unread DMs)
            try:
                from trackpro.community.community_manager import CommunityManager
                # Ensure current user set for queries requiring it
                try:
                    from trackpro.auth.user_manager import get_current_user
                    user = get_current_user()
                    if user and user.is_authenticated:
                        CommunityManager().set_current_user(user.id)
                except Exception:
                    pass
                convs = CommunityManager().get_private_conversations()
                unread = sum(int(c.get('unread_count') or 0) for c in (convs or []))
                friends = CommunityManager().get_friends() or []
                self.community_label.setText(f"Friends: {len(friends)} | Unread DMs: {unread}")
            except Exception:
                # Keep prior text if fetch fails
                pass
        except Exception:
            pass

    def set_chip(self, chip: QLabel, text: str, status: str):
        chip.setText(text)
        # Re-apply style based on status
        _ = self.create_status_chip("", status)  # for colors
        color_map = {
            "ok": ("#1e824c", "#2ecc71"),
            "warn": ("#7f6a00", "#f1c40f"),
            "error": ("#7e1d1d", "#e74c3c"),
            "unknown": ("#3a3a3a", "#7f8c8d"),
        }
        bg, fg = color_map.get(status, color_map["unknown"])
        chip.setStyleSheet(f"""
            QLabel[role="chip"] {{
                background-color: {bg};
                color: {fg};
                border-radius: 10px;
                padding: 4px 8px;
                font-size: 11px;
                font-weight: 600;
            }}
        """)

    def on_launch_voice_chat(self):
        try:
            from trackpro.voice_server_manager import start_voice_server
            start_voice_server()
        except Exception as e:
            logger.error(f"Could not launch voice server: {e}")

    def navigate_to_page(self, page_name: str):
        try:
            win = self.window()
            if win and hasattr(win, 'switch_to_page'):
                win.switch_to_page(page_name)
        except Exception as e:
            logger.error(f"Navigation error to {page_name}: {e}")

    def resizeEvent(self, event):
        try:
            new_columns = self._compute_dashboard_columns()
            if new_columns != getattr(self, '_dashboard_columns', new_columns):
                self._dashboard_columns = new_columns
                self._layout_dashboard_cards()
        except Exception:
            pass
        super().resizeEvent(event)
        
    def create_events_section(self):
        """Create the right column events section."""
        events_frame = QFrame()
        events_frame.setFrameStyle(QFrame.Shape.StyledPanel)
        events_frame.setStyleSheet("""
            QFrame {
                background-color: #2a2a2a;
                border-radius: 15px;
                border: 1px solid #3a3a3a;
            }
        """)
        
        events_layout = QVBoxLayout(events_frame)
        events_layout.setContentsMargins(30, 30, 30, 30)
        events_layout.setSpacing(20)
        
        # Events title
        events_title = QLabel("Upcoming Events")
        events_title.setFont(QFont("Arial", 20, QFont.Weight.Bold))
        events_title.setStyleSheet("color: #ffffff; margin-bottom: 10px;")
        events_layout.addWidget(events_title)
        
        # Events container
        self.events_container = QVBoxLayout()
        self.events_container.setSpacing(15)
        events_layout.addLayout(self.events_container)
        
        return events_frame
        
    def create_event_card(self, title, subtitle, description, event_image=None):
        """Create an individual event card."""
        event_frame = QFrame()
        event_frame.setFrameStyle(QFrame.Shape.StyledPanel)
        event_frame.setStyleSheet("""
            QFrame {
                background-color: #333333;
                border-radius: 10px;
                border: 1px solid #444444;
            }
            QFrame:hover {
                background-color: #3a3a3a;
                border: 1px solid #555555;
            }
        """)
        
        event_layout = QHBoxLayout(event_frame)
        event_layout.setContentsMargins(15, 15, 15, 15)
        event_layout.setSpacing(15)
        
        # Event image
        image_label = QLabel()
        image_label.setFixedSize(50, 50)  # Smaller icon
        image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        if event_image:
            pixmap = QPixmap(event_image)
            if not pixmap.isNull():
                scaled_pixmap = pixmap.scaled(50, 50, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                image_label.setPixmap(scaled_pixmap)
            else:
                # Fallback to default event icon
                image_label.setStyleSheet("""
                    QLabel {
                        background-color: #3498db;
                        border-radius: 25px;
                        color: white;
                        font-size: 20px;
                    }
                """)
                image_label.setText("🏁")
        else:
            # Default event icon
            image_label.setStyleSheet("""
                QLabel {
                    background-color: #3498db;
                    border-radius: 25px;
                    color: white;
                    font-size: 20px;
                }
            """)
            image_label.setText("🏁")
        
        event_layout.addWidget(image_label)
        
        # Event details - no borders around text
        details_layout = QVBoxLayout()
        details_layout.setSpacing(4)  # Tighter spacing
        details_layout.setContentsMargins(0, 0, 0, 0)  # No margins
        
        # Title
        title_label = QLabel(title)
        title_label.setFont(QFont("Arial", 13, QFont.Weight.Bold))
        title_label.setStyleSheet("color: #ffffff; background: transparent; border: none;")
        title_label.setWordWrap(True)
        title_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        details_layout.addWidget(title_label)
        
        # Subtitle
        subtitle_label = QLabel(subtitle)
        subtitle_label.setFont(QFont("Arial", 11))
        subtitle_label.setStyleSheet("color: #3498db; background: transparent; border: none;")
        subtitle_label.setWordWrap(True)
        subtitle_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        details_layout.addWidget(subtitle_label)
        
        # Description
        desc_label = QLabel(description)
        desc_label.setFont(QFont("Arial", 10))
        desc_label.setStyleSheet("color: #cccccc; background: transparent; border: none;")
        desc_label.setWordWrap(True)
        desc_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        details_layout.addWidget(desc_label)
        
        # Let the details column expand to use available horizontal space
        event_layout.addLayout(details_layout)
        event_layout.setStretch(0, 0)  # icon keeps fixed width
        event_layout.setStretch(1, 1)  # details expand
        
        # Make the whole card clickable to navigate to Community → Events
        def _on_click(_evt):
            try:
                self.open_community_events()
            except Exception:
                pass
        event_frame.mousePressEvent = _on_click

        return event_frame

    def open_community_events(self):
        """Navigate to the Community page and focus the Events sub-tab."""
        try:
            from PyQt6.QtWidgets import QApplication
            app = QApplication.instance()
            if not app:
                return
            # Locate the main window that hosts pages
            main_window = None
            for widget in app.topLevelWidgets():
                if hasattr(widget, 'switch_to_page') and hasattr(widget, 'get_page'):
                    main_window = widget
                    break
            if not main_window:
                return
            # Switch to Community page
            main_window.switch_to_page("community")
            # Focus Events tab if available
            community_page = getattr(main_window, 'get_page')("community") if hasattr(main_window, 'get_page') else None
            if community_page and hasattr(community_page, 'switch_to_sub_tab'):
                community_page.switch_to_sub_tab('events')
        except Exception:
            return
        
    def update_date(self):
        """Update the date and time display."""
        now = datetime.now()
        date_str = now.strftime("%A, %B %d, %Y")
        time_str = now.strftime("%I:%M %p")
        self.date_label.setText(f"{date_str}\n{time_str}")
        
    def load_events(self):
        """Load and display upcoming events."""
        # Clear existing events
        while self.events_container.count():
            child = self.events_container.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        # Sample events with title, subtitle, description, and image
        events = [
            {
                'title': 'Weekly Racing League',
                'subtitle': 'Every Saturday at 2 PM',
                'description': 'Join our weekly racing league featuring competitive races across various tracks and car classes.',
                'image': None  # Will use default icon
            },
            {
                'title': 'Spa-Francorchamps Open Practice',
                'subtitle': 'This Sunday',
                'description': 'Open practice session on the legendary Spa-Francorchamps circuit. Perfect for improving your lap times.',
                'image': None
            },
            {
                'title': 'TrackPro Community Challenge',
                'subtitle': 'Next Week',
                'description': 'Special community event with unique challenges and rewards for all participants.',
                'image': None
            }
        ]
        
        for event in events:
            event_card = self.create_event_card(
                event['title'],
                event['subtitle'],
                event['description'],
                event['image']
            )
            self.events_container.addWidget(event_card)
        
    def update_user_avatar(self, user_data):
        """Update the user avatar with user data."""
        if not user_data:
            return
            
        # Check if user has an avatar URL
        avatar_url = user_data.get('avatar_url')
        name = user_data.get('display_name') or user_data.get('username') or user_data.get('name', 'User')
        AvatarManager.instance().set_label_avatar(self.avatar_label, avatar_url, name, size=100)
        return
            
        # Fallback to initials if no avatar URL
        # Get user name for initials
        name = user_data.get('display_name') or user_data.get('username') or user_data.get('name', 'U')
        
        # For current user, try to use first and last name if available
        first_name = user_data.get('first_name', '')
        last_name = user_data.get('last_name', '')
        if first_name or last_name:
            name = f"{first_name} {last_name}".strip()
        
        # Generate initials from the name
        initials = self._generate_initials(name)
        
        # Create avatar with initials
        self.create_avatar_with_initials(initials, name)
    
    def load_avatar_from_url(self, url: str):
        """Deprecated: use AvatarManager via update_user_avatar instead."""
        name = "User"
        AvatarManager.instance().set_label_avatar(self.avatar_label, url, name, size=100)
            
    def _generate_initials(self, name):
        """Generate initials from a name."""
        if not name:
            return "U"
        
        parts = name.strip().split()
        if len(parts) >= 2:
            return f"{parts[0][0]}{parts[-1][0]}".upper()
        elif len(parts) == 1:
            return parts[0][:2].upper()
        else:
            return "U"
            
    def create_avatar_with_initials(self, initials, name):
        """Create a circular avatar with user initials."""
        size = 100  # Updated to match the new avatar size
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw circle background using TrackPro colors
        colors = ['#3498db', '#e74c3c', '#f39c12', '#27ae60', '#9b59b6', '#1abc9c']
        color_index = hash(name) % len(colors)
        painter.setBrush(QBrush(QColor(colors[color_index])))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(0, 0, size, size)
        
        # Draw initials
        painter.setPen(QColor('#ffffff'))
        font = painter.font()
        font.setPixelSize(size // 3)  # Adjusted for new size
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, initials)
        
        painter.end()
        
        self.avatar_label.setPixmap(pixmap)
        
    def initialize_avatar(self):
        """Initialize the avatar with current user or default."""
        try:
            # Try to get complete user profile first (includes avatar_url)
            try:
                from ....social import enhanced_user_manager
                complete_profile = enhanced_user_manager.get_complete_user_profile()
                if complete_profile:
                    # Update welcome message
                    name = complete_profile.get('display_name') or complete_profile.get('username') or complete_profile.get('name', 'User')
                    self.welcome_label.setText(f"Welcome back, {name}!")
                    
                    # Update avatar with complete user data (includes avatar_url)
                    self.update_user_avatar(complete_profile)
                    
                    logger.info(f"✅ Avatar initialized with complete profile: {name}")
                    return
            except Exception as profile_error:
                logger.debug(f"Could not get complete user profile: {profile_error}")
            
            # Fallback to basic user manager
            from ....auth.user_manager import get_current_user
            current_user = get_current_user()
            
            if current_user and current_user.is_authenticated:
                # Update welcome message
                self.welcome_label.setText(f"Welcome back, {current_user.name}!")
                
                # Update avatar with user data
                user_data = {
                    'name': current_user.name,
                    'email': current_user.email,
                    'user_id': current_user.id
                }
                self.update_user_avatar(user_data)
                
                logger.info(f"✅ Avatar initialized with user: {current_user.name}")
            else:
                # Use default avatar with "TP" for TrackPro
                self.create_avatar_with_initials("TP", "TrackPro")
                logger.info("ℹ️ Avatar initialized with default TrackPro initials")
                
        except Exception as e:
            logger.error(f"Error initializing avatar: {e}")
            # Fallback to default
            self.create_avatar_with_initials("TP", "TrackPro")
            
    def show_signup_dialog(self):
        """Show the signup dialog."""
        try:
            from trackpro.auth.signup_dialog import SignupDialog
            
            # Get oauth_handler from global managers if available
            oauth_handler = None
            if self.global_managers and hasattr(self.global_managers, 'auth'):
                oauth_handler = self.global_managers.auth
            
            signup_dialog = SignupDialog(self, oauth_handler=oauth_handler)
            result = signup_dialog.exec()
            
            if result == 1:  # Dialog was accepted (user signed up)
                logger.info("🔐 User successfully signed up")
                # Update authentication state
                self.on_auth_state_changed()
                return True
            else:
                return False
                
        except Exception as e:
            logger.error(f"Error showing signup dialog: {e}")
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(
                self, 
                "Authentication Error", 
                f"Could not open signup dialog: {str(e)}"
            )
            return False
    
    def show_login_dialog(self):
        """Show the login dialog."""
        try:
            from trackpro.auth.login_dialog import LoginDialog
            
            # Get oauth_handler from global managers if available
            oauth_handler = None
            if self.global_managers and hasattr(self.global_managers, 'auth'):
                oauth_handler = self.global_managers.auth
            
            login_dialog = LoginDialog(self, oauth_handler=oauth_handler)
            result = login_dialog.exec()
            
            if result == 1:  # Dialog was accepted (user logged in)
                logger.info("🔐 User successfully logged in")
                # Update authentication state
                self.on_auth_state_changed()
                return True
            else:
                return False
                
        except Exception as e:
            logger.error(f"Error showing login dialog: {e}")
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(
                self, 
                "Authentication Error", 
                f"Could not open login dialog: {str(e)}"
            )
            return False

    def on_auth_state_changed(self):
        """Handle authentication state changes."""
        try:
            logger.info("🔄 Home page auth state changed - starting...")
            
            # Check if user is authenticated
            from trackpro.auth.user_manager import get_current_user
            current_user = get_current_user()
            
            if current_user and current_user.is_authenticated:
                logger.info(f"✅ User authenticated: {current_user.email}")
                self.refresh_header()
                logger.info("✅ Home page header refreshed after auth state change")
            else:
                logger.info("ℹ️ User not authenticated")
                self.refresh_header()
                logger.info("✅ Home page header refreshed (not authenticated)")
                
        except Exception as e:
            logger.error(f"❌ Error in home page auth state change: {e}")

    def refresh_header(self):
        """Refresh the header with current user information."""
        try:
            logger.info("🔄 Home page refresh_header started...")
            
            # Get current user
            from trackpro.auth.user_manager import get_current_user
            current_user = get_current_user()
            
            if current_user and current_user.is_authenticated:
                logger.info(f"✅ User authenticated: {current_user.email}")
                
                # Update welcome message
                if hasattr(self, 'welcome_label'):
                    try:
                        self.welcome_label.setText(f"Welcome back, {current_user.name or current_user.email}!")
                        logger.info("✅ Welcome label updated")
                    except Exception as welcome_error:
                        logger.error(f"❌ Error updating welcome label: {welcome_error}")
                
                # Hide auth buttons container for authenticated users
                if hasattr(self, 'auth_buttons_container'):
                    try:
                        self.auth_buttons_container.setVisible(False)
                        logger.info("✅ Auth buttons container hidden")
                    except Exception as auth_error:
                        logger.error(f"❌ Error hiding auth buttons container: {auth_error}")

                # NEW: ensure avatar is updated after authentication using the full profile
                try:
                    from ....social.user_manager import EnhancedUserManager
                    profile = EnhancedUserManager().get_complete_user_profile(current_user.id)
                    if profile:
                        self.update_user_avatar(profile)
                        logger.info("✅ Avatar updated from complete profile")
                    else:
                        # Fallback to minimal structure if profile unavailable
                        self.update_user_avatar({
                            'avatar_url': None,
                            'display_name': current_user.name or current_user.email,
                            'username': None,
                        })
                except Exception as avatar_err:
                    logger.debug(f"Avatar refresh skipped: {avatar_err}")
                
                logger.info("✅ Authenticated with complete profile: {current_user.name or current_user.email}")
            else:
                logger.info("ℹ️ User not authenticated")
                
                # Update welcome message for non-authenticated users
                if hasattr(self, 'welcome_label'):
                    try:
                        self.welcome_label.setText("Welcome to TrackPro! Please log in to get started.")
                        logger.info("✅ Welcome label updated for non-authenticated user")
                    except Exception as welcome_error:
                        logger.error(f"❌ Error updating welcome label: {welcome_error}")
                
                # Reset avatar to default when logged out
                try:
                    self.create_avatar_with_initials("TP", "TrackPro")
                except Exception:
                    try:
                        # Fallback: clear the label if drawing fails
                        if hasattr(self, 'avatar_label'):
                            self.avatar_label.clear()
                    except Exception:
                        pass
                
                # Show auth buttons container for non-authenticated users
                if hasattr(self, 'auth_buttons_container'):
                    try:
                        self.auth_buttons_container.setVisible(True)
                        logger.info("✅ Auth buttons container shown")
                    except Exception as auth_error:
                        logger.error(f"❌ Error showing auth buttons container: {auth_error}")
                
                logger.info("ℹ️ Not authenticated")
            
            logger.info("✅ Home page refresh_header completed successfully")
            
        except Exception as e:
            logger.error(f"❌ Error in home page refresh_header: {e}")
            
    def on_external_auth_change(self):
        """Handle external authentication state changes."""
        # Reset completion flag to allow re-checking
        self._auth_check_completed = False
        self._cached_auth_state = None
        self.on_auth_state_changed()
    
    def on_page_activated(self):
        """Called when the home page is activated."""
        # Reset completion flag to allow re-checking when page is activated
        self._auth_check_completed = False
        self._cached_auth_state = None
        # Check authentication state when page is activated
        self.on_auth_state_changed()