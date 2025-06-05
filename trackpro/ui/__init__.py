"""
TrackPro UI Package
Contains all user interface components for the TrackPro application.
"""

# Import main UI components
# Don't import MainWindow here to avoid conflicts
# Let the main trackpro/__init__.py handle the import directly
MainWindow = None
try:
    from .main_community_ui import (
        CommunityIntegrationDialog,
        CommunityMainInterface,
        open_community_dialog,
        open_social_features,
        open_community_features,
        open_content_management,
        open_achievements,
        open_account_settings
    )
except ImportError:
    # Graceful fallback if community UI is not available
    pass

try:
    from .community_ui import (
        CommunityMainWidget,
        CommunityTheme,
        TeamCard,
        ClubCard,
        EventCard
    )
except ImportError:
    pass

try:
    from .content_management_ui import (
        ContentManagementMainWidget,
        ContentCard,
        ContentBrowserWidget
    )
except ImportError:
    pass

try:
    from .social_ui import (
        SocialMainWidget,
        SocialTheme
    )
except ImportError:
    pass

try:
    from .achievements_ui import (
        GamificationMainWidget,
        AchievementCard
    )
except ImportError:
    pass

try:
    from .user_account_ui import (
        UserAccountMainWidget,
        ProfileEditDialog
    )
except ImportError:
    pass

try:
    from .threshold_assist_panel import ThresholdAssistPanel
except ImportError:
    pass

__all__ = [
    'MainWindow',
    'CommunityIntegrationDialog',
    'CommunityMainInterface',
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
    'ProfileEditDialog',
    'ThresholdAssistPanel',
    'open_community_dialog',
    'open_social_features',
    'open_community_features',
    'open_content_management',
    'open_achievements',
    'open_account_settings'
] 