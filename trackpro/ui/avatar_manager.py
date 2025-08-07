"""Centralized Avatar Manager

Provides a single, robust way to load, cache, and render user avatars across the app.

Key features:
- Asynchronous HTTP fetching using requests (avoids QtNetwork TLS issues)
- Disk caching under ~/.trackpro/cache/avatars with simple TTL
- Consistent circular rendering with initials fallback
- Helper methods for QLabel and QPushButton targets
- Optional synchronous cached retrieval for immediate use
"""

from __future__ import annotations

import hashlib
import os
import threading
import time
from dataclasses import dataclass
from typing import Optional, Callable

import requests
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QPixmap, QPainter, QBrush, QColor, QPen, QIcon, QFont
from PyQt6.QtWidgets import QLabel, QPushButton


_CACHE_DIR = os.path.join(os.path.expanduser("~"), ".trackpro", "cache", "avatars")
_CACHE_TTL_SECONDS = 24 * 60 * 60  # 24h


def _ensure_cache_dir() -> str:
    try:
        os.makedirs(_CACHE_DIR, exist_ok=True)
    except Exception:
        # If we cannot create the directory, fallback to temp in current working dir
        fallback = os.path.join(os.getcwd(), ".avatar_cache")
        try:
            os.makedirs(fallback, exist_ok=True)
            return fallback
        except Exception:
            pass
    return _CACHE_DIR


def _hash_url(url: str) -> str:
    return hashlib.sha256(url.encode("utf-8")).hexdigest()


def _now() -> float:
    return time.time()


@dataclass
class _DownloadTask:
    url: str
    size: int
    name_for_initials: str
    on_result: Callable[[QPixmap], None]
    is_button: bool = False


class AvatarManager:
    _instance: Optional["AvatarManager"] = None
    _lock = threading.Lock()

    def __init__(self) -> None:
        self.cache_dir = _ensure_cache_dir()
        self._thread_pool = []  # keep references to threads to avoid GC during run

    @classmethod
    def instance(cls) -> "AvatarManager":
        with cls._lock:
            if cls._instance is None:
                cls._instance = AvatarManager()
        return cls._instance

    # Public API
    def set_label_avatar(self, label: QLabel, url: Optional[str], name: str, size: int = 64) -> None:
        """Set avatar on a QLabel. Shows initials immediately; updates when image arrives."""
        # Prefer cached image instantly if available; fallback to initials
        try:
            if url:
                cached = self.get_cached_pixmap(url, name, size)
                if cached and not cached.isNull():
                    label.setPixmap(cached)
                else:
                    label.setPixmap(self._create_initials_pixmap(name, size))
            else:
                label.setPixmap(self._create_initials_pixmap(name, size))
        except Exception:
            label.setPixmap(self._create_initials_pixmap(name, size))
        if not url:
            return
        self._start_download(_DownloadTask(
            url=url, size=size, name_for_initials=name,
            on_result=lambda pix: self._update_label_pixmap(label, pix)
        ))

    def set_button_avatar(self, button: QPushButton, url: Optional[str], name: str, size: int = 36) -> None:
        """Set avatar as a circular icon on a QPushButton. Shows initials immediately."""
        button.setIcon(QIcon())
        # Try cached icon immediately; otherwise show initials text
        used_cache = False
        try:
            if url:
                cached = self.get_cached_pixmap(url, name, size)
                if cached and not cached.isNull():
                    button.setIcon(QIcon(cached))
                    button.setText("")
                    used_cache = True
        except Exception:
            pass
        if not used_cache:
            button.setText(self._generate_initials(name))
        if not url:
            return
        self._start_download(_DownloadTask(
            url=url, size=size, name_for_initials=name,
            on_result=lambda pix: self._update_button_icon(button, pix),
            is_button=True,
        ))

    def get_cached_pixmap(self, url: str, name: str, size: int = 64) -> QPixmap:
        """Return a pixmap from cache if fresh; otherwise returns initials fallback.
        Does not perform network fetching. Useful when synchronous return is required.
        """
        normalized_url = self._normalize_public_url(url)
        legacy_url = self._legacy_public_url(url)
        pix = self._load_from_cache(url, size)
        if pix is not None and not pix.isNull():
            return pix
        pix = self._load_from_cache(normalized_url, size) or (self._load_from_cache(legacy_url, size) if legacy_url else None)
        if pix is not None and not pix.isNull():
            return pix
        return self._create_initials_pixmap(name, size)

    # Upload helper
    def upload_avatar(self, user_id: str, file_path: str) -> Optional[str]:
        """Upload an avatar file to Supabase storage and return public URL.

        Path format: avatars/{user_id}/{filename}
        """
        try:
            from ..database.supabase_client import get_supabase_client
            import mimetypes
            client = get_supabase_client()
            if not client:
                return None
            filename = os.path.basename(file_path)
            # IMPORTANT: storage path should NOT include the bucket name
            storage_path = f"{user_id}/{filename}"
            mime_type, _ = mimetypes.guess_type(file_path)
            if not mime_type:
                mime_type = "image/jpeg"
            with open(file_path, "rb") as f:
                data = f.read()
            client.storage.from_("avatars").upload(
                storage_path,
                data,
                {
                    "content-type": mime_type,
                    "cache-control": "3600",
                    "upsert": "true",
                },
            )
            public_url = client.storage.from_("avatars").get_public_url(storage_path)
            return public_url
        except Exception:
            return None

    # Internal helpers
    def _start_download(self, task: _DownloadTask) -> None:
        t = threading.Thread(target=self._download_and_dispatch, args=(task,), daemon=True)
        self._thread_pool.append(t)
        t.start()

    def _download_and_dispatch(self, task: _DownloadTask) -> None:
        # Fetch bytes in background thread; construct QPixmap on main thread for safety
        data = self._fetch_image_bytes(task.url)
        def _finish_on_main_thread():
            if data:
                pix = QPixmap()
                if pix.loadFromData(data):
                    pix = self._circularize(pix, task.size)
                    task.on_result(pix)
                    return
            task.on_result(self._create_initials_pixmap(task.name_for_initials, task.size))
        QTimer.singleShot(0, _finish_on_main_thread)

    def _fetch_image_bytes(self, url: str) -> Optional[bytes]:
        """Fetch image bytes with compatibility for legacy double-avatars URLs.

        Attempts the original URL first, then a normalized variant that removes
        duplicated "/public/avatars/avatars/" if the first fails.
        """
        normalized_url = self._normalize_public_url(url)
        legacy_url = self._legacy_public_url(url)
        candidates = []
        for candidate in [url, normalized_url, legacy_url]:
            if candidate and candidate not in candidates:
                candidates.append(candidate)

        for candidate in candidates:
            # Try cache first (raw bytes)
            cached = self._load_bytes_from_cache(candidate)
            if cached:
                return cached
            # Download
            try:
                resp = requests.get(candidate, timeout=6)
                if resp.status_code == 200:
                    content = resp.content
                    # Store under all known variants to maximize cache hits
                    self._store_in_cache(candidate, content)
                    if normalized_url and candidate != normalized_url:
                        self._store_in_cache(normalized_url, content)
                    if legacy_url and candidate != legacy_url:
                        self._store_in_cache(legacy_url, content)
                    return content
            except Exception:
                continue
        return None

    def _pixmap_from_bytes(self, data: bytes) -> QPixmap:
        pix = QPixmap()
        try:
            pix.loadFromData(data)
        except Exception:
            pass
        return pix

    def _cache_path(self, url: str) -> str:
        return os.path.join(self.cache_dir, _hash_url(url) + ".img")

    def _load_from_cache(self, url: str, size: int) -> Optional[QPixmap]:
        path = self._cache_path(url)
        try:
            if os.path.exists(path) and (_now() - os.path.getmtime(path) < _CACHE_TTL_SECONDS):
                with open(path, "rb") as f:
                    data = f.read()
                pix = self._pixmap_from_bytes(data)
                if pix and not pix.isNull():
                    return self._circularize(pix, size)
        except Exception:
            pass
        return None

    def _load_bytes_from_cache(self, url: str) -> Optional[bytes]:
        path = self._cache_path(url)
        try:
            if os.path.exists(path) and (_now() - os.path.getmtime(path) < _CACHE_TTL_SECONDS):
                with open(path, "rb") as f:
                    return f.read()
        except Exception:
            pass
        return None

    def _store_in_cache(self, url: str, data: bytes) -> None:
        try:
            path = self._cache_path(url)
            with open(path, "wb") as f:
                f.write(data)
        except Exception:
            pass

    def _normalize_public_url(self, url: str) -> str:
        """Fix common mistakes in stored Supabase public URLs.

        - Deduplicate bucket segment: .../public/avatars/avatars/... -> .../public/avatars/...
        - Strip stray trailing question mark without query params
        """
        if not url:
            return url
        fixed = url.replace("/public/avatars/avatars/", "/public/avatars/")
        if fixed.endswith("?"):
            fixed = fixed[:-1]
        return fixed

    def _legacy_public_url(self, url: str) -> Optional[str]:
        """Produce legacy form by inserting an extra 'avatars/' if needed.
        Example: .../public/avatars/<uuid>/file -> .../public/avatars/avatars/<uuid>/file
        """
        if not url or "/public/avatars/" not in url:
            return None
        if "/public/avatars/avatars/" in url:
            return url
        return url.replace("/public/avatars/", "/public/avatars/avatars/")

    def _circularize(self, pixmap: QPixmap, size: int) -> QPixmap:
        if pixmap.isNull():
            return pixmap
        scaled = pixmap.scaled(size, size, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
        circular = QPixmap(size, size)
        circular.fill(Qt.GlobalColor.transparent)
        painter = QPainter(circular)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QBrush(scaled))
        painter.setPen(QPen(Qt.GlobalColor.transparent))
        painter.drawEllipse(0, 0, size, size)
        painter.end()
        return circular

    def _update_label_pixmap(self, label: QLabel, pixmap: QPixmap) -> None:
        try:
            label.setPixmap(pixmap)
        except Exception:
            pass

    def _update_button_icon(self, button: QPushButton, pixmap: QPixmap) -> None:
        try:
            button.setIcon(QIcon(pixmap))
            button.setText("")
        except Exception:
            pass

    def _generate_initials(self, name: str) -> str:
        if not name or name.strip() == "":
            return "U"
        parts = name.strip().split()
        if len(parts) == 1:
            word = parts[0]
            return (word[:2] if len(word) >= 2 else word[0]).upper()
        return (parts[0][0] + parts[-1][0]).upper()

    def _create_initials_pixmap(self, name: str, size: int) -> QPixmap:
        initials = self._generate_initials(name)
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        colors = ["#3498db", "#e74c3c", "#f39c12", "#27ae60", "#9b59b6", "#1abc9c"]
        color_index = hash(name) % len(colors)
        painter.setBrush(QBrush(QColor(colors[color_index])))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(0, 0, size, size)
        painter.setPen(QColor("#ffffff"))
        font = QFont()
        font.setBold(True)
        font.setPixelSize(max(10, size // 3))
        painter.setFont(font)
        painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, initials)
        painter.end()
        return pixmap


