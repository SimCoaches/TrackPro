"""
Centralized Avatar Management System for TrackPro

This module provides a centralized system for loading, caching, and displaying
user avatars across the entire application. It prevents crashes by managing
network requests, implementing caching, and providing fallbacks.
"""

import logging
import hashlib
import os
from typing import Optional, Dict, Any, Callable
from pathlib import Path
from datetime import datetime, timedelta
from threading import Lock
from dataclasses import dataclass
from enum import Enum

from PyQt6.QtCore import QObject, QThread, QTimer, pyqtSignal, QUrl, QSize, Qt, QMetaObject, Q_ARG
from PyQt6.QtGui import QPixmap, QPainter, QBrush, QPen, QColor, QFont, QIcon
from PyQt6.QtWidgets import QLabel, QApplication
from PyQt6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply

logger = logging.getLogger(__name__)

class AvatarSize(Enum):
    """Standard avatar sizes used across the application."""
    TINY = 24
    SMALL = 32
    MEDIUM = 48
    LARGE = 64
    XLARGE = 80
    XXLARGE = 100

@dataclass
class AvatarCache:
    """Cache entry for an avatar."""
    pixmap: QPixmap
    timestamp: datetime
    size: int
    url: str

class AvatarLoadRequest:
    """Represents a request to load an avatar."""
    def __init__(self, url: str, size: int, callback: Callable[[QPixmap], None], 
                 fallback_callback: Optional[Callable[[str], QPixmap]] = None):
        self.url = url
        self.size = size
        self.callback = callback
        self.fallback_callback = fallback_callback
        self.timestamp = datetime.now()

class AvatarManager(QObject):
    """
    Centralized avatar management system.
    
    Features:
    - Caching with TTL
    - Rate limiting
    - Error handling and fallbacks
    - Thread-safe operations
    - Memory management
    - Standardized avatar sizes
    """
    
    # Signals
    avatar_loaded = pyqtSignal(str, QPixmap)  # url, pixmap
    avatar_load_failed = pyqtSignal(str, str)  # url, error_message
    cache_cleared = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Cache settings
        self.cache_ttl = timedelta(hours=24)  # Cache for 24 hours
        self.max_cache_size = 100  # Maximum number of cached avatars
        self.cache: Dict[str, AvatarCache] = {}
        self.cache_lock = Lock()
        
        # Rate limiting
        self.max_concurrent_requests = 3
        self.request_queue: list[AvatarLoadRequest] = []
        self.active_requests = 0
        self.rate_limit_timer = QTimer()
        self.rate_limit_timer.timeout.connect(self._process_request_queue)
        
        # Cleanup timer
        self.cleanup_timer = QTimer()
        self.cleanup_timer.timeout.connect(self._cleanup_cache)
        
        # Background thread for processing
        self.worker_thread = QThread()
        self.worker_thread.start()
        self.moveToThread(self.worker_thread)
        
        # Network manager - must be created after moving to thread
        self.network_manager = QNetworkAccessManager()
        self.network_manager.moveToThread(self.worker_thread)
        self.network_manager.finished.connect(self._on_network_reply_finished)
        
        # Start timers after moving to thread
        self.rate_limit_timer.start(100)  # Process queue every 100ms
        self.cleanup_timer.start(300000)  # Cleanup every 5 minutes
        
        logger.info("AvatarManager initialized")
    
    def get_avatar(self, url: str, size: AvatarSize, callback: Callable[[QPixmap], None],
                   user_name: str = "User", fallback_callback: Optional[Callable[[str], QPixmap]] = None) -> Optional[QPixmap]:
        """
        Get an avatar, either from cache or by loading from URL.
        
        Args:
            url: Avatar URL
            size: Standard avatar size
            callback: Function to call when avatar is loaded
            user_name: User name for fallback initials
            fallback_callback: Optional custom fallback function
            
        Returns:
            Cached pixmap if available, None if needs to be loaded
        """
        if not url:
            # No URL provided, create fallback immediately
            fallback = self._create_fallback_avatar(user_name, size.value)
            self._safe_callback(callback, fallback)
            return fallback
        
        # Check cache first
        cache_key = self._get_cache_key(url, size.value)
        with self.cache_lock:
            if cache_key in self.cache:
                cache_entry = self.cache[cache_key]
                if datetime.now() - cache_entry.timestamp < self.cache_ttl:
                    logger.debug(f"Avatar cache hit: {url}")
                    self._safe_callback(callback, cache_entry.pixmap)
                    return cache_entry.pixmap
                else:
                    # Expired cache entry
                    del self.cache[cache_key]
        
        # Not in cache, queue for loading
        request = AvatarLoadRequest(url, size.value, callback, fallback_callback)
        self.request_queue.append(request)
        
        # Provide immediate fallback
        fallback = self._create_fallback_avatar(user_name, size.value)
        self._safe_callback(callback, fallback)
        
        return None
    
    def _safe_callback(self, callback: Callable[[QPixmap], None], pixmap: QPixmap):
        """Safely execute callback on the main thread."""
        try:
            # Check if we're on the main thread
            if QThread.currentThread() == QApplication.instance().thread():
                # We're on the main thread, call directly
                callback(pixmap)
            else:
                # We're on a background thread, invoke on main thread
                QMetaObject.invokeMethod(
                    QApplication.instance(),
                    lambda: callback(pixmap),
                    Qt.ConnectionType.QueuedConnection
                )
        except Exception as e:
            logger.error(f"Error executing avatar callback: {e}")
    
    def _get_cache_key(self, url: str, size: int) -> str:
        """Generate cache key for URL and size combination."""
        return f"{hashlib.md5(url.encode()).hexdigest()}_{size}"
    
    def _process_request_queue(self):
        """Process queued avatar load requests with rate limiting."""
        if self.active_requests >= self.max_concurrent_requests:
            return
        
        if not self.request_queue:
            return
        
        # Process up to max_concurrent_requests
        while self.request_queue and self.active_requests < self.max_concurrent_requests:
            request = self.request_queue.pop(0)
            self._load_avatar_from_url(request)
            self.active_requests += 1
    
    def _load_avatar_from_url(self, request: AvatarLoadRequest):
        """Load avatar from URL with error handling."""
        try:
            # Create network request
            network_request = QNetworkRequest(QUrl(request.url))
            network_request.setAttribute(QNetworkRequest.Attribute.CacheLoadControlAttribute, 
                                     QNetworkRequest.CacheLoadControl.AlwaysCache)
            
            # Store request info for callback
            reply = self.network_manager.get(network_request)
            reply.setProperty("request", request)
            
            logger.debug(f"Started loading avatar: {request.url}")
            
        except Exception as e:
            logger.error(f"Error creating network request for {request.url}: {e}")
            self._handle_load_failure(request, str(e))
            self.active_requests -= 1
    
    def _on_network_reply_finished(self, reply: QNetworkReply):
        """Handle network reply completion."""
        request = reply.property("request")
        if not request:
            logger.error("No request found in network reply")
            self.active_requests -= 1
            return
        
        try:
            if reply.error() == QNetworkReply.NetworkError.NoError:
                # Successfully downloaded
                image_data = reply.readAll()
                pixmap = QPixmap()
                
                if pixmap.loadFromData(image_data):
                    # Process and cache the avatar
                    processed_pixmap = self._process_avatar_pixmap(pixmap, request.size)
                    self._cache_avatar(request.url, processed_pixmap, request.size)
                    
                    # Call the callback safely
                    self._safe_callback(request.callback, processed_pixmap)
                    self.avatar_loaded.emit(request.url, processed_pixmap)
                    
                    logger.debug(f"Successfully loaded avatar: {request.url}")
                else:
                    raise Exception("Failed to load image data")
            else:
                # Network error
                error_msg = reply.errorString()
                logger.warning(f"Network error loading avatar {request.url}: {error_msg}")
                self._handle_load_failure(request, error_msg)
                
        except Exception as e:
            logger.error(f"Error processing avatar {request.url}: {e}")
            self._handle_load_failure(request, str(e))
        
        finally:
            reply.deleteLater()
            self.active_requests -= 1
    
    def _handle_load_failure(self, request: AvatarLoadRequest, error_msg: str):
        """Handle avatar load failure."""
        logger.warning(f"Avatar load failed for {request.url}: {error_msg}")
        self.avatar_load_failed.emit(request.url, error_msg)
        
        # If we have a custom fallback, use it
        if request.fallback_callback:
            try:
                fallback = request.fallback_callback(request.url)
                self._safe_callback(request.callback, fallback)
            except Exception as e:
                logger.error(f"Custom fallback failed: {e}")
                # Use default fallback
                fallback = self._create_fallback_avatar("User", request.size)
                self._safe_callback(request.callback, fallback)
        else:
            # Use default fallback
            fallback = self._create_fallback_avatar("User", request.size)
            self._safe_callback(request.callback, fallback)
    
    def _process_avatar_pixmap(self, pixmap: QPixmap, size: int) -> QPixmap:
        """Process and resize avatar pixmap."""
        if pixmap.isNull():
            return self._create_fallback_avatar("User", size)
        
        # Scale to target size
        scaled_pixmap = pixmap.scaled(
            size, size,
            Qt.AspectRatioMode.KeepAspectRatioByExpanding,
            Qt.TransformationMode.SmoothTransformation
        )
        
        # Create circular mask
        circular_pixmap = QPixmap(size, size)
        circular_pixmap.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(circular_pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Create circular path
        from PyQt6.QtGui import QPainterPath
        path = QPainterPath()
        path.addEllipse(0, 0, size, size)
        painter.setClipPath(path)
        
        # Draw the scaled image
        painter.drawPixmap(0, 0, size, size, scaled_pixmap)
        
        # Draw border
        painter.setClipping(False)
        painter.setPen(QPen(QColor("#ffffff"), 2))
        painter.drawEllipse(1, 1, size-2, size-2)
        
        painter.end()
        return circular_pixmap
    
    def _create_fallback_avatar(self, name: str, size: int) -> QPixmap:
        """Create a fallback avatar with user initials."""
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Generate initials
        initials = self._generate_initials(name)
        
        # Draw circle background using TrackPro colors
        colors = ['#3498db', '#e74c3c', '#f39c12', '#27ae60', '#9b59b6', '#1abc9c']
        color_index = hash(name) % len(colors)
        painter.setBrush(QBrush(QColor(colors[color_index])))
        painter.setPen(QPen(Qt.GlobalColor.transparent))
        painter.drawEllipse(0, 0, size, size)
        
        # Draw initials
        painter.setPen(QColor('#ffffff'))
        font = painter.font()
        font.setPixelSize(size // 3)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, initials)
        
        painter.end()
        return pixmap
    
    def _generate_initials(self, name: str) -> str:
        """Generate initials from a name."""
        if not name:
            return "U"
        
        parts = name.strip().split()
        if len(parts) >= 2:
            return f"{parts[0][0]}{parts[-1][0]}".upper()
        elif len(parts) == 1:
            return parts[0][:2].upper()
        else:
            return "U"
    
    def _cache_avatar(self, url: str, pixmap: QPixmap, size: int):
        """Cache an avatar."""
        cache_key = self._get_cache_key(url, size)
        
        with self.cache_lock:
            # Remove oldest entries if cache is full
            if len(self.cache) >= self.max_cache_size:
                oldest_key = min(self.cache.keys(), 
                               key=lambda k: self.cache[k].timestamp)
                del self.cache[oldest_key]
            
            # Add new entry
            self.cache[cache_key] = AvatarCache(
                pixmap=pixmap,
                timestamp=datetime.now(),
                size=size,
                url=url
            )
    
    def _cleanup_cache(self):
        """Remove expired cache entries."""
        with self.cache_lock:
            current_time = datetime.now()
            expired_keys = [
                key for key, entry in self.cache.items()
                if current_time - entry.timestamp > self.cache_ttl
            ]
            
            for key in expired_keys:
                del self.cache[key]
            
            if expired_keys:
                logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")
    
    def clear_cache(self):
        """Clear all cached avatars."""
        with self.cache_lock:
            self.cache.clear()
        logger.info("Avatar cache cleared")
        self.cache_cleared.emit()
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self.cache_lock:
            return {
                'total_entries': len(self.cache),
                'max_size': self.max_cache_size,
                'active_requests': self.active_requests,
                'queued_requests': len(self.request_queue)
            }
    
    def shutdown(self):
        """Shutdown the avatar manager."""
        logger.info("Shutting down AvatarManager")
        self.cleanup_timer.stop()
        self.rate_limit_timer.stop()
        self.worker_thread.quit()
        self.worker_thread.wait()

# Global avatar manager instance
_avatar_manager: Optional[AvatarManager] = None

def get_avatar_manager() -> AvatarManager:
    """Get the global avatar manager instance."""
    global _avatar_manager
    if _avatar_manager is None:
        _avatar_manager = AvatarManager()
    return _avatar_manager

def shutdown_avatar_manager():
    """Shutdown the global avatar manager."""
    global _avatar_manager
    if _avatar_manager:
        _avatar_manager.shutdown()
        _avatar_manager = None
