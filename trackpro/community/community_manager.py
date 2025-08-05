"""Community Manager for handling channels and messages."""

import logging
import threading
import traceback
from typing import List, Dict, Any, Optional
from datetime import datetime
from PyQt6.QtCore import QObject, pyqtSignal

logger = logging.getLogger(__name__)


class CommunityManager(QObject):
    """Manages community channels and messages with database integration."""
    
    # Singleton instance
    _instance = None
    _initialized = False
    _initialization_lock = threading.Lock()
    
    # Signals
    message_received = pyqtSignal(dict)  # New message received
    user_joined_channel = pyqtSignal(str, dict)  # channel_id, user_data
    user_left_channel = pyqtSignal(str, str)  # channel_id, user_id
    user_status_changed = pyqtSignal(str, str, dict)  # channel_id, user_id, status_data
    
    def __new__(cls):
        if cls._instance is None:
            with cls._initialization_lock:
                if cls._instance is None:
                    cls._instance = super(CommunityManager, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            with self._initialization_lock:
                if not self._initialized:
                    super().__init__()
                    self.current_user_id = None
                    self._setup_database_connection()
                    self._setup_realtime_subscriptions()
                    self._initialized = True
                    logger.info("✅ CommunityManager singleton initialized")
                else:
                    logger.debug("🔄 CommunityManager singleton already initialized, reusing instance")
        else:
            logger.debug("🔄 CommunityManager singleton already initialized, reusing instance")
    
    @classmethod
    def reset_instance(cls):
        """Reset the singleton instance (for testing purposes)."""
        with cls._initialization_lock:
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
    
    def get_current_user_id(self) -> Optional[str]:
        """Get the current authenticated user ID."""
        return self.current_user_id
    
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
                logger.warning("❌ No Supabase client available for getting messages")
                return []
            
            logger.info(f"🔍 Getting messages for channel {channel_id}")
            response = self.client.table("community_messages").select(
                "message_id, content, message_type, created_at, sender_id"
            ).eq("channel_id", channel_id).order("created_at", desc=False).limit(limit).execute()
            
            messages = response.data or []
            logger.info(f"📨 Retrieved {len(messages)} messages")
            
            # Try to get user display info from the public table first (no RLS restrictions)
            user_display_info = {}
            user_profiles = {}
            user_details = {}
            try:
                if messages:
                    sender_ids = list(set(msg.get('sender_id') for msg in messages if msg.get('sender_id')))
                    if sender_ids:
                        logger.info(f"🔍 Fetching user display info for {len(sender_ids)} sender IDs")
                        
                        # Try to get user display info from public_user_display_info table (no RLS)
                        try:
                            display_response = self.client.table("public_user_display_info").select(
                                "user_id, display_name, username, avatar_url"
                            ).in_("user_id", sender_ids).execute()
                            
                            user_display_info = {user['user_id']: user for user in (display_response.data or [])}
                            logger.info(f"✅ Retrieved {len(user_display_info)} user display info records")
                            
                        except Exception as display_error:
                            logger.warning(f"⚠️ Could not fetch user display info: {display_error}")
                        
                        # Fallback: Try to get user profiles from user_profiles table
                        if not user_display_info:
                            try:
                                user_response = self.client.table("user_profiles").select(
                                    "user_id, username, display_name, avatar_url"
                                ).in_("user_id", sender_ids).execute()
                                
                                user_profiles = {user['user_id']: user for user in (user_response.data or [])}
                                logger.info(f"✅ Retrieved {len(user_profiles)} user profiles")
                                
                            except Exception as profile_error:
                                logger.warning(f"⚠️ Could not fetch user profiles from user_profiles table: {profile_error}")
                            
                            # Try to get user details from user_details table
                            try:
                                details_response = self.client.table("user_details").select(
                                    "user_id, first_name, last_name"
                                ).in_("user_id", sender_ids).execute()
                                
                                user_details = {user['user_id']: user for user in (details_response.data or [])}
                                logger.info(f"✅ Retrieved {len(user_details)} user details")
                                
                            except Exception as details_error:
                                logger.warning(f"⚠️ Could not fetch user details from user_details table: {details_error}")
                        
                        # Log what we found
                        for user_id in sender_ids:
                            display_info = user_display_info.get(user_id, {})
                            profile = user_profiles.get(user_id, {})
                            details = user_details.get(user_id, {})
                            
                            # Generate display name from available data
                            display_name = self._generate_display_name(display_info, profile, details)
                            logger.info(f"  👤 {user_id}: {display_name}")
                            
            except Exception as e:
                logger.warning(f"⚠️ Could not fetch user data: {e}")
                # Continue without user data - we'll use fallback names
            
            # Add user data to messages
            for message in messages:
                sender_id = message.get('sender_id')
                if sender_id:
                    # Get user data from all tables
                    display_info = user_display_info.get(sender_id, {})
                    profile = user_profiles.get(sender_id, {})
                    details = user_details.get(sender_id, {})
                    
                    # Generate proper display name
                    display_name = self._generate_display_name(display_info, profile, details)
                    message['sender_name'] = display_name
                    message['user_display_info'] = display_info
                    message['user_profiles'] = profile
                    message['user_details'] = details
                    
                    logger.info(f"✅ Message {message.get('message_id')}: sender_name = {display_name}")
                else:
                    message['sender_name'] = 'Unknown'
                    logger.warning(f"⚠️ Message {message.get('message_id')}: No sender_id found")
            
            return messages
            
        except Exception as e:
            logger.error(f"❌ Error getting messages: {e}")
            return []
    
    def _generate_display_name(self, display_info: dict, profile: dict, details: dict) -> str:
        """Generate a display name from user display info, profile, and details data."""
        try:
            # Priority 1: Use display_name from public_user_display_info (no RLS restrictions)
            display_name = display_info.get('display_name', '')
            if display_name:
                return display_name
            
            # Priority 2: Use username from public_user_display_info
            username = display_info.get('username', '')
            if username:
                return username
            
            # Priority 3: Try first_name + last_name from user_details
            first_name = details.get('first_name', '')
            last_name = details.get('last_name', '')
            if first_name or last_name:
                full_name = f"{first_name} {last_name}".strip()
                if full_name:
                    return full_name
            
            # Priority 4: Try display_name from user_profiles
            display_name = profile.get('display_name', '')
            if display_name:
                return display_name
            
            # Priority 5: Try username from user_profiles
            username = profile.get('username', '')
            if username:
                return username
            
            # Priority 6: If we have a user_id, generate a fallback name
            user_id = display_info.get('user_id') or profile.get('user_id')
            if user_id:
                return self._generate_fallback_name(user_id)
            
            return "User"
            
        except Exception as e:
            logger.debug(f"Error generating display name: {e}")
            return "User"
    
    def _generate_fallback_name(self, sender_id: str) -> str:
        """Generate a fallback name for a sender_id when no user profile exists."""
        try:
            # Use a hash of the sender_id to generate a consistent name
            import hashlib
            hash_obj = hashlib.md5(sender_id.encode())
            hash_hex = hash_obj.hexdigest()[:8]
            
            # Generate a name based on the hash - more racing-themed names
            names = [
                "Racer", "Driver", "Speedster", "Champion", "Pilot", "RacerX", 
                "TrackMaster", "SpeedDemon", "RacingFan", "GearHead", "Turbo", 
                "Nitro", "Veloce", "Rapid", "Swift", "Fast", "Quick", "Zoom",
                "Rally", "Drift", "Circuit", "Formula", "GT", "LeMans", "Nascar",
                "F1", "Rally", "Drift", "Circuit", "Formula", "GT", "LeMans"
            ]
            
            name_index = int(hash_hex, 16) % len(names)
            base_name = names[name_index]
            
            # Add a number suffix for uniqueness (smaller range for better readability)
            number_suffix = int(hash_hex[4:8], 16) % 99 + 1
            
            return f"{base_name}{number_suffix}"
            
        except Exception as e:
            logger.debug(f"Error generating fallback name: {e}")
            return "Racer"
    
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
                            logger.info(f"🔍 Fetching complete message data for: {new_message.get('message_id')}")
                            # First get the message data
                            response = self.client.table("community_messages").select(
                                "message_id, content, message_type, created_at, sender_id"
                            ).eq("message_id", new_message['message_id']).execute()
                            
                            if response.data:
                                complete_message = response.data[0]
                                logger.info(f"✅ Retrieved complete message: {complete_message}")
                                # Fetch user data for this message
                                if complete_message.get('sender_id'):
                                    logger.info(f"👤 Fetching user data for sender_id: {complete_message['sender_id']}")
                                    user_response = self.client.table("user_profiles").select(
                                        "user_id, username, display_name, avatar_url"
                                    ).eq("user_id", complete_message['sender_id']).execute()
                                    
                                    if user_response.data:
                                        complete_message['user_profiles'] = user_response.data[0]
                                        # Also add sender_name for backward compatibility
                                        user_profile = user_response.data[0]
                                        complete_message['sender_name'] = user_profile.get('display_name') or user_profile.get('username') or 'Unknown'
                                        logger.info(f"✅ Fetched user data for real-time message: {user_response.data[0]}")
                                        logger.info(f"✅ Real-time message sender_name: {complete_message['sender_name']}")
                                    else:
                                        logger.warning(f"❌ No user data found for sender_id: {complete_message['sender_id']}")
                                        # Try to get from current user context
                                        try:
                                            from ..auth.user_manager import get_current_user
                                            user = get_current_user()
                                            if user and user.is_authenticated and complete_message.get('sender_id') == user.id:
                                                complete_message['sender_name'] = user.name or user.email or 'You'
                                                logger.info(f"✅ Real-time message sender_name: {complete_message['sender_name']} (from current user)")
                                            else:
                                                complete_message['sender_name'] = 'Unknown'
                                                logger.warning(f"❌ Real-time message sender_name: Unknown (no user profile or current user)")
                                        except Exception as e:
                                            logger.debug(f"Could not get current user for real-time message: {e}")
                                            complete_message['sender_name'] = 'Unknown'
                                            logger.warning(f"❌ Real-time message sender_name: Unknown (exception)")
                                logger.info(f"✅ Fetched complete message with sender info: {complete_message}")
                                self.message_received.emit(complete_message)
                            else:
                                logger.warning("❌ Could not fetch complete message data")
                                self.message_received.emit(new_message)
                        else:
                            logger.warning("❌ No client or message_id available for real-time message")
                            self.message_received.emit(new_message)
                    except Exception as fetch_error:
                        logger.error(f"❌ Error fetching complete message data: {fetch_error}")
                        import traceback
                        logger.debug(f"Traceback: {traceback.format_exc()}")
                        self.message_received.emit(new_message)
            
        except Exception as e:
            logger.error(f"❌ Error handling real-time message: {e}")
            import traceback
            logger.debug(f"Traceback: {traceback.format_exc()}")
    
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
            
            # Get conversations where current user is user1
            response1 = self.client.table("private_conversations").select(
                """
                conversation_id, created_at, updated_at,
                user1:user1_id(user_id, username, display_name, avatar_url),
                user2:user2_id(user_id, username, display_name, avatar_url)
                """
            ).eq("user1_id", self.current_user_id).execute()
            
            # Get conversations where current user is user2
            response2 = self.client.table("private_conversations").select(
                """
                conversation_id, created_at, updated_at,
                user1:user1_id(user_id, username, display_name, avatar_url),
                user2:user2_id(user_id, username, display_name, avatar_url)
                """
            ).eq("user2_id", self.current_user_id).execute()
            
            # Combine both results
            conversations = (response1.data or []) + (response2.data or [])
            
            # Sort by updated_at descending
            conversations.sort(key=lambda x: x.get('updated_at', ''), reverse=True)
            
            # Add last message and unread count for each conversation
            for conv in conversations:
                conv['last_message'] = self._get_last_private_message(conv['conversation_id'])
                conv['unread_count'] = self._get_unread_private_message_count(conv['conversation_id'])
                
                # Determine the other user in the conversation
                if conv.get('user1', {}).get('user_id') == self.current_user_id:
                    conv['other_user'] = conv.get('user2', {})
                else:
                    conv['other_user'] = conv.get('user1', {})
            
            return conversations
            
        except Exception as e:
            logger.error(f"Error getting private conversations: {e}")
            return []
    
    def get_user_id_by_username(self, username: str) -> Optional[str]:
        """Get user ID by username."""
        try:
            if not self.client:
                return None
            
            # Try public_user_display_info first (public table)
            response = self.client.table("public_user_display_info").select("user_id").eq("username", username).single().execute()
            
            if response.data:
                return response.data['user_id']
            
            # Fallback to user_profiles if not found in public table
            response = self.client.table("user_profiles").select("user_id").eq("username", username).single().execute()
            
            if response.data:
                return response.data['user_id']
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting user ID by username: {e}")
            return None
    
    def get_conversation_data(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """Get conversation data by conversation ID."""
        try:
            if not self.client or not self.current_user_id:
                return None
            
            response = self.client.table("private_conversations").select(
                """
                conversation_id, created_at, updated_at,
                user1:user1_id(user_id, username, display_name, avatar_url),
                user2:user2_id(user_id, username, display_name, avatar_url)
                """
            ).eq("conversation_id", conversation_id).execute()
            
            if not response.data or len(response.data) == 0:
                return None
            
            conversation_data = response.data[0]
            
            # Add last message and unread count
            conversation_data['last_message'] = self._get_last_private_message(conversation_id)
            conversation_data['unread_count'] = self._get_unread_private_message_count(conversation_id)
            
            # Determine the other user in the conversation
            if conversation_data.get('user1', {}).get('user_id') == self.current_user_id:
                conversation_data['other_user'] = conversation_data.get('user2', {})
            else:
                conversation_data['other_user'] = conversation_data.get('user1', {})
            
            return conversation_data
            
        except Exception as e:
            logger.error(f"Error getting conversation data: {e}")
            return None
    
    def get_or_create_conversation(self, other_user_identifier: str) -> Optional[str]:
        """Get existing conversation or create new one with another user.
        
        Args:
            other_user_identifier: Can be either a user ID or username
        """
        try:
            if not self.client or not self.current_user_id:
                return None
            
            # If the identifier looks like a UUID, treat it as a user ID
            # Otherwise, treat it as a username and look up the user ID
            if len(other_user_identifier) == 36 and '-' in other_user_identifier:
                other_user_id = other_user_identifier
            else:
                # Treat as username and look up user ID
                other_user_id = self.get_user_id_by_username(other_user_identifier)
                if not other_user_id:
                    logger.error(f"Could not find user with username: {other_user_identifier}")
                    return None
            
            # Check if conversation already exists - try both combinations
            # First, check if current user is user1 and other user is user2
            response = self.client.table("private_conversations").select("conversation_id").eq("user1_id", self.current_user_id).eq("user2_id", other_user_id).execute()
            
            if response.data:
                return response.data[0]['conversation_id']
            
            # Then, check if current user is user2 and other user is user1
            response = self.client.table("private_conversations").select("conversation_id").eq("user1_id", other_user_id).eq("user2_id", self.current_user_id).execute()
            
            if response.data:
                return response.data[0]['conversation_id']
            
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
            ).eq("conversation_id", conversation_id).order("created_at", desc=True).limit(1).execute()
            
            if response.data and len(response.data) > 0:
                return response.data[0]
            
            return None
            
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
    
    # Friend-related methods
    def get_friends(self) -> List[Dict[str, Any]]:
        """Get the current user's friends list."""
        try:
            if not self.client or not self.current_user_id:
                logger.warning(f"Cannot get friends: no database connection or user not authenticated. Client: {bool(self.client)}, User ID: {self.current_user_id}")
                return []
            
            logger.info(f"🔍 Getting friends for user: {self.current_user_id}")
            
            # Get accepted friendships where current user is either requester or addressee
            # Use two separate queries and combine results
            requester_response = self.client.table("friendships").select(
                "id, requester_id, addressee_id, status, created_at"
            ).eq("requester_id", self.current_user_id).eq("status", "accepted").execute()
            
            addressee_response = self.client.table("friendships").select(
                "id, requester_id, addressee_id, status, created_at"
            ).eq("addressee_id", self.current_user_id).eq("status", "accepted").execute()
            
            # Combine results
            friendships = []
            if requester_response.data:
                friendships.extend(requester_response.data)
            if addressee_response.data:
                friendships.extend(addressee_response.data)
            
            # Check for errors in either query
            if hasattr(requester_response, 'error') and requester_response.error:
                logger.error(f"Error getting requester friendships: {requester_response.error}")
            if hasattr(addressee_response, 'error') and addressee_response.error:
                logger.error(f"Error getting addressee friendships: {addressee_response.error}")
            logger.info(f"📋 Found {len(friendships)} friendships")
            
            if not friendships:
                return []
            
            # Get friend user IDs (exclude current user)
            friend_ids = []
            for friendship in friendships:
                if friendship['requester_id'] == self.current_user_id:
                    friend_ids.append(friendship['addressee_id'])
                else:
                    friend_ids.append(friendship['requester_id'])
            
            logger.info(f"👥 Friend IDs: {friend_ids}")
            
            if not friend_ids:
                return []
            
            # Get friend details from public_user_display_info
            friends_response = self.client.table("public_user_display_info").select(
                "user_id, display_name, username, avatar_url"
            ).in_("user_id", friend_ids).execute()
            
            if hasattr(friends_response, 'error') and friends_response.error:
                logger.error(f"Error getting friend details: {friends_response.error}")
                return []
            
            friends = friends_response.data
            logger.info(f"✅ Retrieved {len(friends)} friends with details")
            
            return friends
            
        except Exception as e:
            logger.error(f"Error getting friends: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return []
    
    def get_friend_requests(self) -> List[Dict[str, Any]]:
        """Get pending friend requests for the current user."""
        try:
            if not self.client or not self.current_user_id:
                logger.warning("Cannot get friend requests: no database connection or user not authenticated")
                return []
            
            # Get pending friend requests where current user is the addressee
            response = self.client.table("friendships").select(
                "id, requester_id, addressee_id, status, created_at"
            ).eq("addressee_id", self.current_user_id).eq("status", "pending").execute()
            
            if not response.data:
                return []
            
            # Get requester user profiles
            requester_ids = [req['requester_id'] for req in response.data]
            user_response = self.client.table("public_user_display_info").select(
                "user_id, display_name, username, avatar_url"
            ).in_("user_id", requester_ids).execute()
            
            requests = []
            for friendship in response.data:
                requester_id = friendship['requester_id']
                requester_profile = next((u for u in user_response.data or [] if u['user_id'] == requester_id), None)
                
                if requester_profile:
                    requests.append({
                        'friendship_id': friendship['id'],
                        'requester_id': requester_id,
                        'display_name': requester_profile.get('display_name') or requester_profile.get('username') or 'Unknown User',
                        'username': requester_profile.get('username'),
                        'status': 'Pending',
                        'avatar_url': requester_profile.get('avatar_url'),
                        'created_at': friendship['created_at']
                    })
            
            return requests
            
        except Exception as e:
            logger.error(f"Error getting friend requests: {e}")
            return []
    
    def send_friend_request(self, target_username: str) -> bool:
        """Send a friend request to a user by username."""
        try:
            if not self.client or not self.current_user_id:
                logger.warning("Cannot send friend request: no database connection or user not authenticated")
                return False
            
            # Get target user by username
            target_user_response = self.client.table("public_user_display_info").select("user_id").eq("username", target_username).execute()
            
            if not target_user_response.data:
                logger.warning(f"User with username '{target_username}' not found")
                return False
            
            target_user_id = target_user_response.data[0]['user_id']
            
            if target_user_id == self.current_user_id:
                logger.warning("Cannot send friend request to yourself")
                return False
            
            # Check if friendship already exists
            # Use two separate queries to check for existing friendships
            existing_response1 = self.client.table("friendships").select("id, status").eq("requester_id", self.current_user_id).eq("addressee_id", target_user_id).execute()
            existing_response2 = self.client.table("friendships").select("id, status").eq("requester_id", target_user_id).eq("addressee_id", self.current_user_id).execute()
            
            # Combine results
            existing_friendships = []
            if existing_response1.data:
                existing_friendships.extend(existing_response1.data)
            if existing_response2.data:
                existing_friendships.extend(existing_response2.data)
            
            if existing_friendships:
                logger.warning("Friendship already exists")
                return False
            
            # Create friend request
            friendship_data = {
                "requester_id": self.current_user_id,
                "addressee_id": target_user_id,
                "status": "pending"
            }
            
            response = self.client.table("friendships").insert(friendship_data).execute()
            
            if response.data:
                logger.info(f"Friend request sent to {target_username}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error sending friend request: {e}")
            return False
    
    def accept_friend_request(self, friendship_id: str) -> bool:
        """Accept a friend request."""
        try:
            if not self.client or not self.current_user_id:
                logger.warning("Cannot accept friend request: no database connection or user not authenticated")
                return False
            
            # Update friendship status to accepted
            response = self.client.table("friendships").update({"status": "accepted"}).eq("id", friendship_id).eq("addressee_id", self.current_user_id).execute()
            
            if response.data:
                logger.info(f"Friend request {friendship_id} accepted")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error accepting friend request: {e}")
            return False
    
    def decline_friend_request(self, friendship_id: str) -> bool:
        """Decline a friend request."""
        try:
            if not self.client or not self.current_user_id:
                logger.warning("Cannot decline friend request: no database connection or user not authenticated")
                return False
            
            # Delete the friendship record
            response = self.client.table("friendships").delete().eq("id", friendship_id).eq("addressee_id", self.current_user_id).execute()
            
            if response.data:
                logger.info(f"Friend request {friendship_id} declined")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error declining friend request: {e}")
            return False
    
    def remove_friend(self, friend_user_id: str) -> bool:
        """Remove a friend (delete friendship)."""
        try:
            if not self.client or not self.current_user_id:
                logger.warning("Cannot remove friend: no database connection or user not authenticated")
                return False
            
            # Delete the friendship record
            # Use two separate delete operations to handle both directions
            response1 = self.client.table("friendships").delete().eq("requester_id", self.current_user_id).eq("addressee_id", friend_user_id).execute()
            response2 = self.client.table("friendships").delete().eq("requester_id", friend_user_id).eq("addressee_id", self.current_user_id).execute()
            
            # Check if either deletion was successful
            response = response1 if response1.data else response2
            
            if response.data:
                logger.info(f"Friend {friend_user_id} removed")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error removing friend: {e}")
            return False 