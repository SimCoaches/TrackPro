"""Friends Manager for comprehensive friend system functionality."""

import logging
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from enum import Enum
from ..database.base import DatabaseManager
from ..database.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)

class FriendshipStatus(Enum):
    """Friendship status enumeration."""
    PENDING = "pending"
    ACCEPTED = "accepted"
    BLOCKED = "blocked"
    DECLINED = "declined"

class FriendsManager(DatabaseManager):
    """Comprehensive friends management system."""
    
    def __init__(self):
        """Initialize the friends manager."""
        super().__init__("friendships")
        self.supabase = get_supabase_client()
    
    # =====================================================
    # FRIEND REQUEST MANAGEMENT
    # =====================================================
    
    def send_friend_request(self, requester_id: str, addressee_id: str) -> Dict[str, Any]:
        """Send a friend request to another user.
        
        Args:
            requester_id: ID of user sending the request
            addressee_id: ID of user receiving the request
            
        Returns:
            Dictionary with success status and message
        """
        try:
            # Validate users are different
            if requester_id == addressee_id:
                return {"success": False, "message": "Cannot send friend request to yourself"}
            
            # Check if addressee exists
            addressee_response = self.client.from_("user_profiles").select("user_id, username, privacy_settings").eq("user_id", addressee_id).single().execute()
            if not addressee_response.data:
                return {"success": False, "message": "User not found"}
            
            addressee = addressee_response.data
            privacy_settings = addressee.get('privacy_settings', {})
            
            # Check privacy settings for friend requests
            friend_request_setting = privacy_settings.get('friend_requests', 'everyone')
            if friend_request_setting == 'none':
                return {"success": False, "message": "User is not accepting friend requests"}
            
            # Check if friendship already exists
            existing_friendship = self.get_friendship_status(requester_id, addressee_id)
            if existing_friendship:
                status = existing_friendship.get('status')
                if status == FriendshipStatus.ACCEPTED.value:
                    return {"success": False, "message": "Already friends"}
                elif status == FriendshipStatus.PENDING.value:
                    return {"success": False, "message": "Friend request already sent"}
                elif status == FriendshipStatus.BLOCKED.value:
                    return {"success": False, "message": "Cannot send friend request"}
            
            # Create friend request
            friendship_data = {
                'requester_id': requester_id,
                'addressee_id': addressee_id,
                'status': FriendshipStatus.PENDING.value,
                'created_at': datetime.utcnow().isoformat(),
                'updated_at': datetime.utcnow().isoformat()
            }
            
            response = self.client.from_("friendships").insert(friendship_data).execute()
            if not response.data:
                return {"success": False, "message": "Failed to send friend request"}
            
            # Create activity for friend request
            self._create_friend_activity(requester_id, "friend_request_sent", {
                'target_user_id': addressee_id,
                'target_username': addressee.get('username')
            })
            
            # Create notification for addressee (would be implemented in notification system)
            self._create_friend_notification(addressee_id, "friend_request_received", {
                'requester_id': requester_id,
                'friendship_id': response.data[0]['id']
            })
            
            logger.info(f"Friend request sent from {requester_id} to {addressee_id}")
            return {"success": True, "message": "Friend request sent successfully"}
            
        except Exception as e:
            logger.error(f"Error sending friend request: {e}")
            return {"success": False, "message": "Failed to send friend request"}
    
    def respond_to_friend_request(self, friendship_id: str, user_id: str, accept: bool) -> Dict[str, Any]:
        """Respond to a friend request (accept or decline).
        
        Args:
            friendship_id: ID of the friendship record
            user_id: ID of user responding (must be the addressee)
            accept: True to accept, False to decline
            
        Returns:
            Dictionary with success status and message
        """
        try:
            # Get the friendship record
            friendship_response = self.client.from_("friendships").select("*").eq("id", friendship_id).single().execute()
            if not friendship_response.data:
                return {"success": False, "message": "Friend request not found"}
            
            friendship = friendship_response.data
            
            # Verify user is the addressee
            if friendship['addressee_id'] != user_id:
                return {"success": False, "message": "Not authorized to respond to this request"}
            
            # Verify request is still pending
            if friendship['status'] != FriendshipStatus.PENDING.value:
                return {"success": False, "message": "Friend request is no longer pending"}
            
            # Update friendship status
            new_status = FriendshipStatus.ACCEPTED.value if accept else FriendshipStatus.DECLINED.value
            update_data = {
                'status': new_status,
                'updated_at': datetime.utcnow().isoformat()
            }
            
            response = self.client.from_("friendships").update(update_data).eq("id", friendship_id).execute()
            if not response.data:
                return {"success": False, "message": "Failed to update friend request"}
            
            # Create activities for both users
            if accept:
                self._create_friend_activity(user_id, "friend_request_accepted", {
                    'friend_user_id': friendship['requester_id']
                })
                self._create_friend_activity(friendship['requester_id'], "friend_added", {
                    'friend_user_id': user_id
                })
                
                # Create notification for requester
                self._create_friend_notification(friendship['requester_id'], "friend_request_accepted", {
                    'accepter_id': user_id,
                    'friendship_id': friendship_id
                })
                
                message = "Friend request accepted"
            else:
                message = "Friend request declined"
            
            logger.info(f"Friend request {friendship_id} {'accepted' if accept else 'declined'} by {user_id}")
            return {"success": True, "message": message}
            
        except Exception as e:
            logger.error(f"Error responding to friend request: {e}")
            return {"success": False, "message": "Failed to respond to friend request"}
    
    def cancel_friend_request(self, requester_id: str, addressee_id: str) -> Dict[str, Any]:
        """Cancel a pending friend request.
        
        Args:
            requester_id: ID of user who sent the request
            addressee_id: ID of user who received the request
            
        Returns:
            Dictionary with success status and message
        """
        try:
            # Find the pending friendship
            friendship_response = self.client.from_("friendships").select("*").eq("requester_id", requester_id).eq("addressee_id", addressee_id).eq("status", FriendshipStatus.PENDING.value).single().execute()
            
            if not friendship_response.data:
                return {"success": False, "message": "No pending friend request found"}
            
            # Delete the friendship record
            delete_response = self.client.from_("friendships").delete().eq("id", friendship_response.data['id']).execute()
            
            if delete_response.data:
                logger.info(f"Friend request cancelled from {requester_id} to {addressee_id}")
                return {"success": True, "message": "Friend request cancelled"}
            else:
                return {"success": False, "message": "Failed to cancel friend request"}
                
        except Exception as e:
            logger.error(f"Error cancelling friend request: {e}")
            return {"success": False, "message": "Failed to cancel friend request"}
    
    # =====================================================
    # FRIEND MANAGEMENT
    # =====================================================
    
    def remove_friend(self, user_id: str, friend_id: str) -> Dict[str, Any]:
        """Remove a friend (unfriend).
        
        Args:
            user_id: ID of user removing the friend
            friend_id: ID of friend being removed
            
        Returns:
            Dictionary with success status and message
        """
        try:
            # Find the friendship (could be in either direction)
            friendship_response = self.client.from_("friendships").select("*").or_(
                f"and(requester_id.eq.{user_id},addressee_id.eq.{friend_id}),and(requester_id.eq.{friend_id},addressee_id.eq.{user_id})"
            ).eq("status", FriendshipStatus.ACCEPTED.value).single().execute()
            
            if not friendship_response.data:
                return {"success": False, "message": "Friendship not found"}
            
            # Delete the friendship
            delete_response = self.client.from_("friendships").delete().eq("id", friendship_response.data['id']).execute()
            
            if delete_response.data:
                # Create activity
                self._create_friend_activity(user_id, "friend_removed", {
                    'friend_user_id': friend_id
                })
                
                logger.info(f"Friendship removed between {user_id} and {friend_id}")
                return {"success": True, "message": "Friend removed successfully"}
            else:
                return {"success": False, "message": "Failed to remove friend"}
                
        except Exception as e:
            logger.error(f"Error removing friend: {e}")
            return {"success": False, "message": "Failed to remove friend"}
    
    def block_user(self, blocker_id: str, blocked_id: str) -> Dict[str, Any]:
        """Block a user.
        
        Args:
            blocker_id: ID of user doing the blocking
            blocked_id: ID of user being blocked
            
        Returns:
            Dictionary with success status and message
        """
        try:
            # Remove existing friendship if any
            existing_friendship = self.get_friendship_status(blocker_id, blocked_id)
            if existing_friendship:
                self.client.from_("friendships").delete().eq("id", existing_friendship['id']).execute()
            
            # Create block record
            block_data = {
                'requester_id': blocker_id,
                'addressee_id': blocked_id,
                'status': FriendshipStatus.BLOCKED.value,
                'created_at': datetime.utcnow().isoformat(),
                'updated_at': datetime.utcnow().isoformat()
            }
            
            response = self.client.from_("friendships").insert(block_data).execute()
            if response.data:
                logger.info(f"User {blocked_id} blocked by {blocker_id}")
                return {"success": True, "message": "User blocked successfully"}
            else:
                return {"success": False, "message": "Failed to block user"}
                
        except Exception as e:
            logger.error(f"Error blocking user: {e}")
            return {"success": False, "message": "Failed to block user"}
    
    def unblock_user(self, blocker_id: str, blocked_id: str) -> Dict[str, Any]:
        """Unblock a user.
        
        Args:
            blocker_id: ID of user doing the unblocking
            blocked_id: ID of user being unblocked
            
        Returns:
            Dictionary with success status and message
        """
        try:
            # Find the block record
            block_response = self.client.from_("friendships").select("*").eq("requester_id", blocker_id).eq("addressee_id", blocked_id).eq("status", FriendshipStatus.BLOCKED.value).single().execute()
            
            if not block_response.data:
                return {"success": False, "message": "Block record not found"}
            
            # Delete the block record
            delete_response = self.client.from_("friendships").delete().eq("id", block_response.data['id']).execute()
            
            if delete_response.data:
                logger.info(f"User {blocked_id} unblocked by {blocker_id}")
                return {"success": True, "message": "User unblocked successfully"}
            else:
                return {"success": False, "message": "Failed to unblock user"}
                
        except Exception as e:
            logger.error(f"Error unblocking user: {e}")
            return {"success": False, "message": "Failed to unblock user"}
    
    # =====================================================
    # FRIEND LISTS AND QUERIES
    # =====================================================
    
    def get_friends_list(self, user_id: str, include_online_status: bool = True) -> List[Dict[str, Any]]:
        """Get user's friends list.
        
        Args:
            user_id: User ID to get friends for
            include_online_status: Whether to include online status
            
        Returns:
            List of friends with their information
        """
        try:
            # Use the user_friends view for efficient querying
            response = self.client.from_("user_friends").select("*").eq("user_id", user_id).execute()
            friends = response.data or []
            
            if include_online_status:
                # Add online status (would be implemented with real-time presence system)
                for friend in friends:
                    friend['is_online'] = self._get_user_online_status(friend['friend_id'])
                    friend['last_seen'] = self._get_user_last_seen(friend['friend_id'])
            
            return friends
            
        except Exception as e:
            logger.error(f"Error getting friends list: {e}")
            return []
    
    def get_pending_friend_requests(self, user_id: str, sent: bool = False) -> List[Dict[str, Any]]:
        """Get pending friend requests for a user.
        
        Args:
            user_id: User ID
            sent: If True, get requests sent by user; if False, get requests received
            
        Returns:
            List of pending friend requests
        """
        try:
            if sent:
                # Requests sent by this user
                response = self.client.from_("friendships").select("""
                    id, addressee_id, created_at,
                    user_profiles!friendships_addressee_id_fkey(username, display_name, avatar_url, level)
                """).eq("requester_id", user_id).eq("status", FriendshipStatus.PENDING.value).execute()
            else:
                # Requests received by this user
                response = self.client.from_("friendships").select("""
                    id, requester_id, created_at,
                    user_profiles!friendships_requester_id_fkey(username, display_name, avatar_url, level)
                """).eq("addressee_id", user_id).eq("status", FriendshipStatus.PENDING.value).execute()
            
            return response.data or []
            
        except Exception as e:
            logger.error(f"Error getting pending friend requests: {e}")
            return []
    
    def get_blocked_users(self, user_id: str) -> List[Dict[str, Any]]:
        """Get list of users blocked by the user.
        
        Args:
            user_id: User ID
            
        Returns:
            List of blocked users
        """
        try:
            response = self.client.from_("friendships").select("""
                id, addressee_id, created_at,
                user_profiles!friendships_addressee_id_fkey(username, display_name, avatar_url)
            """).eq("requester_id", user_id).eq("status", FriendshipStatus.BLOCKED.value).execute()
            
            return response.data or []
            
        except Exception as e:
            logger.error(f"Error getting blocked users: {e}")
            return []
    
    def get_mutual_friends(self, user1_id: str, user2_id: str) -> List[Dict[str, Any]]:
        """Get mutual friends between two users.
        
        Args:
            user1_id: First user ID
            user2_id: Second user ID
            
        Returns:
            List of mutual friends
        """
        try:
            # Get friends of both users
            user1_friends = {friend['friend_id'] for friend in self.get_friends_list(user1_id, include_online_status=False)}
            user2_friends = {friend['friend_id'] for friend in self.get_friends_list(user2_id, include_online_status=False)}
            
            # Find mutual friends
            mutual_friend_ids = user1_friends.intersection(user2_friends)
            
            if not mutual_friend_ids:
                return []
            
            # Get user details for mutual friends
            response = self.client.from_("user_profiles").select(
                "user_id, username, display_name, avatar_url, level"
            ).in_("user_id", list(mutual_friend_ids)).execute()
            
            return response.data or []
            
        except Exception as e:
            logger.error(f"Error getting mutual friends: {e}")
            return []
    
    # =====================================================
    # FRIEND DISCOVERY AND SUGGESTIONS
    # =====================================================
    
    def get_friend_suggestions(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get friend suggestions for a user.
        
        Args:
            user_id: User ID
            limit: Maximum number of suggestions
            
        Returns:
            List of suggested users
        """
        try:
            suggestions = []
            
            # Get mutual friend suggestions
            mutual_suggestions = self._get_mutual_friend_suggestions(user_id, limit // 2)
            suggestions.extend(mutual_suggestions)
            
            # Get similar level suggestions
            if len(suggestions) < limit:
                level_suggestions = self._get_similar_level_suggestions(user_id, limit - len(suggestions))
                suggestions.extend(level_suggestions)
            
            # Get recently active suggestions
            if len(suggestions) < limit:
                active_suggestions = self._get_recently_active_suggestions(user_id, limit - len(suggestions))
                suggestions.extend(active_suggestions)
            
            # Remove duplicates and current friends
            current_friends = {friend['friend_id'] for friend in self.get_friends_list(user_id, include_online_status=False)}
            unique_suggestions = []
            seen_ids = set()
            
            for suggestion in suggestions:
                user_id_key = suggestion.get('user_id')
                if user_id_key and user_id_key not in seen_ids and user_id_key not in current_friends and user_id_key != user_id:
                    seen_ids.add(user_id_key)
                    unique_suggestions.append(suggestion)
            
            return unique_suggestions[:limit]
            
        except Exception as e:
            logger.error(f"Error getting friend suggestions: {e}")
            return []
    
    def _get_mutual_friend_suggestions(self, user_id: str, limit: int) -> List[Dict[str, Any]]:
        """Get friend suggestions based on mutual friends."""
        try:
            # Get user's friends
            user_friends = self.get_friends_list(user_id, include_online_status=False)
            friend_ids = [friend['friend_id'] for friend in user_friends]
            
            if not friend_ids:
                return []
            
            # Get friends of friends
            suggestions = []
            for friend_id in friend_ids[:5]:  # Limit to avoid too many queries
                friend_friends = self.get_friends_list(friend_id, include_online_status=False)
                for friend_friend in friend_friends[:3]:  # Limit suggestions per friend
                    if friend_friend['friend_id'] != user_id:
                        # Add mutual friend count
                        mutual_count = len(self.get_mutual_friends(user_id, friend_friend['friend_id']))
                        friend_friend['mutual_friends_count'] = mutual_count
                        friend_friend['suggestion_reason'] = f"Mutual friends with {friend_friends[0].get('friend_username', 'a friend')}"
                        suggestions.append(friend_friend)
            
            return suggestions[:limit]
            
        except Exception as e:
            logger.error(f"Error getting mutual friend suggestions: {e}")
            return []
    
    def _get_similar_level_suggestions(self, user_id: str, limit: int) -> List[Dict[str, Any]]:
        """Get friend suggestions based on similar level."""
        try:
            # Get user's level
            from .user_manager import enhanced_user_manager
            user_profile = enhanced_user_manager.get_complete_user_profile(user_id)
            if not user_profile:
                return []
            
            user_level = user_profile.get('level', 1)
            level_range = 3
            
            # Get users with similar levels
            response = self.client.from_("user_profiles").select(
                "user_id, username, display_name, avatar_url, level, reputation_score"
            ).gte("level", user_level - level_range).lte("level", user_level + level_range).neq("user_id", user_id).limit(limit * 2).execute()
            
            suggestions = response.data or []
            
            # Add suggestion reason
            for suggestion in suggestions:
                suggestion['suggestion_reason'] = f"Similar level ({suggestion.get('level', 1)})"
            
            return suggestions[:limit]
            
        except Exception as e:
            logger.error(f"Error getting similar level suggestions: {e}")
            return []
    
    def _get_recently_active_suggestions(self, user_id: str, limit: int) -> List[Dict[str, Any]]:
        """Get friend suggestions based on recent activity."""
        try:
            # Get recently active users
            cutoff_date = (datetime.utcnow() - timedelta(days=7)).isoformat()
            
            response = self.client.from_("user_stats").select("""
                user_id, last_active,
                user_profiles!user_stats_user_id_fkey(username, display_name, avatar_url, level)
            """).gte("last_active", cutoff_date).neq("user_id", user_id).order("last_active", desc=True).limit(limit).execute()
            
            suggestions = []
            for item in response.data or []:
                if item.get('user_profiles'):
                    profile = item['user_profiles']
                    profile['user_id'] = item['user_id']
                    profile['suggestion_reason'] = "Recently active"
                    suggestions.append(profile)
            
            return suggestions
            
        except Exception as e:
            logger.error(f"Error getting recently active suggestions: {e}")
            return []
    
    # =====================================================
    # UTILITY METHODS
    # =====================================================
    
    def get_friendship_status(self, user1_id: str, user2_id: str) -> Optional[Dict[str, Any]]:
        """Get friendship status between two users.
        
        Args:
            user1_id: First user ID
            user2_id: Second user ID
            
        Returns:
            Friendship record or None
        """
        try:
            # Check both directions
            response = self.client.from_("friendships").select("*").or_(
                f"and(requester_id.eq.{user1_id},addressee_id.eq.{user2_id}),and(requester_id.eq.{user2_id},addressee_id.eq.{user1_id})"
            ).execute()
            
            return response.data[0] if response.data else None
            
        except Exception as e:
            logger.error(f"Error getting friendship status: {e}")
            return None
    
    def are_friends(self, user1_id: str, user2_id: str) -> bool:
        """Check if two users are friends.
        
        Args:
            user1_id: First user ID
            user2_id: Second user ID
            
        Returns:
            True if they are friends, False otherwise
        """
        friendship = self.get_friendship_status(user1_id, user2_id)
        return friendship and friendship.get('status') == FriendshipStatus.ACCEPTED.value
    
    def is_blocked(self, blocker_id: str, blocked_id: str) -> bool:
        """Check if a user is blocked by another user.
        
        Args:
            blocker_id: ID of potential blocker
            blocked_id: ID of potentially blocked user
            
        Returns:
            True if blocked, False otherwise
        """
        try:
            response = self.client.from_("friendships").select("id").eq("requester_id", blocker_id).eq("addressee_id", blocked_id).eq("status", FriendshipStatus.BLOCKED.value).execute()
            return len(response.data or []) > 0
        except Exception as e:
            logger.error(f"Error checking block status: {e}")
            return False
    
    def get_friend_count(self, user_id: str) -> int:
        """Get the number of friends a user has.
        
        Args:
            user_id: User ID
            
        Returns:
            Number of friends
        """
        try:
            response = self.client.from_("friendships").select("id", count="exact").or_(
                f"requester_id.eq.{user_id},addressee_id.eq.{user_id}"
            ).eq("status", FriendshipStatus.ACCEPTED.value).execute()
            
            return response.count or 0
            
        except Exception as e:
            logger.error(f"Error getting friend count: {e}")
            return 0
    
    def _get_user_online_status(self, user_id: str) -> bool:
        """Get user's online status (placeholder for real-time system)."""
        # This would be implemented with a real-time presence system
        # For now, return False as placeholder
        return False
    
    def _get_user_last_seen(self, user_id: str) -> Optional[str]:
        """Get user's last seen timestamp."""
        try:
            response = self.client.from_("user_stats").select("last_active").eq("user_id", user_id).single().execute()
            return response.data.get('last_active') if response.data else None
        except Exception as e:
            logger.error(f"Error getting last seen: {e}")
            return None
    
    def _create_friend_activity(self, user_id: str, activity_type: str, metadata: Dict[str, Any]):
        """Create a friend-related activity."""
        try:
            activity_data = {
                'user_id': user_id,
                'activity_type': activity_type,
                'title': self._get_activity_title(activity_type, metadata),
                'description': self._get_activity_description(activity_type, metadata),
                'metadata': metadata,
                'privacy_level': 'friends',
                'created_at': datetime.utcnow().isoformat()
            }
            
            self.client.from_("user_activities").insert(activity_data).execute()
            
        except Exception as e:
            logger.error(f"Error creating friend activity: {e}")
    
    def _create_friend_notification(self, user_id: str, notification_type: str, metadata: Dict[str, Any]):
        """Create a friend-related notification (placeholder)."""
        # This would be implemented with the notification system
        logger.info(f"Notification created for user {user_id}: {notification_type}")
    
    def _get_activity_title(self, activity_type: str, metadata: Dict[str, Any]) -> str:
        """Generate activity title based on type and metadata."""
        titles = {
            'friend_request_sent': f"Sent friend request to {metadata.get('target_username', 'someone')}",
            'friend_request_accepted': f"Accepted friend request from {metadata.get('friend_username', 'someone')}",
            'friend_added': f"Became friends with {metadata.get('friend_username', 'someone')}",
            'friend_removed': f"Removed {metadata.get('friend_username', 'someone')} from friends"
        }
        return titles.get(activity_type, "Friend activity")
    
    def _get_activity_description(self, activity_type: str, metadata: Dict[str, Any]) -> str:
        """Generate activity description based on type and metadata."""
        descriptions = {
            'friend_request_sent': "Sent a friend request",
            'friend_request_accepted': "Accepted a friend request",
            'friend_added': "Added a new friend",
            'friend_removed': "Removed a friend"
        }
        return descriptions.get(activity_type, "")

# Create a global instance
# Note: Global instance creation removed to prevent import-time initialization
# Use trackpro.social.friends_manager or trackpro.social.get_friends_manager() instead 