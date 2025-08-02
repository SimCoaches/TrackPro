#!/usr/bin/env python3
"""
Example screen that demonstrates how to access the global iRacing telemetry data.
This shows how any screen in your new UI can connect to and use iRacing telemetry.
"""

import logging
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QGridLayout, QGroupBox
from PyQt6.QtCore import QTimer, pyqtSignal
from PyQt6.QtGui import QFont

logger = logging.getLogger(__name__)

class TelemetryExampleScreen(QWidget):
    """Example screen that displays live iRacing telemetry data."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.iracing_api = None
        self.setup_ui()
        self.setup_telemetry_connection()
        
        # Update timer for UI refreshes
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_telemetry_display)
        self.update_timer.start(100)  # Update every 100ms for smooth display
    
    def setup_ui(self):
        """Set up the user interface."""
        layout = QVBoxLayout(self)
        
        # Title
        title = QLabel("iRacing Telemetry Data")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)
        
        # Connection status
        self.connection_label = QLabel("Connection Status: Checking...")
        layout.addWidget(self.connection_label)
        
        # Telemetry data grid
        telemetry_group = QGroupBox("Live Telemetry")
        telemetry_layout = QGridLayout(telemetry_group)
        
        # Create labels for telemetry data
        self.telemetry_labels = {}
        
        # Speed and engine data
        telemetry_layout.addWidget(QLabel("Speed:"), 0, 0)
        self.telemetry_labels['speed'] = QLabel("0 mph")
        telemetry_layout.addWidget(self.telemetry_labels['speed'], 0, 1)
        
        telemetry_layout.addWidget(QLabel("RPM:"), 0, 2)
        self.telemetry_labels['rpm'] = QLabel("0")
        telemetry_layout.addWidget(self.telemetry_labels['rpm'], 0, 3)
        
        # Input data
        telemetry_layout.addWidget(QLabel("Throttle:"), 1, 0)
        self.telemetry_labels['throttle'] = QLabel("0%")
        telemetry_layout.addWidget(self.telemetry_labels['throttle'], 1, 1)
        
        telemetry_layout.addWidget(QLabel("Brake:"), 1, 2)
        self.telemetry_labels['brake'] = QLabel("0%")
        telemetry_layout.addWidget(self.telemetry_labels['brake'], 1, 3)
        
        # Position data
        telemetry_layout.addWidget(QLabel("Lap:"), 2, 0)
        self.telemetry_labels['lap'] = QLabel("0")
        telemetry_layout.addWidget(self.telemetry_labels['lap'], 2, 1)
        
        telemetry_layout.addWidget(QLabel("Position:"), 2, 2)
        self.telemetry_labels['position'] = QLabel("0")
        telemetry_layout.addWidget(self.telemetry_labels['position'], 2, 3)
        
        # Gear and track data
        telemetry_layout.addWidget(QLabel("Gear:"), 3, 0)
        self.telemetry_labels['gear'] = QLabel("N")
        telemetry_layout.addWidget(self.telemetry_labels['gear'], 3, 1)
        
        telemetry_layout.addWidget(QLabel("Track Temp:"), 3, 2)
        self.telemetry_labels['track_temp'] = QLabel("0°F")
        telemetry_layout.addWidget(self.telemetry_labels['track_temp'], 3, 3)
        
        layout.addWidget(telemetry_group)
        
        # Session info
        session_group = QGroupBox("Session Information")
        session_layout = QVBoxLayout(session_group)
        
        self.session_labels = {}
        self.session_labels['track_name'] = QLabel("Track: Not connected")
        self.session_labels['car_name'] = QLabel("Car: Not connected")
        self.session_labels['session_type'] = QLabel("Session: Not connected")
        
        session_layout.addWidget(self.session_labels['track_name'])
        session_layout.addWidget(self.session_labels['car_name'])
        session_layout.addWidget(self.session_labels['session_type'])
        
        layout.addWidget(session_group)
        
        layout.addStretch()
    
    def setup_telemetry_connection(self):
        """Set up connection to the global iRacing telemetry system."""
        try:
            # Import the global iRacing API access function
            from new_ui import get_global_iracing_api
            
            # Get the global iRacing API instance
            self.iracing_api = get_global_iracing_api()
            
            if self.iracing_api:
                # Register for telemetry data updates
                self.iracing_api.register_on_telemetry_data(self.on_telemetry_data)
                
                # Register for connection status changes
                self.iracing_api.register_on_connection_changed(self.on_connection_changed)
                
                logger.info("✅ Connected to global iRacing telemetry system")
            else:
                logger.warning("⚠️ Global iRacing API not available")
                self.connection_label.setText("Connection Status: Global iRacing API not available")
                
        except Exception as e:
            logger.error(f"❌ Failed to connect to global iRacing telemetry: {e}")
            self.connection_label.setText(f"Connection Status: Error - {e}")
    
    def on_telemetry_data(self, telemetry):
        """Handle incoming telemetry data from iRacing."""
        # This is called automatically when new telemetry data arrives
        # The telemetry data is a dictionary with all iRacing telemetry values
        
        # Store the latest telemetry for display updates
        if hasattr(self, 'iracing_api') and self.iracing_api:
            # We can access current_telemetry directly for the latest data
            pass
    
    def on_connection_changed(self, is_connected, session_info):
        """Handle iRacing connection status changes."""
        if is_connected:
            self.connection_label.setText("Connection Status: ✅ Connected to iRacing")
            self.connection_label.setStyleSheet("color: green;")
            
            # Update session info if available
            if session_info:
                track_name = session_info.get('WeekendInfo', {}).get('TrackDisplayName', 'Unknown Track')
                self.session_labels['track_name'].setText(f"Track: {track_name}")
                
                # Get car name from DriverInfo
                driver_info = session_info.get('DriverInfo', {}).get('Drivers', [])
                if driver_info and len(driver_info) > 0:
                    car_name = driver_info[0].get('CarScreenName', 'Unknown Car')
                    self.session_labels['car_name'].setText(f"Car: {car_name}")
                
                session_type = session_info.get('SessionInfo', {}).get('Sessions', [{}])[0].get('SessionType', 'Unknown')
                self.session_labels['session_type'].setText(f"Session: {session_type}")
        else:
            self.connection_label.setText("Connection Status: ❌ Disconnected from iRacing")
            self.connection_label.setStyleSheet("color: red;")
            
            # Clear session info
            self.session_labels['track_name'].setText("Track: Not connected")
            self.session_labels['car_name'].setText("Car: Not connected")
            self.session_labels['session_type'].setText("Session: Not connected")
    
    def update_telemetry_display(self):
        """Update the telemetry display with the latest data."""
        if not self.iracing_api or not hasattr(self.iracing_api, 'current_telemetry'):
            return
        
        # Get the current telemetry data
        telemetry = self.iracing_api.current_telemetry
        
        if not telemetry:
            return
        
        try:
            # Update speed (convert from m/s to mph)
            speed_ms = telemetry.get('Speed', 0)
            speed_mph = speed_ms * 2.237  # Convert m/s to mph
            self.telemetry_labels['speed'].setText(f"{speed_mph:.1f} mph")
            
            # Update RPM
            rpm = telemetry.get('RPM', 0)
            self.telemetry_labels['rpm'].setText(f"{rpm:.0f}")
            
            # Update throttle (convert to percentage)
            throttle = telemetry.get('Throttle', 0) * 100
            self.telemetry_labels['throttle'].setText(f"{throttle:.1f}%")
            
            # Update brake (convert to percentage)
            brake = telemetry.get('Brake', 0) * 100
            self.telemetry_labels['brake'].setText(f"{brake:.1f}%")
            
            # Update lap number
            lap = telemetry.get('Lap', 0)
            self.telemetry_labels['lap'].setText(f"{lap}")
            
            # Update position
            position = telemetry.get('Position', 0)
            self.telemetry_labels['position'].setText(f"{position}")
            
            # Update gear
            gear = telemetry.get('Gear', -1)
            if gear == -1:
                gear_text = "R"
            elif gear == 0:
                gear_text = "N"
            else:
                gear_text = str(gear)
            self.telemetry_labels['gear'].setText(gear_text)
            
            # Update track temperature
            track_temp = telemetry.get('TrackTemp', 0)
            track_temp_f = track_temp * 9/5 + 32  # Convert C to F
            self.telemetry_labels['track_temp'].setText(f"{track_temp_f:.1f}°F")
            
        except Exception as e:
            logger.error(f"❌ Error updating telemetry display: {e}")
    
    def closeEvent(self, event):
        """Clean up when the widget is closed."""
        if self.update_timer:
            self.update_timer.stop()
        
        # Unregister from telemetry callbacks to prevent memory leaks
        if self.iracing_api:
            try:
                # Note: The SimpleIRacingAPI should have methods to unregister callbacks
                # but we'll just let the garbage collector handle it for now
                pass
            except Exception as e:
                logger.error(f"Error cleaning up telemetry connections: {e}")
        
        super().closeEvent(event)

if __name__ == "__main__":
    """
    To test this screen independently, you would need to:
    1. Run new_ui.py first to initialize the global iRacing connection
    2. Then you could import and use this screen in your application
    
    Example usage in your main UI:
    
    from example_telemetry_screen import TelemetryExampleScreen
    
    # In your main window or tab system:
    telemetry_screen = TelemetryExampleScreen()
    # Add it to your UI layout, tabs, or stack
    """
    print("This is an example telemetry screen for the new TrackPro UI.")
    print("Run new_ui.py to see it in action with the full application.")