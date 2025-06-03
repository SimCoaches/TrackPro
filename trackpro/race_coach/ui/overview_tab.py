"""Overview tab for Race Coach - Live telemetry dashboard.

This module contains the overview tab that displays live telemetry data
including gauges, input traces, and real-time values.
"""

import logging
import math
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QGridLayout, QSizePolicy
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

# Import common widgets
from .common_widgets import SpeedGauge, RPMGauge, SteeringWheelWidget, InputTraceWidget

logger = logging.getLogger(__name__)


class OverviewTab(QWidget):
    """Overview tab displaying live telemetry dashboard."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_widget = parent
        self.setup_ui()

    def setup_ui(self):
        """Set up the overview tab UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # Title
        title_label = QLabel("Race Coach Overview")
        title_label.setStyleSheet("""
            font-size: 18px;
            font-weight: bold;
            color: white;
            padding: 10px;
        """)
        layout.addWidget(title_label)

        # Main dashboard frame
        dashboard_frame = QFrame()
        dashboard_frame.setFrameStyle(QFrame.StyledPanel | QFrame.Sunken)
        dashboard_frame.setStyleSheet("background-color: #2D2D30; border-radius: 5px;")
        dashboard_layout = QVBoxLayout(dashboard_frame)

        # Info text
        info_label = QLabel("Connect to iRacing to see live telemetry data.")
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #CCC; font-size: 14px; padding: 10px;")
        dashboard_layout.addWidget(info_label)

        # Create live telemetry section
        telemetry_section = self.create_live_telemetry_section()
        dashboard_layout.addWidget(telemetry_section)

        layout.addWidget(dashboard_frame)
        layout.addStretch()

    def create_live_telemetry_section(self):
        """Create the live telemetry display section."""
        section = QWidget()
        layout = QVBoxLayout(section)
        layout.setSpacing(15)

        # Section title
        title = QLabel("Live Telemetry")
        title.setStyleSheet("""
            font-size: 16px;
            font-weight: bold;
            color: #00ff88;
            margin-bottom: 10px;
        """)
        layout.addWidget(title)

        # Create main telemetry layout
        telemetry_layout = QHBoxLayout()
        telemetry_layout.setSpacing(20)

        # Left side - Gauges
        gauges_widget = QWidget()
        gauges_layout = QVBoxLayout(gauges_widget)
        gauges_layout.setSpacing(10)

        # Speed gauge
        self.speed_gauge = SpeedGauge()
        gauges_layout.addWidget(self.speed_gauge)

        # RPM gauge
        self.rpm_gauge = RPMGauge()
        gauges_layout.addWidget(self.rpm_gauge)

        telemetry_layout.addWidget(gauges_widget)

        # Center - Steering wheel and input trace
        center_widget = QWidget()
        center_layout = QVBoxLayout(center_widget)
        center_layout.setSpacing(10)

        # Steering wheel
        self.steering_wheel = SteeringWheelWidget()
        center_layout.addWidget(self.steering_wheel)

        # Input trace
        self.input_trace = InputTraceWidget()
        self.input_trace.setMinimumHeight(150)
        center_layout.addWidget(self.input_trace)

        telemetry_layout.addWidget(center_widget)

        # Right side - Current values
        values_widget = QWidget()
        values_layout = QGridLayout(values_widget)
        values_layout.setSpacing(10)
        values_layout.setContentsMargins(10, 10, 10, 10)

        # Style for labels
        label_style = "color: #AAA; font-size: 12px;"
        value_style = "color: white; font-size: 14px; font-weight: bold;"

        # Speed
        values_layout.addWidget(QLabel("Speed:", styleSheet=label_style), 0, 0)
        self.speed_value = QLabel("0.0 km/h")
        self.speed_value.setStyleSheet(value_style)
        values_layout.addWidget(self.speed_value, 0, 1)

        # Throttle
        values_layout.addWidget(QLabel("Throttle:", styleSheet=label_style), 1, 0)
        self.throttle_value = QLabel("0%")
        self.throttle_value.setStyleSheet(value_style)
        values_layout.addWidget(self.throttle_value, 1, 1)

        # Brake
        values_layout.addWidget(QLabel("Brake:", styleSheet=label_style), 2, 0)
        self.brake_value = QLabel("0%")
        self.brake_value.setStyleSheet(value_style)
        values_layout.addWidget(self.brake_value, 2, 1)

        # Clutch
        values_layout.addWidget(QLabel("Clutch:", styleSheet=label_style), 3, 0)
        self.clutch_value = QLabel("0%")
        self.clutch_value.setStyleSheet(value_style)
        values_layout.addWidget(self.clutch_value, 3, 1)

        # Gear
        values_layout.addWidget(QLabel("Gear:", styleSheet=label_style), 4, 0)
        self.gear_value = QLabel("N")
        self.gear_value.setStyleSheet(value_style)
        values_layout.addWidget(self.gear_value, 4, 1)

        # RPM
        values_layout.addWidget(QLabel("RPM:", styleSheet=label_style), 5, 0)
        self.rpm_value = QLabel("0")
        self.rpm_value.setStyleSheet(value_style)
        values_layout.addWidget(self.rpm_value, 5, 1)

        # Lap
        values_layout.addWidget(QLabel("Lap:", styleSheet=label_style), 6, 0)
        self.lap_value = QLabel("0")
        self.lap_value.setStyleSheet(value_style)
        values_layout.addWidget(self.lap_value, 6, 1)

        # Lap time
        values_layout.addWidget(QLabel("Lap Time:", styleSheet=label_style), 7, 0)
        self.laptime_value = QLabel("--:--.---")
        self.laptime_value.setStyleSheet(value_style)
        values_layout.addWidget(self.laptime_value, 7, 1)

        # Add stretch to push values to top
        values_layout.setRowStretch(8, 1)

        telemetry_layout.addWidget(values_widget)

        layout.addLayout(telemetry_layout)
        return section

    def update_telemetry(self, telemetry_data):
        """Update the overview display with new telemetry data."""
        if not telemetry_data or not isinstance(telemetry_data, dict):
            return

        try:
            # Extract telemetry values
            throttle = telemetry_data.get("Throttle", telemetry_data.get("throttle", 0))
            brake = telemetry_data.get("Brake", telemetry_data.get("brake", 0))
            clutch = telemetry_data.get("Clutch", telemetry_data.get("clutch", 0))
            speed = telemetry_data.get("Speed", telemetry_data.get("speed", 0))
            rpm = telemetry_data.get("RPM", telemetry_data.get("rpm", 0))
            gear = telemetry_data.get("Gear", telemetry_data.get("gear", 0))
            lap = telemetry_data.get("Lap", telemetry_data.get("lap_count", 0))
            laptime = telemetry_data.get("LapCurrentLapTime", telemetry_data.get("lap_time", 0))
            steering = telemetry_data.get(
                "steering",
                telemetry_data.get(
                    "SteeringWheelAngle", telemetry_data.get("Steer", telemetry_data.get("steer", 0))
                ),
            )

            # Update input trace
            if hasattr(self, "input_trace"):
                self.input_trace.add_data_point(throttle, brake, clutch)

            # Convert speed to km/h if needed
            if isinstance(speed, (int, float)) and speed > 0:
                speed *= 3.6  # Convert m/s to km/h

            # Format gear text
            gear_text = "R" if gear == -1 else "N" if gear == 0 else str(gear)

            # Update text values
            self.speed_value.setText(f"{speed:.1f} km/h")
            self.throttle_value.setText(f"{throttle*100:.0f}%")
            self.brake_value.setText(f"{brake*100:.0f}%")
            self.clutch_value.setText(f"{(1-clutch)*100:.0f}%")  # Invert clutch for display
            self.gear_value.setText(gear_text)
            self.rpm_value.setText(f"{rpm:.0f}")
            self.lap_value.setText(str(lap))
            self.laptime_value.setText(self._format_time(laptime))

            # Update gauges
            if hasattr(self, "speed_gauge"):
                self.speed_gauge.set_value(speed)

            if hasattr(self, "rpm_gauge"):
                self.rpm_gauge.set_value(rpm)
                # Check if we have session info for redline
                if hasattr(self.parent_widget, "session_info") and self.parent_widget.session_info:
                    driver_info = self.parent_widget.session_info.get("DriverInfo", {})
                    if "DriverCarRedLine" in driver_info:
                        redline = driver_info["DriverCarRedLine"]
                        self.rpm_gauge.set_redline(redline)

            # Update steering wheel
            if hasattr(self, "steering_wheel"):
                # Normalize steering value to -1.0 to 1.0 range if needed
                if abs(steering) > 1.0:
                    # Convert from radians to normalized value
                    max_rotation = telemetry_data.get(
                        "SteeringWheelAngleMax", telemetry_data.get("steering_max", 3.0 * math.pi)
                    )

                    if max_rotation > 0:
                        # Clamp steering angle to max_rotation
                        clamped_steering = max(-max_rotation, min(max_rotation, steering))
                        steering_normalized = clamped_steering / max_rotation
                        steering_normalized = max(-1.0, min(1.0, steering_normalized))

                        self.steering_wheel.set_max_rotation(max_rotation)
                        self.steering_wheel.set_value(steering_normalized)
                else:
                    # Already normalized
                    steering_normalized = max(-1.0, min(1.0, steering))
                    self.steering_wheel.set_value(steering_normalized)

        except Exception as e:
            logger.error(f"Error updating overview telemetry: {e}")

    def _format_time(self, time_in_seconds):
        """Format time in seconds to MM:SS.mmm format."""
        if time_in_seconds is None or time_in_seconds < 0:
            return "--:--.---"
        minutes = int(time_in_seconds // 60)
        seconds = time_in_seconds % 60
        return f"{minutes:02d}:{seconds:06.3f}"

    def clear_telemetry(self):
        """Clear all telemetry displays."""
        # Reset gauges
        if hasattr(self, "speed_gauge"):
            self.speed_gauge.set_value(0)
        if hasattr(self, "rpm_gauge"):
            self.rpm_gauge.set_value(0)
        if hasattr(self, "steering_wheel"):
            self.steering_wheel.set_value(0)
        
        # Clear input trace
        if hasattr(self, "input_trace"):
            self.input_trace.clear_data()
        
        # Reset text values
        self.speed_value.setText("0.0 km/h")
        self.throttle_value.setText("0%")
        self.brake_value.setText("0%")
        self.clutch_value.setText("0%")
        self.gear_value.setText("N")
        self.rpm_value.setText("0")
        self.lap_value.setText("0")
        self.laptime_value.setText("--:--.---") 