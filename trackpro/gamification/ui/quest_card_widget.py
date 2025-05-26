from PyQt5.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton, QProgressBar, 
    QSizePolicy
)
from PyQt5.QtCore import Qt, pyqtSignal, QSize, QTimer, QUrl, QPropertyAnimation, QEasingCurve, pyqtProperty, QObject
from PyQt5.QtGui import QFont, QPixmap, QColor
from PyQt5.QtMultimedia import QSoundEffect
import logging
# External UI helper for toast notifications
from .notifications import ToastNotification

logger = logging.getLogger(__name__)

class QuestCardWidget(QWidget):
    """
    Custom widget to display a single quest as a visually distinct card.
    Corresponds to section 3.2 of the quest_ui_revamp_plan.md.
    """
    # Signal to be emitted when the claim button is clicked, carrying the quest_id
    claim_button_clicked = pyqtSignal(str)

    # For animated button fill property
    _claim_button_fill_ratio = 0.0
    _animated_xp_value = 0
    _animated_rp_xp_value = 0

    def __init__(self, quest_data, parent=None):
        super().__init__(parent)
        self.quest_id = quest_data.get("id") # Store quest_id for the signal
        self._previously_claimed = quest_data.get("is_claimed", False)
        self._rewards_list: list = quest_data.get("rewards_list", [])  # store for reuse
        self._claim_button_fill_ratio = 0.0 # Initialize here
        self._animated_xp_value = 0
        self._animated_rp_xp_value = 0
        self.xp_reward_label: QLabel | None = None
        self.rp_xp_reward_label: QLabel | None = None
        self._xp_count_anim: QPropertyAnimation | None = None # To hold animation object
        self._rp_xp_count_anim: QPropertyAnimation | None = None # To hold animation object

        # Define base styles for child widgets consistently
        self.base_widget_styles = """
            QLabel { color: #E0E0E0; background-color: transparent; }
            QProgressBar { border: 1px solid #555; border-radius: 7px; background-color: #505050; text-align: center; }
            QProgressBar::chunk { background-color: #27ae60; border-radius: 6px; margin: 1px; }
        """

        # Configure stylesheets for different card states
        self.style_config = {
            "normal": {
                "card": """
                    QuestCardWidget {
                        background-color: #3A3A3A;
                        border: 1px solid #555555;
                        border-radius: 8px;
                        color: white;
                    }
                    QuestCardWidget:hover {
                        background-color: #424242;
                        border: 1px solid #666666;
                    }
                """,
                "children": self.base_widget_styles
            },
            "claimed": {
                "card": """
                    QuestCardWidget {
                        background-color: #303030;
                        border: 1px solid #444444;
                        border-radius: 8px;
                        color: white;
                    }
                    QuestCardWidget:hover {
                        background-color: #303030;
                        border: 1px solid #444444;
                    }
                """,
                "children": self.base_widget_styles
            },
            "pulse": { # For temporary highlight when claimed
                "card": """
                    QuestCardWidget {
                        background-color: #353535; /* Slightly lighter background for pulse */
                        border: 2px solid #DAA520; /* Gold, thicker border */
                        border-radius: 8px;
                        color: white;
                    }
                    QuestCardWidget:hover {
                        background-color: #353535;
                        border: 2px solid #DAA520;
                    }
                """,
                "children": self.base_widget_styles
            }
        }

        self._init_ui(quest_data)
        
        # Initialize sound effects with error handling
        self.claim_sound = QSoundEffect(self)
        self.click_sound = QSoundEffect(self)
        
        # Try to load sound files, but don't fail if they don't exist
        try:
            sound_file_path = "trackpro/resources/sounds/quest_claim.wav" 
            self.claim_sound.setSource(QUrl.fromLocalFile(sound_file_path))
            self.claim_sound.setVolume(0.8)
        except Exception as e:
            logger.warning(f"Could not load claim sound: {e}")
            
        try:
            click_sound_path = "trackpro/resources/sounds/quest_click.wav"
            self.click_sound.setSource(QUrl.fromLocalFile(click_sound_path))
            self.click_sound.setVolume(0.25)
        except Exception as e:
            logger.warning(f"Could not load click sound: {e}")

        # Set initial stylesheet
        initial_style_parts = self.style_config["normal"]
        self.setStyleSheet(initial_style_parts["card"] + initial_style_parts["children"])
        
        self.set_quest_data(quest_data) # Populate with initial data

    def _init_ui(self, quest_data):
        """Initializes the UI elements of the quest card."""
        self.setFixedHeight(120) # Recommended fixed height for consistency (adjustable)
        
        # Main card styling - now handled by __init__ and set_quest_data via style_config
        # self.setStyleSheet(""" ... """) # Removed from here

        # Main horizontal layout
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10) # Padding within the card
        main_layout.setSpacing(15) # Spacing between left and right sections

        # --- Left Section (Quest Details) ---
        left_section_widget = QWidget()
        left_layout = QVBoxLayout(left_section_widget)
        left_layout.setContentsMargins(0,0,0,0)
        left_layout.setSpacing(5)

        self.quest_title_label = QLabel("Quest Title Placeholder")
        font_title = QFont()
        font_title.setBold(True)
        font_title.setPointSize(11)
        self.quest_title_label.setFont(font_title)
        self.quest_title_label.setWordWrap(True)
        self.quest_title_label.setStyleSheet("color: white;") # Explicitly white for title

        self.quest_description_label = QLabel("Quest description placeholder (optional)")
        font_desc = QFont()
        font_desc.setPointSize(9)
        self.quest_description_label.setFont(font_desc)
        self.quest_description_label.setWordWrap(True)
        self.quest_description_label.setStyleSheet("color: #BBBBBB;") # Subtler color for description
        self.quest_description_label.setVisible(False) # Optional, hide by default

        # Progress Display Area
        progress_area_layout = QHBoxLayout()
        progress_area_layout.setContentsMargins(0,0,0,0)
        progress_area_layout.setSpacing(5)

        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(15) # Increased height slightly as per plan example
        self.progress_bar.setTextVisible(False) # Text will be handled by progress_text_label
        # Styling for progress bar
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #555;
                border-radius: 7px;
                background-color: #505050;
                text-align: center; /* Ensure text would be centered if visible */
            }
            QProgressBar::chunk {
                background-color: #27ae60; /* Green for progress */
                border-radius: 6px;
                margin: 1px; /* Margin for the chunk to not touch border */
            }
        """)

        self.progress_text_label = QLabel("0/100")
        font_progress_text = QFont()
        font_progress_text.setPointSize(8)
        self.progress_text_label.setFont(font_progress_text)
        # self.progress_text_label.setStyleSheet("color: #DDDDDD;")
        
        progress_area_layout.addWidget(self.progress_bar, 1) # Progress bar takes stretch
        progress_area_layout.addWidget(self.progress_text_label)

        left_layout.addWidget(self.quest_title_label)
        left_layout.addWidget(self.quest_description_label)
        left_layout.addLayout(progress_area_layout)
        left_layout.addStretch(1) # Push content to the top

        # --- Right Section (Rewards & Claim) ---
        right_section_widget = QWidget()
        # Set a fixed width for the right section to ensure consistency
        right_section_widget.setFixedWidth(150) # Adjust as needed
        right_layout = QVBoxLayout(right_section_widget)
        right_layout.setContentsMargins(0,0,0,0)
        right_layout.setSpacing(5)
        right_layout.setAlignment(Qt.AlignTop) # Align content to top

        # New rewards layout area
        self.rewards_layout_widget = QWidget() # Create a container widget for the QHBoxLayout
        self.rewards_layout = QHBoxLayout(self.rewards_layout_widget)
        self.rewards_layout.setContentsMargins(0,0,0,0)
        self.rewards_layout.setSpacing(5) # Spacing between icon and text, and between reward items
        self.rewards_layout.setAlignment(Qt.AlignRight | Qt.AlignTop) # Align entire block to top-right

        self.claim_button = QPushButton("Claim")
        self.claim_button.setFixedHeight(30)
        # self.claim_button.setFixedWidth(100) # Or let it expand in its fixed width section
        # Styling will be applied based on state (claimable, claimed)
        # Example initial style (can be part of a theme or dynamic)
        # self.claim_button.setStyleSheet("""
        #     QPushButton { background-color: #27ae60; color: white; font-weight: bold; border-radius: 4px; }
        #     QPushButton:hover { background-color: #2ecc71; }
        #     QPushButton:disabled { background-color: #555555; color: #888888; }
        # """)
        self.claim_button.clicked.connect(self._on_claim_button_clicked_animated)


        right_layout.addWidget(self.rewards_layout_widget, 0, Qt.AlignTop) # Add new rewards container
        right_layout.addStretch(1) # Pushes claim button towards the bottom of its area
        right_layout.addWidget(self.claim_button, 0, Qt.AlignBottom) # Add claim button, align bottom


        # Add sections to main layout
        main_layout.addWidget(left_section_widget, 1) # Left section stretches
        main_layout.addWidget(right_section_widget, 0) # Right section has fixed width

        self.setLayout(main_layout)

    def set_quest_data(self, quest_data):
        """
        Populates the card's UI elements with data from a quest dictionary.
        quest_data is expected to have keys like 'title', 'description', 
        'progress_current', 'target_value', 'rewards_list', 'is_complete', 'is_claimed'.
        """
        self.quest_id = quest_data.get("id")
        
        # 1. Quest Title
        self.quest_title_label.setText(quest_data.get("title", "N/A"))

        # 2. Quest Description (Optional)
        description = quest_data.get("description")
        if description:
            self.quest_description_label.setText(description)
            self.quest_description_label.setVisible(True)
        else:
            self.quest_description_label.setVisible(False)

        # 3. Progress Bar and Text
        current_value = quest_data.get("progress_current", 0)
        # Ensure target_value defaults to at least 1 if not specified or 0.
        target_value = quest_data.get("progress_target", 1)
        progress_text_override = quest_data.get("progress_text_override")

        # Always set the range first.
        # Use max(1, target_value) to ensure the range is never zero, e.g. (0,0).
        actual_target_for_range = max(1, target_value)
        self.progress_bar.setRange(0, actual_target_for_range)

        if progress_text_override:
            self.progress_text_label.setText(progress_text_override)
            if quest_data.get("is_complete"):
                # For completed quests (even with override), show full progress relative to its actual target.
                self.progress_bar.setValue(actual_target_for_range)
            else: # In progress but with an override text
                self.progress_bar.setValue(current_value)
        # elif target_value > 0: # This condition is effectively covered now by actual_target_for_range logic
        # Display standard progress if no override text
        # Ensure current_value does not exceed actual_target_for_range for display
        # If target_value was originally 0 (now actual_target_for_range is 1), current_value should be 0 or 1.
        elif not progress_text_override : # only set text if no override
            self.progress_bar.setValue(min(current_value, actual_target_for_range))
            self.progress_text_label.setText(f"{min(current_value, actual_target_for_range)}/{target_value if target_value > 0 else actual_target_for_range}")
        # else: # Fallback for quests where target_value might be 0 or not meaningful, and no override
            # This case should be handled by actual_target_for_range being 1.
            # self.progress_bar.setValue(1 if quest_data.get("is_complete") else 0)
            # self.progress_text_label.setText("Completed" if quest_data.get("is_complete") else "Pending")

        # 4. Rewards List
        # Clear previous reward items from the layout
        while self.rewards_layout.count():
            child = self.rewards_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        self.xp_reward_label = None # Clear references
        self.rp_xp_reward_label = None # Clear references

        rewards_list = quest_data.get("rewards_list", [])
        if not rewards_list or (len(rewards_list) == 1 and rewards_list[0].get('type') == 'none'):
            # Display a default message if no specific rewards or only a 'none' type reward
            no_reward_label = QLabel("No specific rewards") # Or an empty string: ""
            no_reward_label.setStyleSheet("color: #AAAAAA; font-style: italic;")
            no_reward_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.rewards_layout.addWidget(no_reward_label)
        else:
            for reward_item in rewards_list:
                reward_type = reward_item.get("type")
                reward_text = reward_item.get("text", "")
                icon_path = None

                if reward_type == 'xp':
                    icon_path = "trackpro/resources/icons/xp_icon.png"
                elif reward_type == 'rp_xp':
                    icon_path = "trackpro/resources/icons/rp_xp_icon.png"
                # Add more types and icon paths here if needed (e.g., 'title', 'badge')

                if icon_path:
                    icon_label = QLabel()
                    pixmap = QPixmap(icon_path)
                    if not pixmap.isNull(): # Check if pixmap loaded successfully
                        icon_label.setPixmap(pixmap.scaled(16, 16, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                    else:
                        # Use text-based icons as fallback
                        if reward_type == 'xp':
                            icon_label.setText("⭐")
                        elif reward_type == 'rp_xp':
                            icon_label.setText("💎")
                        else:
                            icon_label.setText("🎁")
                        icon_label.setStyleSheet("font-size: 14px;")
                    icon_label.setToolTip(reward_type.replace("_", " ").title()) # e.g. "Xp" or "Rp Xp"
                    self.rewards_layout.addWidget(icon_label)
                
                text_label = QLabel(reward_text)
                font_rewards_text = QFont()
                font_rewards_text.setPointSize(9)
                text_label.setFont(font_rewards_text)
                text_label.setStyleSheet("color: #DAA520;") # Gold-like color for rewards text
                text_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter) # Align text within its own space
                self.rewards_layout.addWidget(text_label)

                # Store references to labels for animation
                if reward_type == 'xp':
                    self.xp_reward_label = text_label
                elif reward_type == 'rp_xp':
                    self.rp_xp_reward_label = text_label

        # 5. Claim Button State & Text and Styling
        is_complete = quest_data.get("is_complete", False)
        is_claimed = quest_data.get("is_claimed", False)

        # Base style for all buttons to ensure border-radius and padding are consistent
        # Specific background/text colors will override per state.
        base_button_style = "font-weight: bold; border-radius: 4px; padding: 4px; font-size: 9pt;"

        # Base card style (will be appended to if claimed)
        # This is now managed by self.style_config
        # current_card_style = """...""" # Removed

        card_style_key = "normal" # Default style key
        just_claimed_this_call = False

        if is_claimed:
            self.claim_button.setText("Claimed ✓")
            self.claim_button.setEnabled(False)
            self.claim_button.setStyleSheet(base_button_style + 
                                            "background-color: #555555; color: #888888;")
            card_style_key = "claimed"
            if not self._previously_claimed:
                just_claimed_this_call = True
        elif is_complete:
            self.claim_button.setText("Claim Reward")
            self.claim_button.setEnabled(True)
            # MODIFIED: Initial style for a claimable button (before fill animation on click)
            self.claim_button.setStyleSheet(base_button_style +
                                            "background-color: #474747; color: white;" + 
                                            "QPushButton:hover { background-color: #585858; }" +
                                            "QPushButton:pressed { background-color: #383838; }")
            # Reset for next potential animation, ensures setter uses base for gradient start if called before anim
            self._claim_button_fill_ratio = 0.0 
            # card_style_key remains "normal"
        else: # Not complete, not claimable
            self.claim_button.setText("In Progress")
            self.claim_button.setEnabled(False)
            self.claim_button.setStyleSheet(base_button_style +
                                            "background-color: #404040; color: #AAAAAA;")
            # card_style_key remains "normal"

        # Apply the determined stylesheet
        chosen_style_parts = self.style_config[card_style_key]
        self.setStyleSheet(chosen_style_parts["card"] + chosen_style_parts["children"])
        
        # Store rewards list for possible replay via double-click
        self._rewards_list = rewards_list

        if just_claimed_this_call:
            self._play_claim_feedback(card_style_key, rewards_list) # card_style_key will be "claimed"

        self._previously_claimed = is_claimed
        
        # Apply overall card dimming if claimed or not actionable (unless it's achievement always bright)
        # For now, this is not implemented here, could be done via opacity or specific styling for all child widgets

    # --- Custom Properties for Animation ---
    @pyqtProperty(float)
    def claimButtonFillRatio(self):
        return self._claim_button_fill_ratio

    @claimButtonFillRatio.setter
    def claimButtonFillRatio(self, ratio):
        self._claim_button_fill_ratio = ratio
        base_color = "#474747" # Must match the initial claimable button background
        fill_color = "#27ae60" # Green accent

        # Clamp ratio to avoid issues with gradient stops
        clamped_ratio = max(0.0, min(ratio, 1.0))
        
        current_style_bg = ""
        if clamped_ratio == 0.0:
            current_style_bg = f"background-color: {base_color};"
        elif clamped_ratio == 1.0:
            current_style_bg = f"background-color: {fill_color};"
        else:
            current_style_bg = f"""
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                            stop:0 {fill_color},
                                            stop:{clamped_ratio} {fill_color},
                                            stop:{min(clamped_ratio + 0.0001, 1.0)} {base_color},
                                            stop:1 {base_color});
            """
        
        # Base button style parts (font, border, padding)
        base_button_style_parts = "font-weight: bold; border-radius: 4px; padding: 4px; font-size: 9pt; color: white;"
        
        self.claim_button.setStyleSheet(base_button_style_parts + current_style_bg)

    @pyqtProperty(int)
    def animatedXpValue(self):
        return self._animated_xp_value

    @animatedXpValue.setter
    def animatedXpValue(self, value):
        self._animated_xp_value = value
        if self.xp_reward_label:
            self.xp_reward_label.setText(f"+{value} XP")

    @pyqtProperty(int)
    def animatedRpXpValue(self):
        return self._animated_rp_xp_value

    @animatedRpXpValue.setter
    def animatedRpXpValue(self, value):
        self._animated_rp_xp_value = value
        if self.rp_xp_reward_label:
            self.rp_xp_reward_label.setText(f"+{value} RP XP") # Ensure format matches

    def _on_claim_button_clicked_animated(self):
        """Handles the claim button click with a fill animation before emitting the signal."""
        try:
            if self.click_sound.isLoaded():
                self.click_sound.play()
        except Exception as e:
            logger.debug(f"Could not play click sound: {e}")

        if self.quest_id and self.claim_button.isEnabled():
            self.claim_button.setEnabled(False) # Disable during animation and processing
            self.claim_button.setText("Claiming...")

            # Ensure the property is at 0 before starting animation for consistent fill
            # Setting it directly will trigger the setter and apply initial gradient style
            self.claimButtonFillRatio = 0.0 

            self._button_fill_anim = QPropertyAnimation(self, b"claimButtonFillRatio", self)
            self._button_fill_anim.setDuration(600)  # Duration of the fill in ms
            self._button_fill_anim.setStartValue(0.0)
            self._button_fill_anim.setEndValue(1.0)
            self._button_fill_anim.setEasingCurve(QEasingCurve.InOutQuad)
            
            # Disconnect previous connection if any to avoid multiple emissions
            try:
                self._button_fill_anim.finished.disconnect(self._emit_claim_signal_after_fill)
            except TypeError: # No connection existed
                pass # It's fine if no connection existed
            self._button_fill_anim.finished.connect(self._emit_claim_signal_after_fill)
            self._button_fill_anim.start()

    def _emit_claim_signal_after_fill(self):
        """Emits the actual claim signal after the fill animation is complete."""
        if self.quest_id:
            self.claim_button_clicked.emit(self.quest_id)
            
    def _on_claim_button_clicked(self):
        """DEPRECATED by _on_claim_button_clicked_animated - kept for reference or quick toggle if needed."""
        # Play click sound immediately on press (regardless of success)
        if self.click_sound.isLoaded():
            self.click_sound.play()
        if self.quest_id:
            self.claim_button_clicked.emit(self.quest_id)

    def _play_claim_feedback(self, final_style_key, rewards_list):
        """Plays sound, pulse animation, toast, boing, and counts up rewards."""
        # 1. Play sound
        try:
            if self.claim_sound.isLoaded():
                self.claim_sound.play()
        except Exception as e:
            logger.debug(f"Could not play claim sound: {e}")

        # 2. Toast notification (top-right of parent window)
        if rewards_list:
            # Build a concise message like "+150 XP  +10 RP"
            msg_parts = []
            icon_path_for_toast = None
            for idx, item in enumerate(rewards_list):
                text = item.get("text")
                if text:
                    msg_parts.append(text)
                # Use first item's icon for the toast if we have one
                if idx == 0:
                    r_type = item.get("type")
                    if r_type == 'xp':
                        icon_path_for_toast = "trackpro/resources/icons/xp_icon.png"
                    elif r_type == 'rp_xp':
                        icon_path_for_toast = "trackpro/resources/icons/rp_xp_icon.png"
            if msg_parts:
                toast = ToastNotification(self.window(), " ".join(msg_parts), notification_type="success")
                toast.show_notification()

        # 3. Card pulse animation
        pulse_style_parts = self.style_config["pulse"]
        revert_style_parts = self.style_config[final_style_key] # Should be "claimed" state

        # Apply pulse style
        self.setStyleSheet(pulse_style_parts["card"] + pulse_style_parts["children"])

        # After a delay, revert to the normal claimed style
        QTimer.singleShot(400, lambda: self.setStyleSheet(revert_style_parts["card"] + revert_style_parts["children"]))

        # 4. "Boing" scale animation (card briefly enlarges and shrinks)
        original_geom = self.geometry()
        # Calculate a slightly larger geometry (10% bigger)
        scale_factor = 0.05  # 5% enlargement on each side (total ~10% bigger)
        enlarged_geom = original_geom.adjusted(
            int(-original_geom.width() * scale_factor),
            int(-original_geom.height() * scale_factor),
            int(original_geom.width() * scale_factor),
            int(original_geom.height() * scale_factor),
        )

        # Create animation if not already running
        anim = QPropertyAnimation(self, b"geometry")
        anim.setDuration(250)
        anim.setEasingCurve(QEasingCurve.OutBack)
        anim.setKeyValueAt(0.0, original_geom)
        anim.setKeyValueAt(0.5, enlarged_geom)
        anim.setKeyValueAt(1.0, original_geom)
        # Keep a reference so it isn't garbage collected
        self._scale_anim = anim
        anim.start()

        # 5. Animate Reward Numbers (Count-up)
        xp_to_animate = 0
        rp_xp_to_animate = 0
        for item in rewards_list:
            r_type = item.get("type")
            r_text = item.get("text", "")
            try:
                if r_type == 'xp':
                    xp_to_animate = int(r_text.replace("+", "").split(" ")[0])
                elif r_type == 'rp_xp':
                    rp_xp_to_animate = int(r_text.replace("+", "").split(" ")[0])
            except (ValueError, IndexError):
                pass # Could not parse number

        if self.xp_reward_label and xp_to_animate > 0:
            self.xp_reward_label.setText("+0 XP") # Start from 0
            self._xp_count_anim = QPropertyAnimation(self, b"animatedXpValue", self)
            self._xp_count_anim.setDuration(700) # Animation duration in ms
            self._xp_count_anim.setStartValue(0)
            self._xp_count_anim.setEndValue(xp_to_animate)
            self._xp_count_anim.setEasingCurve(QEasingCurve.OutCubic)
            self._xp_count_anim.start()
        
        if self.rp_xp_reward_label and rp_xp_to_animate > 0:
            self.rp_xp_reward_label.setText("+0 RP XP") # Start from 0
            self._rp_xp_count_anim = QPropertyAnimation(self, b"animatedRpXpValue", self)
            self._rp_xp_count_anim.setDuration(700)
            self._rp_xp_count_anim.setStartValue(0)
            self._rp_xp_count_anim.setEndValue(rp_xp_to_animate)
            self._rp_xp_count_anim.setEasingCurve(QEasingCurve.OutCubic)
            self._rp_xp_count_anim.start()

    # ------------------------------------------------------------------
    # Testing helper: double-click to replay feedback when already claimed
    # ------------------------------------------------------------------
    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton and self._previously_claimed:
            # Replay feedback using stored rewards
            self._play_claim_feedback("claimed", self._rewards_list)
        super().mouseDoubleClickEvent(event)

# Example Usage (for testing QuestCardWidget standalone if needed)
if __name__ == '__main__':
    import sys
    from PyQt5.QtWidgets import QApplication, QMainWindow
    from PyQt5.QtCore import QUrl # Required for QSoundEffect paths
    
    # Example quest data structures
    quest_data_incomplete = {
        "id": "daily_lap_1",
        "title": "Drive 5 Laps at Monza",
        "description": "Complete 5 full laps at Autodromo Nazionale Monza in any car.",
        "progress_current": 2,
        "progress_target": 5,
        "rewards_list": [{"type": "xp", "text": "+150 XP"}, {"type": "rp_xp", "text": "+10 RP"}],
        "is_complete": False,
        "is_claimed": False
    }

    quest_data_complete_claimable = {
        "id": "daily_pb_1",
        "title": "Set a New Personal Best",
        "description": "Beat your previous best lap time on any track.",
        "progress_text_override": "Completed!",
        "progress_current": 1,
        "progress_target": 1,
        "rewards_list": [{"type": "xp", "text": "+250 XP"}],
        "is_complete": True,
        "is_claimed": False
    }

    quest_data_claimed = {
        "id": "weekly_dist_1",
        "title": "Drive 100km This Week",
        "description": None,
        "progress_current": 100,
        "progress_target": 100,
        "rewards_list": [{"type": "xp", "text": "+500 XP"}, {"type": "rp_xp", "text": "+50 RP"}, {"type": "title", "text": "Title: Road Warrior"}],
        "is_complete": True,
        "is_claimed": True
    }

    app = QApplication(sys.argv)
    # Basic dark theme for testing
    app.setStyle("Fusion")
    # ... (palette code from QuestViewWidget could be reused here if desired for consistency)

    main_window = QMainWindow()
    main_window.setWindowTitle("QuestCardWidget Test")
    main_window.setGeometry(100, 100, 450, 400) # Adjusted size for multiple cards
    
    container = QWidget()
    layout = QVBoxLayout(container)
    
    card1 = QuestCardWidget(quest_data_incomplete)
    card2 = QuestCardWidget(quest_data_complete_claimable)
    card3 = QuestCardWidget(quest_data_claimed)
    
    layout.addWidget(card1)
    layout.addWidget(card2)
    layout.addWidget(card3)
    layout.addStretch(1)

    main_window.setCentralWidget(container)
    main_window.show()
    sys.exit(app.exec_()) 