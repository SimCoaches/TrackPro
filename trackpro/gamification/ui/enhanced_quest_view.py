from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QTabWidget, QScrollArea, QFrame,
    QProgressBar, QGraphicsOpacityEffect, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QPropertyAnimation, QEasingCurve, QRect, QParallelAnimationGroup
from PyQt6.QtGui import QFont, QPixmap, QPainter, QColor, QLinearGradient, QPen
import logging

# Import the quest card widget and Supabase functions
from .quest_card_widget import QuestCardWidget
from .notifications import LevelUpNotification, XPGainNotification
from trackpro.gamification.supabase_gamification import (
    get_user_quests, claim_quest_reward, assign_daily_quests, 
    assign_weekly_quests, get_user_profile
)

# Set up logging
logger = logging.getLogger(__name__)

class QuestHeaderWidget(QWidget):
    """Enhanced header widget showing user level, XP, and quest progress"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(120)
        self.setStyleSheet("""
            QuestHeaderWidget {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #2C3E50, stop:0.5 #34495E, stop:1 #2C3E50);
                border-radius: 10px;
                border: 2px solid #3498DB;
            }
        """)
        
        self._init_ui()
        
    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 15, 20, 15)
        layout.setSpacing(30)
        
        # Left section - User Level and XP
        left_section = self._create_level_section()
        layout.addWidget(left_section)
        
        # Center section - Quest Progress Summary
        center_section = self._create_progress_section()
        layout.addWidget(center_section, 1)
        
        # Right section - Actions
        right_section = self._create_actions_section()
        layout.addWidget(right_section)
        
    def _create_level_section(self):
        frame = QFrame()
        frame.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(frame)
        layout.setSpacing(5)
        
        # Level display
        self.level_label = QLabel("Level 1")
        self.level_label.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        self.level_label.setStyleSheet("color: #F39C12; font-weight: bold;")
        layout.addWidget(self.level_label)
        
        # XP Progress bar
        self.xp_progress = QProgressBar()
        self.xp_progress.setFixedHeight(20)
        self.xp_progress.setStyleSheet("""
            QProgressBar {
                border: 2px solid #34495E;
                border-radius: 10px;
                background-color: #2C3E50;
                text-align: center;
                color: white;
                font-weight: bold;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #3498DB, stop:1 #2980B9);
                border-radius: 8px;
            }
        """)
        layout.addWidget(self.xp_progress)
        
        # XP text
        self.xp_label = QLabel("0 / 100 XP")
        self.xp_label.setFont(QFont("Arial", 10))
        self.xp_label.setStyleSheet("color: #BDC3C7;")
        self.xp_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.xp_label)
        
        return frame
        
    def _create_progress_section(self):
        frame = QFrame()
        frame.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(frame)
        layout.setSpacing(8)
        
        # Title
        title = QLabel("Quest Progress")
        title.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        title.setStyleSheet("color: #ECF0F1;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # Progress stats
        stats_layout = QHBoxLayout()
        
        # Daily quests
        daily_frame = self._create_stat_frame("Daily", "0/3", "#E74C3C")
        stats_layout.addWidget(daily_frame)
        
        # Weekly quests  
        weekly_frame = self._create_stat_frame("Weekly", "0/3", "#F39C12")
        stats_layout.addWidget(weekly_frame)
        
        # Achievements
        achievement_frame = self._create_stat_frame("Achievements", "0/10", "#9B59B6")
        stats_layout.addWidget(achievement_frame)
        
        layout.addLayout(stats_layout)
        
        return frame
        
    def _create_stat_frame(self, title, value, color):
        frame = QFrame()
        frame.setStyleSheet(f"""
            QFrame {{
                background-color: rgba(255, 255, 255, 0.1);
                border-radius: 8px;
                border: 1px solid {color};
            }}
        """)
        frame.setFixedSize(80, 50)
        
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(2)
        
        title_label = QLabel(title)
        title_label.setFont(QFont("Arial", 8, QFont.Weight.Bold))
        title_label.setStyleSheet(f"color: {color};")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)
        
        value_label = QLabel(value)
        value_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        value_label.setStyleSheet("color: white;")
        value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(value_label)
        
        # Store references for updates
        if title == "Daily":
            self.daily_progress_label = value_label
        elif title == "Weekly":
            self.weekly_progress_label = value_label
        elif title == "Achievements":
            self.achievement_progress_label = value_label
            
        return frame
        
    def _create_actions_section(self):
        frame = QFrame()
        frame.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(frame)
        layout.setSpacing(8)
        
        # Claim All button
        self.claim_all_button = QPushButton("Claim All Rewards")
        self.claim_all_button.setFixedHeight(35)
        self.claim_all_button.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #27AE60, stop:1 #229954);
                color: white;
                font-weight: bold;
                font-size: 11pt;
                border-radius: 8px;
                border: 2px solid #2ECC71;
                padding: 5px 15px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #2ECC71, stop:1 #27AE60);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #229954, stop:1 #1E8449);
            }
            QPushButton:disabled {
                background: #7F8C8D;
                border-color: #95A5A6;
                color: #BDC3C7;
            }
        """)
        layout.addWidget(self.claim_all_button)
        
        # Refresh button
        self.refresh_button = QPushButton("Refresh Quests")
        self.refresh_button.setFixedHeight(30)
        self.refresh_button.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #3498DB, stop:1 #2980B9);
                color: white;
                font-weight: bold;
                font-size: 10pt;
                border-radius: 6px;
                border: 1px solid #5DADE2;
                padding: 3px 10px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #5DADE2, stop:1 #3498DB);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #2980B9, stop:1 #1F618D);
            }
        """)
        layout.addWidget(self.refresh_button)
        
        return frame
        
    def update_user_data(self, user_profile):
        """Update header with user profile data"""
        if not user_profile:
            return
            
        level = user_profile.get('level', 1)
        current_xp = user_profile.get('current_xp', 0)
        
        # Calculate XP for current level and next level
        current_level_xp = (level - 1) ** 2 * 100
        next_level_xp = level ** 2 * 100
        xp_in_level = current_xp - current_level_xp
        xp_needed = next_level_xp - current_level_xp
        
        # Update UI
        self.level_label.setText(f"Level {level}")
        self.xp_progress.setMaximum(xp_needed)
        self.xp_progress.setValue(xp_in_level)
        self.xp_label.setText(f"{xp_in_level} / {xp_needed} XP")
        
    def update_quest_progress(self, daily_complete, daily_total, weekly_complete, weekly_total, achievement_complete, achievement_total):
        """Update quest progress counters"""
        self.daily_progress_label.setText(f"{daily_complete}/{daily_total}")
        self.weekly_progress_label.setText(f"{weekly_complete}/{weekly_total}")
        self.achievement_progress_label.setText(f"{achievement_complete}/{achievement_total}")


class EnhancedQuestViewWidget(QWidget):
    """Enhanced quest view with improved UI, animations, and full functionality"""
    
    # Signal emitted when a quest is claimed (quest_title, xp_reward, level_up_info)
    quest_claimed = pyqtSignal(str, int, dict)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("EnhancedQuestViewWidget")
        
        # Animation and notification system
        self.pending_notifications = []
        self.notification_timer = QTimer()
        self.notification_timer.timeout.connect(self._process_next_notification)
        
        self._init_ui()
        self._load_initial_data()
        
    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(15)
        
        # Main title
        title_label = QLabel("Quest System")
        title_font = QFont("Arial", 24, QFont.Weight.Bold)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("""
            color: #2C3E50;
                            font-weight: bold;
            margin-bottom: 10px;
        """)
        main_layout.addWidget(title_label)
        
        # Header widget
        self.header_widget = QuestHeaderWidget()
        main_layout.addWidget(self.header_widget)
        
        # Connect header buttons
        self.header_widget.claim_all_button.clicked.connect(self._handle_claim_all)
        self.header_widget.refresh_button.clicked.connect(self.load_quests_from_supabase)
        
        # Tab widget for quest categories
        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: 2px solid #34495E;
                background-color: #ECF0F1;
                border-radius: 8px;
                margin-top: 10px;
            }
            QTabBar::tab {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #BDC3C7, stop:1 #95A5A6);
                color: #2C3E50;
                padding: 12px 20px;
                margin-right: 2px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                font-weight: bold;
                font-size: 11pt;
            }
            QTabBar::tab:selected {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #3498DB, stop:1 #2980B9);
                color: white;
            }
            QTabBar::tab:hover:!selected {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #D5DBDB, stop:1 #AEB6BF);
            }
        """)
        
        # Create quest tabs
        self.daily_scroll, self.daily_layout = self._create_quest_tab()
        self.weekly_scroll, self.weekly_layout = self._create_quest_tab()
        self.achievement_scroll, self.achievement_layout = self._create_quest_tab()
        
        self.tab_widget.addTab(self.daily_scroll, "🌅 Daily Quests")
        self.tab_widget.addTab(self.weekly_scroll, "📅 Weekly Quests")
        self.tab_widget.addTab(self.achievement_scroll, "🏆 Achievements")
        
        main_layout.addWidget(self.tab_widget)
        
    def _create_quest_tab(self):
        """Create a scroll area with layout for quest cards"""
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("""
            QScrollArea {
                background-color: transparent;
                border: none;
            }
            QScrollBar:vertical {
                background-color: #BDC3C7;
                width: 12px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background-color: #7F8C8D;
                border-radius: 6px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #5D6D7E;
            }
        """)
        
        content_widget = QWidget()
        content_widget.setStyleSheet("background-color: transparent;")
        content_layout = QVBoxLayout(content_widget)
        content_layout.setSpacing(12)
        content_layout.setContentsMargins(15, 15, 15, 15)
        
        scroll_area.setWidget(content_widget)
        return scroll_area, content_layout
        
    def _load_initial_data(self):
        """Load initial user profile and quest data"""
        # Load user profile
        profile, message = get_user_profile()
        if profile:
            self.header_widget.update_user_data(profile)
        
        # Load quests
        self.load_quests_from_supabase()
        
    def load_quests_from_supabase(self):
        """Load quests from Supabase and update UI"""
        logger.info("Loading quests from Supabase")
        
        # Get quests from Supabase
        quests_data, message = get_user_quests()
        
        if quests_data is None:
            logger.error(f"Failed to load quests: {message}")
            # Show fallback test data
            self._load_test_quests()
            return
            
        logger.info(f"Successfully loaded {len(quests_data)} quests")
        
        # Group quests by type
        daily_quests = []
        weekly_quests = []
        achievement_quests = []
        
        for quest in quests_data:
            quest_card_data = self._format_quest_for_card(quest)
            
            quest_type = quest.get("quest_type")
            if quest_type == "daily":
                daily_quests.append(quest_card_data)
            elif quest_type == "weekly":
                weekly_quests.append(quest_card_data)
            elif quest_type in ["achievement", "event"]:
                achievement_quests.append(quest_card_data)
                
        # Update quest tabs
        self._update_quest_tab(self.daily_layout, daily_quests)
        self._update_quest_tab(self.weekly_layout, weekly_quests)
        self._update_quest_tab(self.achievement_layout, achievement_quests)
        
        # Update header progress
        self._update_header_progress(daily_quests, weekly_quests, achievement_quests)
        
        # Update claim all button state
        self._update_claim_all_button()
        
    def _format_quest_for_card(self, quest):
        """Format quest data for QuestCardWidget"""
        # Calculate progress
        progress = quest.get("progress", {})
        criteria = quest.get("completion_criteria", {})
        is_complete = quest.get("is_complete", False)
        
        if is_complete:
            progress_current = criteria.get("target_value", 1)
            progress_target = criteria.get("target_value", 1)
            progress_text = "Completed!"
        else:
            progress_current = progress.get("current_value", 0)
            progress_target = criteria.get("target_value", 1)
            progress_text = None
            
            # Handle special quest types
            if "action" in criteria:
                action = criteria.get("action")
                if action == "earn_pb":
                    track = criteria.get("track_name", "any track")
                    progress_text = f"Set PB @ {track}"
                    progress_current = 0
                    progress_target = 1
                elif action == "complete_race":
                    count = criteria.get("count", 1)
                    current = progress.get("races_completed", 0)
                    progress_text = f"{current}/{count} races"
                    progress_current = current
                    progress_target = count
                    
        # Format rewards
        rewards_list = []
        if quest.get("xp_reward", 0) > 0:
            rewards_list.append({
                "type": "xp",
                "text": f"+{quest['xp_reward']} XP"
            })
        if quest.get("race_pass_xp_reward", 0) > 0:
            rewards_list.append({
                "type": "rp_xp", 
                "text": f"+{quest['race_pass_xp_reward']} RP XP"
            })
            
        return {
            "id": quest.get("user_quest_id"),
            "title": quest.get("name", "Unknown Quest"),
            "description": quest.get("description"),
            "progress_current": progress_current,
            "progress_target": progress_target,
            "progress_text_override": progress_text,
            "rewards_list": rewards_list,
            "is_complete": is_complete,
            "is_claimed": quest.get("is_claimed", False),
            "type": quest.get("quest_type")
        }
        
    def _update_quest_tab(self, layout, quest_list):
        """Update a quest tab with new quest cards"""
        # Clear existing widgets
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
                
        if not quest_list:
            # Show empty state
            empty_label = QLabel("No quests available")
            empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_label.setStyleSheet("""
                color: #7F8C8D;
                font-size: 14pt;
                font-style: italic;
                padding: 40px;
            """)
            layout.addWidget(empty_label)
            layout.addStretch()
            return
            
        # Add quest cards
        for quest_data in quest_list:
            card = QuestCardWidget(quest_data)
            card.claim_button_clicked.connect(self._handle_quest_claim)
            layout.addWidget(card)
            
        layout.addStretch()
        
    def _update_header_progress(self, daily_quests, weekly_quests, achievement_quests):
        """Update header progress counters"""
        daily_complete = sum(1 for q in daily_quests if q["is_complete"])
        weekly_complete = sum(1 for q in weekly_quests if q["is_complete"])
        achievement_complete = sum(1 for q in achievement_quests if q["is_complete"])
        
        self.header_widget.update_quest_progress(
            daily_complete, len(daily_quests),
            weekly_complete, len(weekly_quests), 
            achievement_complete, len(achievement_quests)
        )
        
    def _update_claim_all_button(self):
        """Update claim all button state"""
        claimable_count = self._get_claimable_quest_count()
        self.header_widget.claim_all_button.setEnabled(claimable_count > 0)
        
    def _get_claimable_quest_count(self):
        """Get number of claimable quests"""
        count = 0
        for layout in [self.daily_layout, self.weekly_layout, self.achievement_layout]:
            for i in range(layout.count()):
                widget = layout.itemAt(i).widget()
                if isinstance(widget, QuestCardWidget):
                    if widget.claim_button.isEnabled() and widget.claim_button.text() == "Claim Reward":
                        count += 1
        return count
        
    def _handle_quest_claim(self, quest_id):
        """Handle individual quest claim"""
        logger.info(f"Claiming quest: {quest_id}")
        
        success, message, reward_info = claim_quest_reward(quest_id)
        
        if success:
            xp_reward = reward_info.get("xp_reward", 0)
            level_up = reward_info.get("new_level", 1) > reward_info.get("old_level", 1)
            
            # Find quest title
            quest_title = self._find_quest_title_by_id(quest_id)
            
            # Create notification data
            notification_data = {
                "quest_title": quest_title,
                "xp_reward": xp_reward,
                "level_up": level_up,
                "old_level": reward_info.get("old_level", 1),
                "new_level": reward_info.get("new_level", 1)
            }
            
            # Add to notification queue
            self.pending_notifications.append(notification_data)
            
            # Start processing notifications if not already running
            if not self.notification_timer.isActive():
                self._process_next_notification()
                
            # Refresh data
            self._refresh_after_claim()
            
        else:
            QMessageBox.warning(self, "Quest Claim Failed", f"Failed to claim quest: {message}")
            
    def _handle_claim_all(self):
        """Handle claim all button"""
        claimable_quests = self._get_claimable_quest_ids()
        
        if not claimable_quests:
            QMessageBox.information(self, "No Rewards", "No rewards available to claim.")
            return
            
        self.header_widget.claim_all_button.setEnabled(False)
        self.header_widget.claim_all_button.setText("Claiming...")
        
        total_xp = 0
        successful_claims = []
        
        for quest_id in claimable_quests:
            success, message, reward_info = claim_quest_reward(quest_id)
            if success:
                quest_title = self._find_quest_title_by_id(quest_id)
                xp_reward = reward_info.get("xp_reward", 0)
                total_xp += xp_reward
                successful_claims.append({
                    "quest_title": quest_title,
                    "xp_reward": xp_reward,
                    "level_up": reward_info.get("new_level", 1) > reward_info.get("old_level", 1),
                    "old_level": reward_info.get("old_level", 1),
                    "new_level": reward_info.get("new_level", 1)
                })
                
        # Add all successful claims to notification queue
        self.pending_notifications.extend(successful_claims)
        
        # Start processing notifications
        if not self.notification_timer.isActive() and successful_claims:
            self._process_next_notification()
            
        # Refresh UI
        self._refresh_after_claim()
        
        # Show summary
        if successful_claims:
            QMessageBox.information(
                self, 
                "Rewards Claimed", 
                f"Successfully claimed {len(successful_claims)} rewards!\nTotal XP gained: {total_xp}"
            )
        
    def _get_claimable_quest_ids(self):
        """Get list of claimable quest IDs"""
        quest_ids = []
        for layout in [self.daily_layout, self.weekly_layout, self.achievement_layout]:
            for i in range(layout.count()):
                widget = layout.itemAt(i).widget()
                if isinstance(widget, QuestCardWidget):
                    if widget.claim_button.isEnabled() and widget.claim_button.text() == "Claim Reward":
                        quest_ids.append(widget.quest_id)
        return quest_ids
        
    def _find_quest_title_by_id(self, quest_id):
        """Find quest title by ID"""
        for layout in [self.daily_layout, self.weekly_layout, self.achievement_layout]:
            for i in range(layout.count()):
                widget = layout.itemAt(i).widget()
                if isinstance(widget, QuestCardWidget):
                    if widget.quest_id == quest_id:
                        return widget.quest_title_label.text()
        return f"Quest {quest_id}"
        
    def _process_next_notification(self):
        """Process the next notification in the queue"""
        if not self.pending_notifications:
            self.notification_timer.stop()
            return
            
        notification_data = self.pending_notifications.pop(0)
        
        # Show XP gain notification
        xp_notification = XPGainNotification(
            self,
            notification_data["quest_title"],
            notification_data["xp_reward"]
        )
        xp_notification.show_notification()
        
        # If level up occurred, show level up notification after XP notification
        if notification_data["level_up"]:
            QTimer.singleShot(2000, lambda: self._show_level_up_notification(notification_data))
            
        # Schedule next notification
        if self.pending_notifications:
            self.notification_timer.start(3000)  # 3 second delay between notifications
        else:
            self.notification_timer.stop()
            
    def _show_level_up_notification(self, notification_data):
        """Show level up notification"""
        level_up_notification = LevelUpNotification(
            self,
            notification_data["old_level"],
            notification_data["new_level"]
        )
        level_up_notification.show_notification()
        
    def _refresh_after_claim(self):
        """Refresh UI after claiming rewards"""
        # Reload user profile
        profile, _ = get_user_profile()
        if profile:
            self.header_widget.update_user_data(profile)
            
        # Reload quests
        self.load_quests_from_supabase()
        
    def _load_test_quests(self):
        """Load test quest data for development"""
        test_daily = [
            {
                "id": "test_daily_1",
                "title": "Complete 10 Laps",
                "description": "Complete 10 laps on any track",
                "progress_current": 7,
                "progress_target": 10,
                "progress_text_override": None,
                "rewards_list": [{"type": "xp", "text": "+100 XP"}],
                "is_complete": False,
                "is_claimed": False,
                "type": "daily"
            },
            {
                "id": "test_daily_2", 
                "title": "Set a Clean Lap",
                "description": "Complete a lap with no incidents",
                "progress_current": 1,
                "progress_target": 1,
                "progress_text_override": "Completed!",
                "rewards_list": [{"type": "xp", "text": "+75 XP"}],
                "is_complete": True,
                "is_claimed": False,
                "type": "daily"
            }
        ]
        
        test_weekly = [
            {
                "id": "test_weekly_1",
                "title": "Complete 50 Laps",
                "description": "Complete 50 laps in any car/track combination",
                "progress_current": 23,
                "progress_target": 50,
                "progress_text_override": None,
                "rewards_list": [{"type": "xp", "text": "+500 XP"}, {"type": "rp_xp", "text": "+100 RP XP"}],
                "is_complete": False,
                "is_claimed": False,
                "type": "weekly"
            }
        ]
        
        test_achievements = [
            {
                "id": "test_achievement_1",
                "title": "Speed Demon",
                "description": "Reach 200 mph in any car",
                "progress_current": 0,
                "progress_target": 1,
                "progress_text_override": "Reach 200 mph",
                "rewards_list": [{"type": "xp", "text": "+1000 XP"}],
                "is_complete": False,
                "is_claimed": False,
                "type": "achievement"
            }
        ]
        
        self._update_quest_tab(self.daily_layout, test_daily)
        self._update_quest_tab(self.weekly_layout, test_weekly)
        self._update_quest_tab(self.achievement_layout, test_achievements)
        
        self._update_header_progress(test_daily, test_weekly, test_achievements)
        self._update_claim_all_button() 