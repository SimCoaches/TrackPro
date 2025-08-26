"""
Central State Manager for TrackPro UI

This module provides centralized state management to prevent redundant operations
and coordinate updates across all UI components during startup and runtime.

Key Features:
- Single source of truth for authentication state
- Coordinated user profile caching
- Debounced UI updates
- Idempotency checks
- Operation coordination
"""

import logging
import time
import threading
from typing import Optional, Dict, Any, Set, Callable
from PyQt6.QtCore import QObject, pyqtSignal, QTimer

logger = logging.getLogger(__name__)


class CentralStateManager(QObject):
    """
    Central state manager that coordinates all UI state changes.
    
    This prevents the cascade effect where one auth change triggers
    multiple redundant operations across different components.
    """
    
    # Signals - these are the ONLY auth signals that should be emitted
    auth_state_changed = pyqtSignal(bool)
    user_profile_changed = pyqtSignal(dict)
    
    # Singleton pattern
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        # CRITICAL: Call parent QObject __init__ FIRST
        super().__init__()
        
        # Singleton pattern - prevent re-initialization  
        if hasattr(self, '_initialized'):
            return
            
        self._initialized = True
        
        # === STATE TRACKING ===
        self._is_authenticated: Optional[bool] = None
        self._user_profile: Optional[Dict[str, Any]] = None
        self._user_profile_cache_time = 0
        self._user_profile_cache_ttl = 30  # 30 second cache
        
        # === OPERATION COORDINATION ===
        self._pending_operations: Set[str] = set()
        self._operation_lock = threading.Lock()
        self._last_auth_update_time = 0
        self._auth_update_debounce = 0.5  # 500ms debounce
        
        # === COMPONENT REGISTRATION ===
        self._registered_components = set()
        self._component_states: Dict[str, Dict[str, Any]] = {}
        
        # === DEFERRED OPERATION COORDINATION ===
        self._deferred_timers: Dict[str, QTimer] = {}
        
        logger.info("🏛️ Central State Manager initialized")
    
    @classmethod
    def get_instance(cls):
        """Get the singleton instance."""
        return cls()
    
    # === AUTHENTICATION STATE MANAGEMENT ===
    
    def set_auth_state(self, is_authenticated: bool, user_info: Optional[Dict[str, Any]] = None) -> bool:
        """
        Set authentication state with proper debouncing and coordination.
        
        Returns True if state actually changed, False if redundant.
        """
        current_time = time.time()
        
        # Debounce rapid auth state changes
        if (current_time - self._last_auth_update_time) < self._auth_update_debounce:
            logger.debug("🔄 Auth state update debounced - too frequent")
            return False
        
        # Check if this is actually a state change
        if self._is_authenticated == is_authenticated:
            if is_authenticated and user_info:
                # Check if user profile changed
                current_user_id = self._user_profile.get('id') if self._user_profile else None
                new_user_id = user_info.get('id') if user_info else None
                if current_user_id == new_user_id:
                    logger.debug("🔄 Auth state unchanged - no update needed")
                    return False
        
        logger.info(f"🏛️ Central State Manager: Auth state changing to {is_authenticated}")
        
        # Update state
        self._is_authenticated = is_authenticated
        if user_info:
            self._user_profile = user_info.copy()
            self._user_profile_cache_time = current_time
        elif not is_authenticated:
            self._user_profile = None
            self._user_profile_cache_time = 0
        
        self._last_auth_update_time = current_time
        
        # Emit SINGLE coordinated signal
        self.auth_state_changed.emit(is_authenticated)
        
        if user_info:
            self.user_profile_changed.emit(user_info)
        
        return True
    
    def get_auth_state(self) -> Optional[bool]:
        """Get current authentication state."""
        return self._is_authenticated
    
    def get_user_profile(self, force_refresh: bool = False) -> Optional[Dict[str, Any]]:
        """
        Get cached user profile with automatic refresh if needed.
        
        This prevents redundant database queries across components.
        """
        current_time = time.time()
        
        # Check cache validity
        if (not force_refresh and 
            self._user_profile is not None and 
            (current_time - self._user_profile_cache_time) < self._user_profile_cache_ttl):
            logger.debug("🚀 CACHE HIT: Returning cached user profile")
            return self._user_profile.copy()
        
        # Cache miss or forced refresh
        if self._is_authenticated:
            logger.info("🔄 Refreshing user profile from database")
            
            try:
                # Get fresh user profile
                from trackpro.auth.user_manager import get_current_user
                current_user = get_current_user()
                
                if current_user and current_user.is_authenticated:
                    from trackpro.social.user_manager import EnhancedUserManager
                    user_manager = EnhancedUserManager()
                    complete_profile = user_manager.get_complete_user_profile(current_user.id)
                    
                    if complete_profile:
                        user_info = {
                            'id': current_user.id,
                            'email': current_user.email,
                            'name': complete_profile.get('display_name') or complete_profile.get('username') or current_user.name,
                            'avatar_url': complete_profile.get('avatar_url'),
                            'username': complete_profile.get('username'),
                            'display_name': complete_profile.get('display_name')
                        }
                        
                        # Update cache
                        self._user_profile = user_info
                        self._user_profile_cache_time = current_time
                        
                        logger.info(f"✅ Refreshed user profile: {user_info.get('name', 'Unknown')}")
                        return user_info.copy()
                        
            except Exception as e:
                logger.error(f"❌ Error refreshing user profile: {e}")
        
        return None
    
    # === OPERATION COORDINATION ===
    
    def register_operation(self, operation_name: str) -> bool:
        """
        Register an operation to prevent duplicates.
        
        Returns True if operation should proceed, False if already in progress.
        """
        with self._operation_lock:
            if operation_name in self._pending_operations:
                logger.debug(f"🔄 Operation {operation_name} already in progress - skipping")
                return False
            
            self._pending_operations.add(operation_name)
            logger.debug(f"🎯 Registered operation: {operation_name}")
            return True
    
    def complete_operation(self, operation_name: str):
        """Mark an operation as complete."""
        with self._operation_lock:
            self._pending_operations.discard(operation_name)
            logger.debug(f"✅ Completed operation: {operation_name}")
    
    def is_operation_pending(self, operation_name: str) -> bool:
        """Check if an operation is currently pending."""
        return operation_name in self._pending_operations
    
    # === COMPONENT REGISTRATION ===
    
    def register_component(self, component_name: str, component: QObject):
        """Register a component for coordinated updates."""
        self._registered_components.add(component_name)
        self._component_states[component_name] = {}
        logger.debug(f"📝 Registered component: {component_name}")
    
    def set_component_state(self, component_name: str, key: str, value: Any):
        """Set component-specific state."""
        if component_name not in self._component_states:
            self._component_states[component_name] = {}
        self._component_states[component_name][key] = value
    
    def get_component_state(self, component_name: str, key: str, default=None):
        """Get component-specific state."""
        return self._component_states.get(component_name, {}).get(key, default)
    
    # === DEFERRED OPERATION COORDINATION ===
    
    def schedule_deferred_operation(self, operation_name: str, callback: Callable, delay_ms: int = 500):
        """
        Schedule a deferred operation, canceling any existing timer for the same operation.
        
        This prevents multiple deferred operations of the same type.
        """
        # Cancel existing timer if any
        if operation_name in self._deferred_timers:
            self._deferred_timers[operation_name].stop()
            self._deferred_timers[operation_name].deleteLater()
        
        # Create new timer
        timer = QTimer()
        timer.setSingleShot(True)
        timer.timeout.connect(lambda: self._execute_deferred_operation(operation_name, callback))
        
        self._deferred_timers[operation_name] = timer
        timer.start(delay_ms)
        
        logger.debug(f"⏰ Scheduled deferred operation: {operation_name} in {delay_ms}ms")
    
    def _execute_deferred_operation(self, operation_name: str, callback: Callable):
        """Execute a deferred operation and clean up."""
        try:
            logger.debug(f"🚀 Executing deferred operation: {operation_name}")
            callback()
        except Exception as e:
            logger.error(f"❌ Error in deferred operation {operation_name}: {e}")
        finally:
            # Clean up timer
            if operation_name in self._deferred_timers:
                self._deferred_timers[operation_name].deleteLater()
                del self._deferred_timers[operation_name]
    
    def cancel_deferred_operation(self, operation_name: str):
        """Cancel a pending deferred operation."""
        if operation_name in self._deferred_timers:
            self._deferred_timers[operation_name].stop()
            self._deferred_timers[operation_name].deleteLater()
            del self._deferred_timers[operation_name]
            logger.debug(f"❌ Cancelled deferred operation: {operation_name}")
    
    # === UTILITY METHODS ===
    
    def get_state_summary(self) -> Dict[str, Any]:
        """Get a summary of current state for debugging."""
        return {
            'is_authenticated': self._is_authenticated,
            'user_profile_cached': self._user_profile is not None,
            'pending_operations': list(self._pending_operations),
            'registered_components': len(self._registered_components),
            'deferred_timers': list(self._deferred_timers.keys())
        }


# Convenience function for easy access
def get_state_manager() -> CentralStateManager:
    """Get the central state manager instance."""
    return CentralStateManager.get_instance()
