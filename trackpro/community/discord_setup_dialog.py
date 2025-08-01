"""Discord Setup Dialog for TrackPro - Configure Discord server connection."""

import logging
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, 
                             QLineEdit, QPushButton, QLabel, QTextEdit, QCheckBox,
                             QMessageBox, QFrame, QTabWidget, QWidget, QDialogButtonBox)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont, QPixmap, QIcon
import requests
import json
import re

logger = logging.getLogger(__name__)

class DiscordServerValidator(QThread):
    """Thread to validate Discord server ID and fetch server info."""
    
    validation_complete = pyqtSignal(bool, dict)  # success, server_info
    
    def __init__(self, server_id):
        super().__init__()
        self.server_id = server_id
    
    def run(self):
        """Validate the Discord server ID."""
        try:
            # Use Discord widget API to validate server
            url = f"https://discord.com/api/guilds/{self.server_id}/widget.json"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                server_info = response.json()
                self.validation_complete.emit(True, server_info)
            else:
                self.validation_complete.emit(False, {})
                
        except Exception as e:
            logger.error(f"Error validating Discord server: {e}")
            self.validation_complete.emit(False, {})

class DiscordSetupDialog(QDialog):
    """Setup dialog for configuring Discord integration."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.server_id = ""
        self.channel_id = ""
        self.server_info = {}
        self.validator_thread = None
        self.use_widget_mode = True  # Default to widget mode
        
        self.setWindowTitle("Discord Integration Setup")
        self.setFixedSize(600, 500)
        self.setModal(True)
        
        self.setup_ui()
        self.load_existing_config()
    
    def setup_ui(self):
        """Set up the user interface."""
        layout = QVBoxLayout(self)
        
        # Header
        header = self.create_header()
        layout.addWidget(header)
        
        # Tabs for different setup methods
        self.tab_widget = QTabWidget()
        
        # Easy setup tab
        easy_tab = self.create_easy_setup_tab()
        self.tab_widget.addTab(easy_tab, "Easy Setup")
        
        # Manual setup tab
        manual_tab = self.create_manual_setup_tab()
        self.tab_widget.addTab(manual_tab, "Manual Setup")
        
        # Instructions tab
        instructions_tab = self.create_instructions_tab()
        self.tab_widget.addTab(instructions_tab, "Instructions")
        
        layout.addWidget(self.tab_widget)
        
        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept_setup)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
    
    def create_header(self) -> QWidget:
        """Create the header with Discord branding."""
        header = QFrame()
        header.setStyleSheet("""
            QFrame {
                background-color: #7289DA;
                border-radius: 8px;
                padding: 10px;
            }
            QLabel {
                color: white;
            }
        """)
        
        layout = QVBoxLayout(header)
        
        title = QLabel("Discord Integration Setup")
        title.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        subtitle = QLabel("Connect your Discord server to TrackPro")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle)
        
        return header
    
    def create_easy_setup_tab(self) -> QWidget:
        """Create the easy setup tab with Discord invite link parsing."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Instructions
        instructions = QLabel("""
<b>Easy Setup:</b><br>
1. Copy a Discord invite link to your server<br>
2. Paste it below and we'll extract the server information<br>
3. Make sure your server has widgets enabled in Server Settings → Widget
        """)
        instructions.setWordWrap(True)
        layout.addWidget(instructions)
        
        # Invite link input
        form_layout = QFormLayout()
        
        self.invite_input = QLineEdit()
        self.invite_input.setPlaceholderText("https://discord.gg/your-invite-code")
        self.invite_input.textChanged.connect(self.parse_invite_link)
        form_layout.addRow("Discord Invite Link:", self.invite_input)
        
        # Server info display
        self.server_info_label = QLabel("Paste an invite link to see server information")
        self.server_info_label.setStyleSheet("""
            QLabel {
                background-color: #f0f0f0;
                border: 1px solid #ccc;
                border-radius: 4px;
                padding: 10px;
                min-height: 80px;
            }
        """)
        self.server_info_label.setWordWrap(True)
        form_layout.addRow("Server Info:", self.server_info_label)
        
        layout.addLayout(form_layout)
        
        # Validate button
        self.validate_btn = QPushButton("Validate Server")
        self.validate_btn.clicked.connect(self.validate_server)
        self.validate_btn.setEnabled(False)
        layout.addWidget(self.validate_btn)
        
        # Mode selection for easy setup too
        mode_frame = QFrame()
        mode_frame.setStyleSheet("QFrame { border: 1px solid #ddd; border-radius: 4px; padding: 8px; }")
        mode_layout = QVBoxLayout(mode_frame)
        
        mode_title = QLabel("<b>Choose Integration Mode:</b>")
        mode_layout.addWidget(mode_title)
        
        self.easy_widget_mode_cb = QCheckBox("Widget Mode - View-only, lightweight")
        self.easy_widget_mode_cb.setChecked(True)
        mode_layout.addWidget(self.easy_widget_mode_cb)
        
        self.easy_webapp_mode_cb = QCheckBox("Web App Mode - Full Discord functionality")
        self.easy_webapp_mode_cb.setChecked(False)
        mode_layout.addWidget(self.easy_webapp_mode_cb)
        
        # Make mutually exclusive
        self.easy_widget_mode_cb.toggled.connect(lambda checked: self.easy_webapp_mode_cb.setChecked(not checked) if checked else None)
        self.easy_webapp_mode_cb.toggled.connect(lambda checked: self.easy_widget_mode_cb.setChecked(not checked) if checked else None)
        
        layout.addWidget(mode_frame)
        layout.addStretch()
        
        return widget
    
    def create_manual_setup_tab(self) -> QWidget:
        """Create the manual setup tab for advanced users."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Instructions
        instructions = QLabel("""
<b>Manual Setup:</b><br>
For advanced users who know their Discord server ID directly.
        """)
        instructions.setWordWrap(True)
        layout.addWidget(instructions)
        
        # Manual input form
        form_layout = QFormLayout()
        
        self.server_id_input = QLineEdit()
        self.server_id_input.setPlaceholderText("123456789012345678")
        self.server_id_input.textChanged.connect(self.manual_server_id_changed)
        form_layout.addRow("Server ID:", self.server_id_input)
        
        self.channel_id_input = QLineEdit()
        self.channel_id_input.setPlaceholderText("123456789012345678 (optional)")
        form_layout.addRow("Default Channel ID:", self.channel_id_input)
        
        layout.addLayout(form_layout)
        
        # Mode selection
        mode_label = QLabel("<b>Integration Mode:</b>")
        layout.addWidget(mode_label)
        
        self.widget_mode_cb = QCheckBox("Widget Mode (lightweight, read-only)")
        self.widget_mode_cb.setChecked(True)
        self.widget_mode_cb.setToolTip("View messages and members, but cannot send messages. Lightweight and fast.")
        layout.addWidget(self.widget_mode_cb)
        
        self.webapp_mode_cb = QCheckBox("Web App Mode (full functionality)")
        self.webapp_mode_cb.setChecked(False)
        self.webapp_mode_cb.setToolTip("Complete Discord experience with messaging and voice chat. Requires Discord login.")
        layout.addWidget(self.webapp_mode_cb)
        
        # Make checkboxes mutually exclusive
        self.widget_mode_cb.toggled.connect(lambda checked: self.webapp_mode_cb.setChecked(not checked) if checked else None)
        self.webapp_mode_cb.toggled.connect(lambda checked: self.widget_mode_cb.setChecked(not checked) if checked else None)
        
        self.auto_connect_cb = QCheckBox("Auto-connect on startup")
        self.auto_connect_cb.setChecked(True)
        layout.addWidget(self.auto_connect_cb)
        
        layout.addStretch()
        
        return widget
    
    def create_instructions_tab(self) -> QWidget:
        """Create the instructions tab with detailed help."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        instructions_text = QTextEdit()
        instructions_text.setReadOnly(True)
        instructions_text.setHtml("""
<h3>Discord Integration Instructions</h3>

<h4>What you need:</h4>
<ul>
<li>Admin access to your Discord server</li>
<li>Server widgets enabled</li>
<li>A Discord invite link or server ID</li>
</ul>

<h4>How to enable widgets:</h4>
<ol>
<li>Go to your Discord server</li>
<li>Click on the server name → Server Settings</li>
<li>Go to Widget in the left sidebar</li>
<li>Toggle "Enable Server Widget" ON</li>
<li>Choose an invite channel (recommended: general chat)</li>
<li>Save changes</li>
</ol>

<h4>Getting your server ID:</h4>
<ol>
<li>Enable Developer Mode: User Settings → Advanced → Developer Mode</li>
<li>Right-click your server name</li>
<li>Click "Copy Server ID"</li>
</ol>

<h4>Two integration modes:</h4>
<p><b>Widget Mode:</b> Uses Discord's widget system. Limited to viewing messages and member lists. No voice chat.</p>
<p><b>Web App Mode:</b> Embeds full Discord web application. Full functionality including voice chat, but requires Discord login.</p>

<h4>Privacy & Security:</h4>
<p>This integration only connects to Discord's public APIs and your configured server. No TrackPro data is sent to Discord except for standard web requests.</p>
        """)
        layout.addWidget(instructions_text)
        
        return widget
    
    def parse_invite_link(self, link_text):
        """Parse Discord invite link to extract server information."""
        # Clear previous info
        self.server_info_label.setText("Parsing invite link...")
        self.validate_btn.setEnabled(False)
        
        if not link_text.strip():
            self.server_info_label.setText("Paste an invite link to see server information")
            return
        
        # Extract invite code from various Discord URL formats
        invite_patterns = [
            r'discord\.gg/([a-zA-Z0-9]+)',
            r'discord\.com/invite/([a-zA-Z0-9]+)',
            r'discordapp\.com/invite/([a-zA-Z0-9]+)'
        ]
        
        invite_code = None
        for pattern in invite_patterns:
            match = re.search(pattern, link_text)
            if match:
                invite_code = match.group(1)
                break
        
        if not invite_code:
            self.server_info_label.setText("❌ Invalid Discord invite link format")
            return
        
        # Fetch invite information
        self.fetch_invite_info(invite_code)
    
    def fetch_invite_info(self, invite_code):
        """Fetch invite information from Discord API."""
        try:
            url = f"https://discord.com/api/v9/invites/{invite_code}?with_counts=true"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                invite_data = response.json()
                guild_data = invite_data.get('guild', {})
                
                if guild_data:
                    server_name = guild_data.get('name', 'Unknown Server')
                    server_id = guild_data.get('id', '')
                    member_count = invite_data.get('approximate_member_count', 0)
                    online_count = invite_data.get('approximate_presence_count', 0)
                    
                    info_text = f"""
✅ <b>{server_name}</b><br>
📋 Server ID: {server_id}<br>
👥 Members: {member_count:,}<br>
🟢 Online: {online_count:,}
                    """.strip()
                    
                    self.server_info_label.setText(info_text)
                    self.server_id = server_id
                    self.validate_btn.setEnabled(True)
                else:
                    self.server_info_label.setText("❌ Could not fetch server information")
            else:
                self.server_info_label.setText("❌ Invalid or expired invite link")
                
        except Exception as e:
            logger.error(f"Error fetching invite info: {e}")
            self.server_info_label.setText("❌ Error fetching server information")
    
    def validate_server(self):
        """Validate the Discord server and check widget availability."""
        if not self.server_id:
            QMessageBox.warning(self, "Validation Error", "No server ID to validate")
            return
        
        self.validate_btn.setEnabled(False)
        self.validate_btn.setText("Validating...")
        
        # Start validation thread
        self.validator_thread = DiscordServerValidator(self.server_id)
        self.validator_thread.validation_complete.connect(self.on_validation_complete)
        self.validator_thread.start()
    
    def on_validation_complete(self, success, server_info):
        """Handle validation completion."""
        self.validate_btn.setEnabled(True)
        self.validate_btn.setText("Validate Server")
        
        if success:
            server_name = server_info.get('name', 'Unknown Server')
            member_count = len(server_info.get('members', []))
            
            QMessageBox.information(self, "Validation Success", 
                                  f"✅ Server '{server_name}' validated successfully!\n"
                                  f"Members visible: {member_count}\n"
                                  f"Widget is properly configured.")
            
            self.server_info = server_info
        else:
            QMessageBox.warning(self, "Validation Failed", 
                              "❌ Could not validate server.\n\n"
                              "Please check:\n"
                              "• Server widgets are enabled\n"
                              "• Server ID is correct\n"
                              "• You have proper permissions")
    
    def manual_server_id_changed(self, server_id):
        """Handle manual server ID input change."""
        self.server_id = server_id.strip()
    
    def load_existing_config(self):
        """Load existing Discord configuration if available."""
        try:
            import os
            config_path = os.path.join(os.path.dirname(__file__), "discord_config.json")
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    config = json.load(f)
                    
                existing_server_id = config.get('server_id', '')
                existing_channel_id = config.get('channel_id', '')
                
                if existing_server_id:
                    self.server_id_input.setText(existing_server_id)
                    self.server_id = existing_server_id
                    
                if existing_channel_id:
                    self.channel_id_input.setText(existing_channel_id)
                    self.channel_id = existing_channel_id
                    
        except Exception as e:
            logger.error(f"Error loading existing config: {e}")
    
    def accept_setup(self):
        """Accept the setup and validate inputs."""
        # Get values from current tab
        current_tab = self.tab_widget.currentIndex()
        
        if current_tab == 0:  # Easy setup
            if not self.server_id:
                QMessageBox.warning(self, "Setup Error", 
                                  "Please enter a Discord invite link and validate the server.")
                return
            # Use mode selection from easy setup
            self.use_widget_mode = self.easy_widget_mode_cb.isChecked()
        elif current_tab == 1:  # Manual setup
            self.server_id = self.server_id_input.text().strip()
            self.channel_id = self.channel_id_input.text().strip()
            
            if not self.server_id:
                QMessageBox.warning(self, "Setup Error", 
                                  "Please enter a Discord server ID.")
                return
            
            # Store mode preference
            self.use_widget_mode = self.widget_mode_cb.isChecked()
        
        # Validate server ID format (Discord snowflake - 17-19 digits)
        if not re.match(r'^\d{17,19}$', self.server_id):
            QMessageBox.warning(self, "Setup Error", 
                              "Invalid server ID format. Discord server IDs are 17-19 digits.")
            return
        
        self.accept()

# Example usage and testing
if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    dialog = DiscordSetupDialog()
    
    if dialog.exec() == QDialog.DialogCode.Accepted:
        print(f"Server ID: {dialog.server_id}")
        print(f"Channel ID: {dialog.channel_id}")
    
    sys.exit() 