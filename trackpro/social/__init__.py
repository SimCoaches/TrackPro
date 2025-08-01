"""
TrackPro Social Module - Comprehensive social features and community management.

This module provides comprehensive social features for the TrackPro application,
including friends, messaging, activity feeds, teams, clubs, and community events.
"""

# Lazy initialization - only create managers when needed
_managers = {}

def get_enhanced_user_manager():
    """Get the enhanced user manager instance (lazy initialization)."""
    if 'enhanced_user_manager' not in _managers:
        from .user_manager import EnhancedUserManager
        _managers['enhanced_user_manager'] = EnhancedUserManager()
    return _managers['enhanced_user_manager']

def get_friends_manager():
    """Get the friends manager instance (lazy initialization)."""
    if 'friends_manager' not in _managers:
        from .friends_manager import FriendsManager
        _managers['friends_manager'] = FriendsManager()
    return _managers['friends_manager']

def get_messaging_manager():
    """Get the messaging manager instance (lazy initialization)."""
    if 'messaging_manager' not in _managers:
        from .messaging_manager import MessagingManager
        _managers['messaging_manager'] = MessagingManager()
    return _managers['messaging_manager']

def get_activity_manager():
    """Get the activity manager instance (lazy initialization)."""
    if 'activity_manager' not in _managers:
        from .activity_manager import ActivityManager
        _managers['activity_manager'] = ActivityManager()
    return _managers['activity_manager']

def get_community_manager():
    """Get the community manager instance (lazy initialization)."""
    if 'community_manager' not in _managers:
        from .community_manager import CommunityManager
        _managers['community_manager'] = CommunityManager()
    return _managers['community_manager']

def get_achievements_manager():
    """Get the achievements manager instance (lazy initialization)."""
    if 'achievements_manager' not in _managers:
        from .achievements_manager import AchievementsManager
        _managers['achievements_manager'] = AchievementsManager()
    return _managers['achievements_manager']

def get_reputation_manager():
    """Get the reputation manager instance (lazy initialization)."""
    if 'reputation_manager' not in _managers:
        from .reputation_manager import ReputationManager
        _managers['reputation_manager'] = ReputationManager()
    return _managers['reputation_manager']

def get_content_manager():
    """Get the content manager instance (lazy initialization)."""
    if 'content_manager' not in _managers:
        from .content_manager import ContentManager
        _managers['content_manager'] = ContentManager()
    return _managers['content_manager']

# Module-level lazy initialization using __getattr__
def __getattr__(name):
    """Lazy initialization for backward compatibility."""
    if name == 'enhanced_user_manager':
        return get_enhanced_user_manager()
    elif name == 'friends_manager':
        return get_friends_manager()
    elif name == 'messaging_manager':
        return get_messaging_manager()
    elif name == 'activity_manager':
        return get_activity_manager()
    elif name == 'community_manager':
        return get_community_manager()
    elif name == 'achievements_manager':
        return get_achievements_manager()
    elif name == 'reputation_manager':
        return get_reputation_manager()
    elif name == 'content_manager':
        return get_content_manager()
    else:
        raise AttributeError(f"module '{__name__}' has no attribute '{name}'")

# Export all managers for easy access
__all__ = [
    'enhanced_user_manager',
    'friends_manager', 
    'messaging_manager',
    'activity_manager',
    'community_manager',
    'achievements_manager',
    'reputation_manager',
    'content_manager',
    'get_enhanced_user_manager',
    'get_friends_manager',
    'get_messaging_manager',
    'get_activity_manager',
    'get_community_manager',
    'get_achievements_manager',
    'get_reputation_manager',
    'get_content_manager'
]

# Version info
__version__ = "1.0.0"
__author__ = "TrackPro Development Team"
__description__ = "Comprehensive social features and community management system for TrackPro" 