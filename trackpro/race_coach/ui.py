import logging
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout,
                           QPushButton, QLabel, QTabWidget, QGroupBox,
                           QSplitter, QComboBox, QStatusBar, QMainWindow, QMessageBox)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QColor, QPalette

logger = logging.getLogger(__name__)

class RaceCoachWidget(QWidget):
    """Main widget for the Race Coach feature that can be embedded as a tab."""
    
    def __init__(self, parent=None, iracing_api=None, data_manager=None, model=None, lap_analysis=None, super_lap=None):
        """Initialize the Race Coach widget.
        
        Args:
            parent: Parent widget
            iracing_api: Instance of IRacingAPI class
            data_manager: Instance of DataManager class
            model: Instance of RacingModel class
            lap_analysis: Instance of LapAnalysis class
            super_lap: Instance of SuperLap class
        """
        super().__init__(parent)
        
        # Store components
        from .iracing_api import IRacingAPI
        from .data_manager import DataManager
        from .model import RacingModel
        from .analysis import LapAnalysis
        from .superlap import SuperLap
        
        try:
            self.iracing_api = iracing_api or IRacingAPI()
            self.data_manager = data_manager or DataManager(db_path="race_coach.db")  # Use a relative path
            self.model = model or RacingModel(self.data_manager)
            self.lap_analysis = lap_analysis or LapAnalysis(self.data_manager)
            self.super_lap = super_lap or SuperLap(self.data_manager, self.model)
            
            # Set up callbacks
            self.iracing_api.on_connected = self.on_iracing_connected
            self.iracing_api.on_disconnected = self.on_iracing_disconnected
            self.iracing_api.on_telemetry_update = self.on_telemetry_update
            self.iracing_api.on_session_info_update = self.on_session_info_update
            
            # Initialize state
            self.iracing_connected = False
            self.current_track = None
            self.current_car = None
        
            # Set up UI
            self.setup_ui()
            
            logger.info("Race Coach widget initialized")
        except Exception as e:
            logger.error(f"Error initializing Race Coach widget: {e}")
            raise
    
    def setup_ui(self):
        """Set up the UI components."""
        # Create main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)
        
        # Create status section at the top
        status_layout = QHBoxLayout()
        status_layout.setSpacing(15)
        
        # iRacing connection status with improved visibility
        self.iracing_status = QLabel("iRacing: Not Connected")
        self.iracing_status.setFont(QFont("Arial", 12, QFont.Bold))
        self.iracing_status.setStyleSheet("""
            QLabel {
                padding: 8px 15px;
                border-radius: 6px;
                font-weight: bold;
                background-color: #FF5252;
                color: white;
            }
        """)
        
        # Current track and car info with improved styling
        self.track_info = QLabel("Track: None")
        self.track_info.setFont(QFont("Arial", 11))
        self.track_info.setStyleSheet("""
            QLabel {
                padding: 6px 10px;
                border-radius: 4px;
                background-color: rgba(255, 255, 255, 0.1);
                color: white;
            }
        """)
        
        self.car_info = QLabel("Car: None")
        self.car_info.setFont(QFont("Arial", 11))
        self.car_info.setStyleSheet("""
            QLabel {
                padding: 6px 10px;
                border-radius: 4px;
                background-color: rgba(255, 255, 255, 0.1);
                color: white;
            }
        """)
        
        # Connect button with improved styling
        self.connect_button = QPushButton("Connect to iRacing")
        self.connect_button.setMinimumWidth(180)
        self.connect_button.setFont(QFont("Arial", 11, QFont.Bold))
        self.connect_button.setStyleSheet("""
            QPushButton {
                padding: 8px 15px;
                border-radius: 6px;
                background-color: #2196F3;
                color: white;
                border: none;
            }
            QPushButton:hover {
                background-color: #0D8BF2;
            }
            QPushButton:pressed {
                background-color: #0B7AD1;
            }
        """)
        self.connect_button.clicked.connect(self.connect_to_iracing)
        
        # Add widgets to status layout
        status_layout.addWidget(self.iracing_status)
        status_layout.addWidget(self.track_info)
        status_layout.addWidget(self.car_info)
        status_layout.addStretch()
        status_layout.addWidget(self.connect_button)
        
        # Container for status with border and background
        status_container = QWidget()
        status_container.setStyleSheet("""
            QWidget {
                background-color: rgba(40, 40, 40, 0.7);
                border-radius: 8px;
                border: 1px solid rgba(100, 100, 100, 0.5);
            }
        """)
        status_container.setLayout(status_layout)
        status_container.setMinimumHeight(70)
        
        # Add status container to main layout
        main_layout.addWidget(status_container)
        
        # Create tab widget for different functionalities
        self.tab_widget = QTabWidget()
        self.tab_widget.setFont(QFont("Arial", 11))
        self.tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid rgba(100, 100, 100, 0.5);
                background-color: rgba(40, 40, 40, 0.7);
                border-radius: 5px;
            }
            QTabBar::tab {
                background-color: rgba(60, 60, 60, 0.7);
                color: white;
                padding: 8px 15px;
                margin-right: 2px;
                border-top-left-radius: 5px;
                border-top-right-radius: 5px;
            }
            QTabBar::tab:selected {
                background-color: rgba(40, 40, 40, 0.9);
                border: 1px solid rgba(100, 100, 100, 0.5);
                border-bottom: none;
            }
        """)
        
        # Create tabs
        self.setup_dashboard_tab()
        self.setup_analysis_tab()
        self.setup_superlap_tab()
        self.setup_settings_tab()
        
        # Add tab widget to main layout
        main_layout.addWidget(self.tab_widget)
        
        # Add status message at the bottom with improved styling
        self.status_message = QLabel("Ready")
        self.status_message.setFont(QFont("Arial", 10))
        self.status_message.setStyleSheet("""
            QLabel {
                padding: 6px 10px;
                color: rgba(255, 255, 255, 0.8);
                background-color: rgba(40, 40, 40, 0.5);
                border-radius: 4px;
            }
        """)
        main_layout.addWidget(self.status_message)
    
    def setup_dashboard_tab(self):
        """Set up the Dashboard tab with current session info."""
        dashboard_widget = QWidget()
        layout = QVBoxLayout(dashboard_widget)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Create header
        header = QLabel("Dashboard")
        header.setFont(QFont("Arial", 18, QFont.Bold))
        header.setStyleSheet("color: white;")
        layout.addWidget(header)
        
        # Add placeholder content
        content = QLabel("Dashboard will display real-time telemetry and session information.")
        content.setAlignment(Qt.AlignCenter)
        content.setFont(QFont("Arial", 12))
        content.setStyleSheet("color: white;")
        layout.addWidget(content)
        
        # Add tab to widget
        self.tab_widget.addTab(dashboard_widget, "Dashboard")
    
    def setup_analysis_tab(self):
        """Set up the Analysis tab for lap time analysis."""
        analysis_widget = QWidget()
        layout = QVBoxLayout(analysis_widget)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Create header
        header = QLabel("Lap Analysis")
        header.setFont(QFont("Arial", 18, QFont.Bold))
        header.setStyleSheet("color: white;")
        layout.addWidget(header)
        
        # Add placeholder content
        content = QLabel("Analysis tab will provide detailed lap analysis and comparison tools.")
        content.setAlignment(Qt.AlignCenter)
        content.setFont(QFont("Arial", 12))
        content.setStyleSheet("color: white;")
        layout.addWidget(content)
        
        # Add tab to widget
        self.tab_widget.addTab(analysis_widget, "Analysis")
    
    def setup_superlap_tab(self):
        """Set up the SUPER LAP tab for optimal lap visualization."""
        superlap_widget = QWidget()
        layout = QVBoxLayout(superlap_widget)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Create header
        header = QLabel("SUPER LAP")
        header.setFont(QFont("Arial", 18, QFont.Bold))
        header.setStyleSheet("color: white;")
        layout.addWidget(header)
        
        # Add placeholder content
        content = QLabel("SUPER LAP will combine the best segments from multiple drivers to create an optimal reference lap.")
        content.setAlignment(Qt.AlignCenter)
        content.setFont(QFont("Arial", 12))
        content.setStyleSheet("color: white;")
        layout.addWidget(content)
        
        # Add tab to widget
        self.tab_widget.addTab(superlap_widget, "SUPER LAP")
    
    def setup_settings_tab(self):
        """Set up the Settings tab for configuration options."""
        settings_widget = QWidget()
        layout = QVBoxLayout(settings_widget)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Create header
        header = QLabel("Settings")
        header.setFont(QFont("Arial", 18, QFont.Bold))
        header.setStyleSheet("color: white;")
        layout.addWidget(header)
        
        # Add placeholder content
        content = QLabel("Settings for the Race Coach feature.")
        content.setAlignment(Qt.AlignCenter)
        content.setFont(QFont("Arial", 12))
        content.setStyleSheet("color: white;")
        layout.addWidget(content)
        
        # Add tab to widget
        self.tab_widget.addTab(settings_widget, "Settings")
    
    def connect_to_iracing(self):
        """Connect to the iRacing API."""
        # This is implemented to either connect or disconnect based on current state
        logger.info("Connect button clicked")
        
        if not self.iracing_connected:
            logger.info("Attempting to connect to iRacing API")
            self.status_message.setText("Connecting to iRacing...")
            
            # Try to connect
            try:
                success = self.iracing_api.connect()
                if success:
                    # Connection callback will update UI
                    logger.info("Connection to iRacing API initiated")
                else:
                    logger.error("Failed to connect to iRacing API")
                    self.status_message.setText("Failed to connect to iRacing - iRacing not running")
                    QMessageBox.warning(
                        self,
                        "Connection Failed",
                        "Could not connect to iRacing. Please make sure iRacing is running.",
                        QMessageBox.Ok
                    )
                    # Ensure status shows disconnected
                    self.on_iracing_disconnected()
            except Exception as e:
                logger.error(f"Error connecting to iRacing API: {e}")
                self.status_message.setText("Error connecting to iRacing")
                QMessageBox.critical(
                    self,
                    "Connection Error",
                    f"Error connecting to iRacing: {str(e)}",
                    QMessageBox.Ok
                )
                # Ensure status shows disconnected
                self.on_iracing_disconnected()
        else:
            # Disconnect
            logger.info("Disconnecting from iRacing API")
            try:
                self.iracing_api.disconnect()
                # Disconnect callback will update UI
            except Exception as e:
                logger.error(f"Error disconnecting from iRacing API: {e}")
                self.status_message.setText("Error disconnecting from iRacing")
    
    def on_iracing_connected(self, track, car):
        """Callback when iRacing connection is established."""
        self.iracing_connected = True
        self.iracing_status.setText("iRacing: Connected")
        self.iracing_status.setStyleSheet("""
            QLabel {
                padding: 8px 15px;
                border-radius: 6px;
                font-weight: bold;
                background-color: #4CAF50;
                color: white;
                font-size: 12pt;
            }
        """)
        self.connect_button.setText("Disconnect")
        self.status_message.setText("Connected to iRacing")
        
        # Update track and car info
        self.current_track = track
        self.current_car = car
        self.track_info.setText(f"Track: {self.current_track}")
        self.car_info.setText(f"Car: {self.current_car}")
    
    def on_iracing_disconnected(self):
        """Callback when iRacing connection is lost."""
        self.iracing_connected = False
        self.iracing_status.setText("iRacing: Not Connected")
        self.iracing_status.setStyleSheet("""
            QLabel {
                padding: 8px 15px;
                border-radius: 6px;
                font-weight: bold;
                background-color: #FF5252;
                color: white;
                font-size: 12pt;
            }
        """)
        self.connect_button.setText("Connect to iRacing")
        self.status_message.setText("Disconnected from iRacing")
        
        # Reset track and car info
        self.current_track = None
        self.current_car = None
        self.track_info.setText("Track: None")
        self.car_info.setText("Car: None")
    
    def on_telemetry_update(self, telemetry):
        """Callback when telemetry data is updated."""
        # Handle telemetry update
        pass
    
    def on_session_info_update(self, session_info):
        """Callback when session information is updated."""
        # Handle session info update
        pass 