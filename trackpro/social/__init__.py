"""
TrackPro Social Module - Comprehensive social features and community management.

This module provides comprehensive social features for the TrackPro application,
including friends, messaging, activity feeds, teams, clubs, and community events.
"""

# Import all managers
from .user_manager import enhanced_user_manager
from .friends_manager import friends_manager
from .messaging_manager import messaging_manager
from .activity_manager import activity_manager
from .community_manager import community_manager
from .achievements_manager import achievements_manager
from .reputation_manager import reputation_manager
from .content_manager import content_manager

# Export all managers for easy access
__all__ = [
    'enhanced_user_manager',
    'friends_manager', 
    'messaging_manager',
    'activity_manager',
    'community_manager',
    'achievements_manager',
    'reputation_manager',
    'content_manager'
]

# Version info
__version__ = "1.0.0"
__author__ = "TrackPro Development Team"
__description__ = "Comprehensive social features and community management system for TrackPro" 