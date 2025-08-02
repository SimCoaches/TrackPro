"""Icon resource management for the modern UI framework.

This module handles loading and managing icons from the QSS/icons directory
structure, providing a resource system for theme-based icon loading.
"""

import os
from pathlib import Path
from typing import Dict, Optional
from PyQt6.QtGui import QIcon, QPixmap
from PyQt6.QtCore import QSize


class IconManager:
    """Manager for theme-based icon resources."""
    
    def __init__(self, ui_resources_path: str):
        """Initialize the icon manager.
        
        Args:
            ui_resources_path: Path to the ui_resources directory
        """
        self.ui_resources_path = Path(ui_resources_path)
        self.icons_path = self.ui_resources_path / "Qss" / "icons"
        self.current_theme_color = "000000"  # Default to black icons
        self.icon_cache: Dict[str, QIcon] = {}
        
    def set_theme_color(self, color: str):
        """Set the current theme color for icons.
        
        Args:
            color: Color code (e.g., "000000", "fefefe", "FFFFFF")
        """
        self.current_theme_color = color
        # Clear cache when theme changes
        self.icon_cache.clear()
        
    def get_icon(self, icon_path: str) -> Optional[QIcon]:
        """Get an icon from the resource system.
        
        Args:
            icon_path: Path in the format "theme-icons:COLOR/SET/icon.png"
                      or just "SET/icon.png" (uses current theme color)
                      
        Returns:
            QIcon instance or None if not found
        """
        # Parse the icon path
        if icon_path.startswith("theme-icons:"):
            # Remove the prefix
            path_part = icon_path.replace("theme-icons:", "")
        else:
            path_part = icon_path
            
        # Check cache first
        cache_key = f"{self.current_theme_color}/{path_part}"
        if cache_key in self.icon_cache:
            return self.icon_cache[cache_key]
            
        # Determine color directory
        if "/" in path_part and path_part.split("/")[0] in ["000000", "fefefe", "FFFFFF", "black", "Icons"]:
            # Color specified in path
            color_dir = path_part.split("/")[0]
            icon_subpath = "/".join(path_part.split("/")[1:])
        else:
            # Use current theme color
            color_dir = self.current_theme_color
            icon_subpath = path_part
            
        # Build full path
        full_path = self.icons_path / color_dir / icon_subpath
        
        # Check if file exists
        if not full_path.exists():
            # Try alternative color directories if not found
            alternative_colors = ["000000", "black", "FFFFFF", "fefefe", "Icons"]
            for alt_color in alternative_colors:
                if alt_color != color_dir:
                    alt_path = self.icons_path / alt_color / icon_subpath
                    if alt_path.exists():
                        full_path = alt_path
                        break
            else:
                # Still not found
                print(f"Icon not found: {icon_path} (searched {full_path})")
                return None
                
        # Create icon
        try:
            icon = QIcon(str(full_path))
            if not icon.isNull():
                # Cache the icon
                self.icon_cache[cache_key] = icon
                return icon
        except Exception as e:
            print(f"Error loading icon {full_path}: {e}")
            
        return None
        
    def get_pixmap(self, icon_path: str, size: QSize = QSize(16, 16)) -> Optional[QPixmap]:
        """Get a pixmap from the resource system.
        
        Args:
            icon_path: Path in the format "theme-icons:COLOR/SET/icon.png"
            size: Size of the pixmap
            
        Returns:
            QPixmap instance or None if not found
        """
        icon = self.get_icon(icon_path)
        if icon:
            return icon.pixmap(size)
        return None
        
    def preload_common_icons(self):
        """Preload commonly used icons for better performance."""
        common_icons = [
            "feather/home.png",
            "feather/settings.png",
            "feather/user.png",
            "feather/menu.png",
            "feather/x-circle.png",
            "feather/bell.png",
            "feather/more-horizontal.png",
            "feather/window_minimize.png",
            "feather/window_close.png",
            "feather/square.png",
            "feather/list.png",
            "feather/printer.png",
            "feather/pie-chart.png",
            "feather/info.png",
            "feather/help-circle.png",
            "material_design/search.png"
        ]
        
        for icon_path in common_icons:
            self.get_icon(icon_path)
            
    def list_available_icon_sets(self) -> list:
        """List all available icon sets.
        
        Returns:
            List of available icon set directories
        """
        sets = []
        for color_dir in self.icons_path.iterdir():
            if color_dir.is_dir():
                for icon_set in color_dir.iterdir():
                    if icon_set.is_dir() and icon_set.name not in sets:
                        sets.append(icon_set.name)
        return sorted(sets)
        
    def list_icons_in_set(self, icon_set: str, color: Optional[str] = None) -> list:
        """List all icons in a specific set.
        
        Args:
            icon_set: Name of the icon set (e.g., "feather", "material_design")
            color: Color directory to search in (defaults to current theme color)
            
        Returns:
            List of icon filenames
        """
        if color is None:
            color = self.current_theme_color
            
        set_path = self.icons_path / color / icon_set
        if not set_path.exists():
            return []
            
        icons = []
        for icon_file in set_path.iterdir():
            if icon_file.is_file() and icon_file.suffix.lower() in ['.png', '.svg', '.jpg', '.jpeg']:
                icons.append(icon_file.name)
                
        return sorted(icons)


def process_qss_for_icons(qss_content: str, icon_manager: IconManager) -> str:
    """Process QSS content to replace theme-icons: paths with actual file paths.
    
    Args:
        qss_content: Raw QSS stylesheet content
        icon_manager: IconManager instance
        
    Returns:
        Processed QSS content with resolved icon paths
    """
    import re
    
    # Find all theme-icons: references
    pattern = r'url\(["\']?theme-icons:([^"\')\s]+)["\']?\)'
    
    def replace_icon_path(match):
        icon_path = match.group(1)
        # Get the full file path
        full_path = icon_manager.icons_path / icon_manager.current_theme_color / icon_path
        
        # Check if exists, try alternatives if not
        if not full_path.exists():
            alternative_colors = ["000000", "black", "FFFFFF", "fefefe", "Icons"]
            for alt_color in alternative_colors:
                alt_path = icon_manager.icons_path / alt_color / icon_path
                if alt_path.exists():
                    full_path = alt_path
                    break
                    
        if full_path.exists():
            # Convert to URL format for QSS
            return f'url("{full_path.as_posix()}")'
        else:
            # Return original if not found
            return match.group(0)
    
    # Replace all occurrences
    processed_content = re.sub(pattern, replace_icon_path, qss_content)
    return processed_content


# Global icon manager instance
_icon_manager: Optional[IconManager] = None


def get_icon_manager() -> Optional[IconManager]:
    """Get the global icon manager instance."""
    return _icon_manager
    

def initialize_icon_manager(ui_resources_path: str) -> IconManager:
    """Initialize the global icon manager.
    
    Args:
        ui_resources_path: Path to the ui_resources directory
        
    Returns:
        IconManager instance
    """
    global _icon_manager
    _icon_manager = IconManager(ui_resources_path)
    return _icon_manager


def get_icon(icon_path: str) -> Optional[QIcon]:
    """Convenience function to get an icon using the global manager.
    
    Args:
        icon_path: Icon path
        
    Returns:
        QIcon instance or None
    """
    if _icon_manager:
        return _icon_manager.get_icon(icon_path)
    return None