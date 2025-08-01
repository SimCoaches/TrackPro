"""
Community Theme Configuration
Provides consistent styling and colors for all community features.
"""

from PyQt6.QtGui import QFont


class CommunityTheme:
    """Theme configuration for community features."""
    
    # Color palette - matches TrackPro's main dark theme
    COLORS = {
        'primary': '#FF6B35',  # TrackPro orange (accent only)
        'secondary': '#2a82da',  # TrackPro blue
        'success': '#4CAF50',
        'warning': '#FF9800',
        'danger': '#f44336',
        'background': '#353535',  # Same as main TrackPro background
        'surface': '#444444',     # Same as main TrackPro surface
        'surface_darker': '#2d2d2d',  # Darker surface for navigation
        'surface_lighter': '#4f4f4f',  # Lighter surface for hover
        'border': '#555555',      # Same as main TrackPro border
        'text_primary': '#ffffff',
        'text_secondary': '#cccccc',
        'text_muted': '#999999',
        'hover': '#4f4f4f',      # Subtle hover, not orange
        'active': '#2a82da',     # Blue for active states
        'accent': '#FF6B35',     # Orange only for accents/highlights
    }
    
    # Typography
    FONTS = {
        'heading': ('Arial', 16, QFont.Weight.Bold),
        'subheading': ('Arial', 14, QFont.Weight.Bold),
        'body': ('Arial', 12),
        'caption': ('Arial', 10),
    }
    
    @classmethod
    def get_stylesheet(cls):
        """Get the complete stylesheet for community components - matches TrackPro main theme."""
        return f"""
            /* Base styling - matches TrackPro exactly */
            QWidget {{
                background-color: {cls.COLORS['background']};
                color: {cls.COLORS['text_primary']};
                font-family: Arial;
                font-size: 12px;
            }}
            
            /* Group boxes */
            QGroupBox {{
                border: 1px solid {cls.COLORS['border']};
                border-radius: 3px;
                padding: 2px;
                margin-top: 3px;
                margin-bottom: 3px;
                font-size: 11px;
            }}
            
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 7px;
                padding: 0px 3px 0px 3px;
                top: -2px;
                color: {cls.COLORS['accent']};
            }}
            
            /* Primary buttons - matches TrackPro exactly */
            QPushButton {{
                background-color: {cls.COLORS['surface']};
                border: 1px solid {cls.COLORS['border']};
                border-radius: 3px;
                padding: 5px 15px;
                color: white;
            }}
            
            QPushButton:hover {{
                background-color: {cls.COLORS['surface_lighter']};
            }}
            
            QPushButton:pressed {{
                background-color: {cls.COLORS['surface_darker']};
            }}
            
            QPushButton:disabled {{
                background-color: {cls.COLORS['surface_darker']};
                color: {cls.COLORS['text_muted']};
            }}
            
            /* Input fields - matches TrackPro exactly */
            QLineEdit, QTextEdit, QComboBox {{
                background-color: {cls.COLORS['surface']};
                border: 1px solid {cls.COLORS['border']};
                border-radius: 3px;
                padding: 5px 10px;
                color: white;
            }}
            
            QLineEdit:focus, QTextEdit:focus, QComboBox:focus {{
                border-color: {cls.COLORS['active']};
            }}
            
            QComboBox::drop-down {{
                border: none;
            }}
            
            QComboBox::down-arrow {{
                image: none;
                border-width: 0px;
            }}
            
            QComboBox QAbstractItemView {{
                background-color: {cls.COLORS['surface']};
                selection-background-color: {cls.COLORS['active']};
                min-width: 200px;
                padding: 5px;
            }}
            
            /* Progress bars - matches TrackPro exactly */
            QProgressBar {{
                border: 1px solid {cls.COLORS['border']};
                border-radius: 2px;
                text-align: center;
                background-color: {cls.COLORS['surface_darker']};
            }}
            
            QProgressBar::chunk {{
                background-color: {cls.COLORS['active']};
            }}
            
            /* Tabs */
            QTabWidget::pane {{
                border: 1px solid {cls.COLORS['border']};
                background-color: {cls.COLORS['background']};
            }}
            
            QTabBar::tab {{
                background-color: {cls.COLORS['surface']};
                border: 1px solid {cls.COLORS['border']};
                border-bottom: none;
                border-radius: 4px;
                padding: 8px 16px;
                margin-right: 2px;
                color: {cls.COLORS['text_primary']};
            }}
            
            QTabBar::tab:selected {{
                background-color: {cls.COLORS['active']};
                color: white;
                font-weight: bold;
            }}
            
            QTabBar::tab:hover {{
                background-color: {cls.COLORS['hover']};
            }}
            
            /* Scrollbars */
            QScrollArea {{
                border: none;
                background-color: {cls.COLORS['background']};
            }}
            
            QScrollBar:vertical {{
                background-color: {cls.COLORS['surface']};
                width: 12px;
                border-radius: 6px;
            }}
            
            QScrollBar::handle:vertical {{
                background-color: {cls.COLORS['border']};
                border-radius: 6px;
                min-height: 20px;
            }}
            
            QScrollBar::handle:vertical:hover {{
                background-color: {cls.COLORS['text_muted']};
            }}
            
            /* Lists */
            QListWidget {{
                background-color: {cls.COLORS['surface']};
                border: 1px solid {cls.COLORS['border']};
                border-radius: 4px;
                padding: 4px;
                alternate-background-color: {cls.COLORS['background']};
            }}
            
            QListWidget::item {{
                padding: 8px;
                border-radius: 4px;
                margin: 2px;
            }}
            
            QListWidget::item:selected {{
                background-color: {cls.COLORS['active']};
                color: white;
            }}
            
            QListWidget::item:hover {{
                background-color: {cls.COLORS['hover']};
            }}
            
            /* Labels */
            QLabel {{
                color: {cls.COLORS['text_primary']};
            }}
        """ 