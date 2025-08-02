import logging
from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import pyqtSignal

logger = logging.getLogger(__name__)

class BasePage(QWidget):
    page_activated = pyqtSignal(str)
    data_updated = pyqtSignal(str, object)
    
    def __init__(self, page_name: str, global_managers=None):
        super().__init__()
        self.page_name = page_name
        self.is_initialized = False
        self.global_managers = global_managers
        
        if global_managers:
            self.performance_manager = getattr(global_managers, 'performance', None)
            self.iracing_monitor = getattr(global_managers, 'iracing', None)
            self.hardware_input = getattr(global_managers, 'hardware', None)
            self.theme_engine = getattr(global_managers, 'theme', None)
            self.auth_handler = getattr(global_managers, 'auth', None)
        else:
            self.performance_manager = None
            self.iracing_monitor = None
            self.hardware_input = None
            self.theme_engine = None
            self.auth_handler = None
        
        self.init_page()
    
    def init_page(self):
        raise NotImplementedError("Subclasses must implement init_page()")
    
    def on_page_activated(self):
        if not self.is_initialized:
            self.lazy_init()
            self.is_initialized = True
        self.page_activated.emit(self.page_name)
        logger.info(f"📄 Page activated: {self.page_name}")
    
    def lazy_init(self):
        pass
    
    def cleanup(self):
        pass
    
    def update_data(self, data_type: str, data):
        self.data_updated.emit(data_type, data)

class GlobalManagers:
    def __init__(self):
        self.performance = None
        self.iracing = None
        self.hardware = None
        self.theme = None
        self.auth = None