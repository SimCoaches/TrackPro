"""Discord Integration for TrackPro - Embed Discord server directly in the app."""

import logging
from typing import Optional, Dict, Any
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QLabel, QFrame, QSplitter, QTabWidget, QMessageBox)
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEngineSettings, QWebEnginePage
from PyQt5.QtCore import Qt, QUrl, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QIcon
import json
import os

logger = logging.getLogger(__name__)

class DiscordWebView(QWebEngineView):
    """Custom web view for Discord with enhanced settings and scaling fixes."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_settings()
        self.setup_page()
    
    def setup_settings(self):
        """Configure web engine settings for MAXIMUM performance."""
        settings = self.settings()
        
        # Core settings only for performance
        settings.setAttribute(QWebEngineSettings.JavascriptEnabled, True)
        settings.setAttribute(QWebEngineSettings.LocalStorageEnabled, True)
        
        # DISABLE ALL heavy features for maximum performance
        settings.setAttribute(QWebEngineSettings.WebGLEnabled, False)  
        settings.setAttribute(QWebEngineSettings.Accelerated2dCanvasEnabled, False)  
        settings.setAttribute(QWebEngineSettings.PlaybackRequiresUserGesture, True)  
        settings.setAttribute(QWebEngineSettings.FullScreenSupportEnabled, False)  
        settings.setAttribute(QWebEngineSettings.AllowRunningInsecureContent, False)  
        settings.setAttribute(QWebEngineSettings.PluginsEnabled, False)  
        settings.setAttribute(QWebEngineSettings.DnsPrefetchEnabled, False)  
        settings.setAttribute(QWebEngineSettings.TouchIconsEnabled, False)  
        settings.setAttribute(QWebEngineSettings.FocusOnNavigationEnabled, False)  
        settings.setAttribute(QWebEngineSettings.ScrollAnimatorEnabled, False)  # Disable scroll animations
        settings.setAttribute(QWebEngineSettings.ErrorPageEnabled, False)  # Disable error pages
        settings.setAttribute(QWebEngineSettings.HyperlinkAuditingEnabled, False)  # Disable link auditing
        settings.setAttribute(QWebEngineSettings.SpatialNavigationEnabled, False)  # Disable spatial navigation
        
        # Keep auto-loading for compatibility 
        settings.setAttribute(QWebEngineSettings.AutoLoadImages, True)  # Keep images enabled for Discord to work
        
        # Optimize zoom for maximum performance 
        self.setZoomFactor(0.6)  # Smaller zoom = faster rendering
    
    def setup_page(self):
        """Setup custom page with CSS injection for better Discord layout."""
        page = self.page()
        
                        # Inject CSS to fix Discord scaling and hide unnecessary elements
        css_fixes = """
        <style>
        /* COMPLETE LAYOUT OVERRIDE - Force channels to left edge */
        
        /* Step 1: Hide server list completely */
        [data-list-id="guildsnav"],
        .guilds-2JjMmN,
        nav[aria-label*="Servers sidebar"],
        .wrapper-1_HaEi,
        .listItem-2GsLbH {
            display: none !important;
            width: 0 !important;
            visibility: hidden !important;
        }
        
        /* Step 2: Override Discord's flex container to start from 0 */
        .app-2CXKsg {
            position: relative !important;
            left: 0 !important;
            margin-left: 0 !important;
            padding-left: 0 !important;
        }
        
        /* Step 3: Force the base layout to use full width from left edge */
        .base-2jDfDU {
            position: absolute !important;
            left: 0 !important;
            top: 0 !important;
            right: 0 !important;
            bottom: 0 !important;
            margin: 0 !important;
            padding: 0 !important;
            width: 100% !important;
        }
        
        /* Step 4: Make channel sidebar start at position 0 */
        .sidebar-1tnWFu {
            position: absolute !important;
            left: 0 !important;
            top: 0 !important;
            height: 100% !important;
            width: 312px !important;
            margin: 0 !important;
            z-index: 100 !important;
        }
        
        /* Step 5: Adjust chat content to sit next to sidebar */
        .content-1SgpWY,
        .chat-2ZfjoI {
            position: absolute !important;
            left: 312px !important;
            top: 0 !important;
            right: 0 !important;
            bottom: 0 !important;
            width: calc(100% - 312px) !important;
        }
        
        /* Make sure channels list is visible */
        .channels-3g2vYe,
        [data-list-id="channels"] {
            display: block !important;
            visibility: visible !important;
        }
        
        /* Expand chat area to use remaining space efficiently */
        .chat-2ZfjoI,
        .content-1SgpWY,
        .chatContent-3KubbW {
            flex: 1 !important;
            max-width: calc(100% - 312px) !important;
        }
        
        /* Make messages use full available width */
        .messages-23can0,
        .scrollerInner-2PPAp2 {
            width: 100% !important;
            max-width: 100% !important;
        }
        </style>
        """
        
        # PERFORMANCE: Use minimal CSS to reduce render lag
        minimal_css = """
        <style>
        /* MINIMAL CSS for performance optimization */
        [data-list-id="guildsnav"], .guilds-2JjMmN { display: none !important; }
        .app-2CXKsg { margin-left: 0 !important; }
        /* Disable animations and transitions for speed */
        * { animation: none !important; transition: none !important; }
        </style>"""
        
        # This CSS will be injected after page loads
        self.discord_css = minimal_css

class DiscordIntegrationWidget(QWidget):
    """Main Discord integration widget for TrackPro."""
    
    # Signals
    discord_ready = pyqtSignal()
    user_joined = pyqtSignal(str)  # username
    user_left = pyqtSignal(str)   # username
    new_message = pyqtSignal(str, str)  # channel, message content
    new_mention = pyqtSignal(str, str)  # username, message content
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.discord_server_id = None
        self.discord_channel_id = None
        self.current_user = None
        self.notification_manager = None  # Will be set by parent
        self.last_message_count = 0  # Track message count for new message detection
        self.last_messages_seen = set()  # Track unique message IDs we've seen
        self.current_user_display_name = None  # Track current user for mention detection
        self.hidden_monitor = None  # Hidden web view for background monitoring
        
        # Performance optimization flags
        self._is_visible = False
        self._lazy_loaded = False
        
        # Connect signals to notification handling
        self.new_message.connect(self.handle_new_message)
        self.new_mention.connect(self.handle_new_mention)
        
        # Initialize UI but defer heavy operations until widget is shown
        self.setup_ui()
        self.load_discord_config()
    
    def set_notification_manager(self, notification_manager):
        """Set the notification manager for handling Discord notifications"""
        self.notification_manager = notification_manager
    
    def handle_new_message(self, channel, message):
        """Handle new Discord message notification"""
        if self.notification_manager:
            # Increment Discord notification count
            current = self.notification_manager.get_notification_count("discord")
            self.notification_manager.update_notification_count("discord", current + 1)
    
    def handle_new_mention(self, username, message):
        """Handle Discord mention notification (higher priority)"""
        if self.notification_manager:
            # Increment Discord notification count by 2 for mentions (higher priority)
            current = self.notification_manager.get_notification_count("discord")
            self.notification_manager.update_notification_count("discord", current + 2)
    
    def setup_ui(self):
        """Set up the SIMPLIFIED user interface for better performance."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Simplified header
        header = self.create_simple_header()
        layout.addWidget(header)
        
        # SINGLE Discord web view - no tabs for better performance
        self.discord_web_view = DiscordWebView()
        self.discord_web_view.loadFinished.connect(self.on_page_loaded)
        layout.addWidget(self.discord_web_view)
        
        # Minimal footer
        footer = self.create_simple_footer()
        layout.addWidget(footer)
    
    def create_simple_header(self) -> QWidget:
        """Create a simplified Discord header for better performance."""
        header = QFrame()
        header.setFixedHeight(40)  # Smaller header
        header.setStyleSheet("""
            QFrame {
                background-color: #2C2F33;
                border-bottom: 1px solid #7289DA;
            }
            QLabel {
                color: #FFFFFF;
                font-weight: bold;
            }
        """)
        
        layout = QHBoxLayout(header)
        
        # Simple Discord logo/icon
        discord_label = QLabel("🎮 Sim Coaches Drivers Lounge")
        discord_label.setFont(QFont("Arial", 12, QFont.Bold))
        layout.addWidget(discord_label)
        
        layout.addStretch()
        
        # Simple status
        self.status_label = QLabel("Connecting...")
        self.status_label.setStyleSheet("color: #FFA500;")  # Orange for connecting
        layout.addWidget(self.status_label)
        
        return header
        
    def create_header(self) -> QWidget:
        """Create the Discord header with server info."""
        header = QFrame()
        header.setFixedHeight(60)
        header.setStyleSheet("""
            QFrame {
                background-color: #2C2F33;
                border-bottom: 2px solid #7289DA;
            }
            QLabel {
                color: #FFFFFF;
                font-weight: bold;
            }
        """)
        
        layout = QHBoxLayout(header)
        
        # Discord logo/icon
        discord_label = QLabel("🎮 Sim Coaches Drivers Lounge")
        discord_label.setFont(QFont("Arial", 14, QFont.Bold))
        layout.addWidget(discord_label)
        
        layout.addStretch()
        
        # Server status
        self.status_label = QLabel("Connecting...")
        self.status_label.setStyleSheet("color: #FFA500;")
        layout.addWidget(self.status_label)
        
        # Settings button
        settings_btn = QPushButton("⚙️")
        settings_btn.setFixedSize(30, 30)
        settings_btn.clicked.connect(self.show_settings)
        settings_btn.setToolTip("Discord Settings")
        layout.addWidget(settings_btn)
        
        return header
    
    def create_server_tab(self) -> QWidget:
        """Create the main server chat tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Discord widget or full Discord web app
        self.discord_web_view = DiscordWebView()
        # Connect to page load finished to inject CSS
        self.discord_web_view.loadFinished.connect(self.on_page_loaded)
        layout.addWidget(self.discord_web_view)
        
        return widget
    
    def create_voice_tab(self) -> QWidget:
        """Create voice channels interface."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Voice channel web view
        self.voice_web_view = DiscordWebView()
        layout.addWidget(self.voice_web_view)
        
        return widget
    
    def create_members_tab(self) -> QWidget:
        """Create server members interface."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Members list web view
        self.members_web_view = DiscordWebView()
        layout.addWidget(self.members_web_view)
        
        return widget
    
    def create_simple_footer(self) -> QWidget:
        """Create a simplified footer for better performance."""
        footer = QFrame()
        footer.setFixedHeight(35)  # Smaller footer
        footer.setStyleSheet("""
            QFrame {
                background-color: #23272A;
                border-top: 1px solid #2C2F33;
            }
        """)
        
        layout = QHBoxLayout(footer)
        
        # Remove the "Open in Browser" button - user requested to hide it
        # browser_btn = QPushButton("🌐 Open in Browser")
        # browser_btn.clicked.connect(self.open_in_browser)
        # browser_btn.setStyleSheet("QPushButton { padding: 4px 8px; }")
        # layout.addWidget(browser_btn)
        
        layout.addStretch()
        
        # Status indicator
        perf_label = QLabel("⚡ Performance Mode")
        perf_label.setStyleSheet("color: #43B581; font-size: 10px;")
        layout.addWidget(perf_label)
        
        return footer

    def create_footer(self) -> QWidget:
        """Create footer with quick actions."""
        footer = QFrame()
        footer.setFixedHeight(50)
        footer.setStyleSheet("""
            QFrame {
                background-color: #23272A;
                border-top: 1px solid #2C2F33;
            }
        """)
        
        layout = QHBoxLayout(footer)
        
        # Mode toggle button
        self.mode_btn = QPushButton("📱 Switch to Widget Mode")
        self.mode_btn.clicked.connect(self.toggle_mode)
        self.mode_btn.setToolTip("Switch between Widget Mode (read-only) and Web App Mode (full features)")
        layout.addWidget(self.mode_btn)
        
        # Zoom controls
        zoom_out_btn = QPushButton("🔍-")
        zoom_out_btn.clicked.connect(self.zoom_out)
        zoom_out_btn.setFixedSize(40, 30)
        layout.addWidget(zoom_out_btn)
        
        zoom_in_btn = QPushButton("🔍+")
        zoom_in_btn.clicked.connect(self.zoom_in)
        zoom_in_btn.setFixedSize(40, 30)
        layout.addWidget(zoom_in_btn)
        
        layout.addStretch()
        
        # Open in browser button
        browser_btn = QPushButton("🌐 Open in Browser")
        browser_btn.clicked.connect(self.open_in_browser)
        layout.addWidget(browser_btn)
        
        return footer
    
    def on_page_loaded(self, success):
        """Called when Discord page finishes loading - inject CSS fixes and message monitoring."""
        if success:
            # Update connection status to show success
            self.status_label.setText("Connected")
            self.status_label.setStyleSheet("color: #43B581;")  # Green
            
            if hasattr(self.discord_web_view, 'discord_css'):
                # Wait a moment for Discord to initialize, then inject CSS and monitoring
                QTimer.singleShot(2000, self.inject_css_fixes)
                QTimer.singleShot(4000, self.inject_message_monitoring)
        else:
            # Show connection failed only if page actually failed to load
            self.status_label.setText("Connection Failed")
            self.status_label.setStyleSheet("color: #F04747;")  # Red
    
    def inject_css_fixes(self):
        """Inject optimized CSS to fix Discord scaling and layout issues."""
        # OPTIMIZED CSS - minimal and fast
        css_script = f"""
        // TrackPro: FAST CSS injection (no debugging)
        var style = document.createElement('style');
        style.textContent = `{self.discord_web_view.discord_css}`;
        document.head.appendChild(style);
        
        // MINIMAL and FAST server list hiding
        function hideServerListFast() {{
            // Hide server list with minimal DOM queries
            var serverSelectors = [
                '[data-list-id="guildsnav"]',
                '.guilds-2JjMmN',
                'nav[aria-label*="Servers sidebar"]',
                '.wrapper-1_HaEi'
            ];
            
            serverSelectors.forEach(function(selector) {{
                var elements = document.querySelectorAll(selector);
                elements.forEach(function(el) {{
                    el.style.display = 'none';
                    el.style.width = '0px';
                }});
            }});
            
            // Position channel sidebar
            var sidebar = document.querySelector('.sidebar-1tnWFu');
            if (sidebar) {{
                sidebar.style.position = 'absolute';
                sidebar.style.left = '0px';
                sidebar.style.top = '0px';
                sidebar.style.width = '312px';
            }}
            
            // Adjust main content
            var content = document.querySelector('.content-1SgpWY, .chat-2ZfjoI');
            if (content) {{
                content.style.left = '312px';
                content.style.width = 'calc(100% - 312px)';
            }}
        }}
        
        // Run layout fixes with minimal retries
        setTimeout(hideServerListFast, 1000);
        setTimeout(hideServerListFast, 3000);
        
        // Single mutation observer (lightweight)
        if (window.MutationObserver) {{
            var layoutObserver = new MutationObserver(function(mutations) {{
                var needsUpdate = mutations.some(function(m) {{
                    return m.addedNodes.length > 0 && 
                           Array.from(m.addedNodes).some(function(n) {{
                               return n.nodeType === 1 && (
                                   n.classList.contains('sidebar') ||
                                   n.classList.contains('guilds')
                               );
                           }});
                }});
                
                if (needsUpdate) {{
                    setTimeout(hideServerListFast, 300);
                }}
            }});
            
            layoutObserver.observe(document.body, {{
                childList: true,
                subtree: false  // Only watch direct children for performance
            }});
        }}
        """
        
        self.discord_web_view.page().runJavaScript(css_script)
    
    def inject_message_monitoring(self):
        """Inject lightweight JavaScript to monitor for new Discord messages."""
        monitoring_script = """
        // TrackPro Discord Message Monitoring - LIGHTWEIGHT VERSION
        console.log('TrackPro: Injecting lightweight Discord message monitoring...');
        
        var trackproSeenBadges = new Set();
        var trackproInitialized = false;
        var trackproInitDelay = 30000; // 30 seconds for better performance
        
        // Lightweight initialization - mark existing badges as seen
        function initializeMonitoring() {
            var existingBadges = document.querySelectorAll('[class*="numberBadge"], [class*="textBadge"], [class*="unread"]');
            existingBadges.forEach(function(badge, index) {
                var badgeId = badge.textContent + '_' + index;
                trackproSeenBadges.add(badgeId);
                badge.classList.add('trackpro-seen');
            });
            
            trackproInitialized = true;
            console.log('TrackPro: Lightweight monitoring initialized');
        }
        
        // Simple and fast notification check
        function checkForNewNotifications() {
            if (!trackproInitialized) return;
            
            try {
                var newNotifications = 0;
                
                // Check for new notification badges (simplified)
                var badges = document.querySelectorAll('[class*="numberBadge"]:not(.trackpro-seen), [class*="textBadge"]:not(.trackpro-seen)');
                badges.forEach(function(badge, index) {
                    var badgeId = badge.textContent + '_' + index;
                    if (badge.textContent && badge.textContent.trim() && !trackproSeenBadges.has(badgeId)) {
                        trackproSeenBadges.add(badgeId);
                        badge.classList.add('trackpro-seen');
                        newNotifications++;
                        
                        // Set global notification flag
                        window.trackproMessageDetected = {
                            author: 'Discord',
                            content: 'New activity detected',
                            timestamp: Date.now()
                        };
                    }
                });
                
            } catch(e) {
                // Silently handle errors to avoid console spam
            }
        }
        
        // Delayed initialization
        setTimeout(initializeMonitoring, trackproInitDelay);
        
        // Very low frequency monitoring (every 2 minutes for maximum performance)
        setInterval(checkForNewNotifications, 120000);
        
        // Lightweight DOM observer
        if (window.MutationObserver) {
            var observer = new MutationObserver(function(mutations) {
                var hasNewBadges = mutations.some(function(m) {
                    return Array.from(m.addedNodes).some(function(n) {
                        return n.nodeType === 1 && 
                               n.className && 
                               (n.className.includes('numberBadge') || n.className.includes('textBadge'));
                    });
                });
                
                if (hasNewBadges) {
                    setTimeout(checkForNewNotifications, 1000);
                }
            });
            
            observer.observe(document.body, {
                childList: true,
                subtree: false // Only watch direct children for better performance
            });
        }
        
        // Expose minimal status function for debugging
        window.trackproStatus = function() {
            console.log('TrackPro: Monitoring active, seen badges:', trackproSeenBadges.size);
        };
        """
        
        self.discord_web_view.page().runJavaScript(monitoring_script)
    
    def check_for_js_notifications(self):
        """Check for Discord notifications from JavaScript (optimized)."""
        def handle_result(result):
            try:
                if result and isinstance(result, dict):
                    # Simple notification handling
                    author = result.get('author', 'Discord')
                    content = result.get('content', 'New activity')
                    
                    # Clear the notification flag
                    self.discord_web_view.page().runJavaScript("window.trackproMessageDetected = null;")
                    
                    # Emit signal for notification
                    self.new_message.emit("Discord", content)
                    
            except Exception as e:
                # Silently handle errors to avoid console spam
                pass
        
        # Lightweight check for notifications
        self.discord_web_view.page().runJavaScript(
            "window.trackproMessageDetected || null",
            handle_result
        )
        
        # Check for mentions
        self.discord_web_view.page().runJavaScript(
            """
            if (window.trackproMentionDetected) {
                var mention = window.trackproMentionDetected;
                window.trackproMentionDetected = null; // Clear it
                mention;
            } else {
                null;
            }
            """,
            self.handle_js_mention_notification
        )
    
    def handle_js_message_notification(self, message_data):
        """Handle message notification from JavaScript - REMOVED (optimized)."""
        pass  # Functionality moved to check_for_js_notifications for better performance
    
    def handle_js_mention_notification(self, mention_data):
        """Handle mention notification from JavaScript - REMOVED (optimized)."""
        pass  # Functionality moved to check_for_js_notifications for better performance
    
    def zoom_in(self):
        """Increase zoom level."""
        current_zoom = self.discord_web_view.zoomFactor()
        new_zoom = min(current_zoom + 0.1, 2.0)  # Max 200%
        self.discord_web_view.setZoomFactor(new_zoom)
    
    def zoom_out(self):
        """Decrease zoom level."""
        current_zoom = self.discord_web_view.zoomFactor()
        new_zoom = max(current_zoom - 0.1, 0.5)  # Min 50%
        self.discord_web_view.setZoomFactor(new_zoom)
    
    def toggle_mode(self):
        """Toggle between Widget Mode and Web App Mode."""
        config_path = os.path.join(os.path.dirname(__file__), "discord_config.json")
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
            
            # Toggle the mode
            current_mode = config.get('use_widget_mode', True)
            config['use_widget_mode'] = not current_mode
            
            with open(config_path, 'w') as f:
                json.dump(config, f, indent=2)
            
            # Reconnect with new mode
            self.connect_to_discord()
            
            # Update button text
            if config['use_widget_mode']:
                self.mode_btn.setText("🌐 Switch to Web App Mode")
                self.status_label.setText("Widget Mode")
            else:
                self.mode_btn.setText("📱 Switch to Widget Mode")
                self.status_label.setText("Web App Mode")
                
        except Exception as e:
            logger.error(f"Error toggling mode: {e}")
    
    def load_discord_config(self):
        """Load Discord configuration from settings."""
        try:
            config_path = os.path.join(os.path.dirname(__file__), "discord_config.json")
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    config = json.load(f)
                    self.discord_server_id = config.get('server_id')
                    self.discord_channel_id = config.get('channel_id')
                    
                    # Update mode button text
                    use_widget = config.get('use_widget_mode', True)
                    if hasattr(self, 'mode_btn'):
                        if use_widget:
                            self.mode_btn.setText("🌐 Switch to Web App Mode")
                        else:
                            self.mode_btn.setText("📱 Switch to Widget Mode")
                    
                    logger.info("Discord configuration loaded")
            else:
                # Create default config
                self.create_default_config()
        except Exception as e:
            logger.error(f"Error loading Discord config: {e}")
            self.show_setup_dialog()
    
    def create_default_config(self):
        """Create default Discord configuration."""
        config = {
            "server_id": "",
            "channel_id": "", 
            "widget_theme": "dark",
            "auto_connect": True,
            "show_member_count": True,
            "show_voice_channels": True,
            "use_widget_mode": True
        }
        
        config_path = os.path.join(os.path.dirname(__file__), "discord_config.json")
        try:
            with open(config_path, 'w') as f:
                json.dump(config, f, indent=2)
            logger.info("Default Discord configuration created")
        except Exception as e:
            logger.error(f"Error creating Discord config: {e}")
    
    def connect_to_discord(self):
        """Connect to Discord server using widget or web app."""
        if not self.discord_server_id:
            self.show_setup_dialog()
            return
        
        try:
            # Option 1: Use Discord Widget (simpler, limited functionality)
            if self.use_widget_mode():
                self.load_discord_widget()
            else:
                # Option 2: Use improved Discord web app (locked to server)
                self.load_discord_web_app()
            
            # IMPORTANT: Start background monitoring regardless of mode
            self.start_background_monitoring()
                
            self.status_label.setText("Connected")
            self.status_label.setStyleSheet("color: #43B581;")  # Green
            self.discord_ready.emit()
            
        except Exception as e:
            logger.error(f"Error connecting to Discord: {e}")
            self.status_label.setText("Connection Failed")
            self.status_label.setStyleSheet("color: #F04747;")  # Red
    
    def use_widget_mode(self) -> bool:
        """Determine whether to use widget mode or full web app."""
        # Load preference from config
        config_path = os.path.join(os.path.dirname(__file__), "discord_config.json")
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    config = json.load(f)
                    return config.get('use_widget_mode', True)  # Default to widget mode
        except Exception:
            pass
        return True  # Default to widget mode for safety
    
    def load_discord_widget(self):
        """Load Discord server using the widget API."""
        if not self.discord_server_id:
            return
        
        # Discord widget URL
        widget_url = f"https://discord.com/widget?id={self.discord_server_id}&theme=dark"
        
        # Load in main Discord view
        self.discord_web_view.setUrl(QUrl(widget_url))
        
        # No longer using separate voice/members tabs in simplified UI
        logger.info(f"Discord widget loaded for server: {self.discord_server_id}")
    
    def load_discord_web_app(self):
        """Load Discord web app locked to the specific server."""
        if not self.discord_server_id:
            return
            
        # Load Discord directly to the configured server instead of the general app
        # This reduces clutter and focuses on the specific server
        if self.discord_channel_id:
            # Go to specific channel if configured
            discord_url = f"https://discord.com/channels/{self.discord_server_id}/{self.discord_channel_id}"
        else:
            # Go to server main page
            discord_url = f"https://discord.com/channels/{self.discord_server_id}"
        
        self.discord_web_view.setUrl(QUrl(discord_url))
        
        # No longer using separate voice/members tabs in simplified UI
        logger.info(f"Discord web app loaded for server: {self.discord_server_id}")
    
    def start_background_monitoring(self):
        """DISABLED: Background monitoring for performance optimization."""
        print("⚡ Discord background monitoring DISABLED for better performance")
        
        # Instead, use very lightweight notification checking only when Discord is visible
        if hasattr(self, 'message_poll_timer'):
            self.message_poll_timer.stop()
            
        self.message_poll_timer = QTimer()
        self.message_poll_timer.timeout.connect(self.check_for_js_notifications)
        self.message_poll_timer.start(60000)  # Check every 60 seconds for maximum performance
    
    def on_hidden_monitor_loaded(self, success):
        """Handle when the hidden monitor finishes loading."""
        if success:
            print("✅ Hidden Discord monitor loaded successfully")
            # Wait a bit for Discord to initialize, then inject monitoring
            QTimer.singleShot(5000, self.inject_hidden_monitoring)
        else:
            print("❌ Hidden Discord monitor failed to load")
    
    def inject_hidden_monitoring(self):
        """Inject monitoring JavaScript into the hidden Discord view."""
        try:
            print("🔧 Injecting monitoring into hidden Discord view...")
            
            # Create a lightweight monitoring script focused on notifications
            lightweight_monitoring = """
            console.log('TrackPro: Hidden background monitoring active');
            
            // Simple notification detection for background monitoring
            var backgroundCheckInterval;
            
            function backgroundNotificationCheck() {
                try {
                    var notifications = 0;
                    
                    // Check for various Discord notification indicators
                    var badges = document.querySelectorAll('[class*="numberBadge"], [class*="textBadge"], [class*="unread"]');
                    var newBadges = 0;
                    
                    badges.forEach(function(badge) {
                        if (badge.textContent && badge.textContent.trim() && 
                            !badge.classList.contains('trackpro-bg-seen')) {
                            
                            badge.classList.add('trackpro-bg-seen');
                            newBadges++;
                            
                            console.log('TrackPro Background: Notification detected:', badge.textContent);
                            
                            // Set global flag for Qt to read
                            window.trackproBackgroundNotification = {
                                type: 'discord',
                                count: badge.textContent.trim(),
                                timestamp: Date.now()
                            };
                        }
                    });
                    
                    // Check for "NEW" badges specifically
                    var newTextBadges = document.querySelectorAll('[class*="textBadge"]');
                    newTextBadges.forEach(function(badge) {
                        if (badge.textContent && badge.textContent.trim().toUpperCase() === 'NEW' && 
                            !badge.classList.contains('trackpro-bg-seen')) {
                            
                            badge.classList.add('trackpro-bg-seen');
                            newBadges++;
                            
                            console.log('TrackPro Background: NEW badge detected');
                            
                            window.trackproBackgroundNotification = {
                                type: 'discord',
                                count: 'NEW',
                                timestamp: Date.now()
                            };
                        }
                    });
                    
                    if (newBadges > 0) {
                        console.log('TrackPro Background: Found', newBadges, 'new notifications');
                    }
                    
                } catch(e) {
                    console.log('TrackPro Background: Error in monitoring:', e);
                }
            }
            
            // Start background monitoring
            backgroundCheckInterval = setInterval(backgroundNotificationCheck, 3000);
            
            // Initial check after delay
            setTimeout(backgroundNotificationCheck, 2000);
            
            console.log('TrackPro: Background monitoring initialized');
            """
            
            # Inject the monitoring script
            self.hidden_monitor.page().runJavaScript(lightweight_monitoring)
            
            # Start polling for background notifications
            if not hasattr(self, 'background_poll_timer'):
                self.background_poll_timer = QTimer()
                self.background_poll_timer.timeout.connect(self.check_background_notifications)
                self.background_poll_timer.start(2000)  # Check every 2 seconds
                
            print("✅ Background monitoring JavaScript injected")
            
        except Exception as e:
            logger.error(f"Error injecting hidden monitoring: {e}")
            print(f"❌ Error injecting background monitoring: {e}")
    
    def check_background_notifications(self):
        """Check for notifications from the background monitor."""
        if self.hidden_monitor:
            try:
                # Check for background notifications
                self.hidden_monitor.page().runJavaScript(
                    """
                    if (window.trackproBackgroundNotification) {
                        var notif = window.trackproBackgroundNotification;
                        window.trackproBackgroundNotification = null; // Clear it
                        notif;
                    } else {
                        null;
                    }
                    """,
                    self.handle_background_notification
                )
            except Exception as e:
                logger.error(f"Error checking background notifications: {e}")
    
    def handle_background_notification(self, notification_data):
        """Handle notification from background monitor."""
        if notification_data:
            try:
                print(f"🔔 Background notification detected: {notification_data}")
                
                # Trigger a Discord notification
                self.new_message.emit("background", f"Discord activity detected: {notification_data.get('count', 'Unknown')}")
                
            except Exception as e:
                logger.error(f"Error handling background notification: {e}")
                print(f"❌ Error handling background notification: {e}")
    
    def show_setup_dialog(self):
        """Show setup dialog for Discord configuration."""
        from .discord_setup_dialog import DiscordSetupDialog
        
        dialog = DiscordSetupDialog(self)
        if dialog.exec_() == dialog.Accepted:
            self.discord_server_id = dialog.server_id
            self.discord_channel_id = dialog.channel_id
            use_widget_mode = getattr(dialog, 'use_widget_mode', True)
            self.save_discord_config(use_widget_mode)
            self.connect_to_discord()
    
    def save_discord_config(self, use_widget_mode=True):
        """Save Discord configuration to file."""
        config = {
            "server_id": self.discord_server_id,
            "channel_id": self.discord_channel_id,
            "widget_theme": "dark",
            "auto_connect": True,
            "show_member_count": True,
            "show_voice_channels": True,
            "use_widget_mode": use_widget_mode
        }
        
        config_path = os.path.join(os.path.dirname(__file__), "discord_config.json")
        try:
            with open(config_path, 'w') as f:
                json.dump(config, f, indent=2)
            logger.info("Discord configuration saved")
        except Exception as e:
            logger.error(f"Error saving Discord config: {e}")
    
    def show_settings(self):
        """Show Discord settings dialog."""
        self.show_setup_dialog()
    
    def toggle_mute(self):
        """Toggle microphone mute."""
        # This would require Discord Rich Presence SDK or bot integration
        # For now, show instructions
        QMessageBox.information(self, "Mute Toggle", 
                              "Use Discord's built-in mute button or Ctrl+Shift+M")
    
    def toggle_deafen(self):
        """Toggle audio deafen."""
        # This would require Discord Rich Presence SDK or bot integration
        QMessageBox.information(self, "Deafen Toggle", 
                              "Use Discord's built-in deafen button or Ctrl+Shift+D")
    
    def open_in_browser(self):
        """Open Discord in external browser."""
        import webbrowser
        if self.discord_server_id:
            url = f"https://discord.com/channels/{self.discord_server_id}"
            webbrowser.open(url)
        else:
            webbrowser.open("https://discord.com")
    
    def showEvent(self, event):
        """Handle widget being shown - optimize for performance."""
        super().showEvent(event)
        self._is_visible = True
        
        # Lazy load Discord content only when first shown
        if not self._lazy_loaded:
            self._lazy_loaded = True
            # Connect to Discord with a small delay to allow UI to settle
            QTimer.singleShot(1000, self._lazy_connect_discord)
        
        # Resume monitoring if it was paused
        if hasattr(self, 'message_poll_timer') and not self.message_poll_timer.isActive():
            self.message_poll_timer.start(60000)
    
    def hideEvent(self, event):
        """Handle widget being hidden - reduce resource usage."""
        super().hideEvent(event)
        self._is_visible = False
        
        # Pause monitoring to save resources when not visible
        if hasattr(self, 'message_poll_timer') and self.message_poll_timer.isActive():
            self.message_poll_timer.stop()
    
    def _lazy_connect_discord(self):
        """Lazy loading of Discord connection for better startup performance."""
        try:
            self.connect_to_discord()
        except Exception as e:
            logger.error(f"Error in lazy Discord connection: {e}")
    
    def closeEvent(self, event):
        """Handle widget being closed - cleanup resources."""
        try:
            # Stop monitoring timer
            if hasattr(self, 'message_poll_timer'):
                self.message_poll_timer.stop()
                
            # Clear web view content to free memory
            if hasattr(self, 'discord_web_view'):
                self.discord_web_view.setUrl(QUrl("about:blank"))
                
            # Clean up hidden monitor
            if self.hidden_monitor:
                self.hidden_monitor.setUrl(QUrl("about:blank"))
                self.hidden_monitor = None
                
        except Exception as e:
            logger.error(f"Error during Discord widget cleanup: {e}")
        
        super().closeEvent(event)

# Global instance
discord_integration = DiscordIntegrationWidget() 