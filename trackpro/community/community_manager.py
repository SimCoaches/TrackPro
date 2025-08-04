"""Community Manager for handling channels and messages."""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from PyQt6.QtCore import QObject, pyqtSignal

logger = logging.getLogger(__name__)


class CommunityManager(QObject):
    """Manages community channels and messages with database integration."""
    
    # Singleton instance
    _instance = None
    _initialized = False
    
    # Signals
    message_received = pyqtSignal(dict)  # New message received
    user_joined_channel = pyqtSignal(str, dict)  # channel_id, user_data
    user_left_channel = pyqtSignal(str, str)  # channel_id, user_id
    user_status_changed = pyqtSignal(str, str, dict)  # channel_id, user_id, status_data
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(CommunityManager, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            super().__init__()
            self.current_user_id = None
            self._setup_database_connection()
            self._setup_realtime_subscriptions()
            self._initialized = True
            logger.info("✅ CommunityManager singleton initialized")
        else:
            logger.debug("🔄 CommunityManager singleton already initialized, reusing instance")
    
    @classmethod
    def reset_instance(cls):
        """Reset the singleton instance (for testing purposes)."""
        cls._instance = None
        cls._initialized = False
        logger.info("🔄 CommunityManager singleton reset")
    
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
        logger.info(f"Setting current user ID: {user_id}")
        self.current_user_id = user_id
    
    def get_channels(self) -> List[Dict[str, Any]]:
        """Get all available channels."""
        try:
            if not self.client:
                logger.warning("No Supabase client available, using fallback channels")
                return self._get_fallback_channels()
            
            logger.info("Querying community_channels table from Supabase...")
            response = self.client.table("community_channels").select(
                "channel_id, name, description, channel_type, is_private, created_at"
            ).order("name").execute()
            
            channels = response.data or []
            logger.info(f"Retrieved {len(channels)} channels from database")
            
            if not channels:
                logger.warning("No channels found in database, using fallback channels")
                return self._get_fallback_channels()
            
            return channels
            
        except Exception as e:
            logger.error(f"Error getting channels: {e}")
            logger.info("Falling back to hardcoded channels due to error")
            return self._get_fallback_channels()
    
    def get_messages(self, channel_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get messages for a specific channel."""
        try:
            if not self.client:
                return []
            
            response = self.client.table("community_messages").select(
                "message_id, content, message_type, created_at, sender_id"
            ).eq("channel_id", channel_id).order("created_at", desc=True).limit(limit).execute()
            
            messages = response.data or []
            
            # Fetch user data for all messages
            if messages:
                sender_ids = list(set(msg['sender_id'] for msg in messages if msg.get('sender_id')))
                if sender_ids:
                    user_response = self.client.table("user_profiles").select(
                        "user_id, username, display_name, avatar_url"
                    ).in_("user_id", sender_ids).execute()
                    
                    users = {user['user_id']: user for user in (user_response.data or [])}
                    
                    # Merge user data into messages
                    for message in messages:
                        if message.get('sender_id') in users:
                            message['user_profiles'] = users[message['sender_id']]
                            # Also add sender_name for backward compatibility
                            user_profile = users[message['sender_id']]
                            message['sender_name'] = user_profile.get('display_name') or user_profile.get('username') or 'Unknown'
                        else:
                            # If no user profile found, try to get from current user context
                            try:
                                from ..auth.user_manager import get_current_user
                                user = get_current_user()
                                if user and user.is_authenticated and message.get('sender_id') == user.id:
                                    message['sender_name'] = user.name or user.email or 'You'
                                else:
                                    message['sender_name'] = 'Unknown'
                            except Exception as e:
                                logger.debug(f"Could not get current user for message: {e}")
                                message['sender_name'] = 'Unknown'
            
            # Reverse to show oldest first
            messages.reverse()
            
            return messages
            
        except Exception as e:
            logger.error(f"Error getting messages for channel {channel_id}: {e}")
            return []
    
    def send_message(self, channel_id: str, content: str, message_type: str = "text") -> bool:
        """Send a message to a channel."""
        try:
            logger.info(f"Attempting to send message to channel {channel_id}")
            logger.info(f"Client available: {self.client is not None}")
            logger.info(f"Current user ID: {self.current_user_id}")
            
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
            
            logger.info(f"Sending message data: {message_data}")
            response = self.client.table("community_messages").insert(message_data).execute()
            
            if response.data:
                logger.info(f"Message sent successfully: {response.data[0]}")
                
                # Fetch user data for the emitted message
                complete_message = response.data[0]
                try:
                    if complete_message.get('sender_id'):
                        user_response = self.client.table("user_profiles").select(
                            "user_id, username, display_name, avatar_url"
                        ).eq("user_id", complete_message['sender_id']).execute()
                        
                        if user_response.data:
                            complete_message['user_profiles'] = user_response.data[0]
                            # Also add sender_name for backward compatibility
                            user_profile = user_response.data[0]
                            complete_message['sender_name'] = user_profile.get('display_name') or user_profile.get('username') or 'Unknown'
                            logger.info(f"✅ Fetched user data for sent message: {user_response.data[0]}")
                        else:
                            logger.warning(f"No user data found for sender_id: {complete_message['sender_id']}")
                            # Try to get from current user context
                            try:
                                from ..auth.user_manager import get_current_user
                                user = get_current_user()
                                if user and user.is_authenticated and complete_message.get('sender_id') == user.id:
                                    complete_message['sender_name'] = user.name or user.email or 'You'
                                else:
                                    complete_message['sender_name'] = 'Unknown'
                            except Exception as e:
                                logger.debug(f"Could not get current user for sent message: {e}")
                                complete_message['sender_name'] = 'Unknown'
                except Exception as user_error:
                    logger.error(f"Error fetching user data for sent message: {user_error}")
                    complete_message['sender_name'] = 'Unknown'
                
                # Emit signal for real-time updates
                self.message_received.emit(complete_message)
                return True
            
            logger.warning("No response data from message insert")
            return False
            
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            return False
    
    def _setup_realtime_subscriptions(self):
        """Setup real-time subscriptions for messages."""
        try:
            if not self.client:
                logger.warning("Cannot setup real-time subscriptions: no database connection")
                return
            
            # TODO: Implement real-time subscriptions when Supabase real-time is properly configured
            # For now, we'll use polling or manual refresh instead
            logger.info("⚠️ Real-time subscriptions disabled - using polling instead")
            
        except Exception as e:
            logger.error(f"Failed to setup real-time subscriptions: {e}")
    
    def _on_message_inserted(self, payload):
        """Handle new message inserted via real-time subscription."""
        try:
            logger.info(f"🔄 Real-time message received: {payload}")
            
            if payload.get('eventType') == 'INSERT':
                new_message = payload.get('new', {})
                if new_message:
                    # Real-time subscriptions don't include joined data by default
                    # We need to fetch the complete message with sender info
                    try:
                        if self.client and new_message.get('message_id'):
                            # First get the message data
                            response = self.client.table("community_messages").select(
                                "message_id, content, message_type, created_at, sender_id"
                            ).eq("message_id", new_message['message_id']).execute()
                            
                            if response.data:
                                complete_message = response.data[0]
                                # Fetch user data for this message
                                if complete_message.get('sender_id'):
                                    user_response = self.client.table("user_profiles").select(
                                        "user_id, username, display_name, avatar_url"
                                    ).eq("user_id", complete_message['sender_id']).execute()
                                    
                                    if user_response.data:
                                        complete_message['user_profiles'] = user_response.data[0]
                                        # Also add sender_name for backward compatibility
                                        user_profile = user_response.data[0]
                                        complete_message['sender_name'] = user_profile.get('display_name') or user_profile.get('username') or 'Unknown'
                                        logger.info(f"✅ Fetched user data for real-time message: {user_response.data[0]}")
                                    else:
                                        logger.warning(f"No user data found for sender_id: {complete_message['sender_id']}")
                                        # Try to get from current user context
                                        try:
                                            from ..auth.user_manager import get_current_user
                                            user = get_current_user()
                                            if user and user.is_authenticated and complete_message.get('sender_id') == user.id:
                                                complete_message['sender_name'] = user.name or user.email or 'You'
                                            else:
                                                complete_message['sender_name'] = 'Unknown'
                                        except Exception as e:
                                            logger.debug(f"Could not get current user for real-time message: {e}")
                                            complete_message['sender_name'] = 'Unknown'
                                logger.info(f"✅ Fetched complete message with sender info: {complete_message}")
                                self.message_received.emit(complete_message)
                            else:
                                logger.warning("Could not fetch complete message data")
                                self.message_received.emit(new_message)
                        else:
                            logger.warning("No client or message_id available for real-time message")
                            self.message_received.emit(new_message)
                    except Exception as fetch_error:
                        logger.error(f"Error fetching complete message data: {fetch_error}")
                        self.message_received.emit(new_message)
            
        except Exception as e:
            logger.error(f"Error handling real-time message: {e}")
    
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
    
    # Private Messaging Methods
    
    def get_private_conversations(self) -> List[Dict[str, Any]]:
        """Get all private conversations for the current user."""
        try:
            if not self.client or not self.current_user_id:
                return []
            
            response = self.client.table("private_conversations").select(
                """
                conversation_id, created_at, updated_at,
                user1:user1_id(user_id, username, display_name, avatar_url),
                user2:user2_id(user_id, username, display_name, avatar_url)
                """
            ).or_(f"user1_id.eq.{self.current_user_id},user2_id.eq.{self.current_user_id}").order("updated_at", desc=True).execute()
            
            conversations = response.data or []
            
            # Add last message and unread count for each conversation
            for conv in conversations:
                conv['last_message'] = self._get_last_private_message(conv['conversation_id'])
                conv['unread_count'] = self._get_unread_private_message_count(conv['conversation_id'])
                
                # Determine the other user in the conversation
                if conv['user1']['user_id'] == self.current_user_id:
                    conv['other_user'] = conv['user2']
                else:
                    conv['other_user'] = conv['user1']
            
            return conversations
            
        except Exception as e:
            logger.error(f"Error getting private conversations: {e}")
            return []
    
    def get_or_create_conversation(self, other_user_id: str) -> Optional[str]:
        """Get existing conversation or create new one with another user."""
        try:
            if not self.client or not self.current_user_id:
                return None
            
            # Check if conversation already exists
            response = self.client.table("private_conversations").select("conversation_id").or_(
                f"and(user1_id.eq.{self.current_user_id},user2_id.eq.{other_user_id}),and(user1_id.eq.{other_user_id},user2_id.eq.{self.current_user_id})"
            ).single().execute()
            
            if response.data:
                return response.data['conversation_id']
            
            # Create new conversation
            conversation_data = {
                "user1_id": self.current_user_id,
                "user2_id": other_user_id
            }
            
            response = self.client.table("private_conversations").insert(conversation_data).execute()
            
            if response.data:
                return response.data[0]['conversation_id']
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting or creating conversation: {e}")
            return None
    
    def get_private_messages(self, conversation_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get messages for a private conversation."""
        try:
            if not self.client:
                return []
            
            response = self.client.table("private_messages").select(
                "message_id, content, created_at, sender_id"
            ).eq("conversation_id", conversation_id).order("created_at", desc=True).limit(limit).execute()
            
            messages = response.data or []
            
            # Fetch user data for all messages
            if messages:
                sender_ids = list(set(msg['sender_id'] for msg in messages if msg.get('sender_id')))
                if sender_ids:
                    user_response = self.client.table("user_profiles").select(
                        "user_id, username, display_name, avatar_url"
                    ).in_("user_id", sender_ids).execute()
                    
                    users = {user['user_id']: user for user in (user_response.data or [])}
                    
                    # Merge user data into messages
                    for message in messages:
                        if message.get('sender_id') in users:
                            message['user_profiles'] = users[message['sender_id']]
            
            # Reverse to show oldest first
            messages.reverse()
            
            return messages
            
        except Exception as e:
            logger.error(f"Error getting private messages: {e}")
            return []
    
    def send_private_message(self, conversation_id: str, content: str) -> bool:
        """Send a message in a private conversation."""
        try:
            if not self.client or not self.current_user_id:
                logger.warning("Cannot send private message: no database connection or user not authenticated")
                return False
            
            if not content.strip():
                return False
            
            message_data = {
                "conversation_id": conversation_id,
                "sender_id": self.current_user_id,
                "content": content.strip()
            }
            
            response = self.client.table("private_messages").insert(message_data).execute()
            
            if response.data:
                # Update conversation's updated_at timestamp
                self.client.table("private_conversations").update({"updated_at": datetime.now().isoformat()}).eq("conversation_id", conversation_id).execute()
                
                # Emit signal for real-time updates
                self.message_received.emit(response.data[0])
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error sending private message: {e}")
            return False
    
    def mark_private_messages_as_read(self, conversation_id: str) -> bool:
        """Mark all messages in a conversation as read."""
        try:
            if not self.client or not self.current_user_id:
                return False
            
            response = self.client.table("private_messages").update({"is_read": True}).eq(
                "conversation_id", conversation_id
            ).neq("sender_id", self.current_user_id).eq("is_read", False).execute()
            
            return True
            
        except Exception as e:
            logger.error(f"Error marking messages as read: {e}")
            return False
    
    def _get_last_private_message(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """Get the last message in a private conversation."""
        try:
            if not self.client:
                return None
            
            response = self.client.table("private_messages").select(
                "content, created_at"
            ).eq("conversation_id", conversation_id).order("created_at", desc=True).limit(1).single().execute()
            
            return response.data
            
        except Exception as e:
            logger.error(f"Error getting last private message: {e}")
            return None
    
    def _get_unread_private_message_count(self, conversation_id: str) -> int:
        """Get the number of unread messages in a conversation."""
        try:
            if not self.client or not self.current_user_id:
                return 0
            
            response = self.client.table("private_messages").select("message_id", count="exact").eq(
                "conversation_id", conversation_id
            ).neq("sender_id", self.current_user_id).eq("is_read", False).execute()
            
            return response.count or 0
            
        except Exception as e:
            logger.error(f"Error getting unread message count: {e}")
            return 0 