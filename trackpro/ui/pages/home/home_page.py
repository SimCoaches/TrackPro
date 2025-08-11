"""Homepage with user welcome, date, and announcements."""

import logging
from datetime import datetime
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QScrollArea, QFrame, QGridLayout, QPushButton, QSizePolicy, QGraphicsDropShadowEffect, QGraphicsOpacityEffect)
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve
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
        # Root background styling
        try:
            self.setObjectName("home")
            self.setStyleSheet(
                """
                QWidget#home {
                    background: qlineargradient(y1:0, y2:1, stop:0 #141414, stop:1 #1a1a1a);
                }
                """
            )
        except Exception:
            pass
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)
        
        # Main content area with two columns (wrapped in widget for animation)
        main_content = QHBoxLayout()
        main_content.setSpacing(30)
        
        # Left column - User welcome section
        left_column = self.create_welcome_section()
        main_content.addWidget(left_column)
        
        # Right column - Dashboard + Events
        right_column = self.create_right_column()
        main_content.addWidget(right_column)
        
        self.main_content_widget = QWidget()
        self.main_content_widget.setLayout(main_content)
        # Disable fade-in effect to avoid QPainter re-entrancy with nested effects
        self._entry_opacity_effect = None
        layout.addWidget(self.main_content_widget)
        
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
        try:
            self.status_timer.setTimerType(QTimer.TimerType.CoarseTimer)
        except Exception:
            pass
        self.status_timer.timeout.connect(self.update_readiness)
        self.status_timer.start(2500)

        # No fade-in; content is visible immediately

    def on_page_activated(self):
        try:
            super().on_page_activated()
        except Exception:
            pass
        self.start_entry_animation()

    def start_entry_animation(self):
        # Animation disabled to eliminate QPainter warnings
        return
        
    def create_welcome_section(self):
        """Create the left column welcome section."""
        welcome_frame = QFrame()
        welcome_frame.setFrameStyle(QFrame.Shape.StyledPanel)
        welcome_frame.setStyleSheet("""
            QFrame {
                background-color: #2a2a2a;
                border-radius: 15px;
                border: none;
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
        self.welcome_label.setFont(QFont("Product Sans", 22, QFont.Weight.Bold))
        self.welcome_label.setStyleSheet("color: #ffffff; margin: 10px;")
        self.welcome_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.welcome_label.setWordWrap(True)
        welcome_layout.addWidget(self.welcome_label)
        
        # Date and time
        self.date_label = QLabel()
        self.date_label.setFont(QFont("Product Sans", 13))
        self.date_label.setStyleSheet("color: #cccccc; margin: 5px;")
        self.date_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        welcome_layout.addWidget(self.date_label)

        # Primary actions
        cta_row = QHBoxLayout()
        cta_row.setSpacing(10)
        primary_btn = QPushButton("Start Coaching")
        primary_btn.setFixedHeight(40)
        primary_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #27ae60;
                color: white;
                border: none;
                padding: 8px 14px;
                border-radius: 8px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover { background-color: #229954; }
            QPushButton:pressed { background-color: #1e8449; }
            """
        )
        primary_btn.clicked.connect(lambda: self.navigate_to_page("race_coach"))
        secondary_btn = QPushButton("Calibrate Pedals")
        secondary_btn.setFixedHeight(40)
        secondary_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #2a82da;
                color: white;
                border: none;
                padding: 8px 14px;
                border-radius: 8px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover { background-color: #2373c0; }
            QPushButton:pressed { background-color: #1e66ac; }
            """
        )
        secondary_btn.clicked.connect(lambda: self.navigate_to_page("pedals"))
        cta_row.addWidget(primary_btn)
        cta_row.addWidget(secondary_btn)
        welcome_layout.addLayout(cta_row)

        # Quick-start checklist
        self.quickstart_container = QWidget()
        self.quickstart_container.setStyleSheet("background: transparent;")
        qs_layout = QVBoxLayout(self.quickstart_container)
        qs_layout.setContentsMargins(0, 10, 0, 0)
        qs_layout.setSpacing(8)
        self.qs_items = {
            'auth': QLabel("1. Sign in"),
            'calibrate': QLabel("2. Calibrate pedals"),
            'voice': QLabel("3. Try voice chat"),
            'community': QLabel("4. Explore community"),
        }
        for key, lbl in self.qs_items.items():
            row = QHBoxLayout()
            lbl.setStyleSheet("color: #dddddd; background: transparent;")
            chip = self.create_status_chip("—", "unknown")
            setattr(self, f"qs_chip_{key}", chip)
            row.addWidget(lbl)
            row.addStretch()
            row.addWidget(chip)
            qs_layout.addLayout(row)
        welcome_layout.addWidget(self.quickstart_container)
        
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
                background-color: transparent;
                border: none;
            }
        """)
        grid = QGridLayout(frame)
        grid.setContentsMargins(20, 20, 20, 20)
        grid.setHorizontalSpacing(16)
        grid.setVerticalSpacing(16)

        # Create cards (consolidated to avoid duplication)
        # - Quick actions live in the hero (welcome) section only
        # - Readiness and UI perf merged into a compact status strip card
        status_strip = self.create_status_strip_card()
        ai_coach = self.create_ai_coach_card()
        race_pass = self.create_race_pass_card()
        community = self.create_community_card()

        # Store for reflow
        self._dashboard_frame = frame
        self._dashboard_grid = grid
        # Four cards: status strip, AI coach, community, race pass
        self._dashboard_cards = [status_strip, ai_coach, community, race_pass]
        self._dashboard_columns = self._compute_dashboard_columns()
        self._layout_dashboard_cards()

        return frame

    def _compute_dashboard_columns(self) -> int:
        try:
            container_width = 0
            if hasattr(self, '_dashboard_frame') and self._dashboard_frame is not None:
                container_width = max(container_width, int(self._dashboard_frame.width()))
            container_width = max(container_width, int(self.width()))
            # Simple breakpoints tuned for our card min widths
            if container_width >= 1500:
                return 3
            if container_width <= 980:
                return 1
            return 2
        except Exception:
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
                background-color: rgba(42,42,42,0.92);
                border-radius: 12px;
                border: none;
            }
            QFrame:hover {
                background-color: rgba(52,52,52,0.96);
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
                font-weight: bold;
            }
        """)
        # Subtle elevation
        try:
            shadow = QGraphicsDropShadowEffect()
            shadow.setBlurRadius(24)
            shadow.setXOffset(0)
            shadow.setYOffset(12)
            shadow.setColor(QColor(0, 0, 0, 120))
            card.setGraphicsEffect(shadow)
        except Exception:
            pass
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        title_label = QLabel(title)
        title_label.setProperty("role", "title")
        # Remove any frames/outline around headers; rely on typography
        title_label.setStyleSheet("background: transparent; border: none;")
        layout.addWidget(title_label)

        return card

    def create_quick_actions_card(self) -> QFrame:
        card = self.create_card("Quick Actions")

        def make_btn(text: str, color: str):
            def darken(hex_color: str, factor: float = 0.85) -> str:
                try:
                    hex_color = hex_color.lstrip('#')
                    r = int(hex_color[0:2], 16)
                    g = int(hex_color[2:4], 16)
                    b = int(hex_color[4:6], 16)
                    r = max(0, min(255, int(r * factor)))
                    g = max(0, min(255, int(g * factor)))
                    b = max(0, min(255, int(b * factor)))
                    return f"#{r:02x}{g:02x}{b:02x}"
                except Exception:
                    return color
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
                QPushButton:hover {{
                    background-color: {darken(color, 0.90)};
                }}
                QPushButton:pressed {{
                    background-color: {darken(color, 0.80)};
                }}
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
        try:
            calibrate_btn.setShortcut("Ctrl+Shift+C")
            coach_btn.setShortcut("Ctrl+Shift+K")
            voice_btn.setShortcut("Ctrl+Shift+V")
            race_pass_btn.setShortcut("Ctrl+Shift+R")
        except Exception:
            pass

        grid = QGridLayout()
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(8)
        grid.addWidget(calibrate_btn, 0, 0)
        grid.addWidget(coach_btn, 0, 1)
        grid.addWidget(voice_btn, 1, 0)
        grid.addWidget(race_pass_btn, 1, 1)
        card.layout().addLayout(grid)
        return card

    def create_status_strip_card(self) -> QFrame:
        """Compact system status strip with colored chips.

        Replaces the previous separate readiness card and removes duplication
        with performance by surfacing UI timing as a chip alongside others.
        """
        card = self.create_card("System Status")
        # Make the card visually slimmer
        try:
            card.layout().setContentsMargins(16, 12, 16, 12)
        except Exception:
            pass

        row = QHBoxLayout()
        row.setSpacing(8)

        # Chips created as attributes so update_readiness can drive them
        self.pedals_chip = self.create_status_chip("Pedals", "unknown")
        self.voice_chip = self.create_status_chip("Voice", "unknown")
        self.auth_chip = self.create_status_chip("Auth", "unknown")
        self.perf_chip = self.create_status_chip("UI", "unknown")

        for chip in (self.pedals_chip, self.voice_chip, self.auth_chip, self.perf_chip):
            row.addWidget(chip)

        row.addStretch()
        card.layout().addLayout(row)
        return card

    def create_status_chip(self, text: str, status: str = "unknown") -> QLabel:
        color_map = {
            "ok": ("rgba(46, 204, 113, 0.18)", "#2ecc71"),
            "warn": ("rgba(241, 196, 15, 0.18)", "#f1c40f"),
            "error": ("rgba(231, 76, 60, 0.18)", "#e74c3c"),
            "unknown": ("rgba(127, 140, 141, 0.18)", "#7f8c8d"),
        }
        bg, fg = color_map.get(status, color_map["unknown"])
        chip = QLabel(text)
        chip.setProperty("role", "chip")
        chip.setStyleSheet(f"""
            QLabel[role="chip"] {{
                background-color: {bg};
                color: {fg};
                border-radius: 12px;
                padding: 4px 10px;
                font-weight: bold;
                font-size: 11px;
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
        """Deprecated: last session snapshot removed from dashboard.

        Kept as a no-op to preserve any indirect calls; returns a small
        transparent container but is no longer added to the dashboard.
        """
        card = QFrame()
        card.setStyleSheet("QFrame { background: transparent; border: none; }")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(0, 0, 0, 0)
        # Maintain perf_label for status chip updates
        self.perf_label = QLabel("Avg UI: — ms | Dropped: —")
        self.perf_label.setVisible(False)
        layout.addWidget(self.perf_label)
        self._last_avg_ui_ms = None
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
            QPushButton:hover {
                background-color: #8d7800;
            }
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
            QPushButton:hover {
                background-color: #2f8fe6;
            }
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
                    try:
                        if hasattr(self, 'qs_chip_auth'):
                            self.set_chip(self.qs_chip_auth, "Done", "ok")
                    except Exception:
                        pass
                else:
                    self.set_chip(self.auth_chip, "Auth: Sign-in", "warn")
                    try:
                        if hasattr(self, 'qs_chip_auth'):
                            self.set_chip(self.qs_chip_auth, "Sign in", "warn")
                        # Show auth buttons when not signed in
                        if hasattr(self, 'auth_buttons_container'):
                            self.auth_buttons_container.setVisible(True)
                    except Exception:
                        pass
            except Exception:
                self.set_chip(self.auth_chip, "Auth: Unknown", "unknown")
                try:
                    if hasattr(self, 'qs_chip_auth'):
                        self.set_chip(self.qs_chip_auth, "—", "unknown")
                except Exception:
                    pass

            # Voice server
            try:
                from trackpro.voice_server_manager import is_voice_server_running
                is_running = is_voice_server_running()
                self.set_chip(self.voice_chip, "Voice: On" if is_running else "Voice: Off", "ok" if is_running else "error")
                try:
                    if hasattr(self, 'qs_chip_voice'):
                        self.set_chip(self.qs_chip_voice, "On" if is_running else "Off", "ok" if is_running else "warn")
                except Exception:
                    pass
            except Exception:
                self.set_chip(self.voice_chip, "Voice: Unknown", "unknown")
                try:
                    if hasattr(self, 'qs_chip_voice'):
                        self.set_chip(self.qs_chip_voice, "—", "unknown")
                except Exception:
                    pass

            # Pedals (actual connection status when available)
            try:
                hw = getattr(self.global_managers, 'hardware', None)
                if hw is None:
                    self.set_chip(self.pedals_chip, "Pedals: —", "warn")
                    try:
                        if hasattr(self, 'qs_chip_calibrate'):
                            self.set_chip(self.qs_chip_calibrate, "Calibrate", "warn")
                    except Exception:
                        pass
                else:
                    if getattr(hw, 'pedals_connected', False):
                        self.set_chip(self.pedals_chip, "Pedals: OK", "ok")
                        try:
                            if hasattr(self, 'qs_chip_calibrate'):
                                self.set_chip(self.qs_chip_calibrate, "Done", "ok")
                        except Exception:
                            pass
                    else:
                        self.set_chip(self.pedals_chip, "Pedals: Off", "error")
                        try:
                            if hasattr(self, 'qs_chip_calibrate'):
                                self.set_chip(self.qs_chip_calibrate, "Calibrate", "warn")
                        except Exception:
                            pass
            except Exception:
                self.set_chip(self.pedals_chip, "Pedals: Unknown", "unknown")
                try:
                    if hasattr(self, 'qs_chip_calibrate'):
                        self.set_chip(self.qs_chip_calibrate, "—", "unknown")
                except Exception:
                    pass

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
                        arrow = ""
                        if self._last_avg_ui_ms is not None:
                            if avg_ms > self._last_avg_ui_ms + 0.2:
                                arrow = " ▲"
                            elif avg_ms < self._last_avg_ui_ms - 0.2:
                                arrow = " ▼"
                        self.perf_label.setText(f"Avg UI: {avg_ms:.1f} ms{arrow} | Dropped: {dropped}")
                        self._last_avg_ui_ms = avg_ms
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
                try:
                    if hasattr(self, 'qs_chip_community'):
                        if len(friends) > 0 or unread > 0:
                            self.set_chip(self.qs_chip_community, "Ready", "ok")
                        else:
                            self.set_chip(self.qs_chip_community, "Explore", "warn")
                except Exception:
                    pass
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
                background-color: rgba(42,42,42,0.92);
                border-radius: 12px;
                border: none;
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
                background-color: rgba(51,51,51,0.95);
                border-radius: 10px;
                border: none;
            }
            QFrame:hover {
                background-color: rgba(58,58,58,0.98);
            }
        """)
        try:
            shadow = QGraphicsDropShadowEffect()
            shadow.setBlurRadius(20)
            shadow.setXOffset(0)
            shadow.setYOffset(10)
            shadow.setColor(QColor(0, 0, 0, 100))
            event_frame.setGraphicsEffect(shadow)
        except Exception:
            pass
        
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