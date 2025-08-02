"""
High-performance telemetry caching system for instant lap switching.
"""

import logging
import threading
import time
from typing import Dict, List, Optional, Tuple, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
import weakref

logger = logging.getLogger(__name__)

class TelemetryCache:
    """Ultra-fast telemetry cache with background preloading and memory optimization."""
    
    def __init__(self, max_memory_mb: int = 500):
        """Initialize telemetry cache.
        
        Args:
            max_memory_mb: Maximum memory usage in MB for cached telemetry
        """
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._cache_lock = threading.RLock()
        self._access_times: Dict[str, float] = {}
        self._preload_executor = ThreadPoolExecutor(max_workers=3, thread_name_prefix="TelemetryPreload")
        self._preload_futures: Dict[str, Any] = {}
        self._max_memory_bytes = max_memory_mb * 1024 * 1024
        self._estimated_memory_usage = 0
        
        # Session-based preloading
        self._current_session_id: Optional[str] = None
        self._session_laps: List[str] = []
        
        logger.info(f"🏁 TelemetryCache initialized with {max_memory_mb}MB limit")
    
    def estimate_telemetry_size(self, telemetry_data: List[Dict]) -> int:
        """Estimate memory usage of telemetry data."""
        if not telemetry_data:
            return 0
        
        # Rough estimate: each point is ~50 fields * 8 bytes average = ~400 bytes
        return len(telemetry_data) * 400
    
    def _evict_oldest_if_needed(self, new_size: int):
        """Evict oldest entries if memory limit would be exceeded."""
        if self._estimated_memory_usage + new_size <= self._max_memory_bytes:
            return
        
        # Sort by access time (oldest first)
        sorted_entries = sorted(self._access_times.items(), key=lambda x: x[1])
        
        evicted_count = 0
        for lap_id, _ in sorted_entries:
            if self._estimated_memory_usage + new_size <= self._max_memory_bytes:
                break
            
            if lap_id in self._cache:
                entry_size = self._cache[lap_id].get('estimated_size', 0)
                del self._cache[lap_id]
                del self._access_times[lap_id]
                self._estimated_memory_usage -= entry_size
                evicted_count += 1
        
        if evicted_count > 0:
            logger.info(f"📦 CACHE: Evicted {evicted_count} entries to free memory")
    
    def get_telemetry(self, lap_id: str) -> Optional[List[Dict]]:
        """Get telemetry from cache or return None if not cached."""
        if not lap_id:
            return None
        
        with self._cache_lock:
            if lap_id in self._cache:
                self._access_times[lap_id] = time.time()
                entry = self._cache[lap_id]
                logger.debug(f"⚡ CACHE HIT: Retrieved {len(entry['data'])} points for lap {lap_id[:8]}")
                return entry['data']
        
        return None
    
    def store_telemetry(self, lap_id: str, telemetry_data: List[Dict], force: bool = False):
        """Store telemetry in cache with memory management."""
        if not lap_id or not telemetry_data:
            return
        
        estimated_size = self.estimate_telemetry_size(telemetry_data)
        
        with self._cache_lock:
            # Skip if already cached and not forcing
            if lap_id in self._cache and not force:
                return
            
            # Evict old entries if needed
            self._evict_oldest_if_needed(estimated_size)
            
            # Store in cache
            self._cache[lap_id] = {
                'data': telemetry_data,
                'cached_at': time.time(),
                'estimated_size': estimated_size
            }
            self._access_times[lap_id] = time.time()
            self._estimated_memory_usage += estimated_size
            
            logger.info(f"💾 CACHE: Stored {len(telemetry_data)} points for lap {lap_id[:8]} ({estimated_size//1024}KB)")
    
    def preload_session_telemetry(self, session_id: str, lap_ids: List[str]):
        """Preload telemetry for all laps in a session in the background."""
        if not session_id or not lap_ids:
            return
        
        self._current_session_id = session_id
        self._session_laps = lap_ids.copy()
        
        # Cancel any existing preload operations
        self._cancel_preload_operations()
        
        # Start preloading uncached laps
        uncached_laps = []
        with self._cache_lock:
            for lap_id in lap_ids:
                if lap_id not in self._cache:
                    uncached_laps.append(lap_id)
        
        if uncached_laps:
            logger.info(f"🔄 CACHE: Starting background preload for {len(uncached_laps)} laps")
            self._start_background_preload(uncached_laps)
        else:
            logger.info(f"✅ CACHE: All {len(lap_ids)} laps already cached")
    
    def _cancel_preload_operations(self):
        """Cancel any running preload operations."""
        for lap_id, future in list(self._preload_futures.items()):
            if not future.done():
                future.cancel()
                logger.debug(f"❌ PRELOAD: Cancelled preload for lap {lap_id[:8]}")
        self._preload_futures.clear()
    
    def _start_background_preload(self, lap_ids: List[str]):
        """Start background preloading for multiple laps."""
        for lap_id in lap_ids:
            if lap_id not in self._preload_futures:
                future = self._preload_executor.submit(self._preload_single_lap, lap_id)
                self._preload_futures[lap_id] = future
    
    def _preload_single_lap(self, lap_id: str):
        """Preload telemetry for a single lap."""
        try:
            # Import here to avoid circular imports
            from Supabase.database import get_lap_telemetry_points
            
            logger.debug(f"🔄 PRELOAD: Loading lap {lap_id[:8]}...")
            
            # Check if still needed (might have been cached by user action)
            with self._cache_lock:
                if lap_id in self._cache:
                    logger.debug(f"⚡ PRELOAD: Lap {lap_id[:8]} already cached, skipping")
                    return
            
            # Load telemetry
            telemetry_data, error = get_lap_telemetry_points(lap_id)
            
            if telemetry_data:
                self.store_telemetry(lap_id, telemetry_data)
                logger.info(f"✅ PRELOAD: Cached {len(telemetry_data)} points for lap {lap_id[:8]}")
            else:
                logger.warning(f"❌ PRELOAD: Failed to load lap {lap_id[:8]}: {error}")
        
        except Exception as e:
            logger.error(f"❌ PRELOAD: Error loading lap {lap_id[:8]}: {e}")
        finally:
            # Clean up future reference
            self._preload_futures.pop(lap_id, None)
    
    def wait_for_lap(self, lap_id: str, timeout: float = 5.0) -> Optional[List[Dict]]:
        """Wait for a specific lap to be preloaded, with timeout."""
        # Check if already cached
        cached_data = self.get_telemetry(lap_id)
        if cached_data:
            return cached_data
        
        # Check if being preloaded
        future = self._preload_futures.get(lap_id)
        if future:
            try:
                logger.info(f"⏳ CACHE: Waiting for preload of lap {lap_id[:8]}...")
                future.result(timeout=timeout)
                return self.get_telemetry(lap_id)
            except Exception as e:
                logger.warning(f"⚠️ CACHE: Preload wait failed for lap {lap_id[:8]}: {e}")
        
        return None
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self._cache_lock:
            return {
                'cached_laps': len(self._cache),
                'memory_usage_mb': self._estimated_memory_usage / (1024 * 1024),
                'memory_limit_mb': self._max_memory_bytes / (1024 * 1024),
                'preload_active': len(self._preload_futures),
                'current_session': self._current_session_id
            }
    
    def clear_cache(self):
        """Clear all cached telemetry."""
        with self._cache_lock:
            self._cache.clear()
            self._access_times.clear()
            self._estimated_memory_usage = 0
        
        self._cancel_preload_operations()
        logger.info("🗑️ CACHE: Cleared all cached telemetry")
    
    def shutdown(self):
        """Shutdown the cache and cleanup resources."""
        logger.info("🛑 CACHE: Shutting down telemetry cache")
        self._cancel_preload_operations()
        self._preload_executor.shutdown(wait=True)
        self.clear_cache()

# Global cache instance
_telemetry_cache: Optional[TelemetryCache] = None
_cache_lock = threading.Lock()

def get_telemetry_cache() -> TelemetryCache:
    """Get the global telemetry cache instance."""
    global _telemetry_cache
    
    if _telemetry_cache is None:
        with _cache_lock:
            if _telemetry_cache is None:
                _telemetry_cache = TelemetryCache()
    
    return _telemetry_cache

def shutdown_telemetry_cache():
    """Shutdown the global telemetry cache."""
    global _telemetry_cache
    
    if _telemetry_cache is not None:
        _telemetry_cache.shutdown()
        _telemetry_cache = None