import logging
import time
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLineEdit, QPushButton, QComboBox, QLabel
from PyQt6.QtCore import pyqtSignal
from ...modern.shared.base_page import GlobalManagers

logger = logging.getLogger(__name__)

class CurveManagerWidget(QWidget):
    curve_saved = pyqtSignal(str, str)
    curve_deleted = pyqtSignal(str, str)
    curve_changed = pyqtSignal(str)
    
    def __init__(self, pedal_name: str, global_managers: GlobalManagers = None):
        super().__init__()
        self.pedal_name = pedal_name
        self.global_managers = global_managers
        
        self.curve_name_input = None
        self.custom_curves_selector = None
        
        # Debounce cache invalidation to prevent excessive invalidation
        self._last_inval = {}
        
        self.init_ui()
        
        # Load existing curve data from hardware
        self.load_existing_curve_data()
    
    def _debounced_cache_invalidate(self, pedal_name: str, curve_cache):
        """Debounce cache invalidation: only once per pedal per second."""
        now = time.monotonic()
        last = self._last_inval.get(pedal_name, 0)
        if now - last > 1.0:
            curve_cache.invalidate_pedal(pedal_name)
            self._last_inval[pedal_name] = now
            logger.info(f"🔄 Invalidated curve cache for {pedal_name}")
    
    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)
        
        group = QGroupBox("Curve Management")
        group.setMaximumHeight(90)
        group.setStyleSheet("""
            QGroupBox {
                border: 1px solid #666666;
                border-radius: 4px;
                margin-top: 1ex;
                font-weight: bold;
                color: #fefefe;
                background-color: #252525;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)
        group_layout = QVBoxLayout()
        group_layout.setSpacing(6)
        group_layout.setContentsMargins(8, 8, 8, 8)
        group.setLayout(group_layout)
        
        # Save curve section - compact horizontal layout
        save_layout = QHBoxLayout()
        save_layout.setSpacing(6)
        curve_name_label = QLabel("Curve Name:")
        curve_name_label.setMaximumWidth(80)
        curve_name_label.setStyleSheet("""
            QLabel {
                background-color: transparent;
                color: #fefefe;
                font-size: 11px;
                padding: 3px 4px;
                margin: 1px 0px;
            }
        """)
        self.curve_name_input = QLineEdit()
        self.curve_name_input.setPlaceholderText("Enter custom curve name...")
        self.curve_name_input.setMaximumHeight(22)
        self.curve_name_input.setStyleSheet("""
            QLineEdit {
                background-color: #252525;
                border: 1px solid #666666;
                border-radius: 3px;
                padding: 4px 8px;
                color: #fefefe;
                font-size: 11px;
            }
            QLineEdit:focus {
                border-color: #fba43b;
            }
            QLineEdit::placeholder {
                color: #999999;
            }
        """)
        save_curve_btn = QPushButton("Save Current Curve")
        save_curve_btn.setMaximumHeight(22)
        save_curve_btn.setStyleSheet("""
            QPushButton {
                background-color: #2a82da;
                color: white;
                font-size: 11px;
                font-weight: bold;
                padding: 2px 8px;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #3498db;
            }
        """)
        save_curve_btn.clicked.connect(self.save_custom_curve)
        
        save_layout.addWidget(curve_name_label)
        save_layout.addWidget(self.curve_name_input)
        save_layout.addWidget(save_curve_btn)
        
        # Load curve section - compact horizontal layout
        load_layout = QHBoxLayout()
        load_layout.setSpacing(6)
        curve_selector_label = QLabel("Load Curve:")
        curve_selector_label.setMaximumWidth(80)
        curve_selector_label.setStyleSheet("""
            QLabel {
                background-color: transparent;
                color: #fefefe;
                font-size: 11px;
                padding: 3px 4px;
                margin: 1px 0px;
            }
        """)
        self.custom_curves_selector = QComboBox()
        self.custom_curves_selector.setMaximumHeight(22)
        self.custom_curves_selector.setStyleSheet("""
            QComboBox {
                background-color: #252525;
                border: 1px solid #666666;
                border-radius: 3px;
                padding: 4px 8px;
                color: #fefefe;
                font-size: 11px;
            }
            QComboBox:focus {
                border-color: #fba43b;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid #fefefe;
            }
        """)
        delete_curve_btn = QPushButton("Delete Selected")
        delete_curve_btn.setMaximumHeight(22)
        delete_curve_btn.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                font-size: 11px;
                font-weight: bold;
                padding: 2px 8px;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
        """)
        delete_curve_btn.clicked.connect(self.delete_selected_curve)
        
        load_layout.addWidget(curve_selector_label)
        load_layout.addWidget(self.custom_curves_selector)
        load_layout.addWidget(delete_curve_btn)
        
        group_layout.addLayout(save_layout)
        group_layout.addLayout(load_layout)
        layout.addWidget(group)
        
        # Populate the curve selector
        self.refresh_custom_curves()
        
    def load_existing_curve_data(self):
        """Load existing curve data from hardware input."""
        try:
            if not self.global_managers:
                return
                
            hardware = getattr(self.global_managers, 'hardware', None)
            if not hardware:
                return
                
            # Refresh the curve list to show available curves from hardware
            self.refresh_custom_curves()
            
            # Load the currently selected curve if it exists
            if hasattr(hardware, 'calibration') and hardware.calibration:
                pedal_calibration = hardware.calibration.get(self.pedal_name, {})
                if pedal_calibration:
                    current_curve = pedal_calibration.get('curve', 'Linear (Default)')
                    
                    # Try to set the current curve in the selector
                    if self.custom_curves_selector:
                        for i in range(self.custom_curves_selector.count()):
                            if self.custom_curves_selector.itemText(i) == current_curve:
                                self.custom_curves_selector.setCurrentIndex(i)
                                logger.info(f"Set current curve for {self.pedal_name}: {current_curve}")
                                break
                                
        except Exception as e:
            logger.debug(f"Failed to load existing curve data for {self.pedal_name}: {e}")
        
        # Connect curve selection change
        self.custom_curves_selector.currentTextChanged.connect(self.on_curve_selected)
    
    def set_global_pedal_system(self, hardware, output, data_queue):
        """Update the hardware input when it becomes available."""
        # Store the hardware reference for potential future use
        self.hardware_input = hardware
        logger.info(f"✅ Hardware input updated for {self.pedal_name} curve manager widget")
    
    def save_custom_curve(self):
        curve_name = self.curve_name_input.text().strip()
        if not curve_name:
            logger.warning(f"Cannot save curve for {self.pedal_name}: empty name")
            return
        
        if curve_name in self.get_default_curves():
            logger.warning(f"Cannot save curve for {self.pedal_name}: '{curve_name}' conflicts with default curve")
            return
        
        logger.info(f"Saving custom curve '{curve_name}' for {self.pedal_name}")
        
        # Save the curve directly to hardware 
        if self.global_managers and hasattr(self.global_managers, 'hardware'):
            hardware = self.global_managers.hardware
            if hardware and hasattr(hardware, 'save_custom_curve'):
                try:
                    # Get current calibration data to save with the curve
                    current_calibration = hardware.calibration.get(self.pedal_name, {})
                    points = current_calibration.get('points', [[0,0],[25,25],[50,50],[75,75],[100,100]])
                    curve_type = current_calibration.get('curve', 'Linear (Default)')
                    
                    # Save to hardware (which handles cloud sync)
                    hardware.save_custom_curve(self.pedal_name, curve_name, points, curve_type)
                    logger.info(f"✅ Saved custom curve '{curve_name}' for {self.pedal_name} to hardware")
                    
                    # Debounce cache invalidation: only once per pedal per second
                    if hasattr(hardware, 'curve_cache'):
                        self._debounced_cache_invalidate(self.pedal_name, hardware.curve_cache)
                    
                except Exception as e:
                    logger.error(f"Failed to save custom curve '{curve_name}' for {self.pedal_name}: {e}")
        
        self.curve_saved.emit(self.pedal_name, curve_name)
        self.curve_name_input.clear()
        self.refresh_custom_curves()
    
    def delete_selected_curve(self):
        selected_curve = self.custom_curves_selector.currentText()
        if selected_curve == "No custom curves" or selected_curve == "New...":
            return
            
        # Don't allow deletion of default curves
        if selected_curve in self.get_default_curves():
            logger.warning(f"Cannot delete default curve: '{selected_curve}'")
            return
        
        logger.info(f"Deleting custom curve '{selected_curve}' for {self.pedal_name}")
        
        # Delete the curve directly from hardware
        if self.global_managers and hasattr(self.global_managers, 'hardware'):
            hardware = self.global_managers.hardware
            if hardware and hasattr(hardware, 'delete_custom_curve'):
                try:
                    hardware.delete_custom_curve(self.pedal_name, selected_curve)
                    logger.info(f"✅ Deleted custom curve '{selected_curve}' for {self.pedal_name} from hardware")
                    
                    # Debounce cache invalidation: only once per pedal per second
                    if hasattr(hardware, 'curve_cache'):
                        self._debounced_cache_invalidate(self.pedal_name, hardware.curve_cache)
                    
                    # Also clear any cached calibration data for this pedal
                    if hasattr(hardware, 'calibration') and self.pedal_name in hardware.calibration:
                        # Keep the current calibration but ensure stale curve references are cleared
                        current_cal = hardware.calibration.get(self.pedal_name, {})
                        if current_cal.get('curve_type') == selected_curve:
                            # Reset to linear if we deleted the currently selected curve
                            current_cal['curve_type'] = 'Linear (Default)'
                            logger.info(f"Reset {self.pedal_name} to Linear after deleting active curve '{selected_curve}'")
                        
                except Exception as e:
                    logger.error(f"Failed to delete custom curve '{selected_curve}' for {self.pedal_name}: {e}")
        
        self.curve_deleted.emit(self.pedal_name, selected_curve)
        self.refresh_custom_curves()
    
    def refresh_custom_curves(self):
        current_text = self.custom_curves_selector.currentText()
        self.custom_curves_selector.clear()
        
        # Force cache invalidation before refreshing to ensure we get latest data
        if self.global_managers and hasattr(self.global_managers, 'hardware'):
            hardware = self.global_managers.hardware
            if hardware and hasattr(hardware, 'curve_cache'):
                self._debounced_cache_invalidate(self.pedal_name, hardware.curve_cache)
        
        # Always include a safe "New..." option first so users don't overwrite by accident
        self.custom_curves_selector.addItem("New...")
        self.custom_curves_selector.setEnabled(True)
        
        custom_curves = self.get_custom_curves()
        logger.info(f"Found {len(custom_curves)} custom curves for {self.pedal_name}: {custom_curves}")
        
        if custom_curves:
            self.custom_curves_selector.addItems(custom_curves)
            # Restore selection when possible (avoid auto-selecting a curve if user was on New...)
            if current_text and current_text in (["New..."] + custom_curves):
                self.custom_curves_selector.setCurrentText(current_text)
            else:
                self.custom_curves_selector.setCurrentText("New...")
        else:
            # No saved curves yet; keep only New...
            self.custom_curves_selector.setCurrentText("New...")
    

    def get_default_curves(self):
        if self.pedal_name == 'brake':
            return ["Linear (Default)", "Threshold", "Trail Brake", "Endurance", "Rally", "ABS Friendly"]
        elif self.pedal_name == 'throttle':
            return ["Linear (Default)", "Track Mode", "Turbo Lag", "NA Engine", "Feathering", "Progressive"]
        elif self.pedal_name == 'clutch':
            return ["Linear (Default)", "Quick Engage", "Heel-Toe", "Bite Point Focus"]
        else:
            return ["Linear (Default)", "Progressive", "Threshold"]
    
    def get_custom_curves(self):
        try:
            # Prefer a directly injected hardware reference, otherwise ask global managers
            hardware = getattr(self, 'hardware_input', None)
            if not hardware and getattr(self, 'global_managers', None):
                hardware = getattr(self.global_managers, 'hardware', None)
                
            logger.debug(f"Getting custom curves for {self.pedal_name}, hardware available: {hardware is not None}")

            if hardware and hasattr(hardware, 'list_available_curves'):
                curves = hardware.list_available_curves(self.pedal_name) or []
                logger.debug(f"Hardware returned {len(curves)} curves for {self.pedal_name}: {curves}")
                
                # Filter out built-in preset names; only show user-saved curves here
                presets = set(self._default_preset_names(self.pedal_name))
                filtered = [c for c in curves if isinstance(c, str) and c.strip() and c not in presets]
                logger.debug(f"After filtering presets, {len(filtered)} custom curves remain: {filtered}")
                return filtered
            else:
                logger.warning(f"No hardware available or list_available_curves method missing for {self.pedal_name}")
        except Exception as e:
            logger.error(f"Failed to load custom curves for {self.pedal_name}: {e}")
        return []

    def _default_preset_names(self, pedal: str):
        if pedal == 'throttle':
            return [
                'Racing', 'Smooth', 'Aggressive', 'Precision Control', 'Traction Limited',
                'Quick Response', 'Rain Mode', 'Drift Control', 'F1 Style', 'Rally',
                'Dirt Track', 'Super Precise', 'Wet Weather Racing', 'Light Rain', 'Extreme Wet'
            ]
        if pedal == 'brake':
            return [
                'Hard Braking', 'Progressive', 'Trail Braking', 'Wet Weather', 'Wet Racing',
                'Wet Circuit', 'Extreme Wet Braking', 'Initial Bite', 'GT3 Racing', 'Endurance',
                'Technical Circuit', 'Oval Track', 'Street Car'
            ]
        if pedal == 'clutch':
            return [
                'Quick Engage', 'Gradual', 'Race Start', 'Slip Control', 'Bite Point Focus',
                'Drift Initiation', 'Smooth Launch', 'Performance Launch', 'Drag Racing',
                'Heel-Toe', 'Rally Start', 'Half Clutch Control', 'Wet Weather Launch',
                'Wet Track Control', 'Wet Engagement'
            ]
        return []
    
    def add_custom_curve(self, curve_name: str):
        self.refresh_custom_curves()
        if curve_name in [self.custom_curves_selector.itemText(i) for i in range(self.custom_curves_selector.count())]:
            self.custom_curves_selector.setCurrentText(curve_name)
    
    def remove_custom_curve(self, curve_name: str):
        self.refresh_custom_curves()
    
    def on_curve_selected(self, curve_name: str):
        """Handle curve selection change."""
        if not curve_name:
            return
        if curve_name == "New...":
            # Prepare for creating a new curve name without changing current calibration
            try:
                if self.curve_name_input:
                    self.curve_name_input.clear()
                    self.curve_name_input.setFocus()
            except Exception:
                pass
            return
        
        # User selected an actual curve to load
        if curve_name and curve_name != "No custom curves":
            logger.info(f"Curve selected for {self.pedal_name}: {curve_name}")
            
            # Load the curve data directly to the hardware
            if self.global_managers and hasattr(self.global_managers, 'hardware'):
                hardware = self.global_managers.hardware
                if hardware and hasattr(hardware, 'load_custom_curve'):
                    try:
                        curve_data = hardware.load_custom_curve(self.pedal_name, curve_name)
                        if curve_data:
                            # Use the hardware method to properly apply the curve AND deadzones
                            if hardware.apply_curve_to_calibration(self.pedal_name, curve_name):
                                logger.info(f"✅ Loaded and applied curve '{curve_name}' for {self.pedal_name}")
                                # Emit signal so the UI can refresh with the newly applied data
                                self.curve_changed.emit(curve_name)
                            else:
                                logger.error(f"❌ Failed to apply curve '{curve_name}' to hardware")

                        else:
                            logger.warning(f"❌ Failed to load curve data for '{curve_name}'")
                    except Exception as e:
                        logger.error(f"❌ Failed to load curve '{curve_name}': {e}")
            
            self.curve_changed.emit(curve_name)
    
