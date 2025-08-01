"""Content Manager for comprehensive content sharing and moderation system."""

import logging
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from enum import Enum
import json
from ..database.base import DatabaseManager
from ..database.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)

class ContentType(Enum):
    """Content type enumeration."""
    SETUP = "setup"
    IMAGE = "image"
    VIDEO = "video"
    REPLAY = "replay"
    TELEMETRY = "telemetry"
    GUIDE = "guide"

class ContentStatus(Enum):
    """Content status enumeration."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    FLAGGED = "flagged"

class PrivacyLevel(Enum):
    """Privacy level enumeration."""
    PUBLIC = "public"
    FRIENDS = "friends"
    PRIVATE = "private"

class ContentManager(DatabaseManager):
    """Comprehensive content sharing and moderation system."""
    
    def __init__(self):
        """Initialize the content manager."""
        super().__init__("shared_setups")
        self.supabase = get_supabase_client()
    
    # =====================================================
    # SETUP SHARING
    # =====================================================
    
    def share_setup(self, user_id: str, title: str, description: str, 
                   setup_data: Dict[str, Any], track_id: int = None, car_id: int = None,
                   category: str = None, tags: List[str] = None, 
                   privacy_level: PrivacyLevel = PrivacyLevel.PUBLIC) -> Optional[Dict[str, Any]]:
        """Share a car setup.
        
        Args:
            user_id: User ID sharing the setup
            title: Setup title
            description: Setup description
            setup_data: Setup configuration data
            track_id: Track ID the setup is for
            car_id: Car ID the setup is for
            category: Setup category (qualifying, race, etc.)
            tags: Setup tags
            privacy_level: Privacy level
            
        Returns:
            Created setup data or None
        """
        try:
            # Check user's reputation for content creation
            from .reputation_manager import reputation_manager
            user_standing = reputation_manager.get_user_standing(user_id)
            if not user_standing.get('can_create_content', True):
                logger.warning(f"User {user_id} cannot create content due to low reputation")
                return None
            
            # Create setup record
            setup_data_record = {
                'user_id': user_id,
                'title': title,
                'description': description,
                'setup_data': setup_data,
                'track_id': track_id,
                'car_id': car_id,
                'category': category,
                'tags': tags or [],
                'privacy_level': privacy_level.value,
                'status': ContentStatus.APPROVED.value,  # Auto-approve for now
                'download_count': 0,
                'rating_average': 0.0,
                'rating_count': 0,
                'created_at': datetime.utcnow().isoformat(),
                'updated_at': datetime.utcnow().isoformat()
            }
            
            response = self.client.from_("shared_setups").insert(setup_data_record).execute()
            if not response.data:
                return None
            
            setup = response.data[0]
            
            # Create activity
            self._create_content_activity(user_id, "setup_shared", {
                'content_id': setup['id'],
                'content_title': title,
                'content_type': ContentType.SETUP.value,
                'track_id': track_id,
                'car_id': car_id
            })
            
            # Award XP for content creation
            from .achievements_manager import achievements_manager, XPType
            achievements_manager.award_xp(user_id, 25, XPType.SOCIAL, f"Shared setup: {title}")
            
            logger.info(f"Setup '{title}' shared by user {user_id}")
            return setup
            
        except Exception as e:
            logger.error(f"Error sharing setup: {e}")
            return None
    
    def get_setup(self, setup_id: str, viewer_id: str = None) -> Optional[Dict[str, Any]]:
        """Get a setup by ID.
        
        Args:
            setup_id: Setup ID
            viewer_id: ID of user viewing the setup
            
        Returns:
            Setup data or None
        """
        try:
            response = self.client.from_("shared_setups").select("""
                *,
                user_profiles(username, display_name, avatar_url, level)
            """).eq("id", setup_id).single().execute()
            
            if not response.data:
                return None
            
            setup = response.data
            
            # Check privacy permissions
            if not self._can_view_content(setup, viewer_id):
                return None
            
            # Add user interaction data if viewer provided
            if viewer_id:
                setup['user_rating'] = self._get_user_rating(setup_id, viewer_id, 'setup')
                setup['user_downloaded'] = self._has_user_downloaded(setup_id, viewer_id)
            
            return setup
            
        except Exception as e:
            logger.error(f"Error getting setup: {e}")
            return None
    
    def search_setups(self, query: str = None, track_id: int = None, car_id: int = None,
                     category: str = None, tags: List[str] = None, 
                     sort_by: str = "created_at", limit: int = 20) -> List[Dict[str, Any]]:
        """Search for setups.
        
        Args:
            query: Search query
            track_id: Filter by track
            car_id: Filter by car
            category: Filter by category
            tags: Filter by tags
            sort_by: Sort field (created_at, rating_average, download_count)
            limit: Maximum number of results
            
        Returns:
            List of matching setups
        """
        try:
            query_builder = self.client.from_("shared_setups").select("""
                *,
                user_profiles(username, display_name, avatar_url, level)
            """).eq("privacy_level", PrivacyLevel.PUBLIC.value).eq("status", ContentStatus.APPROVED.value)
            
            if query:
                query_builder = query_builder.or_(f"title.ilike.%{query}%,description.ilike.%{query}%")
            
            if track_id:
                query_builder = query_builder.eq("track_id", track_id)
            
            if car_id:
                query_builder = query_builder.eq("car_id", car_id)
            
            if category:
                query_builder = query_builder.eq("category", category)
            
            if tags:
                for tag in tags:
                    query_builder = query_builder.contains("tags", [tag])
            
            # Sort options
            if sort_by == "rating_average":
                query_builder = query_builder.order("rating_average", desc=True)
            elif sort_by == "download_count":
                query_builder = query_builder.order("download_count", desc=True)
            else:
                query_builder = query_builder.order("created_at", desc=True)
            
            response = query_builder.limit(limit).execute()
            
            return response.data or []
            
        except Exception as e:
            logger.error(f"Error searching setups: {e}")
            return []
    
    def download_setup(self, setup_id: str, user_id: str) -> Dict[str, Any]:
        """Download a setup.
        
        Args:
            setup_id: Setup ID
            user_id: User ID downloading
            
        Returns:
            Dictionary with success status and setup data
        """
        try:
            # Get setup
            setup = self.get_setup(setup_id, user_id)
            if not setup:
                return {"success": False, "message": "Setup not found or not accessible"}
            
            # Check if already downloaded (to avoid duplicate counting)
            if not self._has_user_downloaded(setup_id, user_id):
                # Increment download count
                self.client.from_("shared_setups").update({
                    'download_count': setup['download_count'] + 1
                }).eq("id", setup_id).execute()
                
                # Record download
                download_record = {
                    'content_id': setup_id,
                    'content_type': ContentType.SETUP.value,
                    'user_id': user_id,
                    'downloaded_at': datetime.utcnow().isoformat()
                }
                
                # Note: This would require a content_downloads table
                # For now, we'll just log it
                logger.info(f"Setup {setup_id} downloaded by user {user_id}")
                
                # Award XP to setup creator
                from .achievements_manager import achievements_manager, XPType
                achievements_manager.award_xp(setup['user_id'], 5, XPType.SOCIAL, f"Setup downloaded: {setup['title']}")
            
            return {
                "success": True,
                "setup_data": setup['setup_data'],
                "message": "Setup downloaded successfully"
            }
            
        except Exception as e:
            logger.error(f"Error downloading setup: {e}")
            return {"success": False, "message": "Failed to download setup"}
    
    # =====================================================
    # MEDIA SHARING
    # =====================================================
    
    def share_media(self, user_id: str, title: str, description: str,
                   media_type: ContentType, file_url: str, thumbnail_url: str = None,
                   metadata: Dict[str, Any] = None, tags: List[str] = None,
                   privacy_level: PrivacyLevel = PrivacyLevel.PUBLIC) -> Optional[Dict[str, Any]]:
        """Share media content (images, videos, replays).
        
        Args:
            user_id: User ID sharing the media
            title: Media title
            description: Media description
            media_type: Type of media
            file_url: URL to the media file
            thumbnail_url: URL to thumbnail image
            metadata: Additional metadata
            tags: Media tags
            privacy_level: Privacy level
            
        Returns:
            Created media data or None
        """
        try:
            # Check user's reputation for content creation
            from .reputation_manager import reputation_manager
            user_standing = reputation_manager.get_user_standing(user_id)
            if not user_standing.get('can_create_content', True):
                logger.warning(f"User {user_id} cannot create content due to low reputation")
                return None
            
            # Create media record
            media_data = {
                'user_id': user_id,
                'title': title,
                'description': description,
                'content_type': media_type.value,
                'file_url': file_url,
                'thumbnail_url': thumbnail_url,
                'metadata': metadata or {},
                'tags': tags or [],
                'privacy_level': privacy_level.value,
                'status': ContentStatus.PENDING.value,  # Require moderation for media
                'view_count': 0,
                'like_count': 0,
                'comment_count': 0,
                'created_at': datetime.utcnow().isoformat(),
                'updated_at': datetime.utcnow().isoformat()
            }
            
            response = self.client.from_("shared_media").insert(media_data).execute()
            if not response.data:
                return None
            
            media = response.data[0]
            
            # Create activity (only if approved)
            if media_type in [ContentType.IMAGE, ContentType.VIDEO]:
                self._create_content_activity(user_id, "media_shared", {
                    'content_id': media['id'],
                    'content_title': title,
                    'content_type': media_type.value
                })
            
            # Award XP for content creation
            from .achievements_manager import achievements_manager, XPType
            xp_amounts = {
                ContentType.IMAGE.value: 15,
                ContentType.VIDEO.value: 30,
                ContentType.REPLAY.value: 20,
                ContentType.TELEMETRY.value: 25
            }
            xp_amount = xp_amounts.get(media_type.value, 15)
            achievements_manager.award_xp(user_id, xp_amount, XPType.SOCIAL, f"Shared {media_type.value}: {title}")
            
            logger.info(f"Media '{title}' ({media_type.value}) shared by user {user_id}")
            return media
            
        except Exception as e:
            logger.error(f"Error sharing media: {e}")
            return None
    
    def get_media(self, media_id: str, viewer_id: str = None) -> Optional[Dict[str, Any]]:
        """Get media by ID.
        
        Args:
            media_id: Media ID
            viewer_id: ID of user viewing the media
            
        Returns:
            Media data or None
        """
        try:
            response = self.client.from_("shared_media").select("""
                *,
                user_profiles(username, display_name, avatar_url, level)
            """).eq("id", media_id).single().execute()
            
            if not response.data:
                return None
            
            media = response.data
            
            # Check privacy permissions
            if not self._can_view_content(media, viewer_id):
                return None
            
            # Increment view count if viewer provided
            if viewer_id and viewer_id != media['user_id']:
                self.client.from_("shared_media").update({
                    'view_count': media['view_count'] + 1
                }).eq("id", media_id).execute()
                media['view_count'] += 1
            
            # Add user interaction data if viewer provided
            if viewer_id:
                media['user_liked'] = self._has_user_liked(media_id, viewer_id)
            
            return media
            
        except Exception as e:
            logger.error(f"Error getting media: {e}")
            return None
    
    def search_media(self, query: str = None, content_type: ContentType = None,
                    tags: List[str] = None, sort_by: str = "created_at", 
                    limit: int = 20) -> List[Dict[str, Any]]:
        """Search for media content.
        
        Args:
            query: Search query
            content_type: Filter by content type
            tags: Filter by tags
            sort_by: Sort field (created_at, view_count, like_count)
            limit: Maximum number of results
            
        Returns:
            List of matching media
        """
        try:
            query_builder = self.client.from_("shared_media").select("""
                *,
                user_profiles(username, display_name, avatar_url, level)
            """).eq("privacy_level", PrivacyLevel.PUBLIC.value).eq("status", ContentStatus.APPROVED.value)
            
            if query:
                query_builder = query_builder.or_(f"title.ilike.%{query}%,description.ilike.%{query}%")
            
            if content_type:
                query_builder = query_builder.eq("content_type", content_type.value)
            
            if tags:
                for tag in tags:
                    query_builder = query_builder.contains("tags", [tag])
            
            # Sort options
            if sort_by == "view_count":
                query_builder = query_builder.order("view_count", desc=True)
            elif sort_by == "like_count":
                query_builder = query_builder.order("like_count", desc=True)
            else:
                query_builder = query_builder.order("created_at", desc=True)
            
            response = query_builder.limit(limit).execute()
            
            return response.data or []
            
        except Exception as e:
            logger.error(f"Error searching media: {e}")
            return []
    
    # =====================================================
    # CONTENT INTERACTION
    # =====================================================
    
    def rate_content(self, content_id: str, user_id: str, rating: int, 
                    content_type: str = "setup") -> Dict[str, Any]:
        """Rate content (setups only for now).
        
        Args:
            content_id: Content ID
            user_id: User ID rating
            rating: Rating (1-5)
            content_type: Type of content
            
        Returns:
            Dictionary with success status
        """
        try:
            if rating < 1 or rating > 5:
                return {"success": False, "message": "Rating must be between 1 and 5"}
            
            # Check if user already rated this content
            existing_rating = self._get_user_rating(content_id, user_id, content_type)
            
            rating_data = {
                'content_id': content_id,
                'content_type': content_type,
                'user_id': user_id,
                'rating': rating,
                'created_at': datetime.utcnow().isoformat()
            }
            
            if existing_rating:
                # Update existing rating
                response = self.client.from_("content_ratings").update({
                    'rating': rating,
                    'updated_at': datetime.utcnow().isoformat()
                }).eq("content_id", content_id).eq("user_id", user_id).eq("content_type", content_type).execute()
            else:
                # Create new rating
                response = self.client.from_("content_ratings").insert(rating_data).execute()
            
            if response.data:
                # Update content average rating
                self._update_content_rating_average(content_id, content_type)
                
                logger.info(f"Content {content_id} rated {rating} by user {user_id}")
                return {"success": True, "message": "Rating submitted successfully"}
            
            return {"success": False, "message": "Failed to submit rating"}
            
        except Exception as e:
            logger.error(f"Error rating content: {e}")
            return {"success": False, "message": "Failed to submit rating"}
    
    def like_media(self, media_id: str, user_id: str) -> Dict[str, Any]:
        """Like or unlike media content.
        
        Args:
            media_id: Media ID
            user_id: User ID
            
        Returns:
            Dictionary with success status and like status
        """
        try:
            # Check if user already liked this media
            existing_like = self.client.from_("content_likes").select("id").eq("content_id", media_id).eq("user_id", user_id).eq("content_type", "media").execute()
            
            if existing_like.data:
                # Unlike
                self.client.from_("content_likes").delete().eq("id", existing_like.data[0]['id']).execute()
                
                # Decrement like count
                media_response = self.client.from_("shared_media").select("like_count").eq("id", media_id).single().execute()
                if media_response.data:
                    new_count = max(0, media_response.data['like_count'] - 1)
                    self.client.from_("shared_media").update({'like_count': new_count}).eq("id", media_id).execute()
                
                return {"success": True, "liked": False, "message": "Media unliked"}
            else:
                # Like
                like_data = {
                    'content_id': media_id,
                    'content_type': 'media',
                    'user_id': user_id,
                    'created_at': datetime.utcnow().isoformat()
                }
                
                response = self.client.from_("content_likes").insert(like_data).execute()
                if response.data:
                    # Increment like count
                    media_response = self.client.from_("shared_media").select("like_count").eq("id", media_id).single().execute()
                    if media_response.data:
                        new_count = media_response.data['like_count'] + 1
                        self.client.from_("shared_media").update({'like_count': new_count}).eq("id", media_id).execute()
                    
                    return {"success": True, "liked": True, "message": "Media liked"}
                
                return {"success": False, "message": "Failed to like media"}
            
        except Exception as e:
            logger.error(f"Error liking media: {e}")
            return {"success": False, "message": "Failed to like media"}
    
    # =====================================================
    # CONTENT MODERATION
    # =====================================================
    
    def flag_content(self, content_id: str, content_type: str, reporter_id: str, 
                    reason: str, details: str = "") -> Dict[str, Any]:
        """Flag content for moderation.
        
        Args:
            content_id: Content ID
            content_type: Type of content
            reporter_id: User ID reporting
            reason: Reason for flagging
            details: Additional details
            
        Returns:
            Dictionary with success status
        """
        try:
            # Check if user already flagged this content
            existing_flag = self.client.from_("content_flags").select("id").eq("content_id", content_id).eq("reporter_id", reporter_id).eq("content_type", content_type).execute()
            
            if existing_flag.data:
                return {"success": False, "message": "You have already flagged this content"}
            
            # Create flag record
            flag_data = {
                'content_id': content_id,
                'content_type': content_type,
                'reporter_id': reporter_id,
                'reason': reason,
                'details': details,
                'status': 'pending',
                'created_at': datetime.utcnow().isoformat()
            }
            
            response = self.client.from_("content_flags").insert(flag_data).execute()
            if response.data:
                # Update content status to flagged if multiple reports
                flag_count = len(self.client.from_("content_flags").select("id").eq("content_id", content_id).eq("content_type", content_type).execute().data or [])
                
                if flag_count >= 3:  # Auto-flag after 3 reports
                    table_name = "shared_setups" if content_type == "setup" else "shared_media"
                    self.client.from_(table_name).update({
                        'status': ContentStatus.FLAGGED.value
                    }).eq("id", content_id).execute()
                
                logger.info(f"Content {content_id} flagged by user {reporter_id} for {reason}")
                return {"success": True, "message": "Content flagged for review"}
            
            return {"success": False, "message": "Failed to flag content"}
            
        except Exception as e:
            logger.error(f"Error flagging content: {e}")
            return {"success": False, "message": "Failed to flag content"}
    
    def moderate_content(self, content_id: str, content_type: str, moderator_id: str,
                        action: str, reason: str = "") -> Dict[str, Any]:
        """Moderate content (approve/reject).
        
        Args:
            content_id: Content ID
            content_type: Type of content
            moderator_id: Moderator user ID
            action: Moderation action (approve/reject)
            reason: Reason for action
            
        Returns:
            Dictionary with success status
        """
        try:
            # Check if user can moderate
            from .reputation_manager import reputation_manager
            moderator_standing = reputation_manager.get_user_standing(moderator_id)
            if not moderator_standing.get('can_moderate', False):
                return {"success": False, "message": "Insufficient permissions to moderate content"}
            
            # Update content status
            new_status = ContentStatus.APPROVED.value if action == "approve" else ContentStatus.REJECTED.value
            table_name = "shared_setups" if content_type == "setup" else "shared_media"
            
            response = self.client.from_(table_name).update({
                'status': new_status,
                'moderated_by': moderator_id,
                'moderated_at': datetime.utcnow().isoformat(),
                'moderation_reason': reason
            }).eq("id", content_id).execute()
            
            if response.data:
                # Create moderation record
                moderation_data = {
                    'content_id': content_id,
                    'content_type': content_type,
                    'moderator_id': moderator_id,
                    'action': action,
                    'reason': reason,
                    'created_at': datetime.utcnow().isoformat()
                }
                
                # Note: This would require a content_moderations table
                logger.info(f"Content {content_id} {action}ed by moderator {moderator_id}")
                
                return {"success": True, "message": f"Content {action}ed successfully"}
            
            return {"success": False, "message": "Failed to moderate content"}
            
        except Exception as e:
            logger.error(f"Error moderating content: {e}")
            return {"success": False, "message": "Failed to moderate content"}
    
    # =====================================================
    # USER CONTENT MANAGEMENT
    # =====================================================
    
    def get_user_content(self, user_id: str, content_type: str = None, 
                        viewer_id: str = None) -> List[Dict[str, Any]]:
        """Get content created by a user.
        
        Args:
            user_id: User ID
            content_type: Filter by content type
            viewer_id: ID of user viewing the content
            
        Returns:
            List of user content
        """
        try:
            content = []
            
            # Get setups
            if not content_type or content_type == "setup":
                setup_query = self.client.from_("shared_setups").select("*").eq("user_id", user_id)
                
                # Apply privacy filter
                if viewer_id != user_id:
                    if viewer_id:
                        # Check if they are friends
                        from .friends_manager import friends_manager
                        if friends_manager.are_friends(user_id, viewer_id):
                            setup_query = setup_query.in_("privacy_level", [PrivacyLevel.PUBLIC.value, PrivacyLevel.FRIENDS.value])
                        else:
                            setup_query = setup_query.eq("privacy_level", PrivacyLevel.PUBLIC.value)
                    else:
                        setup_query = setup_query.eq("privacy_level", PrivacyLevel.PUBLIC.value)
                
                setups = setup_query.execute().data or []
                for setup in setups:
                    setup['content_type'] = 'setup'
                content.extend(setups)
            
            # Get media
            if not content_type or content_type in ["image", "video", "replay", "telemetry"]:
                media_query = self.client.from_("shared_media").select("*").eq("user_id", user_id)
                
                if content_type and content_type != "setup":
                    media_query = media_query.eq("content_type", content_type)
                
                # Apply privacy filter
                if viewer_id != user_id:
                    if viewer_id:
                        from .friends_manager import friends_manager
                        if friends_manager.are_friends(user_id, viewer_id):
                            media_query = media_query.in_("privacy_level", [PrivacyLevel.PUBLIC.value, PrivacyLevel.FRIENDS.value])
                        else:
                            media_query = media_query.eq("privacy_level", PrivacyLevel.PUBLIC.value)
                    else:
                        media_query = media_query.eq("privacy_level", PrivacyLevel.PUBLIC.value)
                
                media = media_query.execute().data or []
                content.extend(media)
            
            # Sort by creation date
            content.sort(key=lambda x: x['created_at'], reverse=True)
            
            return content
            
        except Exception as e:
            logger.error(f"Error getting user content: {e}")
            return []
    
    def delete_content(self, content_id: str, content_type: str, user_id: str) -> Dict[str, Any]:
        """Delete user's own content.
        
        Args:
            content_id: Content ID
            content_type: Type of content
            user_id: User ID (must be content owner)
            
        Returns:
            Dictionary with success status
        """
        try:
            table_name = "shared_setups" if content_type == "setup" else "shared_media"
            
            # Verify ownership
            content_response = self.client.from_(table_name).select("user_id").eq("id", content_id).single().execute()
            if not content_response.data or content_response.data['user_id'] != user_id:
                return {"success": False, "message": "Content not found or not owned by user"}
            
            # Delete content
            delete_response = self.client.from_(table_name).delete().eq("id", content_id).execute()
            
            if delete_response.data:
                logger.info(f"Content {content_id} deleted by user {user_id}")
                return {"success": True, "message": "Content deleted successfully"}
            
            return {"success": False, "message": "Failed to delete content"}
            
        except Exception as e:
            logger.error(f"Error deleting content: {e}")
            return {"success": False, "message": "Failed to delete content"}
    
    # =====================================================
    # UTILITY METHODS
    # =====================================================
    
    def _can_view_content(self, content: Dict[str, Any], viewer_id: str = None) -> bool:
        """Check if viewer can see the content.
        
        Args:
            content: Content data
            viewer_id: Viewer user ID
            
        Returns:
            True if can view, False otherwise
        """
        privacy_level = content.get('privacy_level', PrivacyLevel.FRIENDS.value)
        user_id = content.get('user_id')
        
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
    
    def _get_user_rating(self, content_id: str, user_id: str, content_type: str) -> Optional[int]:
        """Get user's rating for content.
        
        Args:
            content_id: Content ID
            user_id: User ID
            content_type: Content type
            
        Returns:
            User's rating or None
        """
        try:
            response = self.client.from_("content_ratings").select("rating").eq("content_id", content_id).eq("user_id", user_id).eq("content_type", content_type).single().execute()
            return response.data.get('rating') if response.data else None
        except Exception as e:
            logger.error(f"Error getting user rating: {e}")
            return None
    
    def _has_user_downloaded(self, content_id: str, user_id: str) -> bool:
        """Check if user has downloaded content.
        
        Args:
            content_id: Content ID
            user_id: User ID
            
        Returns:
            True if downloaded, False otherwise
        """
        try:
            # This would check a content_downloads table
            # For now, return False as placeholder
            return False
        except Exception as e:
            logger.error(f"Error checking download status: {e}")
            return False
    
    def _has_user_liked(self, content_id: str, user_id: str) -> bool:
        """Check if user has liked content.
        
        Args:
            content_id: Content ID
            user_id: User ID
            
        Returns:
            True if liked, False otherwise
        """
        try:
            response = self.client.from_("content_likes").select("id").eq("content_id", content_id).eq("user_id", user_id).eq("content_type", "media").execute()
            return len(response.data or []) > 0
        except Exception as e:
            logger.error(f"Error checking like status: {e}")
            return False
    
    def _update_content_rating_average(self, content_id: str, content_type: str):
        """Update content's average rating.
        
        Args:
            content_id: Content ID
            content_type: Content type
        """
        try:
            # Get all ratings for this content
            ratings_response = self.client.from_("content_ratings").select("rating").eq("content_id", content_id).eq("content_type", content_type).execute()
            
            ratings = [r['rating'] for r in ratings_response.data or []]
            
            if ratings:
                average_rating = sum(ratings) / len(ratings)
                rating_count = len(ratings)
                
                table_name = "shared_setups" if content_type == "setup" else "shared_media"
                self.client.from_(table_name).update({
                    'rating_average': round(average_rating, 2),
                    'rating_count': rating_count
                }).eq("id", content_id).execute()
                
        except Exception as e:
            logger.error(f"Error updating content rating average: {e}")
    
    def _create_content_activity(self, user_id: str, activity_type: str, metadata: Dict[str, Any]):
        """Create a content-related activity."""
        try:
            from .activity_manager import activity_manager, ActivityType
            
            activity_titles = {
                'setup_shared': f"Shared setup '{metadata.get('content_title', 'Unknown')}'",
                'media_shared': f"Shared {metadata.get('content_type', 'content')}: '{metadata.get('content_title', 'Unknown')}'"
            }
            
            activity_manager.create_activity(
                user_id=user_id,
                activity_type=ActivityType.CONTENT_SHARED,
                title=activity_titles.get(activity_type, "Shared content"),
                description=f"Content activity: {activity_type}",
                metadata=metadata
            )
            
        except Exception as e:
            logger.error(f"Error creating content activity: {e}")

# Create a global instance
# Note: Global instance creation removed to prevent import-time initialization
# Use trackpro.social.content_manager or trackpro.social.get_content_manager() instead