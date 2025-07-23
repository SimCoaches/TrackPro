"""Enhanced User Manager for comprehensive social features."""

import logging
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, date
from ..database.base import DatabaseManager
from ..database.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)

class EnhancedUserManager(DatabaseManager):
    """Enhanced user manager with comprehensive social features."""
    
    def __init__(self):
        """Initialize the enhanced user manager."""
        super().__init__("user_profiles")
        self.supabase = get_supabase_client()
    
    # =====================================================
    # ENHANCED PROFILE MANAGEMENT
    # =====================================================
    
    def get_complete_user_profile(self, user_id: str = None) -> Optional[Dict[str, Any]]:
        """Get complete user profile with stats and social data.
        
        Args:
            user_id: User ID to get profile for (defaults to current user)
            
        Returns:
            Complete user profile data or None
        """
        try:
            if not user_id:
                user = self.supabase.auth.get_user()
                if not user:
                    return None
                user_id = user.id
            
            # First try to get from the view for complete profile data
            response = self.client.from_("user_profile_complete").select("*").eq("user_id", user_id).limit(1).execute()
            
            if response.data:
                return response.data[0]
            
            # If view returns empty (user not in user_profiles), try to get from user_details as fallback
            logger.info(f"User {user_id} not found in user_profile_complete view, checking user_details table")
            
            details_response = self.client.from_("user_details").select("*").eq("user_id", user_id).limit(1).execute()
            
            if details_response.data:
                # Return minimal profile data with 2FA info from user_details
                user_details = details_response.data[0]
                logger.info(f"Found user {user_id} in user_details with twilio_verified={user_details.get('twilio_verified')}")
                
                # Create minimal profile data compatible with existing code
                return {
                    'user_id': user_id,
                    'phone_number': user_details.get('phone_number'),
                    'twilio_verified': user_details.get('twilio_verified', False),
                    'is_2fa_enabled': user_details.get('is_2fa_enabled', False),
                    # Add default values for fields that might be accessed
                    'username': None,
                    'display_name': None,
                    'email': None,
                    'level': 1,
                    'reputation_score': 0,
                    'total_laps': 0,
                    'total_distance_km': 0,
                    'total_time_seconds': 0,
                    'best_lap_time': None,
                    'consistency_rating': 0,
                    'improvement_rate': 0,
                    'last_active': None
                }
            
            # If user not found in either place, return None
            logger.warning(f"User {user_id} not found in either user_profile_complete view or user_details table")
            return None
            
        except Exception as e:
            logger.error(f"Error getting complete user profile: {e}")
            return None
    
    def update_user_profile(self, user_id: str, profile_data: Dict[str, Any]) -> bool:
        """Update user profile with enhanced social features.
        
        Args:
            user_id: User ID to update
            profile_data: Profile data to update
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Separate profile data, stats data, and details data
            profile_fields = {
                'username', 'display_name', 'bio', 'location', 'avatar_url',
                'avatar_frame_id', 'profile_theme', 'privacy_settings', 'preferences'
            }
            
            # 2FA fields belong in user_details table
            details_fields = {
                'phone_number', 'twilio_verified', 'is_2fa_enabled'
            }
            
            profile_update = {k: v for k, v in profile_data.items() if k in profile_fields}
            details_update = {k: v for k, v in profile_data.items() if k in details_fields}
            
            if profile_update:
                response = self.client.from_("user_profiles").update(profile_update).eq("user_id", user_id).execute()
                if not response.data:
                    return False
                    
            if details_update:
                response = self.client.from_("user_details").upsert({**details_update, 'user_id': user_id}).execute()
                if not response.data:
                    return False
            
            # Update user stats if provided
            stats_fields = {
                'total_laps', 'total_distance_km', 'total_time_seconds', 'best_lap_time',
                'favorite_track_id', 'favorite_car_id', 'consistency_rating', 'improvement_rate'
            }
            
            stats_update = {k: v for k, v in profile_data.items() if k in stats_fields}
            
            if stats_update:
                stats_update['updated_at'] = datetime.utcnow().isoformat()
                response = self.client.from_("user_stats").upsert(
                    {**stats_update, 'user_id': user_id}
                ).execute()
                if not response.data:
                    return False
            
            logger.info(f"Updated profile for user {user_id}")
            return True
        except Exception as e:
            logger.error(f"Error updating user profile: {e}")
            return False
    
    def set_avatar_frame(self, user_id: str, frame_id: str) -> bool:
        """Set user's avatar frame.
        
        Args:
            user_id: User ID
            frame_id: Avatar frame ID
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Check if frame exists and user has unlocked it
            frame_response = self.client.from_("avatar_frames").select("*").eq("id", frame_id).single().execute()
            if not frame_response.data:
                logger.warning(f"Avatar frame {frame_id} not found")
                return False
            
            frame = frame_response.data
            
            # Check unlock requirements if not premium
            if not frame.get('is_premium', False):
                requirements = frame.get('unlock_requirements', {})
                if requirements and not self._check_unlock_requirements(user_id, requirements):
                    logger.warning(f"User {user_id} hasn't unlocked avatar frame {frame_id}")
                    return False
            
            # Update user profile
            response = self.client.from_("user_profiles").update({
                'avatar_frame_id': frame_id
            }).eq("user_id", user_id).execute()
            
            return bool(response.data)
        except Exception as e:
            logger.error(f"Error setting avatar frame: {e}")
            return False
    
    def get_available_avatar_frames(self, user_id: str) -> List[Dict[str, Any]]:
        """Get available avatar frames for user.
        
        Args:
            user_id: User ID
            
        Returns:
            List of available avatar frames
        """
        try:
            # Get all frames
            response = self.client.from_("avatar_frames").select("*").execute()
            if not response.data:
                return []
            
            frames = []
            for frame in response.data:
                frame_data = frame.copy()
                
                # Check if unlocked
                requirements = frame.get('unlock_requirements', {})
                if requirements:
                    frame_data['is_unlocked'] = self._check_unlock_requirements(user_id, requirements)
                else:
                    frame_data['is_unlocked'] = True
                
                frames.append(frame_data)
            
            return frames
        except Exception as e:
            logger.error(f"Error getting available avatar frames: {e}")
            return []
    
    def _check_unlock_requirements(self, user_id: str, requirements: Dict[str, Any]) -> bool:
        """Check if user meets unlock requirements.
        
        Args:
            user_id: User ID
            requirements: Requirements to check
            
        Returns:
            True if requirements are met, False otherwise
        """
        try:
            # Get user stats and achievements
            profile = self.get_complete_user_profile(user_id)
            if not profile:
                return False
            
            # Check various requirements
            for req_type, req_value in requirements.items():
                if req_type == 'races_completed':
                    total_laps = profile.get('total_laps', 0)
                    if total_laps is None:
                        total_laps = 0
                    if total_laps < req_value:
                        return False
                elif req_type == 'personal_bests':
                    # This would need to be tracked separately
                    pass
                elif req_type == 'events_won':
                    # This would need to be tracked separately
                    pass
                elif req_type == 'prestige_level':
                    prestige_level = profile.get('prestige_level', 0)
                    if prestige_level is None:
                        prestige_level = 0
                    if prestige_level < req_value:
                        return False
                elif req_type == 'level':
                    level = profile.get('level', 1)
                    if level is None:
                        level = 1
                    if level < req_value:
                        return False
            
            return True
        except Exception as e:
            logger.error(f"Error checking unlock requirements: {e}")
            return False
    
    # =====================================================
    # USER SEARCH AND DISCOVERY
    # =====================================================
    
    def search_users(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Search for users by username or display name.
        
        Args:
            query: Search query
            limit: Maximum number of results
            
        Returns:
            List of matching users
        """
        try:
            # Search by username or display name
            response = self.client.from_("user_profiles").select(
                "user_id, username, display_name, avatar_url, level, reputation_score"
            ).or_(
                f"username.ilike.%{query}%,display_name.ilike.%{query}%"
            ).limit(limit).execute()
            
            return response.data or []
        except Exception as e:
            logger.error(f"Error searching users: {e}")
            return []
    
    def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """Get user by username.
        
        Args:
            username: Username to search for
            
        Returns:
            User data or None
        """
        try:
            response = self.client.from_("user_profiles").select("*").eq("username", username).single().execute()
            return response.data
        except Exception as e:
            logger.error(f"Error getting user by username: {e}")
            return None
    
    def suggest_friends(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Suggest potential friends for user.
        
        Args:
            user_id: User ID
            limit: Maximum number of suggestions
            
        Returns:
            List of suggested users
        """
        try:
            # Get users with similar interests/stats who aren't already friends
            # This is a simplified version - could be enhanced with ML
            user_profile = self.get_complete_user_profile(user_id)
            if not user_profile:
                return []
            
            # Get users with similar level range
            user_level = user_profile.get('level', 1)
            level_range = 5
            
            response = self.client.from_("user_profiles").select(
                "user_id, username, display_name, avatar_url, level, reputation_score"
            ).gte("level", user_level - level_range).lte("level", user_level + level_range).neq("user_id", user_id).limit(limit).execute()
            
            suggestions = response.data or []
            
            # Filter out existing friends
            existing_friends = self.get_user_friends(user_id)
            friend_ids = {friend['friend_id'] for friend in existing_friends}
            
            return [user for user in suggestions if user['user_id'] not in friend_ids]
        except Exception as e:
            logger.error(f"Error getting friend suggestions: {e}")
            return []
    
    # =====================================================
    # USER STATISTICS AND METRICS
    # =====================================================
    
    def update_user_stats(self, user_id: str, stats_update: Dict[str, Any]) -> bool:
        """Update user statistics.
        
        Args:
            user_id: User ID
            stats_update: Statistics to update
            
        Returns:
            True if successful, False otherwise
        """
        try:
            stats_update['updated_at'] = datetime.utcnow().isoformat()
            stats_update['last_active'] = datetime.utcnow().isoformat()
            
            response = self.client.from_("user_stats").upsert(
                {**stats_update, 'user_id': user_id}
            ).execute()
            
            return bool(response.data)
        except Exception as e:
            logger.error(f"Error updating user stats: {e}")
            return False
    
    def get_user_stats(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user statistics.
        
        Args:
            user_id: User ID
            
        Returns:
            User statistics or None
        """
        try:
            response = self.client.from_("user_stats").select("*").eq("user_id", user_id).single().execute()
            return response.data
        except Exception as e:
            logger.error(f"Error getting user stats: {e}")
            return None
    
    def increment_lap_count(self, user_id: str, laps: int = 1, distance_km: float = 0, time_seconds: int = 0) -> bool:
        """Increment user's lap count and related stats.
        
        Args:
            user_id: User ID
            laps: Number of laps to add
            distance_km: Distance to add in kilometers
            time_seconds: Time to add in seconds
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get current stats
            current_stats = self.get_user_stats(user_id)
            if not current_stats:
                current_stats = {
                    'total_laps': 0,
                    'total_distance_km': 0,
                    'total_time_seconds': 0
                }
            
            # Update stats
            new_stats = {
                'total_laps': current_stats.get('total_laps', 0) + laps,
                'total_distance_km': current_stats.get('total_distance_km', 0) + distance_km,
                'total_time_seconds': current_stats.get('total_time_seconds', 0) + time_seconds,
                'last_active': datetime.utcnow().isoformat(),
                'updated_at': datetime.utcnow().isoformat()
            }
            
            return self.update_user_stats(user_id, new_stats)
        except Exception as e:
            logger.error(f"Error incrementing lap count: {e}")
            return False
    
    def update_best_lap_time(self, user_id: str, lap_time: float) -> bool:
        """Update user's best lap time if it's better.
        
        Args:
            user_id: User ID
            lap_time: New lap time in seconds
            
        Returns:
            True if updated, False otherwise
        """
        try:
            current_stats = self.get_user_stats(user_id)
            current_best = current_stats.get('best_lap_time') if current_stats else None
            
            # Update if this is a new personal best
            if current_best is None or lap_time < float(current_best):
                return self.update_user_stats(user_id, {'best_lap_time': lap_time})
            
            return False
        except Exception as e:
            logger.error(f"Error updating best lap time: {e}")
            return False
    
    # =====================================================
    # PRIVACY AND SETTINGS
    # =====================================================
    
    def update_privacy_settings(self, user_id: str, settings: Dict[str, Any]) -> bool:
        """Update user's privacy settings.
        
        Args:
            user_id: User ID
            settings: Privacy settings to update
            
        Returns:
            True if successful, False otherwise
        """
        try:
            response = self.client.from_("user_profiles").update({
                'privacy_settings': settings
            }).eq("user_id", user_id).execute()
            
            return bool(response.data)
        except Exception as e:
            logger.error(f"Error updating privacy settings: {e}")
            return False
    
    def update_preferences(self, user_id: str, preferences: Dict[str, Any]) -> bool:
        """Update user's preferences.
        
        Args:
            user_id: User ID
            preferences: Preferences to update
            
        Returns:
            True if successful, False otherwise
        """
        try:
            response = self.client.from_("user_profiles").update({
                'preferences': preferences
            }).eq("user_id", user_id).execute()
            
            return bool(response.data)
        except Exception as e:
            logger.error(f"Error updating preferences: {e}")
            return False
    
    def get_privacy_settings(self, user_id: str) -> Dict[str, Any]:
        """Get user's privacy settings.
        
        Args:
            user_id: User ID
            
        Returns:
            Privacy settings dictionary
        """
        try:
            response = self.client.from_("user_profiles").select("privacy_settings").eq("user_id", user_id).single().execute()
            return response.data.get('privacy_settings', {}) if response.data else {}
        except Exception as e:
            logger.error(f"Error getting privacy settings: {e}")
            return {}
    
    def can_view_profile(self, viewer_id: str, target_id: str) -> bool:
        """Check if viewer can view target user's profile.
        
        Args:
            viewer_id: ID of user trying to view
            target_id: ID of user being viewed
            
        Returns:
            True if can view, False otherwise
        """
        try:
            if viewer_id == target_id:
                return True
            
            privacy_settings = self.get_privacy_settings(target_id)
            profile_visibility = privacy_settings.get('profile_visibility', 'public')
            
            if profile_visibility == 'public':
                return True
            elif profile_visibility == 'friends':
                # Check if they are friends
                from . import get_friends_manager
                friends_manager = get_friends_manager()
                return friends_manager.are_friends(viewer_id, target_id)
            elif profile_visibility == 'private':
                return False
            
            return False
        except Exception as e:
            logger.error(f"Error checking profile visibility: {e}")
            return False
    
    # =====================================================
    # HELPER METHODS
    # =====================================================
    
    def get_user_friends(self, user_id: str) -> List[Dict[str, Any]]:
        """Get user's friends list.
        
        Args:
            user_id: User ID
            
        Returns:
            List of friends
        """
        try:
            response = self.client.from_("user_friends").select("*").eq("user_id", user_id).execute()
            return response.data or []
        except Exception as e:
            logger.error(f"Error getting user friends: {e}")
            return []
    
    def is_username_available(self, username: str, exclude_user_id: str = None) -> bool:
        """Check if username is available.
        
        Args:
            username: Username to check
            exclude_user_id: User ID to exclude from check (for updates)
            
        Returns:
            True if available, False otherwise
        """
        try:
            query = self.client.from_("user_profiles").select("user_id").eq("username", username)
            
            if exclude_user_id:
                query = query.neq("user_id", exclude_user_id)
            
            response = query.execute()
            return len(response.data or []) == 0
        except Exception as e:
            logger.error(f"Error checking username availability: {e}")
            return False
    
    def get_user_level_info(self, user_id: str) -> Dict[str, Any]:
        """Get user's level and XP information.
        
        Args:
            user_id: User ID
            
        Returns:
            Level information dictionary
        """
        try:
            profile = self.get_complete_user_profile(user_id)
            if not profile:
                return {}
            
            current_xp = profile.get('current_xp', 0)
            level = profile.get('level', 1)
            
            # Calculate XP needed for next level (simple formula)
            xp_for_next_level = level * 1000
            xp_for_current_level = (level - 1) * 1000
            xp_progress = current_xp - xp_for_current_level
            xp_needed = xp_for_next_level - current_xp
            
            return {
                'level': level,
                'current_xp': current_xp,
                'xp_progress': max(0, xp_progress),
                'xp_needed': max(0, xp_needed),
                'xp_for_next_level': xp_for_next_level,
                'progress_percentage': min(100, (xp_progress / 1000) * 100) if xp_progress >= 0 else 0
            }
        except Exception as e:
            logger.error(f"Error getting user level info: {e}")
            return {}

# Note: Global instance creation removed to prevent import-time initialization
# Use trackpro.social.enhanced_user_manager or trackpro.social.get_enhanced_user_manager() instead 