"""
Smart Connection Manager for iRacing - Phase 3 Optimization
Prevents excessive connection attempts with intelligent backoff and caching.
"""

import time
import logging
import threading
from typing import Optional, Callable

logger = logging.getLogger(__name__)

class ExponentialBackoff:
    """Implements exponential backoff for connection attempts."""
    
    def __init__(self, initial_delay: float = 1.0, max_delay: float = 30.0, multiplier: float = 2.0):
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.multiplier = multiplier
        self.current_delay = initial_delay
        self.failure_count = 0
        
    def next_delay(self) -> float:
        """Get the next delay value and increment for next time."""
        delay = self.current_delay
        self.current_delay = min(self.max_delay, self.current_delay * self.multiplier)
        self.failure_count += 1
        return delay
        
    def reset(self):
        """Reset backoff to initial state on successful connection."""
        self.current_delay = self.initial_delay
        self.failure_count = 0
        
    def should_attempt(self, last_attempt_time: float) -> bool:
        """Check if enough time has passed for another attempt."""
        return time.time() - last_attempt_time >= self.current_delay

class ConnectionState:
    """Tracks connection state and prevents redundant operations."""
    
    def __init__(self):
        self.is_connected = False
        self.last_attempt_time = 0.0
        self.last_check_time = 0.0
        self.connection_cache_duration = 5.0  # Cache connection state for 5 seconds
        self.lock = threading.Lock()
        
    def set_connected(self, connected: bool):
        """Update connection state."""
        with self.lock:
            self.is_connected = connected
            self.last_check_time = time.time()
            
    def get_cached_state(self) -> Optional[bool]:
        """Get cached connection state if still valid."""
        with self.lock:
            if time.time() - self.last_check_time < self.connection_cache_duration:
                return self.is_connected
        return None
        
    def set_attempt_time(self):
        """Mark that a connection attempt was made."""
        with self.lock:
            self.last_attempt_time = time.time()

class SmartConnectionManager:
    """
    Smart connection manager that prevents excessive iRacing connection attempts.
    Phase 3 Optimization: Reduces 20+ connection attempts to intelligent, spaced attempts.
    """
    
    def __init__(self):
        self.backoff = ExponentialBackoff(initial_delay=2.0, max_delay=60.0)
        self.state = ConnectionState()
        self.connection_function: Optional[Callable] = None
        self.max_attempts_per_minute = 3
        self.attempt_timestamps = []
        
        logger.info("SmartConnectionManager initialized - Phase 3 optimization active")
        
    def register_connection_function(self, func: Callable):
        """Register the actual connection function to use."""
        self.connection_function = func
        
    def should_attempt_connection(self) -> bool:
        """
        Intelligent decision on whether to attempt connection.
        Considers backoff, rate limiting, and cache validity.
        """
        current_time = time.time()
        
        # Check if we have a valid cached state
        cached_state = self.state.get_cached_state()
        if cached_state is not None:
            if cached_state:  # Already connected
                return False
            # If cached as disconnected, still respect backoff
            
        # Rate limiting: max attempts per minute
        self.attempt_timestamps = [t for t in self.attempt_timestamps if current_time - t < 60]
        if len(self.attempt_timestamps) >= self.max_attempts_per_minute:
            return False
            
        # Respect exponential backoff
        if not self.backoff.should_attempt(self.state.last_attempt_time):
            return False
            
        return True
        
    def attempt_connection(self) -> bool:
        """
        Smart connection attempt with backoff and caching.
        Returns True if connected, False otherwise.
        """
        if not self.should_attempt_connection():
            # Return cached state if available
            cached = self.state.get_cached_state()
            if cached is not None:
                return cached
            return False
            
        if not self.connection_function:
            logger.error("No connection function registered")
            return False
            
        # Record attempt
        current_time = time.time()
        self.state.set_attempt_time()
        self.attempt_timestamps.append(current_time)
        
        logger.info(f"SmartConnectionManager: Attempting iRacing connection (attempt #{self.backoff.failure_count + 1})")
        
        try:
            # Call the actual connection function
            success = self.connection_function()
            
            if success:
                self.backoff.reset()
                self.state.set_connected(True)
                logger.info("SmartConnectionManager: Connection successful - backoff reset")
            else:
                self.state.set_connected(False)
                next_delay = self.backoff.next_delay()
                logger.info(f"SmartConnectionManager: Connection failed - next attempt in {next_delay:.1f}s")
                
            return success
            
        except Exception as e:
            logger.error(f"SmartConnectionManager: Connection attempt failed with exception: {e}")
            self.state.set_connected(False)
            self.backoff.next_delay()
            return False
            
    def force_disconnect(self):
        """Force mark as disconnected (for when we know connection is lost)."""
        self.state.set_connected(False)
        logger.info("SmartConnectionManager: Forced disconnect")
        
    def get_connection_stats(self) -> dict:
        """Get statistics for monitoring and debugging."""
        return {
            "failure_count": self.backoff.failure_count,
            "current_delay": self.backoff.current_delay,
            "is_connected": self.state.is_connected,
            "last_attempt": self.state.last_attempt_time,
            "attempts_last_minute": len(self.attempt_timestamps)
        }

# Global instance for use across the application
iracing_connection_manager = SmartConnectionManager() 