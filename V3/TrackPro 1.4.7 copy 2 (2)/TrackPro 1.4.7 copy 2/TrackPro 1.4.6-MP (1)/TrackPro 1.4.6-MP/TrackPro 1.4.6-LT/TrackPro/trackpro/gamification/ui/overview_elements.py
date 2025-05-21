from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar, QGroupBox, QFrame, QSpacerItem, QSizePolicy, QPushButton
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QColor, QPalette

# --- Add import for RacePassViewWidget ---
from .race_pass_view import RacePassViewWidget
# ----------------------------------------

class GamificationCard(QFrame):
    """A styled frame to be used as a card for gamification sections."""
    def __init__(self, title_text, icon_char=None, parent=None):
        super().__init__(parent)
        self.setObjectName("GamificationCard")
        self.setFrameShape(QFrame.StyledPanel)
        self.setFrameShadow(QFrame.Raised) # Can be QFrame.Sunken or QFrame.Plain
        self.setStyleSheet("""
            GamificationCard {
                background-color: #2E3440; /* Nord Polar Night - darker */
                border-radius: 8px;
                border: 1px solid #3B4252; /* Nord Polar Night - slightly lighter for border */
                padding: 1px; /* Minimal padding to allow content margins to work well */
            }
        """)

        self.card_layout = QVBoxLayout(self)
        self.card_layout.setContentsMargins(12, 8, 12, 12) # Top margin smaller for title
        self.card_layout.setSpacing(8)

        if title_text:
            title_layout = QHBoxLayout()
            title_layout.setContentsMargins(0,0,0,5) # Bottom margin for separation
            if icon_char:
                icon_label = QLabel(icon_char)
                icon_font = QFont("Arial", 14)
                icon_font.setBold(True)
                icon_label.setFont(icon_font)
                icon_label.setStyleSheet("color: #88C0D0;") # Nord Frost - cyan/blue
                title_layout.addWidget(icon_label)
            
            title_label = QLabel(title_text)
            title_font = QFont("Arial", 11)
            title_font.setBold(True)
            title_label.setFont(title_font)
            title_label.setStyleSheet("color: #ECEFF4;") # Nord Snow Storm - light gray/white
            title_layout.addWidget(title_label, 1)
            self.card_layout.addLayout(title_layout)

    def addContentWidget(self, widget):
        self.card_layout.addWidget(widget)

    def addContentLayout(self, layout):
        self.card_layout.addLayout(layout)

class GamificationOverviewWidget(QWidget):
    """Container widget for gamification elements shown on the main overview tab."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("GamificationOverviewWidget")
        self.setStyleSheet("background-color: transparent;") # Make main widget transparent
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(15)

        # Main Title for the Gamification Section
        section_title_label = QLabel("Your Journey")
        section_title_font = QFont("Arial", 16, QFont.Bold)
        section_title_label.setFont(section_title_font)
        section_title_label.setStyleSheet("color: #D8DEE9; padding-bottom: 5px;") # Nord Snow Storm - gray
        section_title_label.setAlignment(Qt.AlignCenter)
        # main_layout.addWidget(section_title_label)

        # --- Level and XP Card ---
        progression_card = GamificationCard("Progression", "⭐") # Icon for level/XP
        progression_content_layout = QVBoxLayout()
        progression_content_layout.setSpacing(6)

        self.level_label = QLabel("Level: 1")
        self.level_label.setFont(QFont("Arial", 14, QFont.Bold))
        self.level_label.setStyleSheet("color: #A3BE8C;") # Nord Frost - green for positive/level

        xp_layout = QHBoxLayout()
        self.xp_label = QLabel("XP: 0 / 100")
        self.xp_label.setStyleSheet("color: #E5E9F0;") # Nord Snow Storm - light gray
        self.xp_bar = QProgressBar()
        self.xp_bar.setRange(0, 100)
        self.xp_bar.setValue(0)
        self.xp_bar.setTextVisible(False)
        self.xp_bar.setFixedHeight(12)
        self.xp_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #4C566A; /* Nord Polar Night - lighter for contrast */
                border-radius: 6px;
                background-color: #3B4252; /* Nord Polar Night - base */
            }
            QProgressBar::chunk {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #81A1C1, stop:1 #88C0D0 ); /* Nord Frost - blue to cyan gradient */
                border-radius: 5px;
            }
        """)
        xp_layout.addWidget(self.xp_label, 1)
        xp_layout.addWidget(self.xp_bar, 2)

        progression_content_layout.addWidget(self.level_label)
        progression_content_layout.addLayout(xp_layout)
        progression_card.addContentLayout(progression_content_layout)
        main_layout.addWidget(progression_card)

        # --- Active Quests Card ---
        quests_card = GamificationCard("Active Quests", "📜") # Icon for quests
        quests_content_layout = QVBoxLayout()
        quests_content_layout.setSpacing(5)
        
        self.quests_summary_label = QLabel("Dailies:\n- Complete 5 laps (0/5)\n- Set a PB at Monza (No)\n\nWeeklies:\n- Drive 50km (0/50)")
        self.quests_summary_label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.quests_summary_label.setStyleSheet("color: #D8DEE9; font-size: 9pt; line-height: 150%;")
        self.quests_summary_label.setWordWrap(True)
        
        # Placeholder for a "View All Quests" button
        view_quests_button = QPushButton("View All Quests →")
        view_quests_button.setStyleSheet("""QPushButton {
            color: #88C0D0; 
            background-color: transparent; 
            border: none; 
            text-align: right;
            font-size: 9pt;
        }
        QPushButton:hover { color: #ECEFF4; }""")
        view_quests_button.setCursor(Qt.PointingHandCursor)
        view_quests_button.clicked.connect(self.show_all_quests_view)
        
        quests_content_layout.addWidget(self.quests_summary_label)
        quests_content_layout.addWidget(view_quests_button, 0, Qt.AlignRight)
        quests_card.addContentLayout(quests_content_layout)
        main_layout.addWidget(quests_card)

        # --- Race Pass Card ---
        race_pass_card = GamificationCard("Race Pass", "🎟️") # Icon for race pass
        race_pass_content_layout = QVBoxLayout()
        race_pass_content_layout.setSpacing(6)
        
        self.race_pass_title_label = QLabel("Season 1: Genesis")
        self.race_pass_title_label.setFont(QFont("Arial", 12, QFont.Bold))
        self.race_pass_title_label.setStyleSheet("color: #EBCB8B;") # Nord Aurora - yellow for emphasis

        self.race_pass_tier_label = QLabel("Tier: 1 / 50")
        self.race_pass_tier_label.setStyleSheet("color: #E5E9F0;")

        self.race_pass_progress_bar = QProgressBar()
        self.race_pass_progress_bar.setRange(0, 1000) 
        self.race_pass_progress_bar.setValue(50)
        self.race_pass_progress_bar.setTextVisible(True)
        self.race_pass_progress_bar.setFormat("%v / %m Season XP")
        self.race_pass_progress_bar.setFixedHeight(16)
        self.race_pass_progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #4C566A;
                border-radius: 8px;
                background-color: #3B4252;
                color: #ECEFF4;
                text-align: center;
                font-weight: bold;
                font-size: 9pt;
            }
            QProgressBar::chunk {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #BF616A, stop:1 #D08770); /* Nord Aurora - red to orange gradient */
                border-radius: 7px;
            }
        """)
        
        # Placeholder for a "View Race Pass" button
        view_pass_button = QPushButton("View Full Pass →")
        view_pass_button.setStyleSheet("""QPushButton {
            color: #88C0D0; 
            background-color: transparent; 
            border: none; 
            text-align: right;
            font-size: 9pt;
        }
        QPushButton:hover { color: #ECEFF4; }""")
        view_pass_button.setCursor(Qt.PointingHandCursor)
        view_pass_button.clicked.connect(self.show_race_pass_view)

        race_pass_content_layout.addWidget(self.race_pass_title_label)
        race_pass_content_layout.addWidget(self.race_pass_tier_label)
        race_pass_content_layout.addWidget(self.race_pass_progress_bar)
        race_pass_content_layout.addWidget(view_pass_button, 0, Qt.AlignRight)
        race_pass_card.addContentLayout(race_pass_content_layout)
        main_layout.addWidget(race_pass_card)
        
        main_layout.addStretch(1) 

    def update_level_xp(self, level, current_xp, needed_xp):
        self.level_label.setText(f"Level: {level}")
        self.xp_label.setText(f"XP: {current_xp} / {needed_xp}")
        if needed_xp > 0 : self.xp_bar.setMaximum(needed_xp)
        else: self.xp_bar.setMaximum(1) # Avoid division by zero or invalid range
        self.xp_bar.setValue(current_xp)

    def update_quests_summary(self, quest_text):
        self.quests_summary_label.setText(quest_text)

    def update_race_pass_summary(self, season_name, current_tier, current_season_xp, needed_season_xp, total_season_xp):
        self.race_pass_title_label.setText(season_name)
        self.race_pass_tier_label.setText(f"Current Tier: {current_tier}")
        
        progress_pct = (current_season_xp / total_season_xp) * 100 if total_season_xp > 0 else 0
        tier_progress = (current_season_xp / needed_season_xp) * 100 if needed_season_xp > 0 else 0
        
        self.race_pass_progress_bar.setValue(int(tier_progress))
        self.race_pass_progress_bar.setFormat(f"{current_season_xp} / {needed_season_xp} Season XP")

    def show_all_quests_view(self):
        print("GamificationOverviewWidget: Opening Quest window")
        
        # Find the main window and use its show_quest_dialog method if available
        main_window = self.window()
        if main_window and hasattr(main_window, 'show_quest_dialog'):
            # Call the method that the menu item would use
            main_window.show_quest_dialog()
        else:
            # Fallback implementation if we can't find the main window method
            from .quest_view import QuestViewWidget
            if not hasattr(self, 'quest_view_window') or not self.quest_view_window.isVisible():
                # Create a parent widget to serve as a dialog container
                from PyQt5.QtWidgets import QDialog, QVBoxLayout
                dialog = QDialog(main_window)  # Make dialog a child of the main window
                dialog.setWindowTitle("Quests")
                dialog.setMinimumSize(600, 500)
                dialog_layout = QVBoxLayout(dialog)
                dialog_layout.setContentsMargins(0, 0, 0, 0)
                
                # Create quest view widget with the dialog as its parent
                quest_view = QuestViewWidget(dialog)
                dialog_layout.addWidget(quest_view)
                
                # Store references for later use
                self.quest_view_window = dialog
                self.quest_view_widget = quest_view
                
                # Connect the claim signals to update XP
                quest_view.quest_claimed.connect(self.on_quest_claimed)
                
                dialog.show()
            else:
                self.quest_view_window.activateWindow()  # Bring to front if already open
                
    def on_quest_claimed(self, quest_title, xp_reward):
        """Update UI when a quest is claimed and XP is awarded"""
        print(f"Quest claimed: {quest_title}, +{xp_reward} XP")
        
        # Get current level and XP values
        current_level_text = self.level_label.text()
        current_level = int(current_level_text.split(": ")[1]) if ": " in current_level_text else 1
        
        current_xp_text = self.xp_label.text()
        current_xp_parts = current_xp_text.split(": ")[1].split(" / ") if ": " in current_xp_text else ["0", "100"]
        current_xp = int(current_xp_parts[0])
        needed_xp = int(current_xp_parts[1])
        
        # Add the new XP
        new_xp = current_xp + xp_reward
        
        # Check for level up
        if new_xp >= needed_xp:
            # Simple level up logic - in a real app this would be handled by the backend
            new_level = current_level + 1
            new_xp = new_xp - needed_xp
            new_needed_xp = needed_xp + 100  # Simple progression
            
            # Update the display
            self.update_level_xp(new_level, new_xp, new_needed_xp)
            
            # Show level up notification
            # In real implementation, call notification manager
            print(f"LEVEL UP! Now level {new_level}")
            
            # Try to use notification system if available
            try:
                from trackpro.gamification.ui.notifications import show_level_up_notification
                main_window = self.window()
                if main_window and hasattr(show_level_up_notification, '__call__'):
                    show_level_up_notification(main_window, new_level)
            except Exception as e:
                print(f"Could not show level up notification: {e}")
        else:
            # Just update the XP
            self.update_level_xp(current_level, new_xp, needed_xp)
        
        # Show claimed notification
        try:
            from trackpro.gamification.ui.notifications import show_quest_completed_notification
            main_window = self.window()
            if main_window and hasattr(show_quest_completed_notification, '__call__'):
                show_quest_completed_notification(main_window, quest_title, xp_reward)
        except Exception as e:
            print(f"Could not show quest notification: {e}")

    def show_race_pass_view(self):
        print("GamificationOverviewWidget: Opening Race Pass window")
        
        # Find the main window and use its show_race_pass_dialog method
        main_window = self.window()
        if main_window and hasattr(main_window, 'show_race_pass_dialog'):
            # Call the same method that the menu item uses
            main_window.show_race_pass_dialog()
        else:
            # Fallback to the original implementation if we can't find the main window
            if not hasattr(self, 'race_pass_window_instance') or not self.race_pass_window_instance.isVisible():
                self.race_pass_window_instance = RacePassViewWidget(None) # No parent to make it a top-level window
                self.race_pass_window_instance.setWindowTitle("Race Pass Details")
                self.race_pass_window_instance.setGeometry(150, 150, 700, 800) # Example position and size
                self.race_pass_window_instance.show()
            else:
                self.race_pass_window_instance.activateWindow() # Bring to front if already open

# Example usage (for testing standalone)
if __name__ == '__main__':
    import sys
    from PyQt5.QtWidgets import QApplication, QMainWindow

    app = QApplication(sys.argv)
    app.setStyle("Fusion") # Fusion often looks better than default on some systems
    
    # Apply a Nord-like palette for testing
    nord_palette = QPalette()
    nord_palette.setColor(QPalette.Window, QColor("#2E3440")) # Dark base
    nord_palette.setColor(QPalette.WindowText, QColor("#D8DEE9")) # Light text
    nord_palette.setColor(QPalette.Base, QColor("#3B4252")) # Slightly lighter base for inputs
    nord_palette.setColor(QPalette.AlternateBase, QColor("#434C5E"))
    nord_palette.setColor(QPalette.ToolTipBase, QColor("#2E3440"))
    nord_palette.setColor(QPalette.ToolTipText, QColor("#D8DEE9"))
    nord_palette.setColor(QPalette.Text, QColor("#D8DEE9"))
    nord_palette.setColor(QPalette.Button, QColor("#4C566A"))
    nord_palette.setColor(QPalette.ButtonText, QColor("#ECEFF4"))
    nord_palette.setColor(QPalette.BrightText, QColor("#BF616A")) # Red for alerts
    nord_palette.setColor(QPalette.Link, QColor("#88C0D0"))
    nord_palette.setColor(QPalette.Highlight, QColor("#5E81AC")) # Blue for selection
    nord_palette.setColor(QPalette.HighlightedText, QColor("#ECEFF4"))
    app.setPalette(nord_palette)

    main_window = QMainWindow()
    gamification_widget = GamificationOverviewWidget()
    main_window.setCentralWidget(gamification_widget)
    main_window.setWindowTitle("Gamification Overview (Nord Style Test)")
    main_window.setGeometry(100, 100, 450, 650) # Adjusted size for better view
    
    # Example updates
    gamification_widget.update_level_xp(7, 1250, 2000)
    gamification_widget.update_quests_summary("Dailies:\n- Drive 25km (15/25)\n- Achieve 3 Clean Laps at Monza (1/3)\n\nWeeklies:\n- Complete 5 Online Races (2/5)\n- Earn 1000 Season XP (350/1000)")
    gamification_widget.update_race_pass_summary("Season One: Ignition Point", 12, 450, 1000, 1000)
    
    main_window.show()
    sys.exit(app.exec_()) 