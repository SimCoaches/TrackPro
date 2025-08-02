"""Custom widgets for the modern UI framework.

This module contains custom Qt widgets that provide enhanced functionality
for the TrackPro modern interface, including animated sliding menus and
smooth page transitions.
"""

import json
from typing import Dict, Any, Optional, List
from PyQt6.QtWidgets import (
    QWidget, QStackedWidget, QVBoxLayout, QHBoxLayout, 
    QGraphicsOpacityEffect, QSizePolicy, QFrame
)
from PyQt6.QtCore import (
    Qt, QPropertyAnimation, QEasingCurve, QRect, QSize, 
    pyqtSignal, QParallelAnimationGroup, QSequentialAnimationGroup,
    QTimer, QObject
)
from PyQt6.QtGui import QPixmap, QPainter


class QCustomSlideMenu(QWidget):
    """Custom sliding menu widget with smooth animations.
    
    This widget provides animated sliding functionality for side menus,
    supporting both left and right slide directions with configurable
    animation properties.
    """
    
    # Signals
    menu_expanded = pyqtSignal()
    menu_collapsed = pyqtSignal()
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        
        # Animation properties
        self.animation_duration = 500  # milliseconds
        self.animation_easing = QEasingCurve.Type.OutCubic
        
        # Size properties
        self.default_width = 40
        self.default_height = 0  # 0 means use parent height
        self.collapsed_width = 40
        self.expanded_width = 130
        
        # State tracking
        self.is_expanded = False
        self.is_animating = False
        
        # Animation objects
        self.slide_animation = None
        
        # Setup widget
        self._setup_widget()
        
    def _setup_widget(self):
        """Initialize the widget properties."""
        # Set initial size
        self.setFixedWidth(self.default_width)
        
        # Enable mouse tracking for hover effects
        self.setMouseTracking(True)
        
        # Set size policy
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
        
    def configure_from_json(self, config: Dict[str, Any]):
        """Configure the widget from JSON configuration.
        
        Args:
            config: Configuration dictionary with menu properties
        """
        # Size configuration
        if "defaultSize" in config and config["defaultSize"]:
            size_config = config["defaultSize"][0]
            self.default_width = size_config.get("width", 40)
            
        if "collapsedSize" in config and config["collapsedSize"]:
            size_config = config["collapsedSize"][0]
            self.collapsed_width = size_config.get("width", 40)
            
        if "expandedSize" in config and config["expandedSize"]:
            size_config = config["expandedSize"][0]
            self.expanded_width = size_config.get("width", 130)
            
        # Animation configuration
        if "menuTransitionAnimation" in config and config["menuTransitionAnimation"]:
            anim_config = config["menuTransitionAnimation"][0]
            self.animation_duration = anim_config.get("animationDuration", 500)
            
            # Map easing curve names to Qt constants
            easing_name = anim_config.get("animationEasingCurve", "OutCubic")
            easing_map = {
                "Linear": QEasingCurve.Type.Linear,
                "InQuad": QEasingCurve.Type.InQuad,
                "OutQuad": QEasingCurve.Type.OutQuad,
                "InOutQuad": QEasingCurve.Type.InOutQuad,
                "OutCubic": QEasingCurve.Type.OutCubic,
                "InCubic": QEasingCurve.Type.InCubic,
                "InOutCubic": QEasingCurve.Type.InOutCubic
            }
            self.animation_easing = easing_map.get(easing_name, QEasingCurve.Type.OutCubic)
        
        # Apply initial size
        self.setFixedWidth(self.default_width)
        
    def toggle_menu(self):
        """Toggle the menu between expanded and collapsed states."""
        if self.is_animating:
            return
            
        if self.is_expanded:
            self.collapse_menu()
        else:
            self.expand_menu()
            
    def expand_menu(self):
        """Expand the menu with animation."""
        if self.is_expanded or self.is_animating:
            return
            
        self._animate_to_width(self.expanded_width)
        self.is_expanded = True
        self.menu_expanded.emit()
        
    def collapse_menu(self):
        """Collapse the menu with animation."""
        if not self.is_expanded or self.is_animating:
            return
            
        self._animate_to_width(self.collapsed_width)
        self.is_expanded = False
        self.menu_collapsed.emit()
        
    def _animate_to_width(self, target_width: int):
        """Animate the widget to the target width.
        
        Args:
            target_width: The target width in pixels
        """
        if self.slide_animation:
            self.slide_animation.stop()
            
        self.is_animating = True
        
        # Create width animation
        self.slide_animation = QPropertyAnimation(self, b"minimumWidth")
        self.slide_animation.setDuration(self.animation_duration)
        self.slide_animation.setEasingCurve(self.animation_easing)
        self.slide_animation.setStartValue(self.width())
        self.slide_animation.setEndValue(target_width)
        
        # Connect animation finished signal
        self.slide_animation.finished.connect(self._on_animation_finished)
        
        # Start animation
        self.slide_animation.start()
        
    def _on_animation_finished(self):
        """Handle animation completion."""
        self.is_animating = False
        
        # Update fixed width to match animated width
        if self.slide_animation:
            final_width = self.slide_animation.endValue()
            self.setFixedWidth(final_width)
            
    def enterEvent(self, event):
        """Handle mouse enter event for auto-expand (optional)."""
        super().enterEvent(event)
        # Could implement auto-expand on hover here if desired
        
    def leaveEvent(self, event):
        """Handle mouse leave event for auto-collapse (optional)."""
        super().leaveEvent(event)
        # Could implement auto-collapse on leave here if desired


class QCustomQStackedWidget(QStackedWidget):
    """Custom stacked widget with smooth page transitions.
    
    This widget provides animated transitions between pages including
    fade effects, slide effects, and combinations thereof.
    """
    
    # Signals
    page_changed = pyqtSignal(int)  # emitted when page change completes
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        
        # Animation properties
        self.fade_duration = 500
        self.slide_duration = 500
        self.fade_enabled = True
        self.slide_enabled = False
        self.fade_easing = QEasingCurve.Type.InOutQuad
        self.slide_easing = QEasingCurve.Type.InOutQuad
        
        # Animation objects
        self.fade_animation_group = None
        self.slide_animation_group = None
        self.is_animating = False
        
        # Page navigation mapping
        self.navigation_buttons = {}
        
    def configure_from_json(self, config: Dict[str, Any]):
        """Configure the widget from JSON configuration.
        
        Args:
            config: Configuration dictionary with transition properties
        """
        # Navigation configuration
        if "navigation" in config and config["navigation"]:
            nav_config = config["navigation"][0]
            if "navigationButtons" in nav_config and nav_config["navigationButtons"]:
                self.navigation_buttons = nav_config["navigationButtons"][0]
                
        # Animation configuration
        if "transitionAnimation" in config and config["transitionAnimation"]:
            anim_config = config["transitionAnimation"][0]
            
            # Fade configuration
            if "fade" in anim_config and anim_config["fade"]:
                fade_config = anim_config["fade"][0]
                self.fade_enabled = fade_config.get("active", True)
                self.fade_duration = fade_config.get("duration", 500)
                
                # Map easing curve
                easing_name = fade_config.get("easingCurve", "InOutQuad")
                self.fade_easing = self._get_easing_curve(easing_name)
                
            # Slide configuration
            if "slide" in anim_config and anim_config["slide"]:
                slide_config = anim_config["slide"][0]
                self.slide_enabled = slide_config.get("active", False)
                self.slide_duration = slide_config.get("duration", 500)
                
                # Map easing curve
                easing_name = slide_config.get("easingCurve", "InOutQuad")
                self.slide_easing = self._get_easing_curve(easing_name)
                
    def _get_easing_curve(self, easing_name: str) -> QEasingCurve.Type:
        """Get Qt easing curve from string name.
        
        Args:
            easing_name: Name of the easing curve
            
        Returns:
            Qt easing curve constant
        """
        easing_map = {
            "Linear": QEasingCurve.Type.Linear,
            "InQuad": QEasingCurve.Type.InQuad,
            "OutQuad": QEasingCurve.Type.OutQuad,
            "InOutQuad": QEasingCurve.Type.InOutQuad,
            "InCubic": QEasingCurve.Type.InCubic,
            "OutCubic": QEasingCurve.Type.OutCubic,
            "InOutCubic": QEasingCurve.Type.InOutCubic,
            "InSine": QEasingCurve.Type.InSine,
            "OutSine": QEasingCurve.Type.OutSine,
            "InOutSine": QEasingCurve.Type.InOutSine
        }
        return easing_map.get(easing_name, QEasingCurve.Type.InOutQuad)
        
    def connect_navigation_button(self, button_name: str, button_widget):
        """Connect a navigation button to page switching.
        
        Args:
            button_name: Name of the button as defined in navigation config
            button_widget: The actual button widget
        """
        if button_name in self.navigation_buttons:
            page_name = self.navigation_buttons[button_name]
            # Connect button click to page switching
            button_widget.clicked.connect(lambda: self.switch_to_page_by_name(page_name))
            
    def switch_to_page_by_name(self, page_name: str):
        """Switch to a page by its object name.
        
        Args:
            page_name: Object name of the page widget
        """
        for i in range(self.count()):
            widget = self.widget(i)
            if widget and widget.objectName() == page_name:
                self.switch_to_page(i)
                return
                
    def switch_to_page(self, index: int):
        """Switch to a page with animation.
        
        Args:
            index: Index of the page to switch to
        """
        if self.is_animating or index == self.currentIndex():
            return
            
        if not (0 <= index < self.count()):
            return
            
        old_widget = self.currentWidget()
        new_widget = self.widget(index)
        
        if not old_widget or not new_widget:
            # Fallback to normal switching if widgets not available
            self.setCurrentIndex(index)
            self.page_changed.emit(index)
            return
            
        # Perform animated transition
        if self.fade_enabled or self.slide_enabled:
            self._animate_transition(old_widget, new_widget, index)
        else:
            # No animation, direct switch
            self.setCurrentIndex(index)
            self.page_changed.emit(index)
            
    def _animate_transition(self, old_widget: QWidget, new_widget: QWidget, new_index: int):
        """Animate the transition between widgets.
        
        Args:
            old_widget: The current widget
            new_widget: The target widget
            new_index: Index of the target widget
        """
        self.is_animating = True
        
        # Prepare new widget
        new_widget.show()
        new_widget.raise_()
        
        animations = []
        
        # Setup fade animation
        if self.fade_enabled:
            fade_out_effect = QGraphicsOpacityEffect()
            fade_in_effect = QGraphicsOpacityEffect()
            
            old_widget.setGraphicsEffect(fade_out_effect)
            new_widget.setGraphicsEffect(fade_in_effect)
            
            # Fade out old widget
            fade_out_anim = QPropertyAnimation(fade_out_effect, b"opacity")
            fade_out_anim.setDuration(self.fade_duration)
            fade_out_anim.setEasingCurve(self.fade_easing)
            fade_out_anim.setStartValue(1.0)
            fade_out_anim.setEndValue(0.0)
            
            # Fade in new widget
            fade_in_anim = QPropertyAnimation(fade_in_effect, b"opacity")
            fade_in_anim.setDuration(self.fade_duration)
            fade_in_anim.setEasingCurve(self.fade_easing)
            fade_in_anim.setStartValue(0.0)
            fade_in_anim.setEndValue(1.0)
            
            animations.extend([fade_out_anim, fade_in_anim])
            
        # Create animation group
        if animations:
            self.fade_animation_group = QParallelAnimationGroup()
            for anim in animations:
                self.fade_animation_group.addAnimation(anim)
                
            self.fade_animation_group.finished.connect(
                lambda: self._on_transition_finished(new_index)
            )
            
            # Switch to new page immediately (will be hidden by opacity)
            self.setCurrentIndex(new_index)
            
            # Start animation
            self.fade_animation_group.start()
        else:
            # No animations to run
            self.setCurrentIndex(new_index)
            self._on_transition_finished(new_index)
            
    def _on_transition_finished(self, new_index: int):
        """Handle transition completion.
        
        Args:
            new_index: Index of the new page
        """
        self.is_animating = False
        
        # Clean up effects
        current_widget = self.currentWidget()
        if current_widget:
            current_widget.setGraphicsEffect(None)
            
        # Emit signal
        self.page_changed.emit(new_index)


class ThemeManager:
    """Manager for handling theme-related operations."""
    
    @staticmethod
    def load_style_config(config_path: str) -> Optional[Dict[str, Any]]:
        """Load style configuration from JSON file.
        
        Args:
            config_path: Path to the JSON configuration file
            
        Returns:
            Configuration dictionary or None if failed
        """
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Error loading style config: {e}")
            return None
            
    @staticmethod
    def apply_custom_widget_configs(widgets: Dict[str, QWidget], config: Dict[str, Any]):
        """Apply configuration to custom widgets.
        
        Args:
            widgets: Dictionary mapping widget names to widget instances
            config: Full configuration dictionary
        """
        # Configure QCustomSlideMenu widgets
        if "QCustomSlideMenu" in config:
            for menu_config in config["QCustomSlideMenu"]:
                menu_name = menu_config.get("name")
                if menu_name and menu_name in widgets:
                    widget = widgets[menu_name]
                    if isinstance(widget, QCustomSlideMenu):
                        widget.configure_from_json(menu_config)
                        
        # Configure QCustomQStackedWidget widgets
        if "QCustomQStackedWidget" in config:
            for stack_config in config["QCustomQStackedWidget"]:
                stack_name = stack_config.get("name")
                if stack_name and stack_name in widgets:
                    widget = widgets[stack_name]
                    if isinstance(widget, QCustomQStackedWidget):
                        widget.configure_from_json(stack_config)