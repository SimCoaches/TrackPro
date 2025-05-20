from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QScrollArea, QFrame, QGridLayout, 
                             QProgressBar, QGroupBox)
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QFont, QColor, QPalette, QPixmap, QPainter

class RacePassViewWidget(QWidget):
    """Dedicated widget to display the full Race Pass track (Free/Premium)."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("RacePassViewWidget")
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(10)

        # Title
        title_label = QLabel("Race Pass - Season 1: Genesis") # Placeholder Title
        title_font = QFont("Arial", 16, QFont.Bold)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title_label)

        # Season Info / Purchase Button
        header_layout = QHBoxLayout()
        self.season_progress_label = QLabel("Your Tier: 5 / 50 | Ends in: 28 days")
        self.season_progress_label.setStyleSheet("color: #DDD; font-size: 11pt;")
        self.purchase_pass_button = QPushButton("Unlock Premium Pass")
        self.purchase_pass_button.setStyleSheet("padding: 8px 15px; background-color: #e67e22; color: white; border-radius: 5px; font-weight: bold;")
        self.purchase_pass_button.setCursor(Qt.PointingHandCursor)
        self.purchase_pass_button.clicked.connect(self.on_purchase_pass)
        header_layout.addWidget(self.season_progress_label)
        header_layout.addStretch()
        header_layout.addWidget(self.purchase_pass_button)
        main_layout.addLayout(header_layout)

        # Scroll Area for Tiers
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("QScrollArea { border: none; background-color: transparent; }")
        
        self.tiers_container = QWidget()
        self.tiers_layout = QVBoxLayout(self.tiers_container) # Use QVBoxLayout for vertical tier list
        self.tiers_layout.setContentsMargins(0, 10, 0, 10)
        self.tiers_layout.setSpacing(10)
        
        scroll_area.setWidget(self.tiers_container)
        main_layout.addWidget(scroll_area)

        # Placeholder data loading
        self._load_placeholder_tiers(50, current_tier=5, premium_active=False)

    def _load_placeholder_tiers(self, num_tiers, current_tier=0, premium_active=False):
        """Populates the tiers view with placeholder data."""
        # Clear existing tiers
        while self.tiers_layout.count():
            child = self.tiers_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        for i in range(1, num_tiers + 1):
            unlocked = i <= current_tier
            # Example reward data - in a real app, this would come from the backend
            free_reward = {"name": f"Free Reward Tier {i}", "type": "XP Boost", "rarity": "common"}
            premium_reward = {"name": f"Premium Item Tier {i}", "type": "Cosmetic", "rarity": "rare"} if i % 3 == 0 else None

            tier_widget = self._create_tier_widget(i, free_reward, premium_reward, unlocked, premium_active)
            self.tiers_layout.addWidget(tier_widget)
        
        self.tiers_layout.addStretch()

    def _create_tier_widget(self, tier_num, free_reward, premium_reward, unlocked, premium_active):
        """Creates a widget for a single tier in the Race Pass."""
        tier_frame = QFrame()
        tier_frame.setObjectName(f"TierFrame{tier_num}")
        tier_frame.setFrameShape(QFrame.StyledPanel)
        tier_frame.setFrameShadow(QFrame.Raised)
        base_style = "border-radius: 8px; padding: 10px;" 
        if unlocked:
            tier_frame.setStyleSheet(f"background-color: #3a3a3a; {base_style}")
        else:
            tier_frame.setStyleSheet(f"background-color: #2c2c2c; {base_style}")

        layout = QHBoxLayout(tier_frame)
        layout.setSpacing(15)

        tier_label = QLabel(f"Tier\n{tier_num}")
        tier_label.setFont(QFont("Arial", 12, QFont.Bold))
        tier_label.setAlignment(Qt.AlignCenter)
        tier_label.setFixedWidth(60)
        if unlocked: tier_label.setStyleSheet("color: #e67e22;")

        layout.addWidget(tier_label)
        layout.addWidget(self._create_reward_display("Free", free_reward, unlocked, False), 1)
        
        if premium_reward:
            separator = QFrame()
            separator.setFrameShape(QFrame.VLine)
            separator.setFrameShadow(QFrame.Sunken)
            separator.setStyleSheet("color: #555;")
            layout.addWidget(separator)
            layout.addWidget(self._create_reward_display("Premium", premium_reward, unlocked and premium_active, True, premium_active), 1)
        else:
            layout.addStretch(1) # Add stretch if no premium reward to balance

        return tier_frame

    def _create_reward_display(self, track_type, reward_data, is_unlocked, is_premium, premium_active=False):
        """Creates a display for a single reward (free or premium)."""
        reward_widget = QWidget()
        reward_layout = QVBoxLayout(reward_widget)
        reward_layout.setContentsMargins(0,0,0,0)
        reward_layout.setSpacing(3)

        track_label_text = track_type
        track_label_style = "font-size: 9pt; color: #999;"
        if is_premium and not premium_active:
            track_label_text += " (Locked)"
            track_label_style = "font-size: 9pt; color: #777;"
        elif is_premium and premium_active:
            track_label_style = "font-size: 9pt; color: #DAA520; font-weight: bold;"
        
        track_label = QLabel(track_label_text)
        track_label.setStyleSheet(track_label_style)

        reward_name = QLabel(reward_data["name"])
        reward_name.setFont(QFont("Arial", 10, QFont.Bold))
        
        reward_type = QLabel(f"Type: {reward_data["type"]} ({reward_data["rarity"]})")
        reward_type.setStyleSheet("font-size: 8pt; color: #AAA;")

        if not is_unlocked and not (is_premium and premium_active):
            reward_name.setStyleSheet("color: #777; font-weight: bold;")
            reward_type.setStyleSheet("font-size: 8pt; color: #666;")
        elif is_unlocked :
             reward_name.setStyleSheet("color: white; font-weight: bold;")

        reward_layout.addWidget(track_label)
        reward_layout.addWidget(reward_name)
        reward_layout.addWidget(reward_type)
        reward_layout.addStretch()
        
        return reward_widget

    def update_race_pass_data(self, season_info, tiers_data, user_progress):
        """
        Updates the entire Race Pass view with new data.
        season_info: dict { name, ends_in_days }
        tiers_data: list of dicts { tier_num, free_reward, premium_reward }
        user_progress: dict { current_tier, is_premium_active }
        """
        self.title_label.setText(f"Race Pass - {season_info.get('name', 'Current Season')}")
        self.season_progress_label.setText(f"Your Tier: {user_progress.get('current_tier', 0)} / {len(tiers_data)} | Ends in: {season_info.get('ends_in_days', '?')} days")
        
        if user_progress.get('is_premium_active', False):
            self.purchase_pass_button.setText("Premium Pass Active")
            self.purchase_pass_button.setEnabled(False)
            self.purchase_pass_button.setStyleSheet("padding: 8px 15px; background-color: #27ae60; color: white; border-radius: 5px; font-weight: bold;")
        else:
            self.purchase_pass_button.setText("Unlock Premium Pass")
            self.purchase_pass_button.setEnabled(True)
            self.purchase_pass_button.setStyleSheet("padding: 8px 15px; background-color: #e67e22; color: white; border-radius: 5px; font-weight: bold;")

        # Clear existing tiers
        while self.tiers_layout.count():
            child = self.tiers_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        current_tier = user_progress.get('current_tier', 0)
        premium_active = user_progress.get('is_premium_active', False)

        for tier_data in tiers_data:
            tier_num = tier_data['tier_num']
            unlocked = tier_num <= current_tier
            tier_widget = self._create_tier_widget(
                tier_num,
                tier_data['free_reward'],
                tier_data.get('premium_reward'), # Optional
                unlocked,
                premium_active
            )
            self.tiers_layout.addWidget(tier_widget)
        self.tiers_layout.addStretch()

    def on_purchase_pass(self):
        print("Purchase Pass button clicked!")
        # Add logic to handle pass purchase - e.g., open a dialog, call backend
        # For now, let's simulate unlocking it:
        self.purchase_pass_button.setText("Premium Pass Active")
        self.purchase_pass_button.setEnabled(False)
        self.purchase_pass_button.setStyleSheet("padding: 8px 15px; background-color: #27ae60; color: white; border-radius: 5px; font-weight: bold;")
        # Re-render tiers with premium active
        current_tier = int(self.season_progress_label.text().split("Your Tier: ")[1].split(" / ")[0])
        num_tiers = int(self.season_progress_label.text().split(" / ")[1].split(" | ")[0])
        self._load_placeholder_tiers(num_tiers, current_tier, premium_active=True)


# Example usage (for testing standalone)
if __name__ == '__main__':
    import sys

    app = QApplication(sys.argv)
    # Set a dark theme for testing
    app.setStyle("Fusion")
    dark_palette = QPalette()
    dark_palette.setColor(QPalette.Window, QColor(53, 53, 53))
    dark_palette.setColor(QPalette.WindowText, Qt.white)
    dark_palette.setColor(QPalette.Base, QColor(42, 42, 42))
    dark_palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
    # ... (add other palette colors as needed for a full dark theme)
    app.setPalette(dark_palette)

    main_window = QMainWindow()
    race_pass_view = RacePassViewWidget()
    main_window.setCentralWidget(race_pass_view)
    main_window.setWindowTitle("Race Pass View Test")
    main_window.setGeometry(100, 100, 700, 800)
    main_window.show()

    # Example of updating with more structured data
    # season_info_data = {"name": "Season Alpha Test", "ends_in_days": 15}
    # tiers_list_data = []
    # for i in range(1, 26):
    #     tiers_list_data.append({
    #         "tier_num": i,
    #         "free_reward": {"name": f"Free Item S-Alpha {i}", "type": "Currency", "rarity": "common"},
    #         "premium_reward": {"name": f"Alpha Skin {i}", "type": "Car Decal", "rarity": "epic"} if i % 2 == 0 else None
    #     })
    # user_progress_data = {"current_tier": 7, "is_premium_active": False}
    # race_pass_view.update_race_pass_data(season_info_data, tiers_list_data, user_progress_data)

    sys.exit(app.exec_()) 