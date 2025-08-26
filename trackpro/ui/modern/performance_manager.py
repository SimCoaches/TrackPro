import time
import threading
import ctypes
import logging
from queue import Queue, Empty
from PyQt6.QtCore import QThread, QTimer, pyqtSignal, QObject
from PyQt6.QtWidgets import QApplication

logger = logging.getLogger(__name__)

class PerformanceManager(QObject):
    ui_update_ready = pyqtSignal(dict)
    performance_warning = pyqtSignal(str, float)
    
    def __init__(self):
        super().__init__()
        self.ui_update_queue = Queue(maxsize=10)
        self.chart_update_queue = Queue(maxsize=5)
        self.ui_timer = None
        self.chart_timer = None
        self.perf_timer = None
        self.performance_stats = {
            'ui_updates': 0,
            'chart_updates': 0,
            'dropped_frames': 0,
            'max_ui_time': 0.0,
            'avg_ui_time': 0.0
        }
        self.frame_times = []
        self._timers_started = False
        # Defer timer setup until actually needed
        logger.info("✅ PerformanceManager initialized (timers deferred)")
    
    def setup_performance_monitoring(self):
        """DISABLED - Performance manager no longer used."""
        logger.info("🛑 Performance manager DISABLED - pedal thread handles UI directly")
        return
    
    def queue_ui_update(self, pedal_data):
        """DISABLED - Performance manager no longer used."""
        return

        try:
            while not self.ui_update_queue.empty():
                try:
                    self.ui_update_queue.get_nowait()
                    self.performance_stats['dropped_frames'] += 1
                except Empty:
                    break
            self.ui_update_queue.put_nowait(pedal_data)
        except:
            self.performance_stats['dropped_frames'] += 1
    
    def queue_chart_update(self, chart_data):
        """Queue chart update - starts timers if not already started."""
        if not self._timers_started:
            self.setup_performance_monitoring()
            
        try:
            while not self.chart_update_queue.empty():
                try:
                    self.chart_update_queue.get_nowait()
                except Empty:
                    break
            self.chart_update_queue.put_nowait(chart_data)
        except:
            pass
    
    def process_ui_updates(self):
        start_time = time.perf_counter()
        updates_processed = 0

        while not self.ui_update_queue.empty() and updates_processed < 5:
            try:
                data = self.ui_update_queue.get_nowait()
                self.ui_update_ready.emit(data)
                updates_processed += 1
                self.performance_stats['ui_updates'] += 1
            except Empty:
                break
        
        elapsed = time.perf_counter() - start_time
        self.frame_times.append(elapsed)
        if len(self.frame_times) > 100:
            self.frame_times.pop(0)
        
        if elapsed > 0.016:
            self.performance_warning.emit("UI Update Lag", elapsed * 1000)
        
        self.performance_stats['max_ui_time'] = max(self.performance_stats['max_ui_time'], elapsed)
        self.performance_stats['avg_ui_time'] = sum(self.frame_times) / len(self.frame_times)
    
    def process_chart_updates(self):
        start_time = time.perf_counter()
        
        try:
            data = self.chart_update_queue.get_nowait()
            self.performance_stats['chart_updates'] += 1
        except Empty:
            return
        
        elapsed = time.perf_counter() - start_time
        if elapsed > 0.033:
            self.performance_warning.emit("Chart Update Lag", elapsed * 1000)
    
    def log_performance(self):
        stats = self.performance_stats
        avg_time_ms = stats['avg_ui_time'] * 1000
        max_time_ms = stats['max_ui_time'] * 1000
        
        logger.info(f"🏁 PERFORMANCE: UI={stats['ui_updates']}/s, Charts={stats['chart_updates']}/s, "
                   f"Dropped={stats['dropped_frames']}, AvgTime={avg_time_ms:.1f}ms, MaxTime={max_time_ms:.1f}ms")
        
        if stats['dropped_frames'] > 50:
            logger.warning(f"⚠️ HIGH FRAME DROPS: {stats['dropped_frames']} - UI performance degraded")
        
        if avg_time_ms > 8.0:
            logger.warning(f"⚠️ SLOW UI UPDATES: {avg_time_ms:.1f}ms average (target <8ms)")
        
        stats['ui_updates'] = 0
        stats['chart_updates'] = 0
        stats['dropped_frames'] = 0
        stats['max_ui_time'] = 0.0

class ChartOptimizer(QObject):
    def __init__(self):
        super().__init__()
        self.last_chart_update = {}
        self.update_threshold = 0.033
        self.batch_updates = {}
        # DISABLED: ChartOptimizer timer causing handle exhaustion
        # self.batch_timer = QTimer()
        # self.batch_timer.timeout.connect(self.flush_batched_updates)
        # self.batch_timer.start(16)
    
    def should_update_chart(self, chart_id: str, current_time: float):
        last_update = self.last_chart_update.get(chart_id, 0)
        if current_time - last_update >= self.update_threshold:
            self.last_chart_update[chart_id] = current_time
            return True
        return False
    
    def batch_chart_update(self, chart_id: str, update_data):
        self.batch_updates[chart_id] = update_data
    
    def flush_batched_updates(self):
        for chart_id, data in self.batch_updates.items():
            pass
        self.batch_updates.clear()

class ThreadPriorityManager:
    @staticmethod
    def set_ui_thread_priority():
        try:
            # Define prototypes to avoid implicit conversions
            kernel32 = ctypes.windll.kernel32
            kernel32.GetCurrentThread.restype = ctypes.c_void_p
            kernel32.SetThreadPriority.argtypes = [ctypes.c_void_p, ctypes.c_int]
            kernel32.SetThreadPriority.restype = ctypes.c_int

            thread_handle = kernel32.GetCurrentThread()
            if kernel32.SetThreadPriority(thread_handle, 1):
                logger.info("🎨 UI THREAD: Set to ABOVE_NORMAL priority")
            else:
                error_code = kernel32.GetLastError()
                logger.warning(f"Failed to set UI thread priority. Error code: {error_code}")
        except Exception as e:
            logger.error(f"Could not set UI thread priority: {e}")
    
    @staticmethod
    def set_chart_thread_priority():
        try:
            kernel32 = ctypes.windll.kernel32
            kernel32.GetCurrentThread.restype = ctypes.c_void_p
            kernel32.SetThreadPriority.argtypes = [ctypes.c_void_p, ctypes.c_int]
            kernel32.SetThreadPriority.restype = ctypes.c_int

            thread_handle = kernel32.GetCurrentThread()
            if kernel32.SetThreadPriority(thread_handle, 0):
                logger.info("📊 CHART THREAD: Set to NORMAL priority")
            else:
                error_code = kernel32.GetLastError()
                logger.warning(f"Failed to set chart thread priority. Error code: {error_code}")
        except Exception as e:
            logger.error(f"Could not set chart thread priority: {e}")
    
    @staticmethod
    def set_background_thread_priority():
        try:
            kernel32 = ctypes.windll.kernel32
            kernel32.GetCurrentThread.restype = ctypes.c_void_p
            kernel32.SetThreadPriority.argtypes = [ctypes.c_void_p, ctypes.c_int]
            kernel32.SetThreadPriority.restype = ctypes.c_int

            thread_handle = kernel32.GetCurrentThread()
            if kernel32.SetThreadPriority(thread_handle, -1):
                logger.info("🔧 BACKGROUND THREAD: Set to BELOW_NORMAL priority")
            else:
                error_code = kernel32.GetLastError()
                logger.warning(f"Failed to set background thread priority. Error code: {error_code}")
        except Exception as e:
            logger.error(f"Could not set background thread priority: {e}")

class CPUCoreManager:
    @staticmethod
    def set_process_affinity():
        try:
            import psutil
            process = psutil.Process()
            cpu_count = psutil.cpu_count()
            
            if cpu_count >= 4:
                core_mask = list(range(min(4, cpu_count)))
                process.cpu_affinity(core_mask)
                logger.info(f"🖥️ CPU AFFINITY: Using cores {core_mask} for TrackPro")
            else:
                logger.info(f"🖥️ CPU AFFINITY: Using all {cpu_count} cores")
        except ImportError:
            logger.warning("psutil not available - cannot set CPU affinity")
        except Exception as e:
            logger.error(f"Could not set CPU affinity: {e}")
    
    @staticmethod
    def get_performance_recommendations():
        try:
            import psutil
            cpu_count = psutil.cpu_count()
            memory = psutil.virtual_memory()
            
            recommendations = []
            
            if cpu_count < 4:
                recommendations.append("⚠️ Consider upgrading to 4+ CPU cores for optimal performance")
            
            if memory.available < 2 * 1024**3:
                recommendations.append("⚠️ Low available RAM - consider closing other applications")
            
            if cpu_count >= 8:
                recommendations.append("✅ Excellent CPU for TrackPro - consider dedicating cores")
            
            return recommendations
        except:
            return ["CPU information unavailable"]