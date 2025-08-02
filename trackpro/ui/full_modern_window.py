import logging
from pathlib import Path
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QStackedWidget,
    QLabel, QPushButton, QFrame, QProgressBar, QComboBox, QLineEdit, QGroupBox)
from PyQt6.QtCore import Qt, pyqtSignal, QPointF, QTimer
from PyQt6.QtGui import QFont

try:
    from .performance_manager import PerformanceManager, ThreadPriorityManager, CPUCoreManager, ChartOptimizer
except ImportError:
    PerformanceManager = None
    ThreadPriorityManager = None
    CPUCoreManager = None
    ChartOptimizer = None
try:
    from .custom_widgets import QCustomQStackedWidget
    from .discord_navigation import DiscordNavigation
except ImportError:
    QCustomQStackedWidget = None
    DiscordNavigation = None
try:
    from .chart_widgets import IntegratedCalibrationChart
except ImportError:
    IntegratedCalibrationChart = None
logger = logging.getLogger(__name__)

class FullModernWindow(QMainWindow):
    calibration_updated = pyqtSignal(str)
    auth_state_changed = pyqtSignal(bool)
    window_state_changed = pyqtSignal(object)
    output_changed = pyqtSignal(str, int, int, int)
    calibration_wizard_completed = pyqtSignal(dict)
    
    def __init__(self, parent=None, oauth_handler=None):
        super().__init__(parent)
        self.oauth_handler = oauth_handler
        self.ui_resources_path = Path(__file__).parent.parent.parent / "ui_resources"
        self.theme_engine = None
        self.icon_manager = None
        self.theme_manager = None
        self.left_menu = None
        self.content_stack = None
        self.pages = {}
        self._pedal_data = {'throttle': {}, 'brake': {}, 'clutch': {}}
        self.pedal_groups = {}
        self.hardware = None
        self.app_instance = None
        
        self.init_performance_optimization()
        self.init_modern_ui()
    
    def init_performance_optimization(self):
        try:
            if CPUCoreManager:
                CPUCoreManager.set_process_affinity()
                recommendations = CPUCoreManager.get_performance_recommendations()
                for rec in recommendations:
                    logger.info(rec)
            
            if ThreadPriorityManager:
                ThreadPriorityManager.set_ui_thread_priority()
            
            if PerformanceManager:
                self.performance_manager = PerformanceManager()
                self.performance_manager.ui_update_ready.connect(self.handle_optimized_ui_update)
                self.performance_manager.performance_warning.connect(self.handle_performance_warning)
                logger.info("🚀 PERFORMANCE: Modern UI optimized for ultra-smooth operation")
            else:
                self.performance_manager = None
                logger.warning("Performance manager not available - using basic UI updates")
            
            if ChartOptimizer:
                self.chart_optimizer = ChartOptimizer()
                logger.info("📊 CHARTS: Optimized rendering with frame rate limiting")
            else:
                self.chart_optimizer = None
                
        except Exception as e:
            logger.error(f"Performance optimization setup failed: {e}")
            self.performance_manager = None
            self.chart_optimizer = None
    
    def handle_optimized_ui_update(self, pedal_data):
        try:
            for pedal, value in pedal_data.items():
                if pedal in self._pedal_data:
                    self.set_input_value(pedal, value)
        except Exception as e:
            logger.error(f"Error in optimized UI update: {e}")
    
    def handle_performance_warning(self, warning_type: str, time_ms: float):
        if time_ms > 20.0:
            logger.warning(f"⚠️ PERFORMANCE WARNING: {warning_type} took {time_ms:.1f}ms (target <16ms)")
        
    def init_modern_ui(self):
        try:
            self.setWindowTitle("TrackPro V1.5.5")
            self.setMinimumSize(1200, 800)
            self.resize(1400, 900)
            self.create_main_layout()
            self.create_pages()
            self.content_stack.setCurrentIndex(0)
            logger.info("Full modern UI initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing full modern UI: {e}")
            self.create_fallback_ui()
    
    def create_main_layout(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        if DiscordNavigation:
            try:
                self.left_menu = DiscordNavigation()
                self.left_menu.page_requested.connect(self.switch_to_page)
            except Exception as e:
                logger.error(f"Error creating Discord navigation: {e}")
                self.left_menu = self.create_basic_menu()
        else:
            self.left_menu = self.create_basic_menu()
        
        if QCustomQStackedWidget:
            try:
                self.content_stack = QCustomQStackedWidget(transition_type="slide_horizontal", animation_duration=250)
            except Exception as e:
                logger.error(f"Error creating custom stacked widget: {e}")
                self.content_stack = QStackedWidget()
        else:
            self.content_stack = QStackedWidget()
        
        main_layout.addWidget(self.left_menu)
        main_layout.addWidget(self.content_stack, 1)
    
    def create_basic_menu(self):
        menu_widget = QWidget()
        menu_widget.setFixedWidth(250)
        menu_widget.setStyleSheet("QWidget { background-color: #2c3e50; color: white; }")
        menu_layout = QVBoxLayout(menu_widget)
        menu_layout.setContentsMargins(10, 20, 10, 20)
        menu_layout.setSpacing(5)
        
        title = QLabel("TrackPro")
        title.setStyleSheet("QLabel { font-size: 18px; font-weight: bold; color: #ecf0f1; padding: 10px; border-bottom: 2px solid #34495e; margin-bottom: 20px; }")
        menu_layout.addWidget(title)
        
        menu_items = [
            {"text": "🏠 Home", "page": "home"},
            {"text": "🦶 Pedals", "page": "pedals"},
            {"text": "🤚 Handbrake", "page": "handbrake"},
            {"text": "🏁 Race Coach", "page": "race_coach"},
            {"text": "🎟️ Race Pass", "page": "race_pass"},
            {"text": "👥 Community", "page": "community"},
            {"text": "❓ Support", "page": "support"},
            {"text": "👤 Account", "page": "account"}
        ]
        
        for item in menu_items:
            btn = QPushButton(item["text"])
            btn.setStyleSheet("QPushButton { background-color: transparent; color: #ecf0f1; border: none; padding: 12px 20px; text-align: left; font-size: 14px; border-radius: 5px; } QPushButton:hover { background-color: #34495e; } QPushButton:pressed { background-color: #3498db; }")
            btn.clicked.connect(lambda checked, page=item["page"]: self.switch_to_page(page))
            menu_layout.addWidget(btn)
        
        menu_layout.addStretch()
        return menu_widget
    
    def create_pages(self):
        self.pages["home"] = self.create_home_page()
        self.content_stack.addWidget(self.pages["home"])
        self.pages["pedals"] = self.create_full_pedals_page()
        self.content_stack.addWidget(self.pages["pedals"])
        self.pages["handbrake"] = self.create_handbrake_page()
        self.content_stack.addWidget(self.pages["handbrake"])
        self.pages["race_coach"] = self.create_race_coach_page()
        self.content_stack.addWidget(self.pages["race_coach"])
        self.pages["race_pass"] = self.create_race_pass_page()
        self.content_stack.addWidget(self.pages["race_pass"])
        self.pages["community"] = self.create_community_page()
        self.content_stack.addWidget(self.pages["community"])
        self.pages["support"] = self.create_support_page()
        self.content_stack.addWidget(self.pages["support"])
        self.pages["account"] = self.create_account_page()
        self.content_stack.addWidget(self.pages["account"])
    
    def create_home_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(40, 40, 40, 40)
        
        header = QLabel("TrackPro Dashboard")
        header.setStyleSheet("QLabel { font-size: 28px; font-weight: bold; color: #2c3e50; margin-bottom: 20px; }")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header)
        
        welcome = QLabel("Welcome to the Modern TrackPro Interface!")
        welcome.setAlignment(Qt.AlignmentFlag.AlignCenter)
        welcome.setStyleSheet("QLabel { font-size: 16px; color: #7f8c8d; margin-bottom: 30px; }")
        layout.addWidget(welcome)
        
        tiles_widget = QWidget()
        tiles_layout = QHBoxLayout(tiles_widget)
        tiles_layout.setSpacing(20)
        
        tile_configs = [
            {"title": "Pedal Setup", "desc": "Configure pedal calibration", "page": "pedals", "color": "#3498db"},
            {"title": "Race Coach", "desc": "AI coaching & telemetry", "page": "race_coach", "color": "#e74c3c"},
            {"title": "Community", "desc": "Connect with racers", "page": "community", "color": "#9b59b6"}
        ]
        
        for config in tile_configs:
            tile = self.create_dashboard_tile(config["title"], config["desc"], config["page"], config["color"])
            tiles_layout.addWidget(tile)
        
        layout.addWidget(tiles_widget)
        layout.addStretch()
        return page
    
    def create_dashboard_tile(self, title: str, description: str, target_page: str, color: str):
        tile = QPushButton()
        tile.setMinimumSize(250, 180)
        tile.setMaximumSize(300, 200)
        tile.setText(f"{title}\n\n{description}")
        tile.setStyleSheet(f"QPushButton {{ background-color: {color}; color: white; border: none; border-radius: 12px; font-size: 14px; font-weight: bold; padding: 20px; }} QPushButton:hover {{ background-color: {color}dd; }} QPushButton:pressed {{ background-color: {color}bb; }}")
        tile.clicked.connect(lambda: self.switch_to_page(target_page))
        return tile
    
    def create_full_pedals_page(self):
        page = QWidget()
        main_layout = QVBoxLayout(page)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(8)
        
        header = QLabel("🦶 Pedal Configuration")
        header.setStyleSheet("font-size: 24px; font-weight: bold; color: #2c3e50; margin-bottom: 10px;")
        main_layout.addWidget(header)
        
        wizard_layout = QHBoxLayout()
        wizard_btn = QPushButton("Calibration Wizard")
        wizard_btn.setMaximumWidth(140)
        wizard_btn.setStyleSheet("QPushButton { background-color: #2a82da; font-size: 11px; font-weight: bold; padding: 6px 12px; max-width: 140px; color: white; border-radius: 3px; } QPushButton:hover { background-color: #3a92ea; }")
        wizard_btn.clicked.connect(self.open_calibration_wizard)
        wizard_layout.addWidget(wizard_btn)
        wizard_layout.addStretch()
        main_layout.addLayout(wizard_layout)
        
        pedals_section_layout = QHBoxLayout()
        pedals_section_layout.setSpacing(8)
        
        for pedal in ['throttle', 'brake', 'clutch']:
            pedal_widget = QWidget()
            pedal_widget.setObjectName(f"{pedal}_widget")
            pedal_layout = QVBoxLayout(pedal_widget)
            pedal_layout.setContentsMargins(5, 5, 5, 5)
            pedal_layout.setSpacing(5)
            self.create_pedal_controls(pedal, pedal_layout)
            pedals_section_layout.addWidget(pedal_widget)
        
        pedals_section_layout.setStretch(0, 1)
        pedals_section_layout.setStretch(1, 1)
        pedals_section_layout.setStretch(2, 1)
        
        main_layout.addLayout(pedals_section_layout)
        main_layout.addStretch()
        return page
    
    def create_pedal_controls(self, pedal_name, parent_layout):
        pedal_key = pedal_name.lower()
        data = self._pedal_data[pedal_key]
        
        # Input Monitor
        input_group = QGroupBox("Input Monitor")
        input_layout = QVBoxLayout()
        input_layout.setContentsMargins(5, 5, 5, 5)
        
        progress = QProgressBar()
        progress.setRange(0, 65535)
        progress.setMinimumHeight(22)
        progress.setStyleSheet("""
            QProgressBar {
                border: 1px solid #444;
                border-radius: 2px;
                text-align: center;
                background-color: #222;
            }
            QProgressBar::chunk {
                background-color: #2a82da;
            }
        """)
        input_layout.addWidget(progress)
        data['input_progress'] = progress
        
        label = QLabel("Raw Input: 0")
        label.setStyleSheet("font-weight: bold;")
        input_layout.addWidget(label)
        data['input_label'] = label
        
        input_group.setLayout(input_layout)
        parent_layout.addWidget(input_group)
        
        parent_layout.addSpacing(5)
        
        self.pedal_groups[pedal_key] = input_group
        
        # Calibration
        cal_group = QGroupBox("Calibration")
        cal_layout = QVBoxLayout()
        cal_layout.setContentsMargins(5, 5, 5, 5)
        cal_layout.setSpacing(5)
        
        logger.info(f"Creating IntegratedCalibrationChart for {pedal_name}")
        try:
            if IntegratedCalibrationChart:
                calibration_chart = IntegratedCalibrationChart(
                    cal_layout, 
                    pedal_name,
                    lambda: self.on_point_moved(pedal_key)
                )
                logger.info(f"Successfully created IntegratedCalibrationChart for {pedal_name}")
                data['calibration_chart'] = calibration_chart
            else:
                chart_widget = self.create_simple_calibration_chart(pedal_name)
                cal_layout.addWidget(chart_widget)
                data['calibration_chart'] = chart_widget
        except Exception as e:
            logger.error(f"Failed to create IntegratedCalibrationChart for {pedal_name}: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            chart_widget = self.create_simple_calibration_chart(pedal_name)
            cal_layout.addWidget(chart_widget)
            data['calibration_chart'] = chart_widget
        
        if data['calibration_chart'] is not None and hasattr(data['calibration_chart'], 'chart_view'):
            try:
                data['calibration_chart'].chart_view.setContentsMargins(10, 0, 10, 10)
            except Exception as e:
                logger.error(f"Failed to set chart margins: {e}")
                pass
            
        cal_layout.addSpacing(10)
        
        controls_layout = QVBoxLayout()
        controls_layout.setContentsMargins(5, 20, 5, 5)
        controls_layout.setSpacing(12)
        
        labels_row = QHBoxLayout()
        labels_row.setSpacing(10)
        
        min_label = QLabel("Min: 0")
        labels_row.addWidget(min_label, 1)
        
        max_label = QLabel("Max: 65535")
        labels_row.addWidget(max_label, 1)
        
        reset_label = QLabel("Reset Curve")
        labels_row.addWidget(reset_label, 1)
        
        labels_row.addStretch(1)
        
        curve_label = QLabel("Curve Type")
        labels_row.addWidget(curve_label, 2)
        
        controls_layout.addLayout(labels_row)
        
        controls_row = QHBoxLayout()
        controls_row.setSpacing(10)
        
        set_min_btn = QPushButton("Set Min")
        set_min_btn.clicked.connect(lambda: self.set_current_as_min(pedal_key))
        set_min_btn.setFixedHeight(27)
        controls_row.addWidget(set_min_btn, 1)
        
        set_max_btn = QPushButton("Set Max")
        set_max_btn.clicked.connect(lambda: self.set_current_as_max(pedal_key))
        set_max_btn.setFixedHeight(27)
        controls_row.addWidget(set_max_btn, 1)
        
        reset_btn = QPushButton("Reset")
        reset_btn.clicked.connect(lambda: self.reset_calibration(pedal_key))
        reset_btn.setFixedHeight(27)
        controls_row.addWidget(reset_btn, 1)
        
        controls_row.addStretch(1)
        
        curve_selector = QComboBox()
        pedal_curves = self.get_pedal_curves(pedal_key)
        curve_selector.addItems(pedal_curves)
        curve_selector.setCurrentText("Linear (Default)")
        
        curve_selector.setMinimumWidth(130)
        curve_selector.setMaximumWidth(140)
        curve_selector.setFixedHeight(27)
        
        curve_selector.setStyleSheet("""
            QComboBox {
                background-color: #444444;
                border: 1px solid #777777;
                border-radius: 4px;
                color: white;
                padding: 0px 5px;
                height: 27px;
                max-height: 27px;
                min-height: 27px;
                font-size: 12px;
                text-align: left;
            }
            
            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: right center;
                width: 15px;
                height: 20px;
                border: none;
                background: transparent;
            }
            
            QComboBox::down-arrow {
                width: 0;
                height: 0;
                border: 4px solid transparent;
                border-top: 4px solid #aaa;
                margin-right: 2px;
            }
            
            QComboBox QAbstractItemView {
                background-color: #444444;
                border: 1px solid #777777;
                selection-background-color: #2a82da;
                selection-color: white;
                color: white;
                padding: 1px;
            }
        """)
        
        curve_selector.currentTextChanged.connect(lambda text: self.on_curve_type_changed(pedal_key, text))
        
        controls_row.addWidget(curve_selector, 2)
        
        controls_layout.addLayout(controls_row)
        
        controls_layout.addSpacing(10)
        
        data['curve_type_selector'] = curve_selector
        
        logger.info(f"[{pedal_key}] Creating curve_type_selector with ID: {id(curve_selector)}")
        
        data['min_label'] = min_label
        data['max_label'] = max_label
        data['min_value'] = 0
        data['max_value'] = 65535
        
        set_min_btn.setFixedHeight(27)
        set_max_btn.setFixedHeight(27)
        reset_btn.setFixedHeight(27)
        
        min_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        max_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        reset_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        curve_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        cal_layout.addLayout(controls_layout)
        cal_layout.addSpacing(5)
        
        cal_group.setLayout(cal_layout)
        parent_layout.addWidget(cal_group)
        
        deadzone_group = QGroupBox("Deadzone Controls")
        deadzone_layout = QVBoxLayout()
        
        deadzone_controls = QHBoxLayout()
        
        min_deadzone_layout = QVBoxLayout()
        min_deadzone_label = QLabel("Min Deadzone: 0%")
        min_deadzone_controls = QHBoxLayout()
        min_deadzone_minus = QPushButton("-")
        min_deadzone_plus = QPushButton("+")
        min_deadzone_minus.setFixedSize(25, 25)
        min_deadzone_plus.setFixedSize(25, 25)
        min_deadzone_controls.addWidget(min_deadzone_minus)
        min_deadzone_controls.addWidget(min_deadzone_plus)
        min_deadzone_layout.addWidget(min_deadzone_label)
        min_deadzone_layout.addLayout(min_deadzone_controls)
        
        max_deadzone_layout = QVBoxLayout()
        max_deadzone_label = QLabel("Max Deadzone: 0%")
        max_deadzone_controls = QHBoxLayout()
        max_deadzone_minus = QPushButton("-")
        max_deadzone_plus = QPushButton("+")
        max_deadzone_minus.setFixedSize(25, 25)
        max_deadzone_plus.setFixedSize(25, 25)
        max_deadzone_controls.addWidget(max_deadzone_minus)
        max_deadzone_controls.addWidget(max_deadzone_plus)
        max_deadzone_layout.addWidget(max_deadzone_label)
        max_deadzone_layout.addLayout(max_deadzone_controls)
        
        deadzone_controls.addLayout(min_deadzone_layout)
        deadzone_controls.addStretch()
        deadzone_controls.addLayout(max_deadzone_layout)
        
        deadzone_layout.addLayout(deadzone_controls)
        deadzone_group.setLayout(deadzone_layout)
        parent_layout.addWidget(deadzone_group)
        
        output_group = QGroupBox("Output Monitor")
        output_layout = QVBoxLayout()
        output_label = QLabel("Mapped Output: 0")
        output_progress = QProgressBar()
        output_progress.setMaximum(65535)
        output_progress.setValue(0)
        output_layout.addWidget(output_label)
        output_layout.addWidget(output_progress)
        output_group.setLayout(output_layout)
        parent_layout.addWidget(output_group)
        
        curve_manager_group = QGroupBox("Curve Management")
        curve_manager_layout = QVBoxLayout()
        
        curve_name_layout = QHBoxLayout()
        curve_name_input = QLineEdit()
        curve_name_input.setPlaceholderText("Enter curve name...")
        save_curve_btn = QPushButton("Save Curve")
        curve_name_layout.addWidget(curve_name_input)
        curve_name_layout.addWidget(save_curve_btn)
        
        delete_curve_btn = QPushButton("Delete Selected Curve")
        
        curve_manager_layout.addLayout(curve_name_layout)
        curve_manager_layout.addWidget(delete_curve_btn)
        curve_manager_group.setLayout(curve_manager_layout)
        parent_layout.addWidget(curve_manager_group)
        
        data['min_deadzone_label'] = min_deadzone_label
        data['max_deadzone_label'] = max_deadzone_label
        data['min_deadzone'] = 0
        data['max_deadzone'] = 0
        data['output_label'] = output_label
        data['output_progress'] = output_progress
        data['curve_name_input'] = curve_name_input
        
        min_deadzone_minus.clicked.connect(lambda: self.adjust_min_deadzone(pedal_key, -1))
        min_deadzone_plus.clicked.connect(lambda: self.adjust_min_deadzone(pedal_key, 1))
        max_deadzone_minus.clicked.connect(lambda: self.adjust_max_deadzone(pedal_key, -1))
        max_deadzone_plus.clicked.connect(lambda: self.adjust_max_deadzone(pedal_key, 1))
        save_curve_btn.clicked.connect(lambda: self.save_custom_curve(pedal_key))
        delete_curve_btn.clicked.connect(lambda: self.delete_current_curve(pedal_key))
        
    @staticmethod
    def get_pedal_curves(pedal_type):
        if pedal_type == 'brake':
            return ["Linear (Default)", "Threshold", "Trail Brake", "Endurance", "Rally", "ABS Friendly"]
        elif pedal_type == 'throttle':
            return ["Linear (Default)", "Track Mode", "Turbo Lag", "NA Engine", "Feathering", "Progressive"]
        elif pedal_type == 'clutch':
            return ["Linear (Default)", "Quick Engage", "Heel-Toe", "Bite Point Focus"]
        else:
            return ["Linear (Default)", "Progressive", "Threshold"]
    
    def set_input_value(self, pedal: str, value: int):
        try:
            data = self._pedal_data[pedal]
            data['input_value'] = value
            if 'input_progress' in data:
                data['input_progress'].setValue(value)
            if 'input_label' in data:
                data['input_label'].setText(f"Raw Input: {value}")
            
            min_val = data.get('min_value', 0)
            max_val = data.get('max_value', 65535)
            
            if max_val > min_val and 'calibration_chart' in data and data['calibration_chart']:
                normalized = ((value - min_val) / (max_val - min_val)) * 100
                normalized = max(0.0, min(100.0, normalized))
                data['calibration_chart'].set_input_indicator(normalized)
        except Exception as e:
            logger.error(f"Error setting input value for {pedal}: {e}")
    
    def set_calibration_points(self, pedal: str, points):
        try:
            data = self._pedal_data[pedal]
            if 'calibration_chart' in data and data['calibration_chart']:
                data['calibration_chart'].set_points(points)
        except Exception as e:
            logger.error(f"Error setting calibration points for {pedal}: {e}")
    
    def get_calibration_points(self, pedal: str):
        try:
            data = self._pedal_data[pedal]
            if 'calibration_chart' in data and data['calibration_chart']:
                return data['calibration_chart'].get_points()
        except Exception as e:
            logger.error(f"Error getting calibration points for {pedal}: {e}")
        return []
    
    def set_curve_type(self, pedal: str, curve_type: str):
        try:
            data = self._pedal_data[pedal]
            data['curve_type'] = curve_type
            if 'curve_selector' in data:
                data['curve_selector'].setCurrentText(curve_type)
        except Exception as e:
            logger.error(f"Error setting curve type for {pedal}: {e}")
    
    def get_curve_type(self, pedal: str):
        try:
            data = self._pedal_data[pedal]
            return data.get('curve_type', 'Linear (Default)')
        except Exception as e:
            logger.error(f"Error getting curve type for {pedal}: {e}")
        return 'Linear (Default)'
    
    def set_calibration_range(self, pedal: str, min_val: int, max_val: int):
        try:
            data = self._pedal_data[pedal]
            data['min_value'] = min_val
            data['max_value'] = max_val
            if 'min_range_label' in data:
                data['min_range_label'].setText(f"Min: {min_val}")
            if 'max_range_label' in data:
                data['max_range_label'].setText(f"Max: {max_val}")
        except Exception as e:
            logger.error(f"Error setting calibration range for {pedal}: {e}")
    
    def get_calibration_range(self, pedal: str):
        try:
            data = self._pedal_data[pedal]
            return (data.get('min_value', 0), data.get('max_value', 65535))
        except Exception as e:
            logger.error(f"Error getting calibration range for {pedal}: {e}")
        return (0, 65535)
    
    def set_pedal_available(self, pedal: str, available: bool):
        try:
            if pedal in self.pedal_groups:
                self.pedal_groups[pedal].setEnabled(available)
        except Exception as e:
            logger.error(f"Error setting pedal availability for {pedal}: {e}")
    
    def set_current_as_min(self, pedal: str):
        try:
            data = self._pedal_data[pedal]
            current_value = data.get('input_value', 0)
            data['min_value'] = current_value
            if 'min_range_label' in data:
                data['min_range_label'].setText(f"Min: {current_value}")
            self.calibration_updated.emit(pedal)
        except Exception as e:
            logger.error(f"Error setting current as min for {pedal}: {e}")
    
    def set_current_as_max(self, pedal: str):
        try:
            data = self._pedal_data[pedal]
            current_value = data.get('input_value', 0)
            data['max_value'] = current_value
            if 'max_range_label' in data:
                data['max_range_label'].setText(f"Max: {current_value}")
            self.calibration_updated.emit(pedal)
        except Exception as e:
            logger.error(f"Error setting current as max for {pedal}: {e}")
    
    def adjust_min_deadzone(self, pedal: str, direction: int):
        try:
            data = self._pedal_data[pedal]
            current = data.get('min_deadzone', 0)
            new_value = max(0, min(50, current + direction))
            data['min_deadzone'] = new_value
            if 'min_deadzone_label' in data:
                data['min_deadzone_label'].setText(f"Min Deadzone: {new_value}%")
        except Exception as e:
            logger.error(f"Error adjusting min deadzone for {pedal}: {e}")
    
    def adjust_max_deadzone(self, pedal: str, direction: int):
        try:
            data = self._pedal_data[pedal]
            current = data.get('max_deadzone', 0)
            new_value = max(0, min(50, current + direction))
            data['max_deadzone'] = new_value
            if 'max_deadzone_label' in data:
                data['max_deadzone_label'].setText(f"Max Deadzone: {new_value}%")
        except Exception as e:
            logger.error(f"Error adjusting max deadzone for {pedal}: {e}")
    
    def save_custom_curve(self, pedal: str):
        try:
            data = self._pedal_data[pedal]
            if 'curve_name_input' in data:
                curve_name = data['curve_name_input'].text().strip()
                if curve_name:
                    logger.info(f"Saving custom curve '{curve_name}' for {pedal}")
                    data['curve_name_input'].clear()
                    self.refresh_curve_lists()
        except Exception as e:
            logger.error(f"Error saving custom curve for {pedal}: {e}")
    
    def delete_current_curve(self, pedal: str):
        try:
            data = self._pedal_data[pedal]
            if 'curve_selector' in data:
                current_curve = data['curve_selector'].currentText()
                if current_curve and "Custom" in current_curve:
                    logger.info(f"Deleting custom curve '{current_curve}' for {pedal}")
                    self.refresh_curve_lists()
        except Exception as e:
            logger.error(f"Error deleting current curve for {pedal}: {e}")
    
    def refresh_curve_lists(self):
        try:
            for pedal in ['throttle', 'brake', 'clutch']:
                data = self._pedal_data.get(pedal, {})
                if 'curve_selector' in data:
                    current = data['curve_selector'].currentText()
                    data['curve_selector'].clear()
                    curves = self.get_pedal_curves(pedal)
                    data['curve_selector'].addItems(curves)
                    if current in curves:
                        data['curve_selector'].setCurrentText(current)
        except Exception as e:
            logger.error(f"Error refreshing curve lists: {e}")
    
    def set_output_value(self, pedal: str, value: int):
        try:
            data = self._pedal_data[pedal]
            if 'output_progress' in data:
                data['output_progress'].setValue(value)
            if 'output_label' in data:
                data['output_label'].setText(f"Mapped Output: {value}")
        except Exception as e:
            logger.error(f"Error setting output value for {pedal}: {e}")
    
    def reset_calibration(self, pedal: str):
        try:
            data = self._pedal_data[pedal]
            data['min_value'] = 0
            data['max_value'] = 65535
            if 'min_range_label' in data:
                data['min_range_label'].setText("Min: 0")
            if 'max_range_label' in data:
                data['max_range_label'].setText("Max: 65535")
            if 'calibration_chart' in data and data['calibration_chart']:
                data['calibration_chart'].reset_to_linear()
            self.calibration_updated.emit(pedal)
        except Exception as e:
            logger.error(f"Error resetting calibration for {pedal}: {e}")
    
    def on_curve_type_changed(self, pedal: str, curve_type: str):
        if not curve_type or curve_type in ["Loading...", "─── Saved Curves ───"]:
            return
        
        logger.info(f"Curve changed for {pedal}: {curve_type}")
        
        built_in_curves = self.get_pedal_curves(pedal)
        
        if curve_type in built_in_curves:
            self.change_response_curve(pedal, curve_type)
        else:
            logger.warning(f"Custom curve loading not implemented: {curve_type}")
    
    def change_response_curve(self, pedal: str, curve_type: str):
        data = self._pedal_data[pedal]
        data['curve_type'] = curve_type
        
        if 'calibration_chart' not in data:
            return
        
        calibration_chart = data['calibration_chart']
        
        built_in_curves = self.get_pedal_curves(pedal)
        if curve_type in built_in_curves:
            new_points = []
            
            logger.info(f"Generating {curve_type} curve for {pedal}")
            
            import math
            
            if curve_type == "Linear (Default)":
                for i in range(5):
                    x = i * 25
                    y = x
                    new_points.append(QPointF(x, y))
            
            elif curve_type == "Progressive":
                for i in range(5):
                    x = i * 25
                    y = ((x / 100) ** 3) * 100
                    new_points.append(QPointF(x, y))
            
            elif curve_type == "Threshold" and pedal == 'brake':
                points_data = [(0, 0), (20, 5), (50, 30), (80, 85), (100, 100)]
                for x, y in points_data:
                    new_points.append(QPointF(x, y))
            
            elif curve_type == "Track Mode" and pedal == 'throttle':
                points_data = [(0, 0), (15, 2), (40, 25), (70, 65), (100, 100)]
                for x, y in points_data:
                    new_points.append(QPointF(x, y))
            
            else:
                for i in range(5):
                    x = i * 25
                    y = x
                    new_points.append(QPointF(x, y))
            
            if hasattr(calibration_chart, 'set_points'):
                calibration_chart.set_points(new_points)
            
            self.calibration_updated.emit(pedal)
    
    def on_curve_selector_changed(self, pedal: str, curve_name: str):
        self.on_curve_type_changed(pedal, curve_name)
    
    def on_point_moved(self, pedal: str):
        try:
            self.calibration_updated.emit(pedal)
        except Exception as e:
            logger.error(f"Error handling point move for {pedal}: {e}")
    
    def create_simple_calibration_chart(self, pedal_name: str):
        chart_widget = QWidget()
        chart_widget.setMinimumHeight(200)
        chart_widget.setStyleSheet("QWidget { background-color: #f8f9fa; border: 1px solid #dee2e6; border-radius: 4px; }")
        
        chart_layout = QVBoxLayout(chart_widget)
        chart_layout.setContentsMargins(10, 10, 10, 10)
        
        title = QLabel(f"{pedal_name.capitalize()} Response Curve")
        title.setStyleSheet("font-weight: bold; color: #495057; font-size: 12px;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        chart_layout.addWidget(title)
        
        try:
            import pyqtgraph as pg
            plot_widget = pg.PlotWidget()
            plot_widget.setBackground('#ffffff')
            plot_widget.setLabel('left', 'Output (%)', color='#495057')
            plot_widget.setLabel('bottom', 'Input (%)', color='#495057')
            plot_widget.showGrid(x=True, y=True, alpha=0.3)
            plot_widget.setXRange(0, 100, padding=0)
            plot_widget.setYRange(0, 100, padding=0)
            plot_widget.setMinimumHeight(150)
            
            x_data = [0, 25, 50, 75, 100]
            y_data = [0, 25, 50, 75, 100]
            plot_widget.plot(x_data, y_data, pen=pg.mkPen(color='#007bff', width=2), symbol='o', symbolBrush='#007bff', symbolSize=8)
            
            chart_layout.addWidget(plot_widget)
            
        except ImportError:
            fallback_label = QLabel("📊 Calibration Chart\n\nLinear Response Curve\n(0,0) → (100,100)")
            fallback_label.setStyleSheet("color: #6c757d; font-size: 11px; text-align: center; padding: 20px;")
            fallback_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            chart_layout.addWidget(fallback_label)
        
        chart_widget.set_input_indicator = lambda x: None
        chart_widget.set_points = lambda points: None
        chart_widget.get_points = lambda: [(0, 0), (25, 25), (50, 50), (75, 75), (100, 100)]
        chart_widget.reset_to_linear = lambda: None
        
        return chart_widget
    
    def open_calibration_wizard(self):
        try:
            from ..pedals.calibration import CalibrationWizard
            if hasattr(self, 'app_instance') and self.app_instance and hasattr(self.app_instance, 'hardware'):
                wizard = CalibrationWizard(self.app_instance.hardware, self)
                if wizard.exec() == 1:
                    results = wizard.get_results()
                    self.calibration_wizard_completed.emit(results)
            else:
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.warning(self, "Error", "Hardware not available for calibration")
        except ImportError:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Error", "Calibration wizard not available")
        except Exception as e:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Error", f"Failed to open calibration wizard: {str(e)}")
    
    def set_hardware(self, hardware):
        self.hardware = hardware
    
    def refresh_curve_lists(self):
        pass
    
    @property
    def statusBar(self):
        return super().statusBar()
    
    @property 
    def stacked_widget(self):
        return self.content_stack
    
    def create_handbrake_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(20, 20, 20, 20)
        header = QLabel("🤚 Handbrake Setup")
        header.setStyleSheet("font-size: 24px; font-weight: bold; color: #2c3e50;")
        layout.addWidget(header)
        layout.addStretch()
        return page
    
    def create_race_coach_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(20, 20, 20, 20)
        header = QLabel("🏁 Race Coach")
        header.setStyleSheet("font-size: 24px; font-weight: bold; color: #2c3e50;")
        layout.addWidget(header)
        layout.addStretch()
        return page
    
    def create_race_pass_page(self):
        """Create the Race Pass page with full functionality."""
        try:
            # Import and create the actual Race Pass page
            from trackpro.ui.pages.race_pass import RacePassPage
            page = RacePassPage()
            return page
        except Exception as e:
            logger.error(f"Failed to create Race Pass page: {e}")
            # Fallback to simple placeholder
            page = QWidget()
            layout = QVBoxLayout(page)
            layout.setContentsMargins(20, 20, 20, 20)
            header = QLabel("🎟️ Race Pass")
            header.setStyleSheet("font-size: 24px; font-weight: bold; color: #2c3e50;")
            layout.addWidget(header)
            
            error_label = QLabel("Race Pass functionality temporarily unavailable.")
            error_label.setStyleSheet("color: #e74c3c; font-size: 14px; margin-top: 10px;")
            layout.addWidget(error_label)
            layout.addStretch()
            return page
    
    def create_community_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(20, 20, 20, 20)
        header = QLabel("👥 Community")
        header.setStyleSheet("font-size: 24px; font-weight: bold; color: #2c3e50;")
        layout.addWidget(header)
        layout.addStretch()
        return page
    
    def create_support_page(self):
        """Create the Support page with full functionality."""
        try:
            # Import and create the actual Support page
            from trackpro.ui.pages.support import SupportPage
            page = SupportPage()
            return page
        except Exception as e:
            logger.error(f"Failed to create Support page: {e}")
            # Fallback to simple placeholder
            page = QWidget()
            layout = QVBoxLayout(page)
            layout.setContentsMargins(20, 20, 20, 20)
            header = QLabel("❓ Support")
            header.setStyleSheet("font-size: 24px; font-weight: bold; color: #2c3e50;")
            layout.addWidget(header)
            
            error_label = QLabel("Support functionality temporarily unavailable.")
            error_label.setStyleSheet("color: #e74c3c; font-size: 14px; margin-top: 10px;")
            layout.addWidget(error_label)
            layout.addStretch()
            return page
    
    def create_account_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(20, 20, 20, 20)
        header = QLabel("👤 Account")
        header.setStyleSheet("font-size: 24px; font-weight: bold; color: #2c3e50;")
        layout.addWidget(header)
        layout.addStretch()
        return page
    
    def create_fallback_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        label = QLabel("TrackPro - Modern UI failed to load")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(label)
        logger.warning("Using fallback UI due to modern UI initialization failure")
    
    def switch_to_page(self, page_name: str):
        try:
            if page_name in self.pages:
                page_index = list(self.pages.keys()).index(page_name)
                self.content_stack.setCurrentIndex(page_index)
                # Update navigation button state
                if hasattr(self.left_menu, 'set_active_page'):
                    self.left_menu.set_active_page(page_name)
                logger.debug(f"Switched to {page_name} page")
            else:
                logger.warning(f"Page '{page_name}' not found")
        except Exception as e:
            logger.error(f"Error switching to page {page_name}: {e}")