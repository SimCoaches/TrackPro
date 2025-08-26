import logging
from PyQt6.QtWidgets import (
    QVBoxLayout,
    QHBoxLayout,
    QTabWidget,
    QWidget,
    QScrollArea,
    QPushButton,
    QLabel,
    QGroupBox,
    QFormLayout,
    QGridLayout,
    QComboBox,
    QLineEdit,
    QCheckBox,
    QSlider,
    QSpinBox,
    QStackedWidget,
)
from PyQt6.QtCore import pyqtSignal, Qt, QTimer, pyqtSlot, QMetaObject, Q_ARG
from PyQt6.QtGui import QColor
from ...modern.shared.base_page import BasePage
from .calibration_widget import PedalCalibrationWidget
from .deadzone_widget import DeadzoneWidget
from .curve_manager_widget import CurveManagerWidget
from ...race_coach.pedals_perf import PedalAggregator
from ....io.pedals_worker import create_pedals_thread

try:
    import serial  # type: ignore
    from serial.tools import list_ports  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    serial = None
    list_ports = None

logger = logging.getLogger(__name__)

class PedalsPage(BasePage):
    pedal_calibrated = pyqtSignal(str, dict)
    curve_changed = pyqtSignal(str, str)
    sample_emitted = pyqtSignal(float, float, float)  # n, x, y for synchronized UI updates
    
    def __init__(self, global_managers=None):
        self.pedal_widgets = {}
        self.pedal_tabs = None
        self.connection_status_label = None
        self.connection_timer = None
        # Will be set when global pedal system is provided by the main window
        self.global_output = None
        self.global_pedal_data_queue = None
        super().__init__("pedals", global_managers)
        
        # Create aggregator with conservative 30Hz to prevent timer exhaustion
        self._agg = PedalAggregator(ui_hz=30, parent=self)
        self._agg.sample.updated.connect(self._on_pedals_frame)  # UI-thread safe

        # Track resources in global manager
        try:
            from new_ui import global_qt_resource_manager
            global_qt_resource_manager.track_widget(self._agg)
        except:
            pass
    
    def init_page(self):
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Apply pyqtgraph performance optimizations once during init
        # pyqtgraph perf: downsampling, clip-to-view, antialias off
        # References: pyqtgraph.readthedocs.io
        try:
            import pyqtgraph as pg
            pg.setConfigOptions(antialias=False)  # global toggle; faster lines
        except Exception:
            pass  # pyqtgraph not available
        
        # Top header: left = Pedals/ABS tabs, right = connection + wizard (right-aligned)
        header_layout = QHBoxLayout()

        # Left: Pedals / ABS buttons
        tabs_container = QWidget()
        tabs_layout = QHBoxLayout(tabs_container)
        tabs_layout.setContentsMargins(0, 0, 0, 0)
        tabs_layout.setSpacing(6)

        self.btn_nav_pedals = QPushButton("Pedals")
        self.btn_nav_abs = QPushButton("ABS")
        for btn in (self.btn_nav_pedals, self.btn_nav_abs):
            btn.setCheckable(True)
            btn.setStyleSheet(
                """
                QPushButton {
                    padding: 8px 10px;
                    border-radius: 6px;
                    background-color: #1f2937;
                    color: #f3f4f6;
                    border: 1px solid #374151;
                }
                QPushButton:hover { background-color: #111827; }
                QPushButton:checked {
                    background-color: #2563eb;
                    color: white;
                    border-color: #1d4ed8;
                    font-weight: bold;
                }
                """
            )
            tabs_layout.addWidget(btn)

        header_layout.addWidget(tabs_container)
        header_layout.addStretch()

        # Right: connection status + calibration wizard button
        right_container = QWidget()
        right_layout = QHBoxLayout(right_container)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(8)

        # Connection status indicator
        self.connection_status_label = QLabel()
        self.connection_status_label.setStyleSheet(
            """
            QLabel {
                padding: 6px 12px;
                border-radius: 4px;
                font-size: 11px;
                font-weight: bold;
                color: white;
            }
            """
        )

        # Calibration wizard button
        wizard_btn = QPushButton("🧙 Calibration Wizard")
        wizard_btn.setMaximumWidth(180)
        wizard_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #5865f2;
                color: white;
                font-weight: bold;
                padding: 6px 12px;
                border: none;
                border-radius: 4px;
                font-size: 11px;
                max-width: 180px;
            }
            QPushButton:hover {
                background-color: #4752c4;
            }
            """
        )
        wizard_btn.clicked.connect(self.open_calibration_wizard)

        right_layout.addWidget(self.connection_status_label)
        right_layout.addWidget(wizard_btn)
        header_layout.addWidget(right_container)

        layout.addLayout(header_layout)
        
        # Setup connection status timer - use conservative interval to prevent handle exhaustion
        self.connection_timer = QTimer()
        self.connection_timer.timeout.connect(self.update_connection_status)
        self.connection_timer.start(5000)  # Update every 5 seconds instead of 1 second

        # Track timer in global manager
        try:
            from new_ui import global_qt_resource_manager
            global_qt_resource_manager.track_timer(self.connection_timer)
        except:
            pass
        
        # Initial connection status update
        self.update_connection_status()
        
        # Content row
        content_row = QHBoxLayout()
        content_row.setContentsMargins(0, 0, 0, 0)
        content_row.setSpacing(12)
        layout.addLayout(content_row)

        # Stacked content
        self.section_stack = QStackedWidget()

        # Pedals content page (existing UI preserved)
        pedals_page = QWidget()
        pedals_page_layout = QVBoxLayout(pedals_page)
        pedals_layout = QHBoxLayout()
        pedals_page_layout.addLayout(pedals_layout)
        self.create_side_by_side_pedals(pedals_layout)
        self.section_stack.addWidget(pedals_page)

        # ABS content page
        abs_page = AbsControlWidget(self.global_managers)
        self.section_stack.addWidget(abs_page)

        # Wire nav
        self.btn_nav_pedals.clicked.connect(lambda: self.switch_section(0))
        self.btn_nav_abs.clicked.connect(lambda: self.switch_section(1))

        # Default selection
        self.btn_nav_pedals.setChecked(True)
        self.section_stack.setCurrentIndex(0)

        # Assemble
        content_row.addWidget(self.section_stack, 1)
        
        # NO performance manager - pedal thread handles UI directly
        # Persist calibration changes from UI to local file (and schedule cloud sync)
        try:
            self.pedal_calibrated.connect(self.on_pedal_calibrated)
        except Exception:
            pass

    def switch_section(self, index: int):
        try:
            self.section_stack.setCurrentIndex(index)
            # Keep nav buttons mutually exclusive
            if index == 0:
                self.btn_nav_pedals.setChecked(True)
                self.btn_nav_abs.setChecked(False)
            else:
                self.btn_nav_pedals.setChecked(False)
                self.btn_nav_abs.setChecked(True)
        except Exception:
            pass

        
    def update_connection_status(self):
        """Update the connection status indicator."""
        if not self.connection_status_label:
            return
            
        if hasattr(self, 'global_managers') and self.global_managers and hasattr(self.global_managers, 'hardware'):
            hardware = self.global_managers.hardware
            
            # Simple check: if pedals_connected is True, then connected
            if hasattr(hardware, 'pedals_connected') and hardware.pedals_connected:
                # Pedals connected
                self.connection_status_label.setText("🟢 Pedals Connected")
                self.connection_status_label.setStyleSheet("""
                    QLabel {
                        background-color: #22c55e;
                        color: white;
                        padding: 6px 12px;
                        border-radius: 4px;
                        font-size: 11px;
                        font-weight: bold;
                    }
                """)
            else:
                # Pedals disconnected
                self.connection_status_label.setText("🔴 Pedals Disconnected")
                self.connection_status_label.setStyleSheet("""
                    QLabel {
                        background-color: #ef4444;
                        color: white;
                        padding: 6px 12px;
                        border-radius: 4px;
                        font-size: 11px;
                        font-weight: bold;
                    }
                """)
        else:
            # Hardware manager not available
            self.connection_status_label.setText("⚪ Hardware Unavailable")
            self.connection_status_label.setStyleSheet("""
                QLabel {
                    background-color: #6b7280;
                    color: white;
                    padding: 6px 12px;
                    border-radius: 4px;
                    font-size: 11px;
                    font-weight: bold;
                }
            """)
    
    def create_side_by_side_pedals(self, parent_layout):
        pedals = ['throttle', 'brake', 'clutch']
        
        for pedal in pedals:
            pedal_widget = self.create_pedal_widget(pedal)
            parent_layout.addWidget(pedal_widget, 1)  # Equal stretch
            self.pedal_widgets[pedal] = pedal_widget
    
    def create_pedal_widget(self, pedal_name: str):
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        main_widget = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(6)  # Reduced spacing between sections
        layout.setContentsMargins(6, 6, 6, 6)  # Reduced margins
        main_widget.setLayout(layout)
        
        calibration_widget = PedalCalibrationWidget(pedal_name, self.global_managers)
        deadzone_widget = DeadzoneWidget(pedal_name, self.global_managers)
        curve_manager_widget = CurveManagerWidget(pedal_name, self.global_managers)
        
        layout.addWidget(calibration_widget)
        layout.addWidget(deadzone_widget)
        layout.addWidget(curve_manager_widget)
        layout.addStretch()
        
        calibration_widget.calibration_updated.connect(
            lambda data, p=pedal_name: self.pedal_calibrated.emit(p, data)
        )
        curve_manager_widget.curve_changed.connect(
            lambda curve, p=pedal_name: self.curve_changed.emit(p, curve)
        )
        # When a curve is loaded, refresh the UI widgets to show the new hardware state
        curve_manager_widget.curve_changed.connect(
            lambda curve: calibration_widget.load_existing_calibration_data()
        )
        curve_manager_widget.curve_changed.connect(
            lambda curve: deadzone_widget.load_existing_deadzone_data()
        )
        # Update both the page and the calibration widget when deadzone changes
        deadzone_widget.deadzone_changed.connect(
            lambda pedal, min_dz, max_dz: self.update_deadzone(pedal, min_dz, max_dz, calibration_widget)
        )
        deadzone_widget.deadzone_changed.connect(
            lambda pedal, min_dz, max_dz: calibration_widget.set_deadzone_values(min_dz, max_dz)
        )
        
        scroll_area.setWidget(main_widget)
        return scroll_area

    def on_pedal_calibrated(self, pedal: str, data: dict):
        try:
            if not getattr(self, 'hardware_input', None) and getattr(self, 'global_managers', None):
                self.hardware_input = getattr(self.global_managers, 'hardware', None)
            hardware = getattr(self, 'hardware_input', None)
            if not hardware:
                return
            # Translate UI data to hardware calibration format
            ui_points = data.get('curve_points') or []
            points = []
            for pt in ui_points:
                try:
                    x, y = pt
                    points.append([int(x), int(y)])
                except Exception:
                    continue
            curve_type = data.get('curve_type') or 'Linear'
            if pedal not in hardware.calibration:
                hardware.calibration[pedal] = {}
            hardware.calibration[pedal]['points'] = points
            hardware.calibration[pedal]['curve'] = curve_type
            # Optionally reflect min/max to axis ranges when provided
            try:
                min_val = data.get('min_value')
                max_val = data.get('max_value')
                if isinstance(min_val, int) and isinstance(max_val, int) and pedal in hardware.axis_ranges:
                    axis_entry = hardware.axis_ranges.get(pedal, {})
                    axis_entry['min'] = min_val
                    axis_entry['max'] = max_val
                    hardware.axis_ranges[pedal] = axis_entry
                    if hasattr(hardware, 'save_axis_ranges'):
                        hardware.save_axis_ranges()
            except Exception:
                pass
            # Persist calibration locally and schedule cloud save
            if hasattr(hardware, 'save_calibration'):
                hardware.save_calibration(hardware.calibration)
        except Exception as e:
            logger.debug(f"Failed to persist calibration for {pedal}: {e}")
    
    def open_calibration_wizard(self):
        try:
            from ....pedals.calibration import CalibrationWizard
            
            # Fallback to global manager hardware if local reference not set yet
            if not getattr(self, 'hardware_input', None) and getattr(self, 'global_managers', None):
                try:
                    self.hardware_input = getattr(self.global_managers, 'hardware', None)
                except Exception:
                    self.hardware_input = None
            if not getattr(self, 'hardware_input', None):
                logger.warning("Hardware input not available - cannot open calibration wizard")
                return
            
            wizard = CalibrationWizard(self.hardware_input, self)
            wizard.calibration_complete.connect(self.on_calibration_complete)
            
            result = wizard.exec()
            if result == wizard.DialogCode.Accepted:
                logger.info("Calibration wizard completed successfully")
            else:
                logger.info("Calibration wizard cancelled")
                
        except ImportError as e:
            logger.error(f"Failed to import CalibrationWizard: {e}")
        except Exception as e:
            logger.error(f"Error opening calibration wizard: {e}")
    
    def update_deadzone(self, pedal_name: str, min_deadzone: int, max_deadzone: int, calibration_widget):
        """Update the deadzone values in the calibration chart."""
        logger.info(f"Updating deadzone for {pedal_name}: min={min_deadzone}%, max={max_deadzone}%")
        # Apply to the calibration widget and refresh visualization
        if hasattr(calibration_widget, 'set_deadzone_values'):
            calibration_widget.set_deadzone_values(min_deadzone, max_deadzone)
        if hasattr(calibration_widget, 'update_deadzone_visualization'):
            calibration_widget.update_deadzone_visualization()
            logger.debug(f"Updated deadzone visualization for {pedal_name}")
        
        # Apply to live hardware so vJoy output uses these deadzones
        try:
            if getattr(self, 'hardware_input', None):
                if pedal_name in self.hardware_input.axis_ranges:
                    axis_entry = self.hardware_input.axis_ranges.get(pedal_name, {})
                    axis_entry['min_deadzone'] = int(max(0, min(50, min_deadzone)))
                    axis_entry['max_deadzone'] = int(max(0, min(50, max_deadzone)))
                    self.hardware_input.axis_ranges[pedal_name] = axis_entry
                    # Persist for future sessions
                    if hasattr(self.hardware_input, 'save_axis_ranges'):
                        self.hardware_input.save_axis_ranges()
                    
                    # Save deadzone settings to cloud
                    try:
                        setattr(self.hardware_input, f'{pedal_name}_deadzone_min', min_deadzone)
                        setattr(self.hardware_input, f'{pedal_name}_deadzone_max', max_deadzone)
                        if hasattr(self.hardware_input, 'save_deadzone_settings'):
                            self.hardware_input.save_deadzone_settings()
                    except Exception as dz_e:
                        logger.debug(f"Failed to save deadzone settings for {pedal_name}: {dz_e}")
        except Exception as e:
            logger.debug(f"Failed to apply deadzones to hardware for {pedal_name}: {e}")
    
    def on_calibration_complete(self, calibration_data):
        logger.info(f"Calibration completed with data: {calibration_data}")
        
        # Update the individual calibration widgets with new data
        for pedal, data in calibration_data.items():
            if pedal in self.pedal_widgets:
                widget = self.pedal_widgets[pedal]
                if hasattr(widget.widget(), 'layout'):
                    calibration_widget = widget.widget().layout().itemAt(0).widget()
                    if hasattr(calibration_widget, 'set_calibration_range'):
                        min_val = data.get('min', 0)
                        max_val = data.get('max', 65535)
                        calibration_widget.set_calibration_range(min_val, max_val)
    
    def handle_hardware_update(self, pedal_data):
        logger.debug(f"🔄 handle_hardware_update called with: {pedal_data}")
        for pedal, value in pedal_data.items():
            logger.debug(f"🎮 Processing pedal {pedal} with value {value}")
            if pedal in self.pedal_widgets:
                widget = self.pedal_widgets[pedal]
                logger.debug(f"✅ Found pedal widget for {pedal}")
                if hasattr(widget.widget(), 'layout'):
                    calibration_widget = widget.widget().layout().itemAt(0).widget()
                    logger.debug(f"✅ Found calibration widget: {calibration_widget}")
                    if hasattr(calibration_widget, 'update_input_value'):
                        logger.debug(f"✅ Calling update_input_value with {value}")
                        calibration_widget.update_input_value(value)
                        logger.debug(f"✅ update_input_value called successfully")
                    else:
                        logger.error(f"❌ calibration_widget missing update_input_value method")
                else:
                    logger.error(f"❌ widget missing layout")
            else:
                logger.error(f"❌ pedal {pedal} not found in pedal_widgets")
    
    def set_pedal_available(self, pedal: str, available: bool):
        if pedal in self.pedal_widgets:
            widget = self.pedal_widgets[pedal]
            widget.setEnabled(available)
    
    # --- Integration with global pedal system (modern UI) ---
    def set_global_pedal_system(self, hardware, output, data_queue):
        """Called by the modern main window once the global pedal system is ready."""
        self.hardware_input = hardware
        self.global_output = output
        self.global_pedal_data_queue = data_queue
        # Optional: attach high-rate worker to feed UI smoothly without object churn
        try:
            if hardware and not hasattr(self, '_pedals_worker'):
                self._pedals_worker, self._pedals_thread = create_pedals_thread(hardware, ui_hz=120)
                self._pedals_worker.samplesReady.connect(self._on_samples_ready, Qt.ConnectionType.QueuedConnection)
                self._pedals_thread.start()
        except Exception:
            pass

        # Refresh connection indicator immediately
        self.update_connection_status()



    def update_pedal_values(self, raw_values: dict):
        """Accept raw pedal values from the global UI updater."""
        try:
            if isinstance(raw_values, dict):
                # Convert raw values to normalized 0-1 range and feed to aggregator
                # This replaces direct UI updates with aggregated updates
                norm_throttle = raw_values.get('throttle', 0) / 65535.0
                norm_brake = raw_values.get('brake', 0) / 65535.0
                norm_clutch = raw_values.get('clutch', 0) / 65535.0
                
                # Use queued connection to be thread-safe
                QMetaObject.invokeMethod(
                    self._agg, "feed",
                    Qt.ConnectionType.QueuedConnection,
                    Q_ARG(float, norm_throttle),
                    Q_ARG(float, norm_brake),
                    Q_ARG(float, norm_clutch),
                )
        except Exception as e:
            logger.debug(f"Error updating pedal values: {e}")
    
    @pyqtSlot(float, float, float)
    def _on_pedals_frame(self, thr, brk, clt):
        """
        Handle aggregated pedal updates at fixed 60Hz rate.
        Never update UI widgets from worker threads—use signals/slots only.
        References:
        - KDAB: Qt threading best practices
        - Qt Forum: UI updates from main thread only
        """
        try:
            # Convert back to raw values for existing widget compatibility
            raw_values = {
                'throttle': int(thr * 65535),
                'brake': int(brk * 65535), 
                'clutch': int(clt * 65535)
            }
            
            # Update widgets through existing method (now at controlled rate)
            self.handle_hardware_update(raw_values)
            
            # Emit the processed values for synchronized UI updates
            # Note: These are already processed values (post-deadzone, post-curve)
            self.sample_emitted.emit(thr, brk, clt)
            
        except Exception as e:
            logger.debug(f"Error in pedal frame update: {e}")

    def get_pedal_calibration(self, pedal: str):
        if pedal in self.pedal_widgets:
            widget = self.pedal_widgets[pedal]
            if hasattr(widget.widget(), 'layout'):
                calibration_widget = widget.widget().layout().itemAt(0).widget()
                if hasattr(calibration_widget, 'get_calibration_data'):
                    return calibration_widget.get_calibration_data()
        return None
    
    def cleanup(self):
        """Clean up all Qt resources to prevent handle exhaustion."""
        # Stop pedal worker/thread if present
        try:
            if hasattr(self, '_pedals_worker') and self._pedals_worker:
                self._pedals_worker.stop()
            if hasattr(self, '_pedals_thread') and self._pedals_thread:
                self._pedals_thread.quit()
                self._pedals_thread.wait(500)
                self._pedals_thread.deleteLater()
        except Exception:
            pass
        # Clean up connection timer
        if self.connection_timer:
            self.connection_timer.stop()
            self.connection_timer.deleteLater()
            self.connection_timer = None

        # Clean up heartbeat timer
        if hasattr(self, '_heartbeat_timer') and self._heartbeat_timer:
            self._heartbeat_timer.stop()
            self._heartbeat_timer.deleteLater()
            self._heartbeat_timer = None

        # Clean up aggregator and disconnect signals
        if hasattr(self, '_agg') and self._agg:
            try:
                self._agg.sample.updated.disconnect(self._on_pedals_frame)
            except:
                pass
            self._agg.deleteLater()
            self._agg = None

        # Clean up calibration widgets
        if hasattr(self, 'pedal_widgets'):
            for widget in self.pedal_widgets.values():
                if widget and hasattr(widget, 'cleanup'):
                    widget.cleanup()
                if widget:
                    widget.deleteLater()

        # Clean up tabs and widgets
        if hasattr(self, 'pedal_tabs') and self.pedal_tabs:
            for i in range(self.pedal_tabs.count()):
                widget = self.pedal_tabs.widget(i)
                if widget:
                    self.pedal_tabs.removeTab(i)
                    widget.deleteLater()

        # Force garbage collection
        import gc
        gc.collect()

    @pyqtSlot(object)
    def _on_samples_ready(self, arr):
        try:
            # Use last sample in batch to drive existing UI
            thr, brk, clt = float(arr[-1,0]), float(arr[-1,1]), float(arr[-1,2])
            self._on_pedals_frame(thr, brk, clt)
        except Exception:
            pass
    
    def closeEvent(self, event):
        """Handle widget close event."""
        self.cleanup()
        super().closeEvent(event) if hasattr(super(), 'closeEvent') else None
    
    def __del__(self):
        """Destructor to ensure proper cleanup."""
        try:
            self.cleanup()
        except Exception as e:
            logger.debug(f"Error in pedals page destructor: {e}")



class AbsControlWidget(QWidget):
    """Controls for the external ESP32-S3 ABS brake module.

    This widget handles serial connection (USB CDC) to the ESP32-S3 and
    sends simple text commands to configure the ABS behavior.
    """

    def __init__(self, global_managers=None):
        super().__init__()
        self.global_managers = global_managers
        self._serial = None
        self._connected = False
        self._port_name = None
        self._baud_rate = 115200
        self._heartbeat_timer = QTimer(self)
        # Make heartbeat timer coarse and slightly jittered to avoid synchronized stalls
        try:
            self._heartbeat_timer.setTimerType(QTimer.TimerType.CoarseTimer)
        except Exception:
            pass
        self._heartbeat_timer.setInterval(2000)
        self._heartbeat_timer.timeout.connect(self._send_heartbeat)
        self._build_ui()

    def _build_ui(self):
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)

        # Connection group
        conn_group = QGroupBox("ESP32-S3 Connection")
        conn_layout = QGridLayout()
        conn_group.setLayout(conn_layout)

        self.port_combo = QComboBox()
        self.refresh_btn = QPushButton("Refresh Ports")
        self.connect_btn = QPushButton("Connect")
        self.disconnect_btn = QPushButton("Disconnect")
        self.disconnect_btn.setEnabled(False)
        self.status_label = QLabel("Disconnected")
        self.status_label.setStyleSheet("color: #ef4444;")

        conn_layout.addWidget(QLabel("Port"), 0, 0)
        conn_layout.addWidget(self.port_combo, 0, 1)
        conn_layout.addWidget(self.refresh_btn, 0, 2)
        conn_layout.addWidget(QLabel("Baud"), 1, 0)
        self.baud_input = QLineEdit(str(self._baud_rate))
        self.baud_input.setMaximumWidth(100)
        conn_layout.addWidget(self.baud_input, 1, 1)
        conn_layout.addWidget(self.connect_btn, 1, 2)
        conn_layout.addWidget(self.disconnect_btn, 1, 3)
        conn_layout.addWidget(QLabel("Status"), 2, 0)
        conn_layout.addWidget(self.status_label, 2, 1, 1, 3)

        main_layout.addWidget(conn_group)

        # Controls group
        ctrl_group = QGroupBox("ABS Control")
        form = QFormLayout()
        ctrl_group.setLayout(form)

        self.enable_checkbox = QCheckBox("Enable ABS Module")
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["Mild", "Standard", "Aggressive", "Custom"])

        self.intensity_slider = QSlider(Qt.Orientation.Horizontal)
        self.intensity_slider.setRange(0, 100)
        self.intensity_slider.setValue(50)
        self.intensity_value = QLabel("50%")

        self.frequency_slider = QSlider(Qt.Orientation.Horizontal)
        self.frequency_slider.setRange(1, 60)  # Hz
        self.frequency_slider.setValue(20)
        self.frequency_value = QLabel("20 Hz")

        self.brake_threshold = QSpinBox()
        self.brake_threshold.setRange(0, 100)
        self.brake_threshold.setValue(5)
        self.brake_threshold.setSuffix(" %")

        # Solenoid gate actuation speed (ramps)
        self.open_ramp_ms = QSpinBox()
        self.open_ramp_ms.setRange(0, 500)
        self.open_ramp_ms.setValue(30)
        self.open_ramp_ms.setSuffix(" ms")
        self.open_ramp_ms.setToolTip("Time to ramp from 0% to target intensity when opening the valve")

        self.close_ramp_ms = QSpinBox()
        self.close_ramp_ms.setRange(0, 500)
        self.close_ramp_ms.setValue(30)
        self.close_ramp_ms.setSuffix(" ms")
        self.close_ramp_ms.setToolTip("Time to ramp from current intensity to 0% when closing the valve")

        self.test_pulse_btn = QPushButton("Test Pulse")
        self.save_defaults_btn = QPushButton("Save As Defaults")

        form.addRow(self.enable_checkbox)
        form.addRow("Mode", self.mode_combo)

        intensity_row = QHBoxLayout()
        intensity_row.addWidget(self.intensity_slider)
        intensity_row.addWidget(self.intensity_value)
        form.addRow("Intensity", intensity_row)

        freq_row = QHBoxLayout()
        freq_row.addWidget(self.frequency_slider)
        freq_row.addWidget(self.frequency_value)
        form.addRow("Frequency", freq_row)

        form.addRow("Brake Start Threshold", self.brake_threshold)
        form.addRow("Open Ramp", self.open_ramp_ms)
        form.addRow("Close Ramp", self.close_ramp_ms)

        buttons_row = QHBoxLayout()
        buttons_row.addWidget(self.test_pulse_btn)
        buttons_row.addWidget(self.save_defaults_btn)
        form.addRow(buttons_row)

        main_layout.addWidget(ctrl_group)
        main_layout.addStretch()

        # Wire up events
        self.refresh_btn.clicked.connect(self._refresh_ports)
        self.connect_btn.clicked.connect(self._connect)
        self.disconnect_btn.clicked.connect(self._disconnect)

        self.enable_checkbox.toggled.connect(self._on_enable_changed)
        self.mode_combo.currentTextChanged.connect(self._on_mode_changed)
        self.intensity_slider.valueChanged.connect(self._on_intensity_changed)
        self.frequency_slider.valueChanged.connect(self._on_frequency_changed)
        self.brake_threshold.valueChanged.connect(self._on_threshold_changed)
        self.open_ramp_ms.valueChanged.connect(self._on_open_ramp_changed)
        self.close_ramp_ms.valueChanged.connect(self._on_close_ramp_changed)
        self.test_pulse_btn.clicked.connect(self._on_test_pulse)
        self.save_defaults_btn.clicked.connect(self._on_save_defaults)

        # Initialize
        self._refresh_ports()
        self._update_values_labels()

    def _update_values_labels(self):
        self.intensity_value.setText(f"{self.intensity_slider.value()}%")
        self.frequency_value.setText(f"{self.frequency_slider.value()} Hz")

    def _refresh_ports(self):
        self.port_combo.clear()
        if list_ports is None:
            self.port_combo.addItem("pyserial not installed")
            self.status_label.setText("pyserial not installed")
            self.status_label.setStyleSheet("color: #6b7280;")
            return
        try:
            ports = list(list_ports.comports())
            for p in ports:
                display = f"{p.device} - {p.description}"
                self.port_combo.addItem(display, p.device)
            if not ports:
                self.port_combo.addItem("No ports found")
        except Exception as e:
            self.port_combo.addItem("Error listing ports")
            self.status_label.setText(f"Port scan error: {e}")
            self.status_label.setStyleSheet("color: #ef4444;")

    def _connect(self):
        if serial is None or list_ports is None:
            self.status_label.setText("pyserial not available")
            self.status_label.setStyleSheet("color: #ef4444;")
            return
        try:
            idx = self.port_combo.currentIndex()
            port = self.port_combo.itemData(idx) or self.port_combo.currentText().split(" ")[0]
            baud = int(self.baud_input.text().strip() or "115200")
            self._serial = serial.Serial(port=port, baudrate=baud, timeout=0.2)
            self._connected = True
            self._port_name = port
            self._baud_rate = baud
            self.status_label.setText(f"Connected: {port} @ {baud}")
            self.status_label.setStyleSheet("color: #22c55e;")
            self.connect_btn.setEnabled(False)
            self.disconnect_btn.setEnabled(True)
            self._heartbeat_timer.start()
            # Send initial state
            self._apply_all_settings()
        except Exception as e:
            self._connected = False
            self._serial = None
            self.status_label.setText(f"Connect failed: {e}")
            self.status_label.setStyleSheet("color: #ef4444;")

    def _disconnect(self):
        self._heartbeat_timer.stop()
        try:
            if self._serial:
                self._serial.close()
        except Exception:
            pass
        self._serial = None
        self._connected = False
        self.connect_btn.setEnabled(True)
        self.disconnect_btn.setEnabled(False)
        self.status_label.setText("Disconnected")
        self.status_label.setStyleSheet("color: #ef4444;")

    def _send(self, line: str):
        if not self._connected or not self._serial:
            return
        try:
            payload = (line.strip() + "\n").encode("utf-8")
            # Non-blocking-ish write: guard against long driver stalls
            try:
                self._serial.write_timeout = 0.05
            except Exception:
                pass
            self._serial.write(payload)
        except Exception as e:
            self.status_label.setText(f"Send error: {e}")
            self.status_label.setStyleSheet("color: #ef4444;")

    def _send_heartbeat(self):
        self._send("PING")

    def _apply_all_settings(self):
        self._on_enable_changed(self.enable_checkbox.isChecked())
        self._on_mode_changed(self.mode_combo.currentText())
        self._on_intensity_changed(self.intensity_slider.value())
        self._on_frequency_changed(self.frequency_slider.value())
        self._on_threshold_changed(self.brake_threshold.value())
        self._on_open_ramp_changed(self.open_ramp_ms.value())
        self._on_close_ramp_changed(self.close_ramp_ms.value())

    # Event handlers -> device commands
    def _on_enable_changed(self, enabled: bool):
        self._send(f"ABS_ENABLE={1 if enabled else 0}")

    def _on_mode_changed(self, mode: str):
        self._send(f"ABS_MODE={mode.upper()}")

    def _on_intensity_changed(self, val: int):
        self.intensity_value.setText(f"{val}%")
        self._send(f"ABS_INTENSITY={val}")

    def _on_frequency_changed(self, val: int):
        self.frequency_value.setText(f"{val} Hz")
        self._send(f"ABS_FREQUENCY_HZ={val}")

    def _on_threshold_changed(self, val: int):
        self._send(f"ABS_BRAKE_START_PCT={val}")

    def _on_open_ramp_changed(self, val: int):
        self._send(f"ABS_OPEN_RAMP_MS={val}")

    def _on_close_ramp_changed(self, val: int):
        self._send(f"ABS_CLOSE_RAMP_MS={val}")

    def _on_test_pulse(self):
        self._send("ABS_TEST_PULSE=1")

    def _on_save_defaults(self):
        self._send("ABS_SAVE_DEFAULTS=1")