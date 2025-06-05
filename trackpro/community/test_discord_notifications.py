#!/usr/bin/env python3
"""
Test script for Discord notification system in TrackPro Community.

This script can be used to test the Discord notification functionality
without needing real Discord messages.
"""

import sys
import os
import time
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QLabel, QHBoxLayout
from PyQt5.QtCore import QTimer, pyqtSignal

# Add the parent directory to path so we can import the community modules
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

try:
    from community_main_widget import CommunityMainWidget, CommunityNotificationManager
    from discord_integration import DiscordIntegrationWidget
    print("✅ Successfully imported Discord notification modules")
except ImportError as e:
    print(f"❌ Failed to import modules: {e}")
    sys.exit(1)


class DiscordNotificationTester(QMainWindow):
    """Simple test application for Discord notifications."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Discord Notification Tester")
        self.setGeometry(100, 100, 800, 600)
        
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Title
        title = QLabel("Discord Notification System Tester")
        title.setStyleSheet("font-size: 18px; font-weight: bold; margin: 10px;")
        layout.addWidget(title)
        
        # Create notification manager
        self.notification_manager = CommunityNotificationManager()
        self.notification_manager.notification_updated.connect(self.on_notification_updated)
        self.notification_manager.total_notifications_updated.connect(self.on_total_updated)
        
        # Status display
        self.status_label = QLabel("Total notifications: 0")
        self.status_label.setStyleSheet("font-size: 14px; margin: 10px;")
        layout.addWidget(self.status_label)
        
        # Individual counters
        counters_layout = QHBoxLayout()
        self.counter_labels = {}
        for section in ["social", "discord", "community", "content", "achievements", "account"]:
            label = QLabel(f"{section}: 0")
            label.setStyleSheet("margin: 5px; padding: 5px; border: 1px solid gray;")
            self.counter_labels[section] = label
            counters_layout.addWidget(label)
        layout.addLayout(counters_layout)
        
        # Test buttons
        buttons_layout = QVBoxLayout()
        
        # Discord simulation buttons
        discord_buttons = QHBoxLayout()
        
        message_btn = QPushButton("Simulate Discord Message")
        message_btn.clicked.connect(self.simulate_discord_message)
        message_btn.setStyleSheet("background-color: #7289DA; color: white; padding: 10px;")
        discord_buttons.addWidget(message_btn)
        
        mention_btn = QPushButton("Simulate Discord Mention")
        mention_btn.clicked.connect(self.simulate_discord_mention)
        mention_btn.setStyleSheet("background-color: #F04747; color: white; padding: 10px;")
        discord_buttons.addWidget(mention_btn)
        
        buttons_layout.addLayout(discord_buttons)
        
        # Other notification buttons
        other_buttons = QHBoxLayout()
        
        social_btn = QPushButton("Add Social Notification")
        social_btn.clicked.connect(self.add_social_notification)
        social_btn.setStyleSheet("background-color: #43B581; color: white; padding: 10px;")
        other_buttons.addWidget(social_btn)
        
        achievement_btn = QPushButton("Add Achievement Notification")
        achievement_btn.clicked.connect(self.add_achievement_notification)
        achievement_btn.setStyleSheet("background-color: #FAA61A; color: white; padding: 10px;")
        other_buttons.addWidget(achievement_btn)
        
        buttons_layout.addLayout(other_buttons)
        
        # Clear buttons
        clear_buttons = QHBoxLayout()
        
        clear_discord_btn = QPushButton("Clear Discord")
        clear_discord_btn.clicked.connect(lambda: self.clear_section("discord"))
        clear_buttons.addWidget(clear_discord_btn)
        
        clear_all_btn = QPushButton("Clear All")
        clear_all_btn.clicked.connect(self.clear_all_notifications)
        clear_all_btn.setStyleSheet("background-color: #36393F; color: white; padding: 10px;")
        clear_buttons.addWidget(clear_all_btn)
        
        buttons_layout.addLayout(clear_buttons)
        layout.addLayout(buttons_layout)
        
        # Auto-simulation controls
        auto_layout = QHBoxLayout()
        
        self.auto_timer = QTimer()
        self.auto_timer.timeout.connect(self.auto_simulate)
        
        start_auto_btn = QPushButton("Start Auto-Simulation")
        start_auto_btn.clicked.connect(self.start_auto_simulation)
        start_auto_btn.setStyleSheet("background-color: #2ECC71; color: white; padding: 8px;")
        auto_layout.addWidget(start_auto_btn)
        
        stop_auto_btn = QPushButton("Stop Auto-Simulation")
        stop_auto_btn.clicked.connect(self.stop_auto_simulation)
        stop_auto_btn.setStyleSheet("background-color: #E74C3C; color: white; padding: 8px;")
        auto_layout.addWidget(stop_auto_btn)
        
        buttons_layout.addLayout(auto_layout)
        
        # Log area
        self.log_label = QLabel("Notification Log:")
        self.log_label.setStyleSheet("font-weight: bold; margin-top: 20px;")
        layout.addWidget(self.log_label)
        
        self.log_text = QLabel("Ready to test notifications...")
        self.log_text.setStyleSheet("border: 1px solid gray; padding: 10px; background-color: #f8f8f8; min-height: 100px;")
        self.log_text.setWordWrap(True)
        layout.addWidget(self.log_text)
        
        # Instructions
        instructions = QLabel(
            "Instructions:\n"
            "1. Click buttons to simulate different types of notifications\n"
            "2. Watch the counters update in real-time\n"
            "3. Use auto-simulation to test continuous notification flow\n"
            "4. This simulates what happens when real Discord messages arrive"
        )
        instructions.setStyleSheet("margin: 10px; font-style: italic; color: #666;")
        layout.addWidget(instructions)
        
        self.log_messages = []
        
    def simulate_discord_message(self):
        """Simulate a Discord message notification."""
        current = self.notification_manager.get_notification_count("discord")
        self.notification_manager.update_notification_count("discord", current + 1)
        self.add_log("📨 Simulated Discord message notification")
        
    def simulate_discord_mention(self):
        """Simulate a Discord mention notification."""
        current = self.notification_manager.get_notification_count("discord")
        self.notification_manager.update_notification_count("discord", current + 2)  # Mentions worth 2
        self.add_log("🔔 Simulated Discord mention notification (worth 2)")
        
    def add_social_notification(self):
        """Add a social notification."""
        current = self.notification_manager.get_notification_count("social")
        self.notification_manager.update_notification_count("social", current + 1)
        self.add_log("👥 Added social notification")
        
    def add_achievement_notification(self):
        """Add an achievement notification."""
        current = self.notification_manager.get_notification_count("achievements")
        self.notification_manager.update_notification_count("achievements", current + 1)
        self.add_log("🏆 Added achievement notification")
        
    def clear_section(self, section):
        """Clear notifications for a specific section."""
        self.notification_manager.clear_notifications(section)
        self.add_log(f"🗑️ Cleared {section} notifications")
        
    def clear_all_notifications(self):
        """Clear all notifications."""
        for section in ["social", "discord", "community", "content", "achievements", "account"]:
            self.notification_manager.clear_notifications(section)
        self.add_log("🗑️ Cleared all notifications")
        
    def start_auto_simulation(self):
        """Start automatic notification simulation."""
        self.auto_timer.start(3000)  # Every 3 seconds
        self.add_log("🔄 Started auto-simulation (every 3 seconds)")
        
    def stop_auto_simulation(self):
        """Stop automatic notification simulation."""
        self.auto_timer.stop()
        self.add_log("⏹️ Stopped auto-simulation")
        
    def auto_simulate(self):
        """Automatically simulate random notifications."""
        import random
        
        notification_types = [
            ("discord", "📨 Auto: Discord message"),
            ("discord", "🔔 Auto: Discord mention", 2),  # Worth 2
            ("social", "👥 Auto: Social notification"),
            ("achievements", "🏆 Auto: Achievement unlocked"),
            ("community", "🏁 Auto: Community update"),
        ]
        
        choice = random.choice(notification_types)
        section = choice[0]
        message = choice[1]
        increment = choice[2] if len(choice) > 2 else 1
        
        current = self.notification_manager.get_notification_count(section)
        self.notification_manager.update_notification_count(section, current + increment)
        self.add_log(message)
        
    def on_notification_updated(self, section_id, count):
        """Handle individual section notification updates."""
        if section_id in self.counter_labels:
            self.counter_labels[section_id].setText(f"{section_id}: {count}")
            
            # Add visual feedback for changes
            label = self.counter_labels[section_id]
            if count > 0:
                label.setStyleSheet("margin: 5px; padding: 5px; border: 2px solid red; background-color: #ffeeee;")
            else:
                label.setStyleSheet("margin: 5px; padding: 5px; border: 1px solid gray;")
        
    def on_total_updated(self, total_count):
        """Handle total notification count updates."""
        self.status_label.setText(f"Total notifications: {total_count}")
        if total_count > 0:
            self.status_label.setStyleSheet("font-size: 14px; margin: 10px; color: red; font-weight: bold;")
        else:
            self.status_label.setStyleSheet("font-size: 14px; margin: 10px;")
            
    def add_log(self, message):
        """Add a message to the log."""
        timestamp = time.strftime("%H:%M:%S")
        log_message = f"[{timestamp}] {message}"
        self.log_messages.append(log_message)
        
        # Keep only last 10 messages
        if len(self.log_messages) > 10:
            self.log_messages = self.log_messages[-10:]
            
        self.log_text.setText("\n".join(self.log_messages))


def main():
    """Run the Discord notification tester."""
    app = QApplication(sys.argv)
    
    # Apply a dark theme
    app.setStyle('Fusion')
    palette = app.palette()
    palette.setColor(palette.Window, palette.color(palette.Base))
    app.setPalette(palette)
    
    tester = DiscordNotificationTester()
    tester.show()
    
    print("🧪 Discord Notification Tester started")
    print("Use the buttons in the window to test different notification types")
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main() 