"""
Performance Monitor - Phase 3 Optimization
Tracks and reports performance improvements from optimization implementations.
"""

import time
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from collections import defaultdict

logger = logging.getLogger(__name__)

@dataclass
class PerformanceMetric:
    """Single performance measurement."""
    name: str
    start_time: float
    end_time: Optional[float] = None
    duration: Optional[float] = None
    metadata: Dict = field(default_factory=dict)
    
    def finish(self, **metadata):
        """Mark the metric as finished and calculate duration."""
        self.end_time = time.time()
        self.duration = self.end_time - self.start_time
        self.metadata.update(metadata)
        return self.duration

class PerformanceMonitor:
    """Tracks performance metrics for Phase 3 optimizations."""
    
    def __init__(self):
        self.metrics: Dict[str, List[PerformanceMetric]] = defaultdict(list)
        self.active_metrics: Dict[str, PerformanceMetric] = {}
        self.startup_time = time.time()
        self.optimization_stats = {
            'cache_hits': 0,
            'cache_misses': 0,
            'debounced_operations': 0,
            'lazy_loads': 0,
            'connection_attempts_saved': 0
        }
        logger.info("Performance monitor initialized for Phase 3 optimizations")
    
    def start_metric(self, name: str, **metadata) -> str:
        """Start tracking a performance metric."""
        metric_id = f"{name}_{time.time()}"
        metric = PerformanceMetric(
            name=name,
            start_time=time.time(),
            metadata=metadata
        )
        self.active_metrics[metric_id] = metric
        return metric_id
    
    def finish_metric(self, metric_id: str, **metadata) -> Optional[float]:
        """Finish tracking a metric and return the duration."""
        if metric_id not in self.active_metrics:
            logger.warning(f"Metric {metric_id} not found in active metrics")
            return None
        
        metric = self.active_metrics.pop(metric_id)
        duration = metric.finish(**metadata)
        self.metrics[metric.name].append(metric)
        
        return duration
    
    def record_instant_metric(self, name: str, value: float, **metadata):
        """Record an instant metric value."""
        metric = PerformanceMetric(
            name=name,
            start_time=time.time(),
            end_time=time.time(),
            duration=value,
            metadata=metadata
        )
        self.metrics[name].append(metric)
    
    def record_cache_hit(self, cache_type: str, items_count: int = 1):
        """Record a cache hit."""
        self.optimization_stats['cache_hits'] += 1
        logger.debug(f"Cache hit: {cache_type} ({items_count} items)")
    
    def record_cache_miss(self, cache_type: str, items_count: int = 1):
        """Record a cache miss."""
        self.optimization_stats['cache_misses'] += 1
        logger.debug(f"Cache miss: {cache_type} ({items_count} items)")
    
    def record_debounced_operation(self, operation_type: str):
        """Record a debounced operation."""
        self.optimization_stats['debounced_operations'] += 1
        logger.debug(f"Debounced operation: {operation_type}")
    
    def record_lazy_load(self, component_name: str, load_time: float):
        """Record a lazy loading event."""
        self.optimization_stats['lazy_loads'] += 1
        self.record_instant_metric(f"lazy_load_{component_name}", load_time)
        logger.debug(f"Lazy loaded: {component_name} in {load_time:.2f}s")
    
    def record_connection_attempt_saved(self, reason: str):
        """Record a saved connection attempt due to smart connection management."""
        self.optimization_stats['connection_attempts_saved'] += 1
        logger.debug(f"Connection attempt saved: {reason}")
    
    def get_metric_stats(self, name: str) -> Dict:
        """Get statistics for a specific metric."""
        if name not in self.metrics:
            return {}
        
        durations = [m.duration for m in self.metrics[name] if m.duration is not None]
        if not durations:
            return {}
        
        return {
            'count': len(durations),
            'min': min(durations),
            'max': max(durations),
            'avg': sum(durations) / len(durations),
            'total': sum(durations)
        }
    
    def get_optimization_summary(self) -> Dict:
        """Get a summary of all Phase 3 optimization benefits."""
        total_runtime = time.time() - self.startup_time
        
        # Calculate cache efficiency
        total_cache_operations = self.optimization_stats['cache_hits'] + self.optimization_stats['cache_misses']
        cache_hit_rate = (self.optimization_stats['cache_hits'] / total_cache_operations * 100) if total_cache_operations > 0 else 0
        
        # Estimate time saved
        estimated_time_saved = (
            self.optimization_stats['cache_hits'] * 0.05 +  # 50ms per cache hit
            self.optimization_stats['debounced_operations'] * 0.1 +  # 100ms per debounced operation
            self.optimization_stats['connection_attempts_saved'] * 1.0  # 1s per saved connection attempt
        )
        
        summary = {
            'runtime_seconds': total_runtime,
            'cache_hit_rate_percent': cache_hit_rate,
            'estimated_time_saved_seconds': estimated_time_saved,
            'optimizations': self.optimization_stats.copy(),
            'performance_improvement_percent': (estimated_time_saved / total_runtime * 100) if total_runtime > 0 else 0
        }
        
        # Add specific metric summaries
        summary['metric_summaries'] = {}
        for metric_name in self.metrics:
            summary['metric_summaries'][metric_name] = self.get_metric_stats(metric_name)
        
        return summary
    
    def log_summary(self):
        """Log a performance summary."""
        summary = self.get_optimization_summary()
        
        logger.info("=== Phase 3 Optimization Performance Summary ===")
        logger.info(f"Runtime: {summary['runtime_seconds']:.2f}s")
        logger.info(f"Cache Hit Rate: {summary['cache_hit_rate_percent']:.1f}%")
        logger.info(f"Estimated Time Saved: {summary['estimated_time_saved_seconds']:.2f}s")
        logger.info(f"Performance Improvement: {summary['performance_improvement_percent']:.1f}%")
        
        logger.info("Optimization Stats:")
        for key, value in summary['optimizations'].items():
            logger.info(f"  {key}: {value}")
        
        # Log top metrics
        if summary['metric_summaries']:
            logger.info("Top Metrics:")
            for name, stats in list(summary['metric_summaries'].items())[:5]:
                if stats:
                    logger.info(f"  {name}: {stats['count']} calls, avg {stats['avg']*1000:.1f}ms")

# Global performance monitor
performance_monitor = PerformanceMonitor()

def timed_operation(operation_name: str, **metadata):
    """Decorator to time an operation."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            metric_id = performance_monitor.start_metric(operation_name, **metadata)
            try:
                result = func(*args, **kwargs)
                performance_monitor.finish_metric(metric_id, success=True)
                return result
            except Exception as e:
                performance_monitor.finish_metric(metric_id, success=False, error=str(e))
                raise
        return wrapper
    return decorator 