"""
Lazy Loading Manager - Phase 3 Optimization
Delays initialization of expensive components until actually needed.
"""

import logging
import time
import threading
from typing import Dict, Callable, Any, Optional
from functools import wraps

logger = logging.getLogger(__name__)

class LazyComponent:
    """Wrapper for lazily-loaded components."""
    
    def __init__(self, loader_func: Callable, name: str):
        self.loader_func = loader_func
        self.name = name
        self._instance = None
        self._loading = False
        self._loaded = False
        self._error = None
        self._load_time = None
        self._lock = threading.Lock()
    
    def get_instance(self):
        """Get the component instance, loading it if necessary."""
        if self._loaded:
            return self._instance
        
        with self._lock:
            # Double-check locking pattern
            if self._loaded:
                return self._instance
            
            if self._loading:
                logger.debug(f"Component {self.name} is already loading, waiting...")
                return None
            
            try:
                self._loading = True
                start_time = time.time()
                
                logger.info(f"Lazy loading component: {self.name}")
                self._instance = self.loader_func()
                
                self._load_time = time.time() - start_time
                self._loaded = True
                self._error = None
                
                logger.info(f"Lazy loaded {self.name} in {self._load_time:.2f}s")
                return self._instance
                
            except Exception as e:
                self._error = str(e)
                self._loading = False
                logger.error(f"Failed to lazy load {self.name}: {e}")
                return None
            finally:
                self._loading = False
    
    def is_loaded(self) -> bool:
        """Check if component is loaded."""
        return self._loaded
    
    def get_load_time(self) -> Optional[float]:
        """Get the time it took to load the component."""
        return self._load_time
    
    def get_error(self) -> Optional[str]:
        """Get any loading error."""
        return self._error

class LazyLoadingManager:
    """Manages lazy loading of components."""
    
    def __init__(self):
        self.components: Dict[str, LazyComponent] = {}
        self.load_stats = {}
    
    def register_component(self, name: str, loader_func: Callable) -> LazyComponent:
        """Register a component for lazy loading."""
        component = LazyComponent(loader_func, name)
        self.components[name] = component
        logger.debug(f"Registered lazy component: {name}")
        return component
    
    def get_component(self, name: str) -> Any:
        """Get a component instance, loading if necessary."""
        if name not in self.components:
            logger.error(f"Component {name} not registered for lazy loading")
            return None
        
        return self.components[name].get_instance()
    
    def is_loaded(self, name: str) -> bool:
        """Check if a component is loaded."""
        if name not in self.components:
            return False
        return self.components[name].is_loaded()
    
    def preload_component(self, name: str) -> bool:
        """Preload a component in background."""
        if name not in self.components:
            logger.error(f"Component {name} not registered for lazy loading")
            return False
        
        def background_loader():
            self.components[name].get_instance()
        
        thread = threading.Thread(target=background_loader, daemon=True)
        thread.start()
        return True
    
    def get_load_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get loading statistics for all components."""
        stats = {}
        total_time = 0
        loaded_count = 0
        
        for name, component in self.components.items():
            stats[name] = {
                'loaded': component.is_loaded(),
                'load_time': component.get_load_time(),
                'error': component.get_error()
            }
            
            if component.is_loaded() and component.get_load_time():
                total_time += component.get_load_time()
                loaded_count += 1
        
        stats['_summary'] = {
            'total_components': len(self.components),
            'loaded_components': loaded_count,
            'total_load_time': total_time,
            'average_load_time': total_time / loaded_count if loaded_count > 0 else 0
        }
        
        return stats

# Global lazy loading manager
lazy_loader = LazyLoadingManager()

def lazy_property(loader_func: Callable):
    """Decorator to create a lazy-loaded property."""
    def decorator(func):
        attr_name = f"_lazy_{func.__name__}"
        component_name = f"{func.__qualname__}_{func.__name__}"
        
        @wraps(func)
        def wrapper(self):
            if not hasattr(self, attr_name):
                # Register with global lazy loader
                component = lazy_loader.register_component(
                    component_name, 
                    lambda: loader_func(self)
                )
                setattr(self, attr_name, component)
            
            return getattr(self, attr_name).get_instance()
        
        return property(wrapper)
    
    return decorator

def lazy_init(name: str = None):
    """Decorator to make a method lazy-initialized."""
    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            component_name = name or f"{self.__class__.__name__}.{func.__name__}"
            
            def loader():
                return func(self, *args, **kwargs)
            
            if component_name not in lazy_loader.components:
                lazy_loader.register_component(component_name, loader)
            
            return lazy_loader.get_component(component_name)
        
        return wrapper
    
    return decorator 