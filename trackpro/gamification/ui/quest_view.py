from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QListWidget, QListWidgetItem, 
    QTabWidget, QGroupBox, QSpacerItem, QSizePolicy, QMessageBox, QScrollArea
)
from PyQt5.QtCore import Qt, pyqtSignal, QSize
from PyQt5.QtGui import QFont
import logging

# Import the new QuestCardWidget
from .quest_card_widget import QuestCardWidget

# Import the gamification Supabase module
from trackpro.gamification.supabase_gamification import (
    get_user_quests, claim_quest_reward, assign_daily_quests, 
    assign_weekly_quests
)

# Set up logging
logger = logging.getLogger(__name__)

class QuestViewWidget(QWidget):
    """Dedicated widget to display all quests (Daily, Weekly, Achievements)."""
    
    # Signal emitted when a quest is claimed (quest_title, xp_reward)
    quest_claimed = pyqtSignal(str, int)
    
    # SHARED STYLING - Define all styles at class level to ensure consistency
    QUEST_LIST_STYLE = """
        QListWidget { 
            background-color: #2A2A2A; 
            border: 1px solid #444; 
            border-radius: 5px; 
            color: white;
            padding-top: 5px; /* Padding for the list widget itself */
        }
        QListWidget::item { 
            padding: 8px 8px; /* Padding for each item in the list */
            border-bottom: 1px solid #383838; 
            margin: 2px 0px;
            /* min-height: 70px;  REMOVED to allow dynamic height based on content */
        }
        QListWidget::item:selected { 
            background-color: #3498db; 
            color: white; 
        }
    """
    
    TABS_STYLE = """
        QTabBar::tab {
            background-color: #333;
            color: #CCC;
            padding: 8px 15px;
            border-top-left-radius: 3px;
            border-top-right-radius: 3px;
        }
        QTabBar::tab:selected {
            background-color: #444;
            color: white;
        }
    """
    
    CLAIM_BUTTON_STYLE = """
        QPushButton {
            background-color: #27ae60; 
            color: white;
            font-weight: bold;
            font-size: 9pt;
            padding: 4px;
            border-radius: 4px;
        }
        QPushButton:hover {
            background-color: #2ecc71;
        }
        QPushButton:pressed {
            background-color: #1c7d44;
        }
        QPushButton:disabled {
            background-color: #555;
            color: #888;
        }
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("QuestViewWidget")
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(10)

        # Title
        title_label = QLabel("Quests")
        title_font = QFont("Arial", 16, QFont.Bold)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title_label)

        # --- Claim All Button ---
        self.claim_all_button = QPushButton("Claim All Rewards")
        self.claim_all_button.setFixedHeight(35)
        # Basic styling, can be enhanced
        self.claim_all_button.setStyleSheet("""
            QPushButton {
                background-color: #007bff; 
                color: white;
                font-weight: bold;
                font-size: 10pt;
                padding: 6px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #0056b3;
            }
            QPushButton:pressed {
                background-color: #004085;
            }
            QPushButton:disabled {
                background-color: #555;
                color: #888;
            }
        """)
        self.claim_all_button.setEnabled(False) # Disabled by default
        self.claim_all_button.clicked.connect(self._handle_claim_all)
        main_layout.addWidget(self.claim_all_button, 0, Qt.AlignRight) # Align to right if desired

        # Create tab widget
        self.tab_widget = QTabWidget()
        
        # Create the content areas for each tab
        self.daily_quests_scroll_area, self.daily_quests_content_widget, self.daily_quests_layout = self._create_quest_tab_content_area()
        self.weekly_quests_scroll_area, self.weekly_quests_content_widget, self.weekly_quests_layout = self._create_quest_tab_content_area()
        self.achievements_scroll_area, self.achievements_content_widget, self.achievements_layout = self._create_quest_tab_content_area()
        
        # Add tabs to the widget
        self.tab_widget.addTab(self.daily_quests_scroll_area, "Dailies")
        self.tab_widget.addTab(self.weekly_quests_scroll_area, "Weeklies")
        self.tab_widget.addTab(self.achievements_scroll_area, "Achievements")
        
        # Apply tab styling once, to the parent QTabWidget
        self.tab_widget.setStyleSheet(self.TABS_STYLE)
        
        main_layout.addWidget(self.tab_widget)

        # Load quests from Supabase
        self.load_quests_from_supabase()

        # Add refresh button
        refresh_button = QPushButton("Refresh Quests")
        refresh_button.clicked.connect(self.load_quests_from_supabase)
        main_layout.addWidget(refresh_button)

    def _create_quest_tab_content_area(self):
        """Create a scroll area with a content widget and a QVBoxLayout for a tab."""
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("QScrollArea { background-color: #2A2A2A; border: 1px solid #444; border-radius: 5px; }") # Basic styling

        content_widget = QWidget() # This widget will hold the quest cards
        content_layout = QVBoxLayout(content_widget)
        content_layout.setSpacing(10) # Gap between quest cards
        content_layout.setContentsMargins(10, 10, 10, 10) # Padding within the scroll area

        scroll_area.setWidget(content_widget)
        return scroll_area, content_widget, content_layout

    def _load_placeholder_quests(self, with_claimed_update=False):
        # Example quests - replace with actual data loading logic
        dailies = [
            {"title": "Complete 10 Laps", "progress": "5/10", "reward": "+100 XP", "complete": False},
            {"title": "Set a PB at Spa", "progress": "0/1", "reward": "+250 XP", "complete": False},
            {"title": "Drive Cleanly for 5 Mins", "progress": "Completed!", "reward": "+50 XP", 
             "complete": True, "claimed": with_claimed_update} # This one gets claimed
        ]
        weeklies = [
            {"title": "Complete 3 Races", "progress": "1/3", "reward": "+500 XP, +1 RP Star", "complete": False},
            {"title": "Drive 100km", "progress": "35/100", "reward": "+300 XP", "complete": False}
        ]
        achievements = [
            {"title": "Reach Level 10", "progress": "Level 5", "reward": "Title: Rookie", "complete": False},
            {"title": "Master 5 Tracks", "progress": "2/5", "reward": "+1000 XP", "complete": False},
             {"title": "Drive 1000 Laps", "progress": "Completed!", "reward": "Badge: Lap Legend", "complete": True, "claimed": True}
        ]

        self.update_quests('daily', dailies)
        self.update_quests('weekly', weeklies)
        self.update_quests('achievement', achievements)

    def load_quests_from_supabase(self):
        """Load quests from Supabase database"""
        logger.info("Loading quests from Supabase")
        self._last_loaded_quests_by_id = {} # Initialize/clear the cache
        
        # Try to get quests from Supabase
        raw_quests, message = get_user_quests() # Renamed to raw_quests to avoid confusion
        
        # If we couldn't get quests from Supabase
        if raw_quests is None:
            logger.error(f"Failed to load quests from Supabase: {message}")
            logger.info("Using local test quests instead")
            
            # Create test quests data directly (ensure this matches new structure too)
            raw_quests = [
                {
                    "user_quest_id": "test_daily_1",
                    "name": "Complete 10 Laps",
                    "description": "Drive 10 laps on any track.", # Added description for testing
                    "quest_type": "daily",
                    "completion_criteria": {"target_value": 10},
                    "progress": {"current_value": 5},
                    "is_complete": False,
                    "is_claimed": False,
                    "xp_reward": 100
                },
                {
                    "user_quest_id": "test_daily_2",
                    "name": "Set a Personal Best at Monza",
                    "description": "Achieve a new personal best lap time at Monza circuit.",
                    "quest_type": "daily",
                    "completion_criteria": {"action": "earn_pb", "track_name": "Monza"},
                    "progress": {},
                    "is_complete": False, # For testing, let's say this is not complete yet by default
                    "is_claimed": False,
                    "xp_reward": 250
                },
                {
                    "user_quest_id": "test_daily_3",
                    "name": "Drive Cleanly for 5 Minutes",
                    "description": "Complete 5 minutes of driving without incidents.",
                    "quest_type": "daily",
                    "completion_criteria": {"action": "drive_clean", "minutes": 5},
                    "progress": {},
                    "is_complete": True,
                    "is_claimed": False,
                    "xp_reward": 150
                },
                # ... (Add similar structure for weekly and achievements test data if needed)
                 {
                    "user_quest_id": "test_weekly_1",
                    "name": "Complete 3 Races",
                    "description": "Finish 3 full race events.",
                    "quest_type": "weekly",
                    "completion_criteria": {"action": "complete_race", "count": 3},
                    "progress": {"races_completed": 1}, # current_value could be races_completed
                    "is_complete": False,
                    "is_claimed": False,
                    "xp_reward": 300,
                    "race_pass_xp_reward": 100
                },
            ]
        else:
            logger.info(f"Successfully retrieved {len(raw_quests)} quests from Supabase")
        
        # Group quests by type
        dailies = []
        weeklies = []
        achievements = []
        
        for quest_from_db in raw_quests: # Renamed to quest_from_db
            # Format reward text
            structured_rewards = self._format_reward_text(quest_from_db) # Get structured rewards
            
            # Prepare data for QuestCardWidget
            current_progress = quest_from_db.get("progress", {})
            completion_criteria = quest_from_db.get("completion_criteria", {})

            progress_current = 0
            progress_target = 0
            progress_text_override = None

            is_complete = quest_from_db.get("is_complete", False)

            if is_complete:
                progress_text_override = "Completed!"
                # For completed quests, show progress bar as full
                if "target_value" in completion_criteria:
                    progress_current = completion_criteria.get("target_value", 1)
                    progress_target = completion_criteria.get("target_value", 1)
                elif "count" in completion_criteria: # for race completion type quests
                    progress_current = completion_criteria.get("count", 1)
                    progress_target = completion_criteria.get("count", 1)
                else: # Default for boolean-like tasks that are complete
                    progress_current = 1
                    progress_target = 1 # Show full bar
            else:
                # Handle progress for non-completed quests
                if "target_value" in completion_criteria: # Standard numeric progress
                    progress_current = current_progress.get("current_value", 0)
                    progress_target = completion_criteria.get("target_value", 1) # Avoid division by zero if target is 0
                elif "action" in completion_criteria: # For action-based quests
                    action_type = completion_criteria.get("action")
                    if action_type == "earn_pb":
                        track = completion_criteria.get("track_name", "a track")
                        progress_text_override = f"Set PB @ {track}"
                        progress_current = 0 # Boolean, 0 out of 1 target
                        progress_target = 1
                    elif action_type == "complete_race":
                        progress_current = current_progress.get("races_completed", 0)
                        progress_target = completion_criteria.get("count", 1)
                        progress_text_override = f"{progress_current}/{progress_target} races"
                    elif action_type == "drive_clean":
                        minutes = completion_criteria.get("minutes", 5)
                        # Assuming no partial progress tracking for this in current_progress
                        progress_text_override = f"Drive clean {minutes}m"
                        progress_current = 0
                        progress_target = 1 # Treat as boolean
                    else:
                        progress_text_override = "In progress"
                        progress_current = 0
                        progress_target = 1 # Default for other actions
                else:
                    progress_text_override = "Pending"
                    progress_current = 0
                    progress_target = 1 # Default for unknown structure
            
            # Ensure target is not zero if current is also zero to avoid 0/0 display issues for progress bar
            if progress_target == 0 and progress_current == 0:
                progress_target = 1

            quest_card_data = {
                "id": quest_from_db.get("user_quest_id"),
                "title": quest_from_db.get("name", "Unknown Quest"),
                "description": quest_from_db.get("description"), # Get description if available
                "progress_current": progress_current,
                "progress_target": progress_target,
                "progress_text_override": progress_text_override,
                "rewards_list": structured_rewards, # New key with structured list
                "is_complete": is_complete,
                "is_claimed": quest_from_db.get("is_claimed", False),
                "type": quest_from_db.get("quest_type") # Keep type for sorting and _last_loaded_quests_by_id
            }
            
            # Sort by quest type
            if quest_from_db.get("quest_type") == "daily":
                dailies.append(quest_card_data)
            elif quest_from_db.get("quest_type") == "weekly":
                weeklies.append(quest_card_data)
            elif quest_from_db.get("quest_type") in ["achievement", "event"]:
                achievements.append(quest_card_data)
            
            # Populate the cache for _find_quest_title_by_id fallback (using the new structure)
            if quest_card_data["id"]:
                self._last_loaded_quests_by_id[quest_card_data["id"]] = quest_card_data
        
        # Update quest lists
        logger.info(f"Updating UI with quests: {len(dailies)} dailies, {len(weeklies)} weeklies, {len(achievements)} achievements")
        self.update_quests('daily', dailies)
        self.update_quests('weekly', weeklies)
        self.update_quests('achievement', achievements)

        self._update_claim_all_button_state() # Update after quests are loaded

    def _format_progress_text(self, quest):
        """DEPRECATED: Format a progress text based on quest data. This logic is now handled in load_quests_from_supabase for QuestCardWidget."""
        # This method is largely superseded by direct data prep for QuestCardWidget.
        # It can be kept for a while if other parts of the code still use it, or removed if not.
        logger.warning("_format_progress_text is deprecated and should ideally not be called.")
        # Get values to format progress
        completion_criteria = quest.get("completion_criteria", {})
        progress = quest.get("progress", {})
        
        # If quest is complete, show "Completed!"
        if quest.get("is_complete", False):
            return "Completed!"
        
        # Different formats depending on criteria type
        if "target_value" in completion_criteria:
            target = completion_criteria.get("target_value")
            current = progress.get("current_value", 0)
            return f"{current}/{target}"
        
        # For quests with a boolean completion check
        elif "action" in completion_criteria:
            action_type = completion_criteria.get("action")
            if action_type == "earn_pb":
                track = completion_criteria.get("track_name", "a track")
                return f"Set a PB at {track}"
            elif action_type == "complete_race":
                count = completion_criteria.get("count", 1)
                return f"0/{count} races"
            elif action_type == "drive_clean":
                minutes = completion_criteria.get("minutes", 5)
                return f"0/{minutes} mins clean"
            else:
                return "In progress"
        
        # Default case
        return "In progress"

    def _format_reward_text(self, quest):
        """Format a reward text based on quest data. 
        Returns a list of dictionaries, e.g., 
        [{'type': 'xp', 'text': '+100 XP'}, {'type': 'rp_xp', 'text': '+50 RP XP'}]"""
        rewards_list = []
        
        # XP reward
        xp = quest.get("xp_reward", 0)
        if xp > 0:
            rewards_list.append({'type': 'xp', 'text': f"+{xp} XP"})
        
        # Race Pass XP reward
        rp_xp = quest.get("race_pass_xp_reward", 0)
        if rp_xp > 0:
            rewards_list.append({'type': 'rp_xp', 'text': f"+{rp_xp} RP XP"})
        
        # Other rewards (like badges, titles)
        other_reward = quest.get("other_reward", {})
        if other_reward:
            if "title" in other_reward:
                rewards_list.append({'type': 'title', 'text': f"Title: {other_reward['title']}"})
            if "badge" in other_reward:
                rewards_list.append({'type': 'badge', 'text': f"Badge: {other_reward['badge']}"})
        
        if not rewards_list:
            return [{'type': 'none', 'text': "No specific reward"}] # Handle case of no rewards
            
        return rewards_list

    def update_quests(self, quest_type, quest_list):
        """Updates the list for a specific quest type."""
        target_layout = None
        if quest_type == 'daily':
            target_layout = self.daily_quests_layout
        elif quest_type == 'weekly':
            target_layout = self.weekly_quests_layout
        elif quest_type == 'achievement':
            target_layout = self.achievements_layout
        else:
            return

        # Clear existing widgets from the layout
        if target_layout is not None:
            while target_layout.count():
                child = target_layout.takeAt(0)
                if child.widget():
                    child.widget().deleteLater()
        
        if not quest_list:
            # Optionally, add a placeholder if the list is empty
            # empty_label = QLabel("No quests available for this category.")
            # empty_label.setStyleSheet("color: #888; font-style: italic; padding: 10px;")
            # empty_label.setAlignment(Qt.AlignCenter)
            # target_layout.addWidget(empty_label)
            return
            
        for quest_data in quest_list:
            if target_layout is not None:
                # Create the new QuestCardWidget
                # quest_data should be formatted by load_quests_from_supabase 
                # to match what QuestCardWidget expects.
                card = QuestCardWidget(quest_data) 
                
                # Apply base styling to the card from QuestViewWidget for consistency if needed
                # Or rely on QuestCardWidget's own styling if defined there.
                # card.setStyleSheet(""" /* Base style for QuestCardWidget if not self-styled */
                #     QuestCardWidget {
                #         background-color: #3A3A3A;
                #         border: 1px solid #555555;
                #         border-radius: 8px;
                #         margin-bottom: 5px; /* Spacing between cards */
                #     }
                # """)
                
                # Connect the card's claim signal to the QuestViewWidget's claim method
                card.claim_button_clicked.connect(self.claim_quest)
                
                target_layout.addWidget(card)

        self._update_claim_all_button_state() # Also update after each list update

    def _create_quest_item_widget(self, quest_data):
        """Creates a custom widget for displaying a single quest item."""
        widget = QWidget()
        # Set a background color for the item_widget to make it an opaque card
        widget.setStyleSheet("background-color: #3C3C3C; border-radius: 3px;")

        layout = QHBoxLayout(widget)
        # Use identical margins and spacing for all quests regardless of type
        layout.setContentsMargins(10, 15, 10, 15)  # Increased top/bottom internal margins to 15px
        layout.setSpacing(15)

        # Quest Info (Title, Progress)
        info_widget = QWidget()
        info_layout = QVBoxLayout(info_widget)
        info_layout.setContentsMargins(0,0,0,0)
        info_layout.setSpacing(10)  # Increased spacing between title and progress to 10px
        
        title_label = QLabel(quest_data['title'])
        title_label.setFont(QFont("Arial", 10, QFont.Bold))
        title_label.setWordWrap(True)
            
        progress_label = QLabel(f"Progress: {quest_data['progress']}")
        progress_label.setStyleSheet("color: #BBB; font-size: 9pt;")
        progress_label.setWordWrap(True)
        
        info_layout.addWidget(title_label)
        info_layout.addWidget(progress_label)
        
        # Reward Info
        reward_label = QLabel(f"Reward: {quest_data['reward']}")
        reward_label.setStyleSheet("color: #DAA520; font-size: 9pt;")
        reward_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        reward_label.setWordWrap(True)
        reward_label.setMinimumWidth(150)

        # Claim Button (if applicable)
        claim_button = QPushButton("Claim Reward")
        claim_button.setFixedWidth(100)
        claim_button.setFixedHeight(28)
        claim_button.setStyleSheet(self.CLAIM_BUTTON_STYLE)
        
        claim_button.setEnabled(quest_data['complete'] and not quest_data.get('claimed', False))
        claim_button.setVisible(quest_data['complete'] and not quest_data.get('claimed', False))
        
        # Connect claim button to claim_quest function with the quest data
        if 'id' in quest_data:
            claim_button.clicked.connect(lambda checked=False, q_id=quest_data['id']: self.claim_quest(q_id))
        else:
            # Fallback for placeholder data without proper IDs
            claim_button.clicked.connect(lambda checked=False, q_title=quest_data['title']: self.claim_quest_by_title(q_title))
        
        # Claimed Indicator
        claimed_label = QLabel("✓ Claimed")
        claimed_label.setStyleSheet("color: #2ECC71; font-weight: bold; font-size: 9pt;")
        claimed_label.setVisible(quest_data.get('claimed', False))

        # Add elements to layout
        layout.addWidget(info_widget, 1) # Info takes stretch space
        layout.addWidget(reward_label)
        layout.addWidget(claim_button)
        layout.addWidget(claimed_label)

        # Dim if claimed or not complete (unless it's an achievement)
        is_achievement = quest_data.get('type', '') == 'achievement' # Assuming type is passed
        if quest_data.get('claimed', False) or (not quest_data['complete'] and not is_achievement):
            widget.setStyleSheet("color: #888;") # Make text dimmer
            # You might need to apply this style to child labels too if direct styling is used
            title_label.setStyleSheet("color: #888; font-weight: bold;")
            progress_label.setStyleSheet("color: #666; font-size: 9pt;")
            reward_label.setStyleSheet("color: #888; font-size: 9pt;")

        widget.setMinimumHeight(90)  # Ensure the item widget has a minimum height
        return widget

    def claim_quest(self, quest_id):
        """Claims a quest by its ID using Supabase API."""
        logger.info(f"Attempting to claim quest with ID: {quest_id}")
        
        try:
            # First try to use Supabase API to claim the quest
            success, message, reward_info = claim_quest_reward(quest_id)
            
            if success:
                logger.info(f"Successfully claimed quest through Supabase: {message}")
                # Extract reward info
                xp_reward = reward_info.get("xp_reward", 0)
                
                # Find the quest title from our UI for better feedback
                quest_title = self._find_quest_title_by_id(quest_id)
                
                # Emit signal with quest info
                logger.info(f"Emitting quest_claimed signal for quest: {quest_title}, XP: {xp_reward}")
                self.quest_claimed.emit(quest_title, xp_reward)
                
                # Refresh the UI
                self.load_quests_from_supabase()
            else:
                logger.error(f"Failed to claim quest through Supabase: {message}")
                
                # FALLBACK: For test/demo quests, manually handle them
                if quest_id.startswith("test_"):
                    logger.info("Quest has test_ prefix, handling locally")
                    # For test quests, manually update them in our UI
                    quest_title = self._find_quest_title_by_id(quest_id)
                    if quest_title:
                        xp_reward = self._get_demo_xp_for_quest(quest_id)
                        logger.info(f"Emitting quest_claimed signal for test quest: {quest_title}, XP: {xp_reward}")
                        self.quest_claimed.emit(quest_title, xp_reward)
                        self._mark_test_quest_claimed(quest_id)
                    else:
                        logger.warning(f"Could not find quest title for ID: {quest_id}")
                else:
                    # Show error message for non-test quests
                    QMessageBox.warning(
                        self, 
                        "Quest Claim Failed", 
                        f"Failed to claim quest reward: {message}"
                    )
        except Exception as e:
            logger.error(f"Error while claiming quest: {e}")
            QMessageBox.critical(
                self, 
                "Error", 
                f"An error occurred while claiming the quest: {str(e)}"
            )

    def _find_quest_title_by_id(self, quest_id_to_find):
        """Find a quest title by its ID by searching through QuestCardWidgets in UI layouts."""
        logger.debug(f"Searching for quest title with ID: {quest_id_to_find}")
        
        layouts_to_search = [
            self.daily_quests_layout, 
            self.weekly_quests_layout, 
            self.achievements_layout
        ]

        for layout in layouts_to_search:
            if layout is not None:
                for i in range(layout.count()):
                    widget = layout.itemAt(i).widget()
                    if isinstance(widget, QuestCardWidget):
                        # Check if the card's quest_id matches
                        if hasattr(widget, 'quest_id') and widget.quest_id == quest_id_to_find:
                            # The title is stored in quest_title_label within the card
                            if hasattr(widget, 'quest_title_label'):
                                title = widget.quest_title_label.text()
                                logger.debug(f"Found title '{title}' for quest ID {quest_id_to_find}")
                                return title
                            else:
                                logger.warning(f"QuestCardWidget with ID {quest_id_to_find} found, but has no quest_title_label attribute.")
                                break # Stop searching this layout if card structure is unexpected
                        
        # Fallback if not found in active UI cards
        logger.warning(f"Could not find QuestCardWidget with ID {quest_id_to_find} in UI layouts.")
        # Attempt to use the cached data as a last resort
        if hasattr(self, '_last_loaded_quests_by_id') and quest_id_to_find in self._last_loaded_quests_by_id:
            cached_quest_data = self._last_loaded_quests_by_id[quest_id_to_find]
            title = cached_quest_data.get("title", f"Quest {quest_id_to_find}")
            logger.warning(f"Returning title '{title}' from _last_loaded_quests_by_id for {quest_id_to_find}.")
            return title
        
        logger.error(f"Failed to find any title for quest ID {quest_id_to_find}. Returning default.")
        return f"Quest {quest_id_to_find}" # Original fallback

    def _get_demo_xp_for_quest(self, quest_id):
        """Get XP reward for a demo quest."""
        # Demo XP values based on quest type
        if "daily" in quest_id:
            return 100 if "1" in quest_id else 150 if "2" in quest_id else 200
        elif "weekly" in quest_id:
            return 300 if "1" in quest_id else 500
        elif "achievement" in quest_id:
            return 1000
        return 100  # Default fallback

    def _mark_test_quest_claimed(self, quest_id):
        """Mark a test quest as claimed in the UI."""
        # No database update needed for test quests, just refresh UI
        logger.info(f"Marking test quest {quest_id} as claimed and refreshing UI")
        self.load_quests_from_supabase()

    def claim_quest_by_title(self, quest_title):
        """Placeholder for claiming by title - only for testing with placeholder data."""
        logger.info(f"Claiming quest with title: {quest_title}")
        
        # For placeholder data, simulate a successful claim
        xp_reward = 100  # Default XP value for placeholder data
        if "Spa" in quest_title:
            xp_reward = 250
        elif "Cleanly" in quest_title:
            xp_reward = 50
        elif "Race" in quest_title:
            xp_reward = 500
        
        # Emit signal with quest info
        logger.info(f"Emitting quest_claimed signal for: {quest_title}, XP: {xp_reward}")
        self.quest_claimed.emit(quest_title, xp_reward)
        
        # Refresh with a "claimed" state for visual feedback in placeholder data
        self.load_quests_from_supabase()

    def _refresh_quests_after_claim(self):
        """Refresh quests after claim - used for both actual and placeholder data."""
        # When working with real data, load from Supabase
        self.load_quests_from_supabase()
        
    def assign_new_quests(self):
        """Assign new daily and weekly quests to the user."""
        # Try to assign new daily quests
        daily_success, daily_message = assign_daily_quests()
        if not daily_success:
            logger.warning(f"Failed to assign daily quests: {daily_message}")
        
        # Try to assign new weekly quests
        weekly_success, weekly_message = assign_weekly_quests()
        if not weekly_success:
            logger.warning(f"Failed to assign weekly quests: {weekly_message}")
        
        # Refresh the UI to show new quests
        self.load_quests_from_supabase()

    def _get_claimable_quest_ids(self):
        """Helper to get a list of all currently claimable quest IDs."""
        claimable_ids = []
        layouts_to_search = [
            self.daily_quests_layout, 
            self.weekly_quests_layout, 
            self.achievements_layout
        ]
        for layout in layouts_to_search:
            if layout:
                for i in range(layout.count()):
                    widget = layout.itemAt(i).widget()
                    if isinstance(widget, QuestCardWidget):
                        # Check if claimable: button enabled and text is "Claim Reward"
                        if widget.claim_button.isEnabled() and widget.claim_button.text() == "Claim Reward":
                            if widget.quest_id:
                                claimable_ids.append(widget.quest_id)
        return claimable_ids

    def _update_claim_all_button_state(self):
        """Enables or disables the 'Claim All' button based on available claimable quests."""
        if hasattr(self, 'claim_all_button'): # Ensure button exists
            claimable_ids = self._get_claimable_quest_ids()
            self.claim_all_button.setEnabled(len(claimable_ids) > 0)

    def _handle_claim_all(self):
        """Handles the 'Claim All' button click."""
        claimable_ids = self._get_claimable_quest_ids()

        if not claimable_ids:
            QMessageBox.information(self, "Claim All", "No rewards available to claim at the moment.")
            return

        self.claim_all_button.setEnabled(False) # Disable while processing
        self.claim_all_button.setText("Claiming All...")

        num_successful_claims = 0
        num_failed_claims = 0
        total_xp_claimed_this_session = 0 # Optional: for a summary

        for quest_id in claimable_ids:
            logger.info(f"Claim All: Attempting to claim quest ID: {quest_id}")
            try:
                success, message, reward_info = claim_quest_reward(quest_id)
                if success:
                    num_successful_claims += 1
                    quest_title = self._find_quest_title_by_id(quest_id) # Re-use existing helper
                    xp_reward = reward_info.get("xp_reward", 0)
                    rp_xp_reward = reward_info.get("race_pass_xp_reward", 0) # Assuming this key might exist
                    total_xp_claimed_this_session += xp_reward + rp_xp_reward 
                    
                    logger.info(f"Claim All: Successfully claimed {quest_title} (ID: {quest_id}). XP: {xp_reward}, RP_XP: {rp_xp_reward}")
                    self.quest_claimed.emit(quest_title, xp_reward + rp_xp_reward) # Emit for each successful claim
                else:
                    num_failed_claims += 1
                    logger.error(f"Claim All: Failed to claim quest {quest_id}: {message}")
            except Exception as e:
                num_failed_claims += 1
                logger.error(f"Claim All: Exception while claiming quest {quest_id}: {e}")
        
        # Refresh the entire quest list once after all attempts
        if num_successful_claims > 0 or num_failed_claims > 0: # Refresh if anything was attempted
             self.load_quests_from_supabase() # This will also update claim_all_button state

        # Restore button text (state will be updated by _update_claim_all_button_state via load_quests)
        self.claim_all_button.setText("Claim All Rewards")

        # Show summary message
        summary_message = []
        if num_successful_claims > 0:
            summary_message.append(f"Successfully claimed {num_successful_claims} reward(s).")
            # Could add total XP: e.g., f" Totaling +{total_xp_claimed_this_session} XP."
        if num_failed_claims > 0:
            summary_message.append(f"Failed to claim {num_failed_claims} reward(s). Check logs for details.")
        
        if not summary_message: # Should not happen if claimable_ids was not empty
            summary_message.append("No rewards were processed.")

        QMessageBox.information(self, "Claim All Results", " ".join(summary_message))

# Example usage (for testing standalone)
if __name__ == '__main__':
    import sys
    from PyQt5.QtWidgets import QApplication, QMainWindow
    from PyQt5.QtGui import QPalette, QColor

    app = QApplication(sys.argv)
    # Set a dark theme for testing
    app.setStyle("Fusion")
    dark_palette = QPalette()
    dark_palette.setColor(QPalette.Window, QColor(53, 53, 53))
    dark_palette.setColor(QPalette.WindowText, Qt.white)
    dark_palette.setColor(QPalette.Base, QColor(42, 42, 42))
    dark_palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
    dark_palette.setColor(QPalette.ToolTipBase, Qt.white)
    dark_palette.setColor(QPalette.ToolTipText, Qt.white)
    dark_palette.setColor(QPalette.Text, Qt.white)
    dark_palette.setColor(QPalette.Button, QColor(53, 53, 53))
    dark_palette.setColor(QPalette.ButtonText, Qt.white)
    dark_palette.setColor(QPalette.BrightText, Qt.red)
    dark_palette.setColor(QPalette.Link, QColor(42, 130, 218))
    dark_palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
    dark_palette.setColor(QPalette.HighlightedText, Qt.black)
    app.setPalette(dark_palette)

    main_window = QMainWindow()
    quest_view = QuestViewWidget()
    main_window.setCentralWidget(quest_view)
    main_window.setWindowTitle("Quest View Test")
    main_window.setGeometry(100, 100, 600, 400)
    main_window.show()
    sys.exit(app.exec_()) 