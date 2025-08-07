"""UI module for TrackPro.

This file avoids importing heavy UI submodules during headless/test runs to
prevent QtWebEngine initialization errors. Set `TRACKPRO_HEADLESS=1` or
`QT_QPA_PLATFORM=offscreen` to enable lightweight imports.
"""

import os as _os

_HEADLESS = _os.environ.get("TRACKPRO_HEADLESS") == "1" or _os.environ.get("QT_QPA_PLATFORM") == "offscreen"

# Always-safe exports
__all__ = []

if not _HEADLESS:
    # Heavy imports only when not headless
    from .modern.main_window import ModernMainWindow as MainWindow
    from .chart_widgets import DraggableChartView, IntegratedCalibrationChart
    from .auth_dialogs import PasswordDialog
    from .shared_imports import __version__, DEFAULT_CURVE_TYPES

    try:
        from .shared_imports import (
            COMMUNITY_UI_AVAILABLE, open_community_dialog, create_community_menu_action,
            open_social_features, open_community_features,
            open_content_management, open_achievements, open_account_settings
        )
    except ImportError:
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

    from .theme import setup_dark_theme
    from .menu_bar import create_menu_bar, force_refresh_login_state
    from .system_tray import (
        setup_system_tray, tray_icon_activated, show_from_tray,
        toggle_minimize_to_tray, exit_application
    )

    try:
        from .community_ui import (
            CommunityMainWidget,
            CommunityTheme,
            TeamCard,
            ClubCard,
            EventCard
        )
    except ImportError:
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

    __all__ = [
        'MainWindow',
        'DraggableChartView',
        'IntegratedCalibrationChart',
        'PasswordDialog',
        '__version__',
        'DEFAULT_CURVE_TYPES',
        'COMMUNITY_UI_AVAILABLE',
        'open_community_dialog',
        'create_community_menu_action',
        'open_social_features',
        'open_community_features',
        'open_content_management',
        'open_achievements',
        'open_account_settings',
        'setup_dark_theme',
        'create_menu_bar',
        'force_refresh_login_state',
        'setup_system_tray',
        'tray_icon_activated',
        'show_from_tray',
        'toggle_minimize_to_tray',
        'exit_application',
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