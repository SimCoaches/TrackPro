"""
Curve Loading Cache System - Phase 3 Optimization
Eliminates redundant file scanning and improves startup performance.
"""

import os
import json
import time
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from threading import Lock

logger = logging.getLogger(__name__)

@dataclass
class CurveMetadata:
    """Metadata for a single curve file."""
    name: str
    file_path: str
    last_modified: float
    file_size: int
    checksum: Optional[str] = None

@dataclass
class CacheEntry:
    """Cache entry containing curve metadata and file info."""
    metadata: CurveMetadata
    cached_time: float
    is_valid: bool = True

class CurveCache:
    """
    Intelligent curve loading cache that tracks file modifications
    and eliminates redundant file system operations.
    """
    
    def __init__(self, cache_file: str = "curve_cache.json", ttl_seconds: int = 3600):
        self.cache_file = Path(cache_file)
        self.ttl_seconds = ttl_seconds
        self.cache: Dict[str, Dict[str, CacheEntry]] = {}  # pedal -> {curve_name -> CacheEntry}
        self.lock = Lock()
        self._load_cache()
        logger.info(f"CurveCache initialized with TTL {ttl_seconds}s")
    
    def _load_cache(self) -> None:
        """Load cache from disk if it exists."""
        try:
            if self.cache_file.exists():
                with open(self.cache_file, 'r') as f:
                    cache_data = json.load(f)
                
                # Convert back to CacheEntry objects
                for pedal, curves in cache_data.items():
                    self.cache[pedal] = {}
                    for curve_name, entry_data in curves.items():
                        metadata = CurveMetadata(**entry_data['metadata'])
                        cache_entry = CacheEntry(
                            metadata=metadata,
                            cached_time=entry_data['cached_time'],
                            is_valid=entry_data.get('is_valid', True)
                        )
                        self.cache[pedal][curve_name] = cache_entry
                
                logger.info(f"Loaded curve cache with {sum(len(curves) for curves in self.cache.values())} entries")
            else:
                logger.info("No existing curve cache found, starting fresh")
        except Exception as e:
            logger.error(f"Error loading curve cache: {e}")
            self.cache = {}
    
    def _save_cache(self) -> None:
        """Save cache to disk."""
        try:
            # Convert CacheEntry objects to serializable format
            cache_data = {}
            for pedal, curves in self.cache.items():
                cache_data[pedal] = {}
                for curve_name, entry in curves.items():
                    cache_data[pedal][curve_name] = {
                        'metadata': asdict(entry.metadata),
                        'cached_time': entry.cached_time,
                        'is_valid': entry.is_valid
                    }
            
            with open(self.cache_file, 'w') as f:
                json.dump(cache_data, f, indent=2)
            
            logger.debug("Curve cache saved to disk")
        except Exception as e:
            logger.error(f"Error saving curve cache: {e}")
    
    def get_cached_curves(self, pedal: str, curves_directory: Path) -> Tuple[List[str], bool]:
        """
        Get cached curve list for a pedal, checking if cache is still valid.
        
        Returns:
            Tuple of (curve_names, cache_hit)
        """
        with self.lock:
            current_time = time.time()
            
            # Check if we have cached data for this pedal
            if pedal not in self.cache:
                logger.debug(f"No cache entry for pedal: {pedal}")
                # Record cache miss
                try:
                    from ..race_coach.performance_monitor import performance_monitor
                    performance_monitor.record_cache_miss(f"curve_cache_{pedal}")
                except ImportError:
                    pass
                return self._scan_and_cache_curves(pedal, curves_directory), False
            
            pedal_cache = self.cache[pedal]
            
            # Check if cache has expired
            if pedal_cache:
                oldest_entry = min(entry.cached_time for entry in pedal_cache.values())
                if current_time - oldest_entry > self.ttl_seconds:
                    logger.debug(f"Cache expired for pedal: {pedal}")
                    try:
                        from ..race_coach.performance_monitor import performance_monitor
                        performance_monitor.record_cache_miss(f"curve_cache_{pedal}")
                    except ImportError:
                        pass
                    return self._scan_and_cache_curves(pedal, curves_directory), False
            
            # Check if directory modification time suggests changes
            try:
                dir_mtime = curves_directory.stat().st_mtime
                cache_time = max(entry.cached_time for entry in pedal_cache.values()) if pedal_cache else 0
                
                if dir_mtime > cache_time:
                    logger.debug(f"Directory modified after cache for pedal: {pedal}")
                    try:
                        from ..race_coach.performance_monitor import performance_monitor
                        performance_monitor.record_cache_miss(f"curve_cache_{pedal}")
                    except ImportError:
                        pass
                    return self._scan_and_cache_curves(pedal, curves_directory), False
            except Exception as e:
                logger.warning(f"Error checking directory mtime: {e}")
                try:
                    from ..race_coach.performance_monitor import performance_monitor
                    performance_monitor.record_cache_miss(f"curve_cache_{pedal}")
                except ImportError:
                    pass
                return self._scan_and_cache_curves(pedal, curves_directory), False
            
            # Validate cached entries against actual files
            valid_curves = []
            invalid_count = 0
            
            for curve_name, cache_entry in pedal_cache.items():
                file_path = Path(cache_entry.metadata.file_path)
                
                try:
                    if file_path.exists():
                        file_stat = file_path.stat()
                        if (file_stat.st_mtime == cache_entry.metadata.last_modified and 
                            file_stat.st_size == cache_entry.metadata.file_size):
                            valid_curves.append(curve_name)
                        else:
                            invalid_count += 1
                    else:
                        invalid_count += 1
                except Exception as e:
                    logger.debug(f"Error validating cached curve {curve_name}: {e}")
                    invalid_count += 1
            
            # If too many invalid entries, refresh the cache
            if invalid_count > len(pedal_cache) * 0.3:  # 30% threshold
                logger.debug(f"Too many invalid cache entries for pedal: {pedal}, refreshing")
                try:
                    from ..race_coach.performance_monitor import performance_monitor
                    performance_monitor.record_cache_miss(f"curve_cache_{pedal}")
                except ImportError:
                    pass
                return self._scan_and_cache_curves(pedal, curves_directory), False
            
            logger.info(f"Cache hit for pedal {pedal}: {len(valid_curves)} curves loaded from cache")
            
            # Record performance metrics (Phase 3 optimization tracking)
            try:
                from ..race_coach.performance_monitor import performance_monitor
                performance_monitor.record_cache_hit(f"curve_cache_{pedal}", len(valid_curves))
            except ImportError:
                pass  # Performance monitoring optional
            
            return valid_curves, True
    
    def _scan_and_cache_curves(self, pedal: str, curves_directory: Path) -> List[str]:
        """Scan directory for curves and update cache."""
        logger.debug(f"Scanning curves directory for pedal: {pedal}")
        
        curve_names = []
        pedal_cache = {}
        current_time = time.time()
        
        try:
            if not curves_directory.exists():
                logger.warning(f"Curves directory does not exist: {curves_directory}")
                self.cache[pedal] = {}
                self._save_cache()
                return []
            
            # Scan for JSON files
            for curve_file in curves_directory.glob("*.json"):
                try:
                    file_stat = curve_file.stat()
                    curve_name = curve_file.stem
                    
                    metadata = CurveMetadata(
                        name=curve_name,
                        file_path=str(curve_file),
                        last_modified=file_stat.st_mtime,
                        file_size=file_stat.st_size
                    )
                    
                    cache_entry = CacheEntry(
                        metadata=metadata,
                        cached_time=current_time,
                        is_valid=True
                    )
                    
                    pedal_cache[curve_name] = cache_entry
                    curve_names.append(curve_name)
                    
                except Exception as e:
                    logger.warning(f"Error processing curve file {curve_file}: {e}")
            
            # Update cache
            self.cache[pedal] = pedal_cache
            self._save_cache()
            
            logger.info(f"Scanned and cached {len(curve_names)} curves for pedal: {pedal}")
            
        except Exception as e:
            logger.error(f"Error scanning curves directory: {e}")
        
        return curve_names
    
    def invalidate_pedal(self, pedal: str) -> None:
        """Invalidate cache for a specific pedal."""
        with self.lock:
            if pedal in self.cache:
                del self.cache[pedal]
                self._save_cache()
                logger.info(f"Invalidated cache for pedal: {pedal}")
    
    def invalidate_all(self) -> None:
        """Invalidate entire cache."""
        with self.lock:
            self.cache.clear()
            self._save_cache()
            logger.info("Invalidated entire curve cache")

# Global instance
curve_cache = CurveCache() 