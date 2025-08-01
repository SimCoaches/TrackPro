"""Messaging Manager for comprehensive chat and messaging functionality."""

import logging
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from enum import Enum
import json
from ..database.base import DatabaseManager
from ..database.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)

class ConversationType(Enum):
    """Conversation type enumeration."""
    DIRECT = "direct"
    GROUP = "group"

class MessageType(Enum):
    """Message type enumeration."""
    TEXT = "text"
    IMAGE = "image"
    FILE = "file"
    TELEMETRY = "telemetry"
    SYSTEM = "system"

class MessagingManager(DatabaseManager):
    """Comprehensive messaging and chat system."""
    
    def __init__(self):
        """Initialize the messaging manager."""
        super().__init__("conversations")
        self.supabase = get_supabase_client()
    
    # =====================================================
    # CONVERSATION MANAGEMENT
    # =====================================================
    
    def create_direct_conversation(self, user1_id: str, user2_id: str) -> Optional[Dict[str, Any]]:
        """Create or get existing direct conversation between two users.
        
        Args:
            user1_id: First user ID
            user2_id: Second user ID
            
        Returns:
            Conversation data or None
        """
        try:
            # Check if conversation already exists
            existing_conv = self.get_direct_conversation(user1_id, user2_id)
            if existing_conv:
                return existing_conv
            
            # Verify users are friends or can message each other
            from .friends_manager import friends_manager
            if not friends_manager.are_friends(user1_id, user2_id):
                # Check privacy settings
                from .user_manager import enhanced_user_manager
                user2_profile = enhanced_user_manager.get_complete_user_profile(user2_id)
                if user2_profile:
                    privacy_settings = user2_profile.get('privacy_settings', {})
                    message_setting = privacy_settings.get('messages', 'friends')
                    if message_setting == 'none' or (message_setting == 'friends' and not friends_manager.are_friends(user1_id, user2_id)):
                        logger.warning(f"User {user1_id} cannot message {user2_id} due to privacy settings")
                        return None
            
            # Create new conversation
            conversation_data = {
                'type': ConversationType.DIRECT.value,
                'created_by': user1_id,
                'created_at': datetime.utcnow().isoformat(),
                'updated_at': datetime.utcnow().isoformat()
            }
            
            response = self.client.from_("conversations").insert(conversation_data).execute()
            if not response.data:
                return None
            
            conversation = response.data[0]
            conversation_id = conversation['id']
            
            # Add participants
            participants = [
                {
                    'conversation_id': conversation_id,
                    'user_id': user1_id,
                    'joined_at': datetime.utcnow().isoformat(),
                    'last_read_at': datetime.utcnow().isoformat()
                },
                {
                    'conversation_id': conversation_id,
                    'user_id': user2_id,
                    'joined_at': datetime.utcnow().isoformat(),
                    'last_read_at': datetime.utcnow().isoformat()
                }
            ]
            
            self.client.from_("conversation_participants").insert(participants).execute()
            
            logger.info(f"Direct conversation created between {user1_id} and {user2_id}")
            return conversation
            
        except Exception as e:
            logger.error(f"Error creating direct conversation: {e}")
            return None
    
    def create_group_conversation(self, creator_id: str, name: str, participant_ids: List[str]) -> Optional[Dict[str, Any]]:
        """Create a group conversation.
        
        Args:
            creator_id: ID of user creating the group
            name: Group name
            participant_ids: List of participant user IDs
            
        Returns:
            Conversation data or None
        """
        try:
            # Validate participants
            if len(participant_ids) < 2:
                logger.warning("Group conversation needs at least 2 participants")
                return None
            
            if len(participant_ids) > 50:  # Limit group size
                logger.warning("Group conversation cannot have more than 50 participants")
                return None
            
            # Create conversation
            conversation_data = {
                'type': ConversationType.GROUP.value,
                'name': name,
                'created_by': creator_id,
                'created_at': datetime.utcnow().isoformat(),
                'updated_at': datetime.utcnow().isoformat()
            }
            
            response = self.client.from_("conversations").insert(conversation_data).execute()
            if not response.data:
                return None
            
            conversation = response.data[0]
            conversation_id = conversation['id']
            
            # Add creator and participants
            all_participants = list(set([creator_id] + participant_ids))
            participants = []
            
            for user_id in all_participants:
                participants.append({
                    'conversation_id': conversation_id,
                    'user_id': user_id,
                    'joined_at': datetime.utcnow().isoformat(),
                    'last_read_at': datetime.utcnow().isoformat()
                })
            
            self.client.from_("conversation_participants").insert(participants).execute()
            
            # Send system message about group creation
            self.send_system_message(conversation_id, f"Group '{name}' created by {creator_id}")
            
            logger.info(f"Group conversation '{name}' created by {creator_id}")
            return conversation
            
        except Exception as e:
            logger.error(f"Error creating group conversation: {e}")
            return None
    
    def get_direct_conversation(self, user1_id: str, user2_id: str) -> Optional[Dict[str, Any]]:
        """Get existing direct conversation between two users.
        
        Args:
            user1_id: First user ID
            user2_id: Second user ID
            
        Returns:
            Conversation data or None
        """
        try:
            # Find conversation where both users are participants
            response = self.client.from_("conversations").select("""
                *,
                conversation_participants!inner(user_id)
            """).eq("type", ConversationType.DIRECT.value).execute()
            
            for conversation in response.data or []:
                participant_ids = {p['user_id'] for p in conversation['conversation_participants']}
                if {user1_id, user2_id} == participant_ids:
                    return conversation
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting direct conversation: {e}")
            return None
    
    def get_user_conversations(self, user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get all conversations for a user.
        
        Args:
            user_id: User ID
            limit: Maximum number of conversations
            
        Returns:
            List of conversations with metadata
        """
        try:
            response = self.client.from_("conversation_participants").select("""
                conversation_id, last_read_at,
                conversations!inner(
                    id, type, name, created_by, created_at, updated_at
                )
            """).eq("user_id", user_id).order("conversations(updated_at)", desc=True).limit(limit).execute()
            
            conversations = []
            for item in response.data or []:
                conv = item['conversations']
                conv['last_read_at'] = item['last_read_at']
                
                # Get other participants for direct conversations
                if conv['type'] == ConversationType.DIRECT.value:
                    other_participant = self._get_other_participant(conv['id'], user_id)
                    if other_participant:
                        conv['other_participant'] = other_participant
                
                # Get last message
                last_message = self.get_last_message(conv['id'])
                if last_message:
                    conv['last_message'] = last_message
                
                # Get unread count
                conv['unread_count'] = self.get_unread_count(conv['id'], user_id)
                
                conversations.append(conv)
            
            return conversations
            
        except Exception as e:
            logger.error(f"Error getting user conversations: {e}")
            return []
    
    # =====================================================
    # MESSAGE MANAGEMENT
    # =====================================================
    
    def send_message(self, conversation_id: str, sender_id: str, content: str, 
                    message_type: MessageType = MessageType.TEXT, metadata: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
        """Send a message in a conversation.
        
        Args:
            conversation_id: Conversation ID
            sender_id: Sender user ID
            content: Message content
            message_type: Type of message
            metadata: Additional message metadata
            
        Returns:
            Message data or None
        """
        try:
            # Verify sender is participant
            if not self.is_participant(conversation_id, sender_id):
                logger.warning(f"User {sender_id} is not a participant in conversation {conversation_id}")
                return None
            
            # Create message
            message_data = {
                'conversation_id': conversation_id,
                'sender_id': sender_id,
                'content': content,
                'message_type': message_type.value,
                'metadata': metadata or {},
                'created_at': datetime.utcnow().isoformat()
            }
            
            response = self.client.from_("messages").insert(message_data).execute()
            if not response.data:
                return None
            
            message = response.data[0]
            
            # Update conversation timestamp
            self.client.from_("conversations").update({
                'updated_at': datetime.utcnow().isoformat()
            }).eq("id", conversation_id).execute()
            
            # Update sender's last read timestamp
            self.update_last_read(conversation_id, sender_id)
            
            # Create activity for message sent
            self._create_message_activity(sender_id, "message_sent", {
                'conversation_id': conversation_id,
                'message_type': message_type.value
            })
            
            logger.info(f"Message sent in conversation {conversation_id} by {sender_id}")
            return message
            
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            return None
    
    def send_system_message(self, conversation_id: str, content: str) -> Optional[Dict[str, Any]]:
        """Send a system message in a conversation.
        
        Args:
            conversation_id: Conversation ID
            content: System message content
            
        Returns:
            Message data or None
        """
        try:
            message_data = {
                'conversation_id': conversation_id,
                'sender_id': None,  # System messages have no sender
                'content': content,
                'message_type': MessageType.SYSTEM.value,
                'metadata': {},
                'created_at': datetime.utcnow().isoformat()
            }
            
            response = self.client.from_("messages").insert(message_data).execute()
            return response.data[0] if response.data else None
            
        except Exception as e:
            logger.error(f"Error sending system message: {e}")
            return None
    
    def get_messages(self, conversation_id: str, user_id: str, limit: int = 50, 
                    before_message_id: str = None) -> List[Dict[str, Any]]:
        """Get messages from a conversation.
        
        Args:
            conversation_id: Conversation ID
            user_id: User ID requesting messages
            limit: Maximum number of messages
            before_message_id: Get messages before this message ID (for pagination)
            
        Returns:
            List of messages
        """
        try:
            # Verify user is participant
            if not self.is_participant(conversation_id, user_id):
                logger.warning(f"User {user_id} is not a participant in conversation {conversation_id}")
                return []
            
            query = self.client.from_("messages").select("""
                *,
                user_profiles(username, display_name, avatar_url)
            """).eq("conversation_id", conversation_id).order("created_at", desc=True).limit(limit)
            
            if before_message_id:
                # Get timestamp of the before message for pagination
                before_response = self.client.from_("messages").select("created_at").eq("id", before_message_id).single().execute()
                if before_response.data:
                    query = query.lt("created_at", before_response.data['created_at'])
            
            response = query.execute()
            messages = response.data or []
            
            # Reverse to get chronological order
            messages.reverse()
            
            return messages
            
        except Exception as e:
            logger.error(f"Error getting messages: {e}")
            return []
    
    def get_last_message(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """Get the last message in a conversation.
        
        Args:
            conversation_id: Conversation ID
            
        Returns:
            Last message or None
        """
        try:
            response = self.client.from_("messages").select("""
                *,
                user_profiles(username, display_name)
            """).eq("conversation_id", conversation_id).order("created_at", desc=True).limit(1).execute()
            
            return response.data[0] if response.data else None
            
        except Exception as e:
            logger.error(f"Error getting last message: {e}")
            return None
    
    def edit_message(self, message_id: str, user_id: str, new_content: str) -> bool:
        """Edit a message (only by sender within time limit).
        
        Args:
            message_id: Message ID
            user_id: User ID attempting to edit
            new_content: New message content
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get message
            response = self.client.from_("messages").select("*").eq("id", message_id).single().execute()
            if not response.data:
                return False
            
            message = response.data
            
            # Verify sender
            if message['sender_id'] != user_id:
                logger.warning(f"User {user_id} cannot edit message {message_id} - not the sender")
                return False
            
            # Check time limit (e.g., 15 minutes)
            message_time = datetime.fromisoformat(message['created_at'].replace('Z', '+00:00'))
            time_limit = datetime.utcnow().replace(tzinfo=message_time.tzinfo) - timedelta(minutes=15)
            
            if message_time < time_limit:
                logger.warning(f"Message {message_id} is too old to edit")
                return False
            
            # Update message
            update_response = self.client.from_("messages").update({
                'content': new_content,
                'edited_at': datetime.utcnow().isoformat()
            }).eq("id", message_id).execute()
            
            return bool(update_response.data)
            
        except Exception as e:
            logger.error(f"Error editing message: {e}")
            return False
    
    def delete_message(self, message_id: str, user_id: str) -> bool:
        """Delete a message (only by sender).
        
        Args:
            message_id: Message ID
            user_id: User ID attempting to delete
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get message
            response = self.client.from_("messages").select("*").eq("id", message_id).single().execute()
            if not response.data:
                return False
            
            message = response.data
            
            # Verify sender
            if message['sender_id'] != user_id:
                logger.warning(f"User {user_id} cannot delete message {message_id} - not the sender")
                return False
            
            # Soft delete by updating deleted_at
            update_response = self.client.from_("messages").update({
                'deleted_at': datetime.utcnow().isoformat()
            }).eq("id", message_id).execute()
            
            return bool(update_response.data)
            
        except Exception as e:
            logger.error(f"Error deleting message: {e}")
            return False
    
    # =====================================================
    # PARTICIPANT MANAGEMENT
    # =====================================================
    
    def add_participant(self, conversation_id: str, user_id: str, added_by: str) -> bool:
        """Add a participant to a group conversation.
        
        Args:
            conversation_id: Conversation ID
            user_id: User ID to add
            added_by: User ID who is adding the participant
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get conversation
            conv_response = self.client.from_("conversations").select("*").eq("id", conversation_id).single().execute()
            if not conv_response.data:
                return False
            
            conversation = conv_response.data
            
            # Only allow adding to group conversations
            if conversation['type'] != ConversationType.GROUP.value:
                logger.warning(f"Cannot add participant to direct conversation {conversation_id}")
                return False
            
            # Verify adder is participant
            if not self.is_participant(conversation_id, added_by):
                logger.warning(f"User {added_by} cannot add participants - not in conversation")
                return False
            
            # Check if user is already participant
            if self.is_participant(conversation_id, user_id):
                logger.warning(f"User {user_id} is already a participant in conversation {conversation_id}")
                return False
            
            # Add participant
            participant_data = {
                'conversation_id': conversation_id,
                'user_id': user_id,
                'joined_at': datetime.utcnow().isoformat(),
                'last_read_at': datetime.utcnow().isoformat()
            }
            
            response = self.client.from_("conversation_participants").insert(participant_data).execute()
            if not response.data:
                return False
            
            # Send system message
            from .user_manager import enhanced_user_manager
            added_user = enhanced_user_manager.get_complete_user_profile(user_id)
            added_by_user = enhanced_user_manager.get_complete_user_profile(added_by)
            
            username = added_user.get('username', 'Unknown') if added_user else 'Unknown'
            added_by_username = added_by_user.get('username', 'Unknown') if added_by_user else 'Unknown'
            
            self.send_system_message(conversation_id, f"{username} was added to the group by {added_by_username}")
            
            logger.info(f"User {user_id} added to conversation {conversation_id} by {added_by}")
            return True
            
        except Exception as e:
            logger.error(f"Error adding participant: {e}")
            return False
    
    def remove_participant(self, conversation_id: str, user_id: str, removed_by: str) -> bool:
        """Remove a participant from a group conversation.
        
        Args:
            conversation_id: Conversation ID
            user_id: User ID to remove
            removed_by: User ID who is removing the participant
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get conversation
            conv_response = self.client.from_("conversations").select("*").eq("id", conversation_id).single().execute()
            if not conv_response.data:
                return False
            
            conversation = conv_response.data
            
            # Only allow removing from group conversations
            if conversation['type'] != ConversationType.GROUP.value:
                logger.warning(f"Cannot remove participant from direct conversation {conversation_id}")
                return False
            
            # Allow self-removal or removal by group creator
            if user_id != removed_by and conversation['created_by'] != removed_by:
                logger.warning(f"User {removed_by} cannot remove {user_id} - not authorized")
                return False
            
            # Remove participant
            delete_response = self.client.from_("conversation_participants").delete().eq("conversation_id", conversation_id).eq("user_id", user_id).execute()
            
            if delete_response.data:
                # Send system message
                from .user_manager import enhanced_user_manager
                removed_user = enhanced_user_manager.get_complete_user_profile(user_id)
                username = removed_user.get('username', 'Unknown') if removed_user else 'Unknown'
                
                if user_id == removed_by:
                    self.send_system_message(conversation_id, f"{username} left the group")
                else:
                    removed_by_user = enhanced_user_manager.get_complete_user_profile(removed_by)
                    removed_by_username = removed_by_user.get('username', 'Unknown') if removed_by_user else 'Unknown'
                    self.send_system_message(conversation_id, f"{username} was removed from the group by {removed_by_username}")
                
                logger.info(f"User {user_id} removed from conversation {conversation_id}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error removing participant: {e}")
            return False
    
    def is_participant(self, conversation_id: str, user_id: str) -> bool:
        """Check if user is a participant in a conversation.
        
        Args:
            conversation_id: Conversation ID
            user_id: User ID
            
        Returns:
            True if participant, False otherwise
        """
        try:
            response = self.client.from_("conversation_participants").select("user_id").eq("conversation_id", conversation_id).eq("user_id", user_id).execute()
            return len(response.data or []) > 0
        except Exception as e:
            logger.error(f"Error checking participant status: {e}")
            return False
    
    def get_participants(self, conversation_id: str) -> List[Dict[str, Any]]:
        """Get all participants in a conversation.
        
        Args:
            conversation_id: Conversation ID
            
        Returns:
            List of participants with user info
        """
        try:
            response = self.client.from_("conversation_participants").select("""
                user_id, joined_at, last_read_at,
                user_profiles(username, display_name, avatar_url, level)
            """).eq("conversation_id", conversation_id).execute()
            
            return response.data or []
            
        except Exception as e:
            logger.error(f"Error getting participants: {e}")
            return []
    
    # =====================================================
    # READ STATUS AND NOTIFICATIONS
    # =====================================================
    
    def update_last_read(self, conversation_id: str, user_id: str) -> bool:
        """Update user's last read timestamp for a conversation.
        
        Args:
            conversation_id: Conversation ID
            user_id: User ID
            
        Returns:
            True if successful, False otherwise
        """
        try:
            response = self.client.from_("conversation_participants").update({
                'last_read_at': datetime.utcnow().isoformat()
            }).eq("conversation_id", conversation_id).eq("user_id", user_id).execute()
            
            return bool(response.data)
            
        except Exception as e:
            logger.error(f"Error updating last read: {e}")
            return False
    
    def get_unread_count(self, conversation_id: str, user_id: str) -> int:
        """Get number of unread messages for a user in a conversation.
        
        Args:
            conversation_id: Conversation ID
            user_id: User ID
            
        Returns:
            Number of unread messages
        """
        try:
            # Get user's last read timestamp
            participant_response = self.client.from_("conversation_participants").select("last_read_at").eq("conversation_id", conversation_id).eq("user_id", user_id).single().execute()
            
            if not participant_response.data:
                return 0
            
            last_read_at = participant_response.data['last_read_at']
            
            # Count messages after last read
            response = self.client.from_("messages").select("id", count="exact").eq("conversation_id", conversation_id).gt("created_at", last_read_at).neq("sender_id", user_id).execute()
            
            return response.count or 0
            
        except Exception as e:
            logger.error(f"Error getting unread count: {e}")
            return 0
    
    def get_total_unread_count(self, user_id: str) -> int:
        """Get total unread message count across all conversations.
        
        Args:
            user_id: User ID
            
        Returns:
            Total unread message count
        """
        try:
            conversations = self.get_user_conversations(user_id)
            total_unread = sum(conv.get('unread_count', 0) for conv in conversations)
            return total_unread
            
        except Exception as e:
            logger.error(f"Error getting total unread count: {e}")
            return 0
    
    # =====================================================
    # SEARCH AND UTILITY METHODS
    # =====================================================
    
    def search_messages(self, conversation_id: str, user_id: str, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Search messages in a conversation.
        
        Args:
            conversation_id: Conversation ID
            user_id: User ID performing search
            query: Search query
            limit: Maximum number of results
            
        Returns:
            List of matching messages
        """
        try:
            # Verify user is participant
            if not self.is_participant(conversation_id, user_id):
                return []
            
            response = self.client.from_("messages").select("""
                *,
                user_profiles(username, display_name, avatar_url)
            """).eq("conversation_id", conversation_id).ilike("content", f"%{query}%").order("created_at", desc=True).limit(limit).execute()
            
            return response.data or []
            
        except Exception as e:
            logger.error(f"Error searching messages: {e}")
            return []
    
    def _get_other_participant(self, conversation_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """Get the other participant in a direct conversation.
        
        Args:
            conversation_id: Conversation ID
            user_id: Current user ID
            
        Returns:
            Other participant info or None
        """
        try:
            response = self.client.from_("conversation_participants").select("""
                user_id,
                user_profiles(username, display_name, avatar_url, level)
            """).eq("conversation_id", conversation_id).neq("user_id", user_id).single().execute()
            
            if response.data and response.data.get('user_profiles'):
                participant = response.data['user_profiles']
                participant['user_id'] = response.data['user_id']
                return participant
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting other participant: {e}")
            return None
    
    def _create_message_activity(self, user_id: str, activity_type: str, metadata: Dict[str, Any]):
        """Create a message-related activity."""
        try:
            activity_data = {
                'user_id': user_id,
                'activity_type': activity_type,
                'title': self._get_activity_title(activity_type, metadata),
                'description': self._get_activity_description(activity_type, metadata),
                'metadata': metadata,
                'privacy_level': 'private',  # Message activities are private
                'created_at': datetime.utcnow().isoformat()
            }
            
            self.client.from_("user_activities").insert(activity_data).execute()
            
        except Exception as e:
            logger.error(f"Error creating message activity: {e}")
    
    def _get_activity_title(self, activity_type: str, metadata: Dict[str, Any]) -> str:
        """Generate activity title based on type and metadata."""
        titles = {
            'message_sent': "Sent a message",
            'group_created': f"Created group '{metadata.get('group_name', 'Unknown')}'",
            'group_joined': f"Joined group '{metadata.get('group_name', 'Unknown')}'"
        }
        return titles.get(activity_type, "Messaging activity")
    
    def _get_activity_description(self, activity_type: str, metadata: Dict[str, Any]) -> str:
        """Generate activity description based on type and metadata."""
        descriptions = {
            'message_sent': f"Sent a {metadata.get('message_type', 'text')} message",
            'group_created': "Created a new group conversation",
            'group_joined': "Joined a group conversation"
        }
        return descriptions.get(activity_type, "")

# Create a global instance
# Note: Global instance creation removed to prevent import-time initialization
# Use trackpro.social.messaging_manager or trackpro.social.get_messaging_manager() instead 