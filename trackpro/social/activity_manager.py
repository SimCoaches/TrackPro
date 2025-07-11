"""Activity Manager for comprehensive activity feed and social interaction tracking."""

import logging
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from enum import Enum
from ..database.base import DatabaseManager
from ..database.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)

class ActivityType(Enum):
    """Activity type enumeration."""
    # Racing activities
    LAP_COMPLETED = "lap_completed"
    PERSONAL_BEST = "personal_best"
    SESSION_COMPLETED = "session_completed"
    TRACK_MASTERED = "track_mastered"
    
    # Social activities
    FRIEND_ADDED = "friend_added"
    MESSAGE_SENT = "message_sent"
    GROUP_JOINED = "group_joined"
    
    # Achievement activities
    ACHIEVEMENT_UNLOCKED = "achievement_unlocked"
    LEVEL_UP = "level_up"
    STREAK_MILESTONE = "streak_milestone"
    
    # Community activities
    TEAM_JOINED = "team_joined"
    EVENT_PARTICIPATED = "event_participated"
    CONTENT_SHARED = "content_shared"
    SETUP_SHARED = "setup_shared"
    
    # System activities
    PROFILE_UPDATED = "profile_updated"
    AVATAR_CHANGED = "avatar_changed"

class PrivacyLevel(Enum):
    """Privacy level enumeration."""
    PUBLIC = "public"
    FRIENDS = "friends"
    PRIVATE = "private"

class InteractionType(Enum):
    """Interaction type enumeration."""
    LIKE = "like"
    COMMENT = "comment"
    SHARE = "share"

class ActivityManager(DatabaseManager):
    """Comprehensive activity feed and interaction management."""
    
    def __init__(self):
        """Initialize the activity manager."""
        super().__init__("user_activities")
        self.supabase = get_supabase_client()
    
    # =====================================================
    # ACTIVITY CREATION
    # =====================================================
    
    def create_activity(self, user_id: str, activity_type: ActivityType, title: str, 
                       description: str = "", metadata: Dict[str, Any] = None, 
                       privacy_level: PrivacyLevel = PrivacyLevel.FRIENDS) -> Optional[Dict[str, Any]]:
        """Create a new user activity.
        
        Args:
            user_id: User ID
            activity_type: Type of activity
            title: Activity title
            description: Activity description
            metadata: Additional activity metadata
            privacy_level: Privacy level for the activity
            
        Returns:
            Created activity data or None
        """
        try:
            activity_data = {
                'user_id': user_id,
                'activity_type': activity_type.value,
                'title': title,
                'description': description,
                'metadata': metadata or {},
                'privacy_level': privacy_level.value,
                'created_at': datetime.utcnow().isoformat()
            }
            
            response = self.client.from_("user_activities").insert(activity_data).execute()
            if response.data:
                activity = response.data[0]
                logger.info(f"Activity created: {activity_type.value} for user {user_id}")
                return activity
            
            return None
            
        except Exception as e:
            logger.error(f"Error creating activity: {e}")
            return None
    
    def create_racing_activity(self, user_id: str, activity_type: ActivityType, 
                              lap_time: float = None, track_id: int = None, 
                              car_id: int = None, improvement: float = None) -> Optional[Dict[str, Any]]:
        """Create a racing-related activity.
        
        Args:
            user_id: User ID
            activity_type: Type of racing activity
            lap_time: Lap time in seconds
            track_id: Track ID
            car_id: Car ID
            improvement: Improvement amount (for personal bests)
            
        Returns:
            Created activity data or None
        """
        try:
            metadata = {
                'lap_time': lap_time,
                'track_id': track_id,
                'car_id': car_id,
                'improvement': improvement
            }
            
            # Generate title and description based on activity type
            title, description = self._generate_racing_activity_content(
                activity_type, lap_time, track_id, car_id, improvement
            )
            
            return self.create_activity(
                user_id=user_id,
                activity_type=activity_type,
                title=title,
                description=description,
                metadata=metadata,
                privacy_level=PrivacyLevel.FRIENDS
            )
            
        except Exception as e:
            logger.error(f"Error creating racing activity: {e}")
            return None
    
    def create_social_activity(self, user_id: str, activity_type: ActivityType, 
                              target_user_id: str = None, target_username: str = None,
                              additional_data: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
        """Create a social-related activity.
        
        Args:
            user_id: User ID
            activity_type: Type of social activity
            target_user_id: Target user ID (for friend activities)
            target_username: Target username
            additional_data: Additional activity data
            
        Returns:
            Created activity data or None
        """
        try:
            metadata = {
                'target_user_id': target_user_id,
                'target_username': target_username,
                **(additional_data or {})
            }
            
            title, description = self._generate_social_activity_content(
                activity_type, target_username, additional_data
            )
            
            return self.create_activity(
                user_id=user_id,
                activity_type=activity_type,
                title=title,
                description=description,
                metadata=metadata,
                privacy_level=PrivacyLevel.FRIENDS
            )
            
        except Exception as e:
            logger.error(f"Error creating social activity: {e}")
            return None
    
    def create_achievement_activity(self, user_id: str, achievement_id: str, 
                                   achievement_name: str, achievement_rarity: str = "common") -> Optional[Dict[str, Any]]:
        """Create an achievement unlock activity.
        
        Args:
            user_id: User ID
            achievement_id: Achievement ID
            achievement_name: Achievement name
            achievement_rarity: Achievement rarity
            
        Returns:
            Created activity data or None
        """
        try:
            metadata = {
                'achievement_id': achievement_id,
                'achievement_name': achievement_name,
                'achievement_rarity': achievement_rarity
            }
            
            title = f"Unlocked achievement: {achievement_name}"
            description = f"Earned a {achievement_rarity} achievement"
            
            # Determine privacy based on rarity
            privacy_level = PrivacyLevel.PUBLIC if achievement_rarity in ['epic', 'legendary'] else PrivacyLevel.FRIENDS
            
            return self.create_activity(
                user_id=user_id,
                activity_type=ActivityType.ACHIEVEMENT_UNLOCKED,
                title=title,
                description=description,
                metadata=metadata,
                privacy_level=privacy_level
            )
            
        except Exception as e:
            logger.error(f"Error creating achievement activity: {e}")
            return None
    
    # =====================================================
    # ACTIVITY FEEDS
    # =====================================================
    
    def get_user_feed(self, user_id: str, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """Get activity feed for a user (their own activities + friends' activities).
        
        Args:
            user_id: User ID
            limit: Maximum number of activities
            offset: Offset for pagination
            
        Returns:
            List of activities for the feed
        """
        try:
            # Get user's friends
            from .friends_manager import friends_manager
            friends = friends_manager.get_friends_list(user_id, include_online_status=False)
            friend_ids = [friend['friend_id'] for friend in friends]
            
            # Include user's own activities
            all_user_ids = [user_id] + friend_ids
            
            # Get activities from user and friends
            response = self.client.from_("user_activities").select("""
                *,
                user_profiles(username, display_name, avatar_url, level),
                activity_interactions(
                    id, interaction_type, user_id, created_at,
                    user_profiles(username, display_name, avatar_url)
                )
            """).in_("user_id", all_user_ids).or_(
                "privacy_level.eq.public,privacy_level.eq.friends"
            ).order("created_at", desc=True).range(offset, offset + limit - 1).execute()
            
            activities = response.data or []
            
            # Add interaction counts and user interaction status
            for activity in activities:
                activity['interaction_counts'] = self._get_interaction_counts(activity['id'])
                activity['user_interactions'] = self._get_user_interactions(activity['id'], user_id)
            
            return activities
            
        except Exception as e:
            logger.error(f"Error getting user feed: {e}")
            return []
    
    def get_user_activities(self, user_id: str, viewer_id: str = None, 
                           limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """Get activities for a specific user.
        
        Args:
            user_id: User whose activities to get
            viewer_id: ID of user viewing the activities
            limit: Maximum number of activities
            offset: Offset for pagination
            
        Returns:
            List of user activities
        """
        try:
            # Determine privacy filter based on relationship
            privacy_filter = self._get_privacy_filter(user_id, viewer_id)
            
            query = self.client.from_("user_activities").select("""
                *,
                user_profiles(username, display_name, avatar_url, level),
                activity_interactions(
                    id, interaction_type, user_id, created_at,
                    user_profiles(username, display_name, avatar_url)
                )
            """).eq("user_id", user_id)
            
            if privacy_filter:
                query = query.in_("privacy_level", privacy_filter)
            
            response = query.order("created_at", desc=True).range(offset, offset + limit - 1).execute()
            
            activities = response.data or []
            
            # Add interaction counts and user interaction status
            for activity in activities:
                activity['interaction_counts'] = self._get_interaction_counts(activity['id'])
                if viewer_id:
                    activity['user_interactions'] = self._get_user_interactions(activity['id'], viewer_id)
            
            return activities
            
        except Exception as e:
            logger.error(f"Error getting user activities: {e}")
            return []
    
    def get_public_feed(self, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """Get public activity feed.
        
        Args:
            limit: Maximum number of activities
            offset: Offset for pagination
            
        Returns:
            List of public activities
        """
        try:
            response = self.client.from_("user_activities").select("""
                *,
                user_profiles(username, display_name, avatar_url, level),
                activity_interactions(
                    id, interaction_type, user_id, created_at,
                    user_profiles(username, display_name, avatar_url)
                )
            """).eq("privacy_level", PrivacyLevel.PUBLIC.value).order("created_at", desc=True).range(offset, offset + limit - 1).execute()
            
            activities = response.data or []
            
            # Add interaction counts
            for activity in activities:
                activity['interaction_counts'] = self._get_interaction_counts(activity['id'])
            
            return activities
            
        except Exception as e:
            logger.error(f"Error getting public feed: {e}")
            return []
    
    # =====================================================
    # ACTIVITY INTERACTIONS
    # =====================================================
    
    def add_interaction(self, activity_id: str, user_id: str, interaction_type: InteractionType, 
                       content: str = None) -> Optional[Dict[str, Any]]:
        """Add an interaction to an activity.
        
        Args:
            activity_id: Activity ID
            user_id: User ID adding the interaction
            interaction_type: Type of interaction
            content: Content for comments
            
        Returns:
            Created interaction data or None
        """
        try:
            # Check if activity exists and is accessible
            activity = self.get_activity(activity_id, user_id)
            if not activity:
                logger.warning(f"Activity {activity_id} not accessible to user {user_id}")
                return None
            
            # For likes, check if user already liked
            if interaction_type == InteractionType.LIKE:
                existing_like = self.client.from_("activity_interactions").select("id").eq("activity_id", activity_id).eq("user_id", user_id).eq("interaction_type", InteractionType.LIKE.value).execute()
                
                if existing_like.data:
                    # Remove existing like (toggle)
                    self.client.from_("activity_interactions").delete().eq("id", existing_like.data[0]['id']).execute()
                    logger.info(f"Like removed from activity {activity_id} by user {user_id}")
                    return {"action": "removed"}
            
            # Create interaction
            interaction_data = {
                'activity_id': activity_id,
                'user_id': user_id,
                'interaction_type': interaction_type.value,
                'content': content,
                'created_at': datetime.utcnow().isoformat()
            }
            
            response = self.client.from_("activity_interactions").insert(interaction_data).execute()
            if response.data:
                interaction = response.data[0]
                
                # Create notification for activity owner (if not self-interaction)
                if activity['user_id'] != user_id:
                    self._create_interaction_notification(activity['user_id'], user_id, activity_id, interaction_type)
                
                logger.info(f"Interaction {interaction_type.value} added to activity {activity_id} by user {user_id}")
                return interaction
            
            return None
            
        except Exception as e:
            logger.error(f"Error adding interaction: {e}")
            return None
    
    def remove_interaction(self, interaction_id: str, user_id: str) -> bool:
        """Remove an interaction (only by the user who created it).
        
        Args:
            interaction_id: Interaction ID
            user_id: User ID attempting to remove
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Verify user owns the interaction
            response = self.client.from_("activity_interactions").select("*").eq("id", interaction_id).eq("user_id", user_id).single().execute()
            
            if not response.data:
                logger.warning(f"Interaction {interaction_id} not found or not owned by user {user_id}")
                return False
            
            # Delete interaction
            delete_response = self.client.from_("activity_interactions").delete().eq("id", interaction_id).execute()
            
            if delete_response.data:
                logger.info(f"Interaction {interaction_id} removed by user {user_id}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error removing interaction: {e}")
            return False
    
    def get_activity_interactions(self, activity_id: str, interaction_type: InteractionType = None, 
                                 limit: int = 50) -> List[Dict[str, Any]]:
        """Get interactions for an activity.
        
        Args:
            activity_id: Activity ID
            interaction_type: Filter by interaction type
            limit: Maximum number of interactions
            
        Returns:
            List of interactions
        """
        try:
            query = self.client.from_("activity_interactions").select("""
                *,
                user_profiles(username, display_name, avatar_url, level)
            """).eq("activity_id", activity_id)
            
            if interaction_type:
                query = query.eq("interaction_type", interaction_type.value)
            
            response = query.order("created_at", desc=True).limit(limit).execute()
            
            return response.data or []
            
        except Exception as e:
            logger.error(f"Error getting activity interactions: {e}")
            return []
    
    # =====================================================
    # ACTIVITY MANAGEMENT
    # =====================================================
    
    def get_activity(self, activity_id: str, viewer_id: str = None) -> Optional[Dict[str, Any]]:
        """Get a specific activity.
        
        Args:
            activity_id: Activity ID
            viewer_id: ID of user viewing the activity
            
        Returns:
            Activity data or None
        """
        try:
            response = self.client.from_("user_activities").select("""
                *,
                user_profiles(username, display_name, avatar_url, level)
            """).eq("id", activity_id).single().execute()
            
            if not response.data:
                return None
            
            activity = response.data
            
            # Check privacy permissions
            if not self._can_view_activity(activity, viewer_id):
                return None
            
            # Add interaction data
            activity['interaction_counts'] = self._get_interaction_counts(activity_id)
            if viewer_id:
                activity['user_interactions'] = self._get_user_interactions(activity_id, viewer_id)
            
            return activity
            
        except Exception as e:
            logger.error(f"Error getting activity: {e}")
            return None
    
    def update_activity(self, activity_id: str, user_id: str, updates: Dict[str, Any]) -> bool:
        """Update an activity (only by owner).
        
        Args:
            activity_id: Activity ID
            user_id: User ID attempting to update
            updates: Updates to apply
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Verify user owns the activity
            response = self.client.from_("user_activities").select("user_id").eq("id", activity_id).single().execute()
            
            if not response.data or response.data['user_id'] != user_id:
                logger.warning(f"Activity {activity_id} not found or not owned by user {user_id}")
                return False
            
            # Apply updates
            allowed_fields = {'title', 'description', 'privacy_level', 'metadata'}
            filtered_updates = {k: v for k, v in updates.items() if k in allowed_fields}
            
            if filtered_updates:
                update_response = self.client.from_("user_activities").update(filtered_updates).eq("id", activity_id).execute()
                return bool(update_response.data)
            
            return False
            
        except Exception as e:
            logger.error(f"Error updating activity: {e}")
            return False
    
    def delete_activity(self, activity_id: str, user_id: str) -> bool:
        """Delete an activity (only by owner).
        
        Args:
            activity_id: Activity ID
            user_id: User ID attempting to delete
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Verify user owns the activity
            response = self.client.from_("user_activities").select("user_id").eq("id", activity_id).single().execute()
            
            if not response.data or response.data['user_id'] != user_id:
                logger.warning(f"Activity {activity_id} not found or not owned by user {user_id}")
                return False
            
            # Delete activity (this will cascade delete interactions)
            delete_response = self.client.from_("user_activities").delete().eq("id", activity_id).execute()
            
            if delete_response.data:
                logger.info(f"Activity {activity_id} deleted by user {user_id}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error deleting activity: {e}")
            return False
    
    # =====================================================
    # ACTIVITY STATISTICS
    # =====================================================
    
    def get_user_activity_stats(self, user_id: str, days: int = 30) -> Dict[str, Any]:
        """Get activity statistics for a user.
        
        Args:
            user_id: User ID
            days: Number of days to analyze
            
        Returns:
            Activity statistics
        """
        try:
            cutoff_date = (datetime.utcnow() - timedelta(days=days)).isoformat()
            
            # Get activity counts by type
            response = self.client.from_("user_activities").select("activity_type").eq("user_id", user_id).gte("created_at", cutoff_date).execute()
            
            activities = response.data or []
            
            # Count by type
            type_counts = {}
            for activity in activities:
                activity_type = activity['activity_type']
                type_counts[activity_type] = type_counts.get(activity_type, 0) + 1
            
            # Get interaction stats
            interaction_response = self.client.from_("activity_interactions").select("interaction_type").eq("user_id", user_id).gte("created_at", cutoff_date).execute()
            
            interactions = interaction_response.data or []
            interaction_counts = {}
            for interaction in interactions:
                interaction_type = interaction['interaction_type']
                interaction_counts[interaction_type] = interaction_counts.get(interaction_type, 0) + 1
            
            return {
                'total_activities': len(activities),
                'activity_types': type_counts,
                'total_interactions': len(interactions),
                'interaction_types': interaction_counts,
                'period_days': days
            }
            
        except Exception as e:
            logger.error(f"Error getting user activity stats: {e}")
            return {}
    
    # =====================================================
    # UTILITY METHODS
    # =====================================================
    
    def _get_privacy_filter(self, user_id: str, viewer_id: str = None) -> List[str]:
        """Get privacy filter for activities based on relationship.
        
        Args:
            user_id: User whose activities are being viewed
            viewer_id: User viewing the activities
            
        Returns:
            List of allowed privacy levels
        """
        if not viewer_id:
            return [PrivacyLevel.PUBLIC.value]
        
        if user_id == viewer_id:
            return [PrivacyLevel.PUBLIC.value, PrivacyLevel.FRIENDS.value, PrivacyLevel.PRIVATE.value]
        
        # Check if they are friends
        from .friends_manager import friends_manager
        if friends_manager.are_friends(user_id, viewer_id):
            return [PrivacyLevel.PUBLIC.value, PrivacyLevel.FRIENDS.value]
        
        return [PrivacyLevel.PUBLIC.value]
    
    def _can_view_activity(self, activity: Dict[str, Any], viewer_id: str = None) -> bool:
        """Check if viewer can see the activity.
        
        Args:
            activity: Activity data
            viewer_id: Viewer user ID
            
        Returns:
            True if can view, False otherwise
        """
        privacy_level = activity.get('privacy_level', PrivacyLevel.FRIENDS.value)
        user_id = activity.get('user_id')
        
        if privacy_level == PrivacyLevel.PUBLIC.value:
            return True
        
        if not viewer_id:
            return False
        
        if user_id == viewer_id:
            return True
        
        if privacy_level == PrivacyLevel.FRIENDS.value:
            from .friends_manager import friends_manager
            return friends_manager.are_friends(user_id, viewer_id)
        
        return False
    
    def _get_interaction_counts(self, activity_id: str) -> Dict[str, int]:
        """Get interaction counts for an activity.
        
        Args:
            activity_id: Activity ID
            
        Returns:
            Dictionary of interaction counts
        """
        try:
            response = self.client.from_("activity_interactions").select("interaction_type").eq("activity_id", activity_id).execute()
            
            interactions = response.data or []
            counts = {}
            
            for interaction in interactions:
                interaction_type = interaction['interaction_type']
                counts[interaction_type] = counts.get(interaction_type, 0) + 1
            
            return counts
            
        except Exception as e:
            logger.error(f"Error getting interaction counts: {e}")
            return {}
    
    def _get_user_interactions(self, activity_id: str, user_id: str) -> Dict[str, Any]:
        """Get user's interactions with an activity.
        
        Args:
            activity_id: Activity ID
            user_id: User ID
            
        Returns:
            Dictionary of user interactions
        """
        try:
            response = self.client.from_("activity_interactions").select("*").eq("activity_id", activity_id).eq("user_id", user_id).execute()
            
            interactions = response.data or []
            user_interactions = {}
            
            for interaction in interactions:
                interaction_type = interaction['interaction_type']
                user_interactions[interaction_type] = interaction
            
            return user_interactions
            
        except Exception as e:
            logger.error(f"Error getting user interactions: {e}")
            return {}
    
    def _generate_racing_activity_content(self, activity_type: ActivityType, lap_time: float = None, 
                                        track_id: int = None, car_id: int = None, 
                                        improvement: float = None) -> Tuple[str, str]:
        """Generate title and description for racing activities."""
        if activity_type == ActivityType.LAP_COMPLETED:
            title = f"Completed a lap in {lap_time:.3f}s"
            description = f"Finished a lap on track {track_id} with car {car_id}"
        elif activity_type == ActivityType.PERSONAL_BEST:
            title = f"New personal best: {lap_time:.3f}s"
            description = f"Improved by {improvement:.3f}s on track {track_id}"
        elif activity_type == ActivityType.SESSION_COMPLETED:
            title = "Completed a racing session"
            description = f"Finished a session on track {track_id}"
        elif activity_type == ActivityType.TRACK_MASTERED:
            title = f"Mastered track {track_id}"
            description = "Achieved consistent lap times and track mastery"
        else:
            title = "Racing activity"
            description = "Completed a racing activity"
        
        return title, description
    
    def _generate_social_activity_content(self, activity_type: ActivityType, target_username: str = None, 
                                        additional_data: Dict[str, Any] = None) -> Tuple[str, str]:
        """Generate title and description for social activities."""
        if activity_type == ActivityType.FRIEND_ADDED:
            title = f"Became friends with {target_username or 'someone'}"
            description = "Added a new friend"
        elif activity_type == ActivityType.GROUP_JOINED:
            group_name = additional_data.get('group_name', 'a group') if additional_data else 'a group'
            title = f"Joined {group_name}"
            description = "Joined a new group"
        elif activity_type == ActivityType.TEAM_JOINED:
            team_name = additional_data.get('team_name', 'a team') if additional_data else 'a team'
            title = f"Joined team {team_name}"
            description = "Joined a racing team"
        else:
            title = "Social activity"
            description = "Participated in social activity"
        
        return title, description
    
    def _create_interaction_notification(self, recipient_id: str, actor_id: str, 
                                       activity_id: str, interaction_type: InteractionType):
        """Create a notification for activity interactions."""
        # This would be implemented with the notification system
        logger.info(f"Notification: User {actor_id} {interaction_type.value}d activity {activity_id} of user {recipient_id}")

# Create a global instance
# Note: Global instance creation removed to prevent import-time initialization
# Use trackpro.social.activity_manager or trackpro.social.get_activity_manager() instead 