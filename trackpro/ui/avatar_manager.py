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
from urllib.parse import urlsplit, urlunsplit, quote
from typing import Optional, Callable

import requests
from PyQt6.QtCore import QTimer, Qt, QRect
from PyQt6.QtGui import QPixmap, QPainter, QBrush, QColor, QPen, QIcon, QFont, QPainterPath
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
    # Optional direct widget refs so we can marshal updates to the GUI thread
    label_ref: Optional[QLabel] = None
    button_ref: Optional[QPushButton] = None


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
        # Guard against zero/invalid sizes during early layout
        try:
            target_size = int(size) if isinstance(size, int) else 64
        except Exception:
            target_size = 64
        if target_size <= 8:
            # Try to infer from label; otherwise fallback to sensible default
            inferred = label.width() or label.height() or 64
            target_size = max(32, inferred)
        # Prefer cached image instantly if available; fallback to initials
        try:
            if url:
                cached = self.get_cached_pixmap(url, name, target_size)
                if cached and not cached.isNull():
                    label.setPixmap(cached)
                else:
                    label.setPixmap(self._create_initials_pixmap(name, target_size))
            else:
                label.setPixmap(self._create_initials_pixmap(name, target_size))
        except Exception:
            label.setPixmap(self._create_initials_pixmap(name, target_size))
        if not url:
            return
        self._start_download(_DownloadTask(
            url=url,
            size=target_size,
            name_for_initials=name,
            label_ref=label,
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
            url=url,
            size=size,
            name_for_initials=name,
            button_ref=button,
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
        
        Enforces one-file-per-user policy by deleting older files after a successful upload.
        Path format: avatars/{user_id}/avatar<ext>
        """
        try:
            from ..database.supabase_client import get_supabase_client
            import mimetypes
            client = get_supabase_client()
            if not client:
                return None

            # Use deterministic filename to avoid piling up many historical files
            original = os.path.basename(file_path)
            root, ext = os.path.splitext(original)
            ext = ext if (ext and len(ext) <= 10) else ".jpg"
            filename = f"avatar{ext}"

            # Path should not include the bucket name
            storage_path = f"{user_id}/{filename}"

            mime_type, _ = mimetypes.guess_type(file_path)
            if not mime_type:
                mime_type = "image/jpeg"

            with open(file_path, "rb") as f:
                data = f.read()

            # Upload with upsert so repeated uploads overwrite the single canonical file
            client.storage.from_("avatars").upload(
                storage_path,
                data,
                {
                    "content-type": mime_type,
                    "cache-control": "3600",
                    "upsert": "true",
                },
            )

            # Best-effort cleanup: remove any other files in this user's folder
            try:
                self._cleanup_user_avatars(client, user_id, keep_path=storage_path)
            except Exception:
                pass

            public_url = client.storage.from_("avatars").get_public_url(storage_path)
            return public_url
        except Exception:
            return None

    def _cleanup_user_avatars(self, client, user_id: str, keep_path: str) -> None:
        """Delete all avatar files in a user's folder except the given keep_path.

        This ensures only the latest avatar remains, preventing stale images showing up elsewhere.
        """
        try:
            files = client.storage.from_("avatars").list(user_id) or []
        except Exception:
            files = []

        if not files:
            return

        to_remove = []
        for entry in files:
            # 'entry' may be dict-like or object with 'name'
            name = entry.get("name") if isinstance(entry, dict) else getattr(entry, "name", None)
            if not name:
                continue
            full_path = f"{user_id}/{name}" if not name.startswith(f"{user_id}/") else name
            if full_path != keep_path:
                to_remove.append(full_path)

        if to_remove:
            try:
                client.storage.from_("avatars").remove(to_remove)
            except Exception:
                # Ignore cleanup failures; the primary upload has already succeeded
                pass

    # Internal helpers
    def _start_download(self, task: _DownloadTask) -> None:
        t = threading.Thread(target=self._download_and_dispatch, args=(task,), daemon=True)
        self._thread_pool.append(t)
        t.start()

    def invalidate_cache(self, url: Optional[str]) -> None:
        """Remove cached bytes for the given URL and its normalized variants.

        This forces a re-fetch the next time the avatar is requested, ensuring
        newly uploaded avatars propagate immediately across the UI.
        """
        try:
            if not url:
                return
            candidates = []
            normalized_url = self._normalize_public_url(url)
            legacy_url = self._legacy_public_url(url)
            sanitized_url = self._sanitize_url(url)
            # Base forms without query (to kill versioned/unversioned pairs)
            base = url.split('?')[0]
            base_norm = normalized_url.split('?')[0] if normalized_url else None
            base_sanitized = sanitized_url.split('?')[0] if sanitized_url else None
            for candidate in [url, normalized_url, legacy_url, sanitized_url, base, base_norm, base_sanitized]:
                if candidate and candidate not in candidates:
                    candidates.append(candidate)
            for candidate in candidates:
                path = self._cache_path(candidate)
                try:
                    if os.path.exists(path):
                        os.remove(path)
                except Exception:
                    pass
        except Exception:
            pass

    def _download_and_dispatch(self, task: _DownloadTask) -> None:
        # Fetch bytes in background thread; then marshal UI update to the GUI thread
        data = self._fetch_image_bytes(task.url)
        pixmap: Optional[QPixmap] = None
        if data:
            try:
                pix = QPixmap()
                if pix.loadFromData(data):
                    pixmap = self._circularize(pix, task.size)
            except Exception:
                pixmap = None
        if pixmap is None:
            pixmap = self._create_initials_pixmap(task.name_for_initials, task.size)

        # Thread-safe UI update via singleShot to the GUI thread
        if task.label_ref is not None:
            try:
                QTimer.singleShot(0, lambda l=task.label_ref, p=pixmap: l.setPixmap(p))
            except Exception:
                try:
                    task.label_ref.setPixmap(pixmap)
                except Exception:
                    pass
        elif task.button_ref is not None:
            try:
                QTimer.singleShot(0, lambda b=task.button_ref, p=pixmap: (b.setIcon(QIcon(p)), b.setText("")))
            except Exception:
                try:
                    task.button_ref.setIcon(QIcon(pixmap))
                    task.button_ref.setText("")
                except Exception:
                    pass

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
            # Sanitize URL (encode spaces and unsafe chars, normalize stray '&')
            safe_candidate = self._sanitize_url(candidate)
            # Try cache first (raw bytes)
            cached = self._load_bytes_from_cache(safe_candidate)
            if cached:
                return cached
            # Download
            try:
                resp = requests.get(safe_candidate, timeout=6)
                if resp.status_code == 200:
                    content = resp.content
                    # Store under all known variants to maximize cache hits
                    self._store_in_cache(safe_candidate, content)
                    if normalized_url:
                        self._store_in_cache(self._sanitize_url(normalized_url), content)
                    if legacy_url:
                        self._store_in_cache(self._sanitize_url(legacy_url), content)
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
        # Normalize '?&' -> '?' to avoid empty param confusion
        fixed = fixed.replace("?&", "?")
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

    def _sanitize_url(self, url: str) -> str:
        """Percent-encode path segments and normalize query formatting.

        - Encodes spaces and other unsafe characters in the path
        - Preserves the query string (after normalizing '?&' -> '?')
        """
        try:
            if not url:
                return url
            # Normalize stray '?&'
            if "?&" in url:
                url = url.replace("?&", "?")
            parts = urlsplit(url)
            # Encode path safely; keep '/' and common filename chars
            safe_path = quote(parts.path, safe="/_-.~%")
            # Rebuild URL
            rebuilt = urlunsplit((parts.scheme, parts.netloc, safe_path, parts.query, parts.fragment))
            return rebuilt
        except Exception:
            return url

    def _circularize(self, pixmap: QPixmap, size: int) -> QPixmap:
        """Return a centered, circular-cropped pixmap that fills the target size.

        Uses KeepAspectRatioByExpanding, centers the crop, and clips with an
        antialiased circular path to avoid any square edges.
        """
        if pixmap.isNull():
            return pixmap
        scaled = pixmap.scaled(
            size, size,
            Qt.AspectRatioMode.KeepAspectRatioByExpanding,
            Qt.TransformationMode.SmoothTransformation,
        )
        result = QPixmap(size, size)
        result.fill(Qt.GlobalColor.transparent)
        painter = QPainter(result)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        # Clip to a perfect circle
        path = QPainterPath()
        path.addEllipse(0, 0, size, size)
        painter.setClipPath(path)
        # Center-crop the scaled image
        src_x = max(0, (scaled.width() - size) // 2)
        src_y = max(0, (scaled.height() - size) // 2)
        src_rect = QRect(src_x, src_y, min(size, scaled.width()), min(size, scaled.height()))
        painter.drawPixmap(QRect(0, 0, size, size), scaled, src_rect)
        painter.end()
        return result

    def _update_label_pixmap_threadsafe(self, label: QLabel, pixmap: QPixmap) -> None:
        # Not used anymore; kept for backward compatibility
        try:
            QTimer.singleShot(0, lambda l=label, p=pixmap: l.setPixmap(p))
        except Exception:
            try:
                label.setPixmap(pixmap)
            except Exception:
                pass

    def _update_button_icon_threadsafe(self, button: QPushButton, pixmap: QPixmap) -> None:
        # Not used anymore; kept for backward compatibility
        try:
            QTimer.singleShot(0, lambda b=button, p=pixmap: (b.setIcon(QIcon(p)), b.setText("")))
        except Exception:
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


