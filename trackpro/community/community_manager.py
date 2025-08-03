"""Community Manager for handling channels and messages."""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from PyQt6.QtCore import QObject, pyqtSignal

logger = logging.getLogger(__name__)


class CommunityManager(QObject):
    """Manages community channels and messages with database integration."""
    
    # Signals
    message_received = pyqtSignal(dict)  # New message received
    user_joined_channel = pyqtSignal(str, dict)  # channel_id, user_data
    user_left_channel = pyqtSignal(str, str)  # channel_id, user_id
    user_status_changed = pyqtSignal(str, str, dict)  # channel_id, user_id, status_data
    
    def __init__(self):
        super().__init__()
        self.current_user_id = None
        self._setup_database_connection()
    
    def _setup_database_connection(self):
        """Setup database connection."""
        try:
            from ..database.supabase_client import get_supabase_client
            self.client = get_supabase_client()
        except Exception as e:
            logger.error(f"Failed to setup database connection: {e}")
            self.client = None
    
    def set_current_user(self, user_id: str):
        """Set the current authenticated user."""
        self.current_user_id = user_id
    
    def get_channels(self) -> List[Dict[str, Any]]:
        """Get all available channels."""
        try:
            if not self.client:
                return self._get_fallback_channels()
            
            response = self.client.table("community_channels").select(
                "channel_id, name, description, channel_type, is_private, created_at"
            ).order("name").execute()
            
            return response.data or []
            
        except Exception as e:
            logger.error(f"Error getting channels: {e}")
            return self._get_fallback_channels()
    
    def get_messages(self, channel_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get messages for a specific channel."""
        try:
            if not self.client:
                return []
            
            response = self.client.table("community_messages").select(
                """
                message_id, content, message_type, created_at,
                sender:sender_id(user_id, username, display_name, avatar_url)
                """
            ).eq("channel_id", channel_id).order("created_at", desc=True).limit(limit).execute()
            
            # Reverse to show oldest first
            messages = response.data or []
            messages.reverse()
            
            return messages
            
        except Exception as e:
            logger.error(f"Error getting messages for channel {channel_id}: {e}")
            return []
    
    def send_message(self, channel_id: str, content: str, message_type: str = "text") -> bool:
        """Send a message to a channel."""
        try:
            if not self.client or not self.current_user_id:
                logger.warning("Cannot send message: no database connection or user not authenticated")
                return False
            
            if not content.strip():
                return False
            
            message_data = {
                "channel_id": channel_id,
                "sender_id": self.current_user_id,
                "content": content.strip(),
                "message_type": message_type
            }
            
            response = self.client.table("community_messages").insert(message_data).execute()
            
            if response.data:
                # Emit signal for real-time updates
                self.message_received.emit(response.data[0])
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            return False
    
    def join_voice_channel(self, channel_id: str) -> bool:
        """Join a voice channel."""
        try:
            if not self.client or not self.current_user_id:
                return False
            
            # Check if already in channel
            existing = self.client.table("community_participants").select(
                "participant_id"
            ).eq("channel_id", channel_id).eq("user_id", self.current_user_id).eq("left_at", None).execute()
            
            if existing.data:
                return True  # Already in channel
            
            # Join the channel
            participant_data = {
                "channel_id": channel_id,
                "user_id": self.current_user_id,
                "is_muted": False,
                "is_deafened": False,
                "is_speaking": False
            }
            
            response = self.client.table("community_participants").insert(participant_data).execute()
            
            if response.data:
                # Send join message
                self.send_message(channel_id, f"joined the channel", "join")
                
                # Emit signal
                user_data = self._get_user_data(self.current_user_id)
                if user_data:
                    self.user_joined_channel.emit(channel_id, user_data)
                
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error joining voice channel: {e}")
            return False
    
    def leave_voice_channel(self, channel_id: str) -> bool:
        """Leave a voice channel."""
        try:
            if not self.client or not self.current_user_id:
                return False
            
            # Update participant record
            response = self.client.table("community_participants").update({
                "left_at": datetime.now().isoformat()
            }).eq("channel_id", channel_id).eq("user_id", self.current_user_id).eq("left_at", None).execute()
            
            if response.data:
                # Send leave message
                self.send_message(channel_id, f"left the channel", "leave")
                
                # Emit signal
                self.user_left_channel.emit(channel_id, self.current_user_id)
                
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error leaving voice channel: {e}")
            return False
    
    def get_voice_participants(self, channel_id: str) -> List[Dict[str, Any]]:
        """Get participants in a voice channel."""
        try:
            if not self.client:
                return []
            
            response = self.client.table("community_participants").select(
                """
                participant_id, joined_at, is_muted, is_deafened, is_speaking,
                user:user_id(user_id, username, display_name, avatar_url)
                """
            ).eq("channel_id", channel_id).eq("left_at", None).execute()
            
            return response.data or []
            
        except Exception as e:
            logger.error(f"Error getting voice participants: {e}")
            return []
    
    def update_voice_status(self, channel_id: str, is_muted: bool = None, 
                          is_deafened: bool = None, is_speaking: bool = None) -> bool:
        """Update voice status (muted, deafened, speaking)."""
        try:
            if not self.client or not self.current_user_id:
                return False
            
            update_data = {}
            if is_muted is not None:
                update_data["is_muted"] = is_muted
            if is_deafened is not None:
                update_data["is_deafened"] = is_deafened
            if is_speaking is not None:
                update_data["is_speaking"] = is_speaking
            
            if not update_data:
                return True
            
            response = self.client.table("community_participants").update(update_data).eq(
                "channel_id", channel_id
            ).eq("user_id", self.current_user_id).eq("left_at", None).execute()
            
            if response.data:
                # Emit status change signal
                status_data = {
                    "is_muted": is_muted if is_muted is not None else response.data[0].get("is_muted"),
                    "is_deafened": is_deafened if is_deafened is not None else response.data[0].get("is_deafened"),
                    "is_speaking": is_speaking if is_speaking is not None else response.data[0].get("is_speaking")
                }
                self.user_status_changed.emit(channel_id, self.current_user_id, status_data)
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error updating voice status: {e}")
            return False
    
    def _get_user_data(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user data by ID."""
        try:
            if not self.client:
                return None
            
            response = self.client.table("user_profiles").select(
                "user_id, username, display_name, avatar_url"
            ).eq("user_id", user_id).single().execute()
            
            return response.data
            
        except Exception as e:
            logger.error(f"Error getting user data: {e}")
            return None
    
    def _get_fallback_channels(self) -> List[Dict[str, Any]]:
        """Get fallback channels when database is unavailable."""
        return [
            {
                "channel_id": "general",
                "name": "general",
                "description": "General discussion for all TrackPro users",
                "channel_type": "text",
                "is_private": False,
                "created_at": datetime.now().isoformat()
            },
            {
                "channel_id": "racing",
                "name": "racing", 
                "description": "Racing tips, strategies, and discussions",
                "channel_type": "text",
                "is_private": False,
                "created_at": datetime.now().isoformat()
            },
            {
                "channel_id": "voice-general",
                "name": "voice-general",
                "description": "Voice channel for general chat",
                "channel_type": "voice",
                "is_private": False,
                "created_at": datetime.now().isoformat()
            },
            {
                "channel_id": "voice-racing",
                "name": "voice-racing",
                "description": "Voice channel for racing discussions", 
                "channel_type": "voice",
                "is_private": False,
                "created_at": datetime.now().isoformat()
            }
        ] 