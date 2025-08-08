"""
Pedal Overlay - Live rolling 5s visualization for throttle, brake, clutch

This overlay reads the latest pedal values from the global hardware system
and renders a rolling 5-second graph similar to RaceApps.

It reuses the existing global hardware connection (no new threads).
"""

from __future__ import annotations

import time
import logging
from collections import deque
from typing import Deque, Dict, Tuple, Optional

from PyQt6.QtCore import Qt, QTimer, QPoint, QPointF, QRect, QLineF, QObject, pyqtSignal
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush, QFont, QPixmap
from PyQt6.QtWidgets import QWidget, QApplication, QSizeGrip, QMenu, QPushButton


logger = logging.getLogger(__name__)


class PedalOverlayWindow(QWidget):
    """Transparent always-on-top overlay that shows last 5s of pedal data."""
    # Emitted when the overlay is closed by the user
    closed = pyqtSignal()

    def __init__(self):
        super().__init__()

        # Visual config
        self.window_width = 520
        self.window_height = 220
        self.aspect_ratio = self.window_width / self.window_height
        self.padding = 12
        self.background_color = QColor(0, 0, 0, 140)
        self.border_color = QColor(255, 255, 255, 40)
        self.grid_color = QColor(255, 255, 255, 25)
        self.text_color = QColor(230, 230, 230, 230)
        self.throttle_color = QColor(0, 200, 0, 220)
        self.brake_color = QColor(220, 0, 0, 220)
        self.clutch_color = QColor(0, 160, 220, 220)

        # Rolling buffers: (timestamp_seconds, value_0_to_1)
        self.history_seconds = 5.0
        self.buffers: Dict[str, Deque[Tuple[float, float]]] = {
            'throttle': deque(),
            'brake': deque(),
            'clutch': deque(),
        }

        # Last known values when hardware not available yet
        self.current_values: Dict[str, float] = {'throttle': 0.0, 'brake': 0.0, 'clutch': 0.0}

        # Window flags for floating transparent window
        flags = Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool
        self.setWindowFlags(flags)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        # Start position and size
        self.setMinimumSize(480, int(480 / self.aspect_ratio))
        self.resize(self.window_width, self.window_height)
        self.move(120, 120)

        # Dragging state (window can be moved by dragging background)
        self._drag_start: Optional[QPoint] = None

        # Resize grip for frameless window resizing
        self.size_grip = QSizeGrip(self)
        grip_size = 18
        self.size_grip.setFixedSize(grip_size, grip_size)
        self._is_adjusting_size = False
        self._grid_pixmap: Optional[QPixmap] = None
        self._cached_plot_size: Optional[Tuple[int, int]] = None
        self._title_font = QFont("Arial", 10, QFont.Weight.Bold)
        self._legend_font = QFont("Arial", 9, QFont.Weight.Normal)
        self._title_metrics = None
        self._legend_metrics = None
        self._top_bar_height = 0

        # Visible close button in top-right
        self.close_button = QPushButton("✕", self)
        self.close_button.setToolTip("Close overlay (Esc)")
        self.close_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.close_button.setFixedSize(22, 22)
        self.close_button.setFlat(True)
        self.close_button.clicked.connect(self.close)
        self.close_button.setStyleSheet(
            """
            QPushButton { color: rgb(230,230,230); background-color: rgba(255,255,255,28); border: 1px solid rgba(255,255,255,40); border-radius: 11px; }
            QPushButton:hover { background-color: rgba(255,255,255,60); }
            QPushButton:pressed { background-color: rgba(255,255,255,90); }
            """
        )

        # Update timer ~60 FPS for smooth drawing (precise, monotonic timestamps)
        self.update_timer = QTimer(self)
        # Use a precise timer to avoid Windows coarse timer jitter that can look like 1s hitching
        try:
            self.update_timer.setTimerType(Qt.TimerType.PreciseTimer)
        except Exception:
            pass  # Fallback safely if Qt version lacks PreciseTimer
        self.update_timer.timeout.connect(self._on_update_timer)
        # Slightly faster than 60 FPS for smoother motion but still very light on CPU
        self.update_timer.start(12)  # ~83 FPS

        self._update_text_metrics()
        logger.info("🎛️ Pedal overlay window initialized")

    def _update_text_metrics(self):
        temp_painter = QPainter()
        temp_painter.begin(self)
        temp_painter.setFont(self._title_font)
        self._title_metrics = temp_painter.fontMetrics()
        temp_painter.setFont(self._legend_font)
        self._legend_metrics = temp_painter.fontMetrics()
        self._top_bar_height = self._title_metrics.height() if self._title_metrics else 18
        temp_painter.end()

    def _rebuild_grid_pixmap(self, plot_rect: QRect):
        width = max(1, plot_rect.width())
        height = max(1, plot_rect.height())
        if self._cached_plot_size == (width, height):
            return
        self._grid_pixmap = QPixmap(width, height)
        self._grid_pixmap.fill(Qt.GlobalColor.transparent)
        p = QPainter(self._grid_pixmap)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        p.setPen(QPen(self.grid_color, 1))
        seconds = 5
        for i in range(seconds + 1):
            x = width - int(i * (width / seconds))
            p.drawLine(x, 0, x, height)
        for frac in (0.0, 0.5, 1.0):
            y = height - int(frac * height)
            p.drawLine(0, y, width, y)
        p.end()
        self._cached_plot_size = (width, height)

    # ----- Interaction -----
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_start = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._drag_start is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_start)
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_start = None
            event.accept()
        else:
            super().mouseReleaseEvent(event)

    # ----- Data update -----
    def _read_latest_pedals(self) -> Dict[str, float]:
        """Read latest raw values (0..65535) from global hardware, normalize to 0..1."""
        try:
            # Import lazily to avoid circular imports at module load time
            from new_ui import get_global_hardware
            hardware = get_global_hardware()
            if hardware and hasattr(hardware, 'last_values') and hardware.last_values:
                raw = hardware.last_values
            else:
                # Fallback to current values when hardware not ready
                raw = {
                    'throttle': int(self.current_values['throttle'] * 65535),
                    'brake': int(self.current_values['brake'] * 65535),
                    'clutch': int(self.current_values['clutch'] * 65535),
                }

            # Normalize
            norm = {}
            for k in ('throttle', 'brake', 'clutch'):
                v = max(0, min(65535, int(raw.get(k, 0))))
                norm[k] = v / 65535.0
            return norm
        except Exception as e:
            # Keep last values on error
            logger.debug(f"Pedal overlay: read error: {e}")
            return self.current_values

    def _on_update_timer(self):
        # Use a monotonic high-resolution clock to prevent wall-clock adjustments from causing jumps
        now = time.perf_counter()
        vals = self._read_latest_pedals()
        self.current_values = vals

        # Append to buffers and drop older than history window
        for name, value in vals.items():
            buf = self.buffers[name]
            buf.append((now, float(value)))
            # Trim
            cutoff = now - self.history_seconds
            while buf and buf[0][0] < cutoff:
                buf.popleft()

        # Trigger repaint
        self.update()

    # ----- Rendering -----
    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        try:
            painter.setRenderHint(QPainter.RenderHint.HighQualityAntialiasing, True)
        except Exception:
            pass

        # Background card
        rect = self.rect()
        bg_rect = rect.adjusted(0, 0, -1, -1)
        painter.setBrush(QBrush(self.background_color))
        painter.setPen(QPen(self.border_color, 1))
        painter.drawRoundedRect(bg_rect, 10, 10)

        # Top bar: title + horizontal legend
        painter.setPen(self.text_color)
        painter.setFont(self._title_font)
        title_text = "Pedals (last 5s)"
        title_metrics = self._title_metrics or painter.fontMetrics()
        title_height = self._top_bar_height
        title_width = title_metrics.horizontalAdvance(title_text)

        top_bar_height = title_height
        top_bar_rect = QRect(self.padding, self.padding, rect.width() - 2 * self.padding, top_bar_height)
        painter.drawText(top_bar_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, title_text)

        # Legend items horizontally to the right of the title
        painter.setFont(self._legend_font)
        legend_metrics = self._legend_metrics or painter.fontMetrics()
        marker_size = 10
        spacing_between_items = 14
        spacing_after_marker = 6

        start_x = self.padding + title_width + 16
        center_y = self.padding + top_bar_height // 2

        legend_items = [
            ("Throttle", self.throttle_color, self.buffers['throttle'][-1][1] if self.buffers['throttle'] else 0.0),
            ("Brake", self.brake_color, self.buffers['brake'][-1][1] if self.buffers['brake'] else 0.0),
            ("Clutch", self.clutch_color, self.buffers['clutch'][-1][1] if self.buffers['clutch'] else 0.0),
        ]

        for name, color, value in legend_items:
            # marker
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(color))
            painter.drawRoundedRect(start_x, center_y - marker_size // 2, marker_size, marker_size, 2, 2)
            # text
            painter.setPen(self.text_color)
            label_text = f"{name}: {int(value * 100):d}%"
            text_x = start_x + marker_size + spacing_after_marker
            text_y = self.padding
            text_w = legend_metrics.horizontalAdvance(label_text)
            text_h = top_bar_height
            painter.drawText(QRect(text_x, text_y, text_w + 2, text_h), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, label_text)
            start_x = text_x + text_w + spacing_between_items

        # Plot area below the top bar
        top = self.padding + top_bar_height + 8
        plot_rect = QRect(self.padding, top, rect.width() - 2 * self.padding, rect.height() - top - self.padding)

        # Draw cached grid
        self._rebuild_grid_pixmap(plot_rect)
        if self._grid_pixmap is not None:
            painter.drawPixmap(plot_rect.topLeft(), self._grid_pixmap)

        # Helper to draw one series
        def draw_series(name: str, color: QColor):
            buf = self.buffers[name]
            if len(buf) < 2:
                return
            painter.setPen(QPen(color, 2))
            # Map timestamps: right edge is current time, left edge is now-5s for smooth continuous scroll
            now_ts = time.perf_counter()
            start_ts = now_ts - self.history_seconds
            # Build a path for sub-pixel smoothness
            from PyQt6.QtGui import QPainterPath
            path = QPainterPath()
            last_px = None
            for ts, val in buf:
                x_frac = (ts - start_ts) / self.history_seconds
                x_frac = max(0.0, min(1.0, x_frac))
                x = float(plot_rect.left() + x_frac * plot_rect.width())
                y = float(plot_rect.bottom() - val * plot_rect.height())
                if last_px is None:
                    path.moveTo(QPointF(x, y))
                else:
                    path.lineTo(QPointF(x, y))
                last_px = (x, y)
            painter.drawPath(path)

        # Draw series: throttle (green), brake (red), clutch (blue)
        draw_series('throttle', self.throttle_color)
        draw_series('brake', self.brake_color)
        draw_series('clutch', self.clutch_color)

        painter.end()

    def resizeEvent(self, event):
        # Enforce constant aspect ratio while allowing free resize gestures
        if not self._is_adjusting_size:
            new_w = max(event.size().width(), self.minimumWidth())
            new_h = max(event.size().height(), self.minimumHeight())

            # Fit to aspect ratio based on the tighter constraint
            target_h = int(new_w / self.aspect_ratio)
            target_w = int(new_h * self.aspect_ratio)
            if target_h <= new_h:
                adjusted_w, adjusted_h = new_w, target_h
            else:
                adjusted_w, adjusted_h = target_w, new_h

            if adjusted_w != self.width() or adjusted_h != self.height():
                self._is_adjusting_size = True
                self.resize(adjusted_w, adjusted_h)
                return  # wait for the next resizeEvent with the corrected size

        # Keep the size grip anchored to the bottom-right corner
        if hasattr(self, 'size_grip') and self.size_grip is not None:
            margin = 2
            grip_w = self.size_grip.width()
            grip_h = self.size_grip.height()
            self.size_grip.move(self.width() - grip_w - margin, self.height() - grip_h - margin)

        # Position the close button at top-right
        btn_margin = 6
        btn_w = self.close_button.width()
        btn_h = self.close_button.height()
        self.close_button.move(self.width() - btn_w - btn_margin, btn_margin)
        self.close_button.raise_()

        # Invalidate cached assets on resize
        self._cached_plot_size = None
        self._grid_pixmap = None
        self._update_text_metrics()
        super().resizeEvent(event)
        self._is_adjusting_size = False

    # ----- Close controls -----
    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.close()
            event.accept()
        else:
            super().keyPressEvent(event)

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        close_action = menu.addAction("Close overlay (Esc)")
        action = menu.exec(event.globalPos())
        if action == close_action:
            self.close()

    def closeEvent(self, event):
        try:
            if hasattr(self, 'update_timer') and self.update_timer is not None:
                self.update_timer.stop()
        finally:
            # Notify listeners (manager) so it can clean up its state
            try:
                # pyqtSignal object stored on instance attribute created above
                self.closed.emit()  # type: ignore[attr-defined]
            except Exception:
                pass
            super().closeEvent(event)


class PedalOverlayManager(QObject):
    """Manager class to start/stop the pedal overlay."""

    def __init__(self):
        super().__init__()
        self.overlay: Optional[PedalOverlayWindow] = None
        self.is_active = False

    def start_overlay(self) -> bool:
        if self.is_active:
            logger.info("Pedal overlay already active")
            return True
        try:
            # Ensure app exists
            if QApplication.instance() is None:
                logger.error("Cannot start pedal overlay without QApplication")
                return False

            self.overlay = PedalOverlayWindow()
            # Keep manager state in sync when user closes the overlay directly
            # pyqt: connect at runtime since signal attribute was created on instance
            try:
                self.overlay.closed.connect(self._on_overlay_closed)  # type: ignore[attr-defined]
            except Exception:
                pass
            self.overlay.show()
            self.overlay.raise_()
            self.is_active = True
            logger.info("🎛️ Pedal overlay started")
            return True
        except Exception as e:
            logger.error(f"Failed to start pedal overlay: {e}")
            self.overlay = None
            self.is_active = False
            return False

    def stop_overlay(self):
        if not self.is_active:
            return
        try:
            if self.overlay:
                self.overlay.update_timer.stop()
                self.overlay.close()
            logger.info("🛑 Pedal overlay stopped")
        finally:
            self.overlay = None
            self.is_active = False

    def _on_overlay_closed(self):
        # Called when the overlay window closes itself (Esc/context menu)
        self.overlay = None
        self.is_active = False
        logger.info("🛑 Pedal overlay closed by user")


