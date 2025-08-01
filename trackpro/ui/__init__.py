"""UI module for TrackPro - reorganized into separate components."""

# Import the main window class
from .main_window import MainWindow

# Import chart widgets
from .chart_widgets import DraggableChartView, IntegratedCalibrationChart

# Import auth dialogs
from .auth_dialogs import PasswordDialog

# Import shared constants - avoid community functions that may not exist
from .shared_imports import __version__, DEFAULT_CURVE_TYPES

# Try to import community functions if available
try:
    from .shared_imports import (
        COMMUNITY_UI_AVAILABLE, open_community_dialog, create_community_menu_action,
        open_social_features, open_community_features, 
        open_content_management, open_achievements, open_account_settings
    )
except ImportError:
    # Fallback if community functions are not available
    COMMUNITY_UI_AVAILABLE = False
    def open_community_dialog(*args, **kwargs):
        pass
    def create_community_menu_action(*args, **kwargs):
        return None
    def open_social_features(*args, **kwargs):
        pass
    def open_community_features(*args, **kwargs):
        pass
    def open_content_management(*args, **kwargs):
        pass
    def open_achievements(*args, **kwargs):
        pass
    def open_account_settings(*args, **kwargs):
        pass

# Import theme and utility functions
from .theme import setup_dark_theme
from .menu_bar import create_menu_bar, force_refresh_login_state  
from .system_tray import (
    setup_system_tray, tray_icon_activated, show_from_tray,
    toggle_minimize_to_tray, exit_application
)

# Import community UI components if available
try:
    from .community_ui import (
        CommunityMainWidget,
        CommunityTheme,
        TeamCard,
        ClubCard,
        EventCard
    )
except ImportError:
    # Graceful fallback if community UI is not available
    CommunityMainWidget = None
    CommunityTheme = None
    TeamCard = None
    ClubCard = None
    EventCard = None

try:
    from .content_management_ui import (
        ContentManagementMainWidget,
        ContentCard,
        ContentBrowserWidget
    )
except ImportError:
    ContentManagementMainWidget = None
    ContentCard = None
    ContentBrowserWidget = None

try:
    from .social_ui import (
        SocialMainWidget,
        SocialTheme
    )
except ImportError:
    SocialMainWidget = None
    SocialTheme = None

try:
    from .achievements_ui import (
        GamificationMainWidget,
        AchievementCard
    )
except ImportError:
    GamificationMainWidget = None
    AchievementCard = None

try:
    from .user_account_ui import (
        UserAccountMainWidget,
        ProfileEditDialog
    )
except ImportError:
    UserAccountMainWidget = None
    ProfileEditDialog = None

# Export all the public API
__all__ = [
    # Main window
    'MainWindow',
    
    # Chart widgets
    'DraggableChartView',
    'IntegratedCalibrationChart', 
    
    # Auth dialogs
    'PasswordDialog',
    
    # Constants
    '__version__',
    'DEFAULT_CURVE_TYPES',
    'COMMUNITY_UI_AVAILABLE',
    
    # Community functions
    'open_community_dialog',
    'create_community_menu_action',
    'open_social_features',
    'open_community_features',
    'open_content_management', 
    'open_achievements',
    'open_account_settings',
    
    # Utility functions
    'setup_dark_theme',
    'create_menu_bar',
    'force_refresh_login_state',
    'setup_system_tray',
    'tray_icon_activated',
    'show_from_tray',
    'toggle_minimize_to_tray',
    'exit_application',
    
    # Community UI components (may be None if not available)
    'CommunityMainWidget',
    'CommunityTheme',
    'TeamCard',
    'ClubCard',
    'EventCard',
    'ContentManagementMainWidget',
    'ContentCard',
    'ContentBrowserWidget',
    'SocialMainWidget',
    'SocialTheme',
    'GamificationMainWidget',
    'AchievementCard',
    'UserAccountMainWidget',
    'ProfileEditDialog'
] 