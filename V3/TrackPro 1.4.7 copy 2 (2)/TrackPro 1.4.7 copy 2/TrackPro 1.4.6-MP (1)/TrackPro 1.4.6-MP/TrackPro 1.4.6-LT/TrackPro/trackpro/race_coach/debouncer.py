"""
State Change Debouncer - Phase 3 Optimization
Prevents cascading refreshes and rapid operations that degrade performance.
"""

import time
import threading
import logging
from typing import Dict, Callable, Any, Optional
from collections import defaultdict

logger = logging.getLogger(__name__)

class DebouncedAction:
    """
    Manages a single debounced action with configurable delay and execution.
    """
    
    def __init__(self, action: Callable, delay: float = 0.5, max_delay: float = 5.0):
        self.action = action
        self.delay = delay
        self.max_delay = max_delay
        self.timer: Optional[threading.Timer] = None
        self.pending_args = None
        self.pending_kwargs = None
        self.first_call_time = None
        self.call_count = 0
        self.lock = threading.Lock()
        
    def trigger(self, *args, **kwargs):
        """Trigger the debounced action with new arguments."""
        with self.lock:
            current_time = time.time()
            
            # Cancel existing timer
            if self.timer and self.timer.is_alive():
                self.timer.cancel()
            
            # Update pending arguments (latest wins)
            self.pending_args = args
            self.pending_kwargs = kwargs
            self.call_count += 1
            
            # Track first call time for max delay enforcement
            if self.first_call_time is None:
                self.first_call_time = current_time
                
            # Calculate delay - enforce max delay if too much time has passed
            time_since_first = current_time - self.first_call_time if self.first_call_time else 0
            actual_delay = min(self.delay, max(0, self.max_delay - time_since_first))
            
            # Schedule execution
            self.timer = threading.Timer(actual_delay, self._execute)
            self.timer.daemon = True
            self.timer.start()
            
            logger.debug(f"Debounced action scheduled in {actual_delay:.1f}s (call #{self.call_count})")
            
    def _execute(self):
        """Execute the debounced action."""
        with self.lock:
            if self.pending_args is None and self.pending_kwargs is None:
                return
                
            args = self.pending_args or ()
            kwargs = self.pending_kwargs or {}
            call_count = self.call_count
            
            # Reset state
            self.pending_args = None
            self.pending_kwargs = None
            self.first_call_time = None
            self.call_count = 0
            
        try:
            logger.debug(f"Executing debounced action (coalesced {call_count} calls)")
            self.action(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error executing debounced action: {e}")
            
    def cancel(self):
        """Cancel any pending execution."""
        with self.lock:
            if self.timer and self.timer.is_alive():
                self.timer.cancel()
            self.pending_args = None
            self.pending_kwargs = None
            self.first_call_time = None
            self.call_count = 0

class SmartDebouncer:
    """
    Smart debouncing system for multiple operations.
    Phase 3 Optimization: Prevents rapid successive operations that cause performance issues.
    """
    
    def __init__(self):
        self.actions: Dict[str, DebouncedAction] = {}
        self.operation_stats = defaultdict(lambda: {"triggers": 0, "executions": 0, "last_execution": 0})
        
        logger.info("SmartDebouncer initialized - Phase 3 optimization active")
        
    def register_action(self, name: str, action: Callable, delay: float = 0.5, max_delay: float = 5.0):
        """Register a debounced action."""
        self.actions[name] = DebouncedAction(action, delay, max_delay)
        logger.debug(f"Registered debounced action '{name}' (delay: {delay}s, max: {max_delay}s)")
        
    def trigger(self, name: str, *args, **kwargs):
        """Trigger a debounced action."""
        if name not in self.actions:
            logger.warning(f"Unknown debounced action: {name}")
            return
            
        self.operation_stats[name]["triggers"] += 1
        self.actions[name].trigger(*args, **kwargs)
        
    def execute_immediately(self, name: str, *args, **kwargs):
        """Execute an action immediately, bypassing debouncing."""
        if name not in self.actions:
            logger.warning(f"Unknown debounced action: {name}")
            return
            
        # Cancel pending execution
        self.actions[name].cancel()
        
        # Execute immediately
        try:
            self.operation_stats[name]["executions"] += 1
            self.operation_stats[name]["last_execution"] = time.time()
            self.actions[name].action(*args, **kwargs)
            logger.debug(f"Executed '{name}' immediately")
        except Exception as e:
            logger.error(f"Error executing '{name}' immediately: {e}")
            
    def cancel_all(self):
        """Cancel all pending debounced actions."""
        cancelled_count = 0
        for action in self.actions.values():
            if action.timer and action.timer.is_alive():
                action.cancel()
                cancelled_count += 1
        
        if cancelled_count > 0:
            logger.info(f"Cancelled {cancelled_count} pending debounced actions")
            
    def get_stats(self) -> dict:
        """Get debouncing statistics for monitoring."""
        return {
            "registered_actions": list(self.actions.keys()),
            "operation_stats": dict(self.operation_stats)
        }

# Specialized debouncing configurations for common TrackPro operations
class TrackProDebouncer(SmartDebouncer):
    """
    Pre-configured debouncer for TrackPro operations.
    Optimizes common patterns found in the application.
    """
    
    def __init__(self):
        super().__init__()
        
        # Register common operations with appropriate delays
        # Note: actions will be registered when the actual functions are available
        logger.info("TrackProDebouncer initialized with optimized delays")
        
    def setup_curve_operations(self, refresh_curves_func: Callable):
        """Setup curve-related debounced operations."""
        # Curve refreshes should be debounced aggressively since they scan filesystem
        self.register_action("refresh_curves", refresh_curves_func, delay=1.0, max_delay=3.0)
        logger.info("Curve operations debouncing configured")
        
    def setup_calibration_operations(self, save_calibration_func: Callable):
        """Setup calibration-related debounced operations."""
        # Calibration saves should be debounced to prevent rapid I/O
        self.register_action("save_calibration", save_calibration_func, delay=0.5, max_delay=2.0)
        logger.info("Calibration operations debouncing configured")
        
    def setup_auth_operations(self, refresh_auth_func: Callable):
        """Setup authentication-related debounced operations."""
        # Auth state changes can trigger cascading updates
        self.register_action("refresh_auth", refresh_auth_func, delay=0.3, max_delay=1.0)
        logger.info("Auth operations debouncing configured")

# Global instance for use across the application
trackpro_debouncer = TrackProDebouncer() 