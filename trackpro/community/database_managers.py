"""
Real Database Managers for TrackPro Community Features
These managers interact with the actual Supabase database to provide real functionality.
"""

from typing import List, Dict, Optional, Any
import uuid
from datetime import datetime, timedelta
import json


class CommunityDatabaseManager:
    """Base database manager with common functionality"""
    
    def __init__(self, supabase_client):
        self.supabase = supabase_client
    
    def get_current_user_id(self):
        """Get the current authenticated user ID"""
        try:
            # Method 1: Try get_user() for active session
            user = self.supabase.auth.get_user()
            if user and hasattr(user, 'user') and user.user:
                return user.user.id
            
            # Method 2: Try get_session() for session data
            session = self.supabase.auth.get_session()
            if session and hasattr(session, 'user') and session.user:
                return session.user.id
                
            # Method 3: Check if there's a stored session we can access
            try:
                # Get the current session from auth storage
                auth_response = self.supabase.auth.get_session()
                if auth_response and hasattr(auth_response, 'user') and auth_response.user:
                    return auth_response.user.id
            except Exception as session_error:
                print(f"Session retrieval failed: {session_error}")
            
            return None
        except Exception as e:
            print(f"Error getting current user ID: {e}")
            return None
    
    def get_user_profile(self, user_id: str) -> Dict:
        """Get user profile information"""
        try:
            response = self.supabase.from_("user_profiles") \
                .select("*") \
                .eq("user_id", user_id) \
                .single() \
                .execute()
            
            if response.data:
                return response.data
            return {}
        except Exception as e:
            print(f"Error getting user profile: {e}")
            return {}
    
    def update_user_profile(self, user_id: str, profile_data: Dict) -> bool:
        """Update user profile information"""
        try:
            self.supabase.from_("user_profiles") \
                .update(profile_data) \
                .eq("user_id", user_id) \
                .execute()
            return True
        except Exception as e:
            print(f"Error updating user profile: {e}")
            return False
    
    def get_user_preferences(self, user_id: str) -> Dict:
        """Get user preferences and settings"""
        try:
            response = self.supabase.from_("user_preferences") \
                .select("*") \
                .eq("user_id", user_id) \
                .single() \
                .execute()
            
            if response.data:
                return response.data
            
            # Return default preferences if none exist
            return {
                'privacy_settings': {
                    'profile_visibility': 'public',
                    'racing_stats_visibility': 'public',
                    'activity_feed_visibility': 'public',
                    'friend_requests': 'everyone',
                    'private_messages': 'friends_only',
                    'team_invitations': 'friends_only',
                    'event_invitations': 'everyone',
                    'show_online_status': True,
                    'show_racing_status': True,
                    'show_recent_activity': True,
                    'share_telemetry': False,
                    'share_setups': True
                },
                'notification_settings': {
                    'friend_requests': True,
                    'new_messages': True,
                    'event_invitations': True,
                    'team_activity': True,
                    'achievement_unlocks': True,
                    'lap_record_beats': True,
                    'race_reminders': True,
                    'email_notifications': {
                        'weekly_summary': False,
                        'event_reminders': True,
                        'account_updates': True,
                        'new_features': False,
                        'community_highlights': False
                    },
                    'quiet_hours_start': '22:00',
                    'quiet_hours_end': '08:00',
                    'timezone': 'UTC+0'
                },
                'racing_preferences': {
                    'distance_units': 'kilometers',
                    'speed_units': 'km/h',
                    'temperature_units': 'celsius',
                    'fuel_units': 'liters',
                    'default_racing_view': 'cockpit',
                    'difficulty_level': 'intermediate',
                    'assist_preferences': 'some_assists',
                    'auto_save_telemetry': True,
                    'auto_analyze_laps': True,
                    'data_retention': '6_months',
                    'default_setup_style': 'balanced',
                    'auto_apply_community_setups': 'ask_first',
                    'preferred_racing_days': 'both',
                    'preferred_start_time': '19:00',
                    'session_length_preference': 'medium'
                },
                'data_settings': {
                    'auto_delete_telemetry': 'never',
                    'keep_screenshots': 'forever'
                }
            }
        except Exception as e:
            print(f"Error getting user preferences: {e}")
            return {}
    
    def update_user_preferences(self, user_id: str, preferences: Dict) -> bool:
        """Update user preferences and settings"""
        try:
            # Check if preferences exist
            existing = self.supabase.from_("user_preferences") \
                .select("user_id") \
                .eq("user_id", user_id) \
                .execute()
            
            if existing.data:
                # Update existing preferences
                self.supabase.from_("user_preferences") \
                    .update(preferences) \
                    .eq("user_id", user_id) \
                    .execute()
            else:
                # Insert new preferences
                preferences['user_id'] = user_id
                self.supabase.from_("user_preferences") \
                    .insert(preferences) \
                    .execute()
            
            return True
        except Exception as e:
            print(f"Error updating user preferences: {e}")
            return False


class SocialManager(CommunityDatabaseManager):
    """Manager for social features - friends, activity feed, messaging"""
    
    def get_friends_list(self, user_id: str) -> List[Dict]:
        """Get list of user's friends with their status"""
        try:
            # Use two separate queries to get friendships where user is either requester or addressee
            requester_response = self.supabase.from_("friendships") \
                .select("""
                    *,
                    requester:user_profiles!friendships_requester_id_fkey(user_id, username, display_name, avatar_url),
                    addressee:user_profiles!friendships_addressee_id_fkey(user_id, username, display_name, avatar_url)
                """) \
                .eq("requester_id", user_id) \
                .eq("status", "accepted") \
                .execute()
            
            addressee_response = self.supabase.from_("friendships") \
                .select("""
                    *,
                    requester:user_profiles!friendships_requester_id_fkey(user_id, username, display_name, avatar_url),
                    addressee:user_profiles!friendships_addressee_id_fkey(user_id, username, display_name, avatar_url)
                """) \
                .eq("addressee_id", user_id) \
                .eq("status", "accepted") \
                .execute()
            
            # Combine results
            response_data = []
            if requester_response.data:
                response_data.extend(requester_response.data)
            if addressee_response.data:
                response_data.extend(addressee_response.data)
            
            friends = []
            for friendship in response_data:
                # Determine if current user is requester or addressee
                if friendship['requester_id'] == user_id:
                    friend = friendship['addressee']
                else:
                    friend = friendship['requester']
                
                # Simplified status - just mark as "Online" for demo
                status = "Online"
                
                friends.append({
                    'user_id': friend['user_id'],
                    'username': friend['username'] or 'Unknown User',
                    'display_name': friend['display_name'] or friend['username'],
                    'avatar_url': friend['avatar_url'],
                    'status': status,
                    'last_activity': "Last race: Silverstone GP"
                })
            
            return friends
        except Exception as e:
            print(f"Error getting friends list: {e}")
            return []
    
    def send_friend_request(self, user_id: str, target_username: str) -> bool:
        """Send a friend request to another user"""
        try:
            # Find target user by username
            target_response = self.supabase.from_("user_profiles") \
                .select("user_id") \
                .eq("username", target_username) \
                .execute()
            
            if not target_response.data:
                return False
            
            target_user_id = target_response.data[0]['user_id']
            
            # Check if friendship already exists using two separate queries
            existing1 = self.supabase.from_("friendships") \
                .select("*") \
                .eq("requester_id", user_id) \
                .eq("addressee_id", target_user_id) \
                .execute()
            
            existing2 = self.supabase.from_("friendships") \
                .select("*") \
                .eq("requester_id", target_user_id) \
                .eq("addressee_id", user_id) \
                .execute()
            
            # Combine results
            existing_data = []
            if existing1.data:
                existing_data.extend(existing1.data)
            if existing2.data:
                existing_data.extend(existing2.data)
            
            if existing_data:
                return False  # Friendship already exists
            
            # Create friend request
            self.supabase.from_("friendships").insert({
                "requester_id": user_id,
                "addressee_id": target_user_id,
                "status": "pending"
            }).execute()
            
            return True
        except Exception as e:
            print(f"Error sending friend request: {e}")
            return False
    
    def get_activity_feed(self, user_id: str) -> List[Dict]:
        """Get activity feed for user - includes own activities, friends' activities, and public activities"""
        try:
            # Get user's own activities (all privacy levels) + public activities from all users
            # Use two separate queries
            user_activities = self.supabase.from_("user_activities") \
                .select("""
                    *,
                    user:user_profiles(username, display_name, avatar_url)
                """) \
                .eq("user_id", user_id) \
                .order("created_at", desc=True) \
                .limit(50) \
                .execute()
            
            public_activities = self.supabase.from_("user_activities") \
                .select("""
                    *,
                    user:user_profiles(username, display_name, avatar_url)
                """) \
                .eq("privacy_level", "public") \
                .order("created_at", desc=True) \
                .limit(50) \
                .execute()
            
            # Combine results
            response_data = []
            if user_activities.data:
                response_data.extend(user_activities.data)
            if public_activities.data:
                response_data.extend(public_activities.data)
            
            # Sort by created_at and limit to 50
            response_data.sort(key=lambda x: x['created_at'], reverse=True)
            response_data = response_data[:50]
            
            activities = []
            for activity in response_data:
                # Get interaction count
                interactions = self.supabase.from_("activity_interactions") \
                    .select("interaction_type") \
                    .eq("activity_id", activity['id']) \
                    .execute()
                
                like_count = len([i for i in interactions.data if i['interaction_type'] == 'like'])
                comment_count = len([i for i in interactions.data if i['interaction_type'] == 'comment'])
                
                # Convert activity type to icon
                type_icons = {
                    'personal_best': '🏁',
                    'achievement': '🏆',
                    'friend_added': '👥',
                    'lap_analysis': '📊',
                    'setup_shared': '⚙️'
                }
                
                activities.append({
                    'id': activity['id'],
                    'user': activity['user'],
                    'type': activity['activity_type'],
                    'icon': type_icons.get(activity['activity_type'], '📢'),
                    'title': activity['title'],
                    'description': activity['description'],
                    'created_at': activity['created_at'],
                    'like_count': like_count,
                    'comment_count': comment_count,
                    'metadata': activity['metadata']
                })
            
            return activities
        except Exception as e:
            print(f"Error getting activity feed: {e}")
            return []
    
    def post_activity(self, user_id: str, activity_type: str, title: str, description: str, metadata: Dict = None, privacy_level: str = "public") -> bool:
        """Post a new activity to the feed"""
        try:
            self.supabase.from_("user_activities").insert({
                "user_id": user_id,
                "activity_type": activity_type,
                "title": title,
                "description": description,
                "metadata": metadata or {},
                "privacy_level": privacy_level  # Now defaults to 'public' so everyone can see!
            }).execute()
            return True
        except Exception as e:
            print(f"Error posting activity: {e}")
            return False
    
    def get_conversations(self, user_id: str) -> List[Dict]:
        """Get user's conversations"""
        try:
            response = self.supabase.from_("conversation_participants") \
                .select("""
                    conversation:conversations(*),
                    last_read_at
                """) \
                .eq("user_id", user_id) \
                .execute()
            
            conversations = []
            for participant in response.data:
                conv = participant['conversation']
                
                # Get other participants
                other_participants = self.supabase.from_("conversation_participants") \
                    .select("user:user_profiles(username, display_name, avatar_url)") \
                    .eq("conversation_id", conv['id']) \
                    .neq("user_id", user_id) \
                    .execute()
                
                # Get latest message
                latest_message = self.supabase.from_("messages") \
                    .select("*, sender_id") \
                    .eq("conversation_id", conv['id']) \
                    .order("created_at", desc=True) \
                    .limit(1) \
                    .execute()
                
                # Count unread messages
                unread_count = 0
                if participant['last_read_at'] and latest_message.data:
                    last_read = datetime.fromisoformat(participant['last_read_at'].replace('Z', '+00:00'))
                    unread_response = self.supabase.from_("messages") \
                        .select("id", count="exact") \
                        .eq("conversation_id", conv['id']) \
                        .gt("created_at", last_read.isoformat()) \
                        .execute()
                    unread_count = unread_response.count or 0
                
                conversations.append({
                    'id': conv['id'],
                    'name': conv['name'] or (other_participants.data[0]['user']['display_name'] if other_participants.data else "Unknown"),
                    'type': conv['type'],
                    'participants': [p['user'] for p in other_participants.data],
                    'latest_message': latest_message.data[0] if latest_message.data else None,
                    'unread_count': unread_count,
                    'updated_at': conv['updated_at']
                })
            
            return conversations
        except Exception as e:
            print(f"Error getting conversations: {e}")
            return []
    
    def get_messages(self, conversation_id: str, limit: int = 50) -> List[Dict]:
        """Get messages for a conversation."""
        try:
            response = self.supabase.from_("messages") \
                .select("*, sender_id") \
                .eq("conversation_id", conversation_id) \
                .order("created_at", desc=True) \
                .limit(limit) \
                .execute()
            
            return response.data if response.data else []
        except Exception as e:
            print(f"Error getting messages: {e}")
            return []
    
    def send_message(self, user_id: str, conversation_id: str, content: str) -> bool:
        """Send a message in a conversation"""
        try:
            # Send message
            self.supabase.from_("messages").insert({
                "conversation_id": conversation_id,
                "sender_id": user_id,
                "content": content,
                "message_type": "text"
            }).execute()
            
            # Update conversation timestamp
            self.supabase.from_("conversations") \
                .update({"updated_at": datetime.now().isoformat()}) \
                .eq("id", conversation_id) \
                .execute()
            
            return True
        except Exception as e:
            print(f"Error sending message: {e}")
            return False


class CommunityManager(CommunityDatabaseManager):
    """Manager for teams, clubs, and events"""
    
    def get_user_teams(self, user_id: str) -> List[Dict]:
        """Get teams the user is a member of"""
        try:
            response = self.supabase.from_("team_members") \
                .select("""
                    role,
                    joined_at,
                    team:teams(*, created_by, member_count:team_members(count))
                """) \
                .eq("user_id", user_id) \
                .execute()
            
            teams = []
            for membership in response.data:
                team = membership['team']
                member_count = len(team['member_count']) if team['member_count'] else 0
                
                teams.append({
                    'id': team['id'],
                    'name': team['name'],
                    'description': team['description'],
                    'logo_url': team['logo_url'],
                    'member_count': f"{member_count} members",
                    'role': membership['role'],
                    'is_active': team['privacy_level'] == 'public',
                    'joined_at': membership['joined_at']
                })
            
            return teams
        except Exception as e:
            print(f"Error getting user teams: {e}")
            return []
    
    def get_clubs(self, user_id: str = None) -> List[Dict]:
        """Get available clubs, marking which ones user is a member of"""
        try:
            response = self.supabase.from_("clubs") \
                .select("*") \
                .order("member_count", desc=True) \
                .execute()
            
            clubs = []
            for club in response.data:
                is_member = False
                if user_id:
                    # Check if user is member
                    membership = self.supabase.from_("club_members") \
                        .select("role") \
                        .eq("club_id", club['id']) \
                        .eq("user_id", user_id) \
                        .execute()
                    is_member = bool(membership.data)
                
                clubs.append({
                    'id': club['id'],
                    'name': club['name'],
                    'description': club['description'],
                    'category': club['category'],
                    'member_count': f"{club['member_count']} members",
                    'is_member': is_member,
                    'logo_url': club['logo_url']
                })
            
            return clubs
        except Exception as e:
            print(f"Error getting clubs: {e}")
            return []
    
    def join_club(self, user_id: str, club_id: str) -> bool:
        """Join a club"""
        try:
            # Check if already a member
            existing = self.supabase.from_("club_members") \
                .select("*") \
                .eq("club_id", club_id) \
                .eq("user_id", user_id) \
                .execute()
            
            if existing.data:
                return False  # Already a member
            
            # Join club
            self.supabase.from_("club_members").insert({
                "club_id": club_id,
                "user_id": user_id,
                "role": "member"
            }).execute()
            
            # Get current member count and increment it
            club = self.supabase.from_("clubs") \
                .select("member_count") \
                .eq("id", club_id) \
                .single() \
                .execute()
            
            if club.data:
                new_count = (club.data.get('member_count', 0) or 0) + 1
                self.supabase.from_("clubs") \
                    .update({"member_count": new_count}) \
                    .eq("id", club_id) \
                    .execute()
            
            return True
        except Exception as e:
            print(f"Error joining club: {e}")
            return False
    
    def get_community_events(self, user_id: str) -> List[Dict]:
        """Get community events"""
        try:
            response = self.supabase.from_("community_events") \
                .select("""
                    *,
                    creator:user_profiles!community_events_created_by_fkey(username, display_name),
                    participant_count:event_participants(count)
                """) \
                .gte("start_time", datetime.now().isoformat()) \
                .order("start_time") \
                .execute()
            
            events = []
            for event in response.data:
                # Check if user is registered
                registration = self.supabase.from_("event_participants") \
                    .select("status") \
                    .eq("event_id", event['id']) \
                    .eq("user_id", user_id) \
                    .execute()
                
                is_registered = bool(registration.data)
                participant_count = len(event['participant_count']) if event['participant_count'] else 0
                max_participants = event['max_participants'] or 50
                
                events.append({
                    'id': event['id'],
                    'title': event['title'],
                    'description': event['description'],
                    'event_type': event['event_type'] or 'Open',
                    'track_name': 'TBD',  # Simplified since tracks table doesn't exist
                    'car_name': 'Open Class',  # Simplified since cars table doesn't exist
                    'start_time': event['start_time'],
                    'registration_info': f"{participant_count}/{max_participants} registered",
                    'is_registered': is_registered,
                    'creator': event['creator']['display_name'] if event['creator'] else 'TrackPro'
                })
            
            return events
        except Exception as e:
            print(f"Error getting community events: {e}")
            return []
    
    def register_for_event(self, user_id: str, event_id: str) -> bool:
        """Register for an event"""
        try:
            # Check if already registered
            existing = self.supabase.from_("event_participants") \
                .select("*") \
                .eq("event_id", event_id) \
                .eq("user_id", user_id) \
                .execute()
            
            if existing.data:
                return False  # Already registered
            
            # Register for event
            self.supabase.from_("event_participants").insert({
                "event_id": event_id,
                "user_id": user_id,
                "status": "registered"
            }).execute()
            
            return True
        except Exception as e:
            print(f"Error registering for event: {e}")
            return False

    def unregister_from_event(self, user_id: str, event_id: str) -> bool:
        """Unregister from an event."""
        try:
            response = self.supabase.from_("event_participants") \
                .delete() \
                .eq("event_id", event_id) \
                .eq("user_id", user_id) \
                .execute()

            if response.status_code == 204 or (hasattr(response, 'data') and response.data):
                return True
            return False
        except Exception as e:
            print(f"Error unregistering from event: {e}")
            return False


class ContentManager(CommunityDatabaseManager):
    """Manager for shared content - setups, media, guides"""
    
    def get_user_content(self, user_id: str) -> List[Dict]:
        """Get content shared by user"""
        try:
            # Get setups
            setups = self.supabase.from_("shared_setups") \
                .select("*") \
                .eq("user_id", user_id) \
                .eq("is_public", True) \
                .execute()
            
            # Get media
            media = self.supabase.from_("shared_media") \
                .select("*") \
                .eq("user_id", user_id) \
                .eq("is_public", True) \
                .execute()
            
            content = []
            
            # Add setups
            for setup in setups.data:
                content.append({
                    'id': setup['id'],
                    'title': setup['name'],
                    'type': 'Car Setup',
                    'category': 'General',  # Simplified since cars table doesn't exist
                    'stats': f"{setup['download_count']} downloads",
                    'uploaded': setup['created_at'],
                    'description': setup['description'],
                    'track': None,  # Simplified since tracks table doesn't exist
                    'rating': setup['rating'],
                    'tags': setup['tags']
                })
            
            # Add media
            for item in media.data:
                content.append({
                    'id': item['id'],
                    'title': item['title'],
                    'type': item['media_type'].title() if item['media_type'] else 'Media',
                    'category': 'General',  # Simplified since cars table doesn't exist
                    'stats': f"{item['view_count']} views" if item['media_type'] == 'video' else f"{item['like_count']} likes",
                    'uploaded': item['created_at'],
                    'description': item['description'],
                    'track': None,  # Simplified since tracks table doesn't exist
                    'file_url': item['file_url'],
                    'thumbnail_url': item['thumbnail_url']
                })
            
            # Sort by upload date
            content.sort(key=lambda x: x['uploaded'], reverse=True)
            
            return content
        except Exception as e:
            print(f"Error getting user content: {e}")
            return []
    
    def get_featured_content(self) -> List[Dict]:
        """Get featured community content"""
        try:
            # Get popular setups
            setups = self.supabase.from_("shared_setups") \
                .select("*, user:user_profiles(username, display_name)") \
                .eq("is_public", True) \
                .order("download_count", desc=True) \
                .limit(10) \
                .execute()
            
            # Get popular media
            media = self.supabase.from_("shared_media") \
                .select("*, user:user_profiles(username, display_name)") \
                .eq("is_public", True) \
                .order("view_count", desc=True) \
                .limit(10) \
                .execute()
            
            content = []
            
            # Add setups
            for setup in setups.data:
                content.append({
                    'id': setup['id'],
                    'title': setup['name'],
                    'type': 'Car Setup',
                    'category': 'General',  # Simplified since cars table doesn't exist
                    'stats': f"{setup['download_count']} downloads",
                    'author': f"by {setup['user']['display_name'] if setup['user'] else 'Unknown'}",
                    'rating': setup['rating'],
                    'description': setup['description']
                })
            
            # Add media
            for item in media.data:
                content.append({
                    'id': item['id'],
                    'title': item['title'],
                    'type': item['media_type'].title() if item['media_type'] else 'Media',
                    'category': 'General',  # Simplified since cars table doesn't exist
                    'stats': f"{item['view_count']} views" if item['media_type'] == 'video' else f"{item['like_count']} likes",
                    'author': f"by {item['user']['display_name'] if item['user'] else 'Unknown'}",
                    'file_url': item['file_url'],
                    'thumbnail_url': item['thumbnail_url']
                })
            
            # Sort by popularity (downloads/views)
            content.sort(key=lambda x: int(x['stats'].split()[0].replace(',', '').replace('K', '000')), reverse=True)
            
            return content[:20]  # Return top 20
        except Exception as e:
            print(f"Error getting featured content: {e}")
            return []
    
    def download_content(self, user_id: str, content_id: str, content_type: str) -> bool:
        """Download/like content"""
        try:
            if content_type == 'Car Setup':
                # Get current download count and increment it
                setup = self.supabase.from_("shared_setups") \
                    .select("download_count") \
                    .eq("id", content_id) \
                    .single() \
                    .execute()
                
                if setup.data:
                    new_count = (setup.data.get('download_count', 0) or 0) + 1
                    self.supabase.from_("shared_setups") \
                        .update({"download_count": new_count}) \
                        .eq("id", content_id) \
                        .execute()
            else:
                # Get current view count and increment it
                media = self.supabase.from_("shared_media") \
                    .select("view_count") \
                    .eq("id", content_id) \
                    .single() \
                    .execute()
                
                if media.data:
                    new_count = (media.data.get('view_count', 0) or 0) + 1
                    self.supabase.from_("shared_media") \
                        .update({"view_count": new_count}) \
                        .eq("id", content_id) \
                        .execute()
            
            return True
        except Exception as e:
            print(f"Error downloading content: {e}")
            return False

    def delete_content(self, user_id: str, content_id: str, content_type: str) -> bool:
        """Delete a piece of user content."""
        try:
            table_name = None
            if content_type == 'Car Setup':
                table_name = 'shared_setups'
            elif content_type in ['Video', 'Screenshot', 'Guide', 'Replay', 'Media']:
                table_name = 'shared_media'

            if not table_name:
                print(f"Unknown content type for deletion: {content_type}")
                return False

            # Ensure user owns the content before deleting
            response = self.supabase.from_(table_name) \
                .delete() \
                .eq("id", content_id) \
                .eq("user_id", user_id) \
                .execute()

            # The API response for delete might not contain data, so check for success differently
            if response.status_code == 204 or (hasattr(response, 'data') and response.data):
                print(f"Deleted content {content_id} from {table_name}")
                return True
            else:
                print(f"Failed to delete content {content_id}. It might not exist or user does not have permission. Status: {response.status_code}")
                return False
        except Exception as e:
            print(f"Error deleting content: {e}")
            return False

    def upload_content(self, user_id: str, content_data: Dict) -> bool:
        """Upload new content."""
        try:
            content_type = content_data.get('type')
            table_name = None
            data_to_insert = {
                'user_id': user_id,
                'is_public': True,
                'description': content_data.get('description'),
                'tags': content_data.get('tags', []),
                'rating': 0,
                'download_count': 0,
            }

            if content_type == 'Car Setup':
                table_name = 'shared_setups'
                data_to_insert['name'] = content_data.get('title')
                data_to_insert['setup_data'] = content_data.get('file_url', {})
            elif content_type in ['Video', 'Screenshot', 'Guide', 'Replay']:
                table_name = 'shared_media'
                data_to_insert['title'] = content_data.get('title')
                data_to_insert['media_type'] = content_type.lower()
                data_to_insert['file_url'] = content_data.get('file_url')
                data_to_insert['thumbnail_url'] = content_data.get('thumbnail_url')
                data_to_insert['view_count'] = 0
                data_to_insert['like_count'] = 0
            
            if not table_name:
                print(f"Unknown content type for upload: {content_type}")
                return False

            self.supabase.from_(table_name).insert(data_to_insert).execute()
            
            # Post an activity feed update
            social_manager = SocialManager(self.supabase)
            social_manager.post_activity(
                user_id,
                'content_shared',
                f"Shared a new {content_type}",
                content_data.get('title'),
                {'content_type': content_type, 'title': content_data.get('title')}
            )

            return True
        except Exception as e:
            print(f"Error uploading content: {e}")
            return False


class AchievementsManager(CommunityDatabaseManager):
    """Manager for achievements and gamification"""
    
    def get_user_achievements(self, user_id: str) -> List[Dict]:
        """Get user's achievements"""
        try:
            response = self.supabase.from_("user_achievements") \
                .select("""
                    *,
                    achievement:achievements(*)
                """) \
                .eq("user_id", user_id) \
                .execute()
            
            achievements = []
            for user_achievement in response.data:
                achievement = user_achievement['achievement']
                
                # Determine if unlocked
                is_unlocked = user_achievement['unlocked_at'] is not None
                
                achievements.append({
                    'id': achievement['id'],
                    'name': achievement['name'],
                    'description': achievement['description'],
                    'category': achievement['category'],
                    'rarity': achievement['rarity'],
                    'icon_url': achievement['icon_url'],
                    'xp_reward': achievement['xp_reward'],
                    'is_unlocked': is_unlocked,
                    'unlocked_at': user_achievement['unlocked_at'],
                    'progress': user_achievement['progress'],
                    'is_showcased': user_achievement['is_showcased']
                })
            
            return achievements
        except Exception as e:
            print(f"Error getting user achievements: {e}")
            return []
    
    def get_user_stats_summary(self, user_id: str) -> Dict:
        """Get user stats summary for achievements tab"""
        try:
            # Get user profile
            profile = self.supabase.from_("user_profiles") \
                .select("current_xp, level, social_xp, prestige_level, reputation_score") \
                .eq("user_id", user_id) \
                .single() \
                .execute()
            
            # Get user stats
            stats = self.supabase.from_("user_stats") \
                .select("*") \
                .eq("user_id", user_id) \
                .single() \
                .execute()
            
            # Get achievement count
            achievement_count = self.supabase.from_("user_achievements") \
                .select("*", count="exact") \
                .eq("user_id", user_id) \
                .not_.is_("unlocked_at", "null") \
                .execute()
            
            if profile.data and stats.data:
                return {
                    'level': profile.data['level'] or 1,
                    'current_xp': profile.data['current_xp'] or 0,
                    'total_laps': stats.data['total_laps'] or 0,
                    'total_distance': f"{float(stats.data['total_distance_km'] or 0):.1f} km",
                    'best_lap_time': stats.data['best_lap_time'],
                    'achievements_unlocked': achievement_count.count or 0,
                    'reputation_score': profile.data['reputation_score'] or 0,
                    'prestige_level': profile.data['prestige_level'] or 0
                }
            
            return {}
        except Exception as e:
            print(f"Error getting user stats: {e}")
            return {}


# Factory function to create all managers
def create_community_managers(supabase_client):
    """Create all community managers with the given Supabase client"""
    return {
        'social_manager': SocialManager(supabase_client),
        'community_manager': CommunityManager(supabase_client),
        'content_manager': ContentManager(supabase_client),
        'achievements_manager': AchievementsManager(supabase_client),
        'user_manager': CommunityDatabaseManager(supabase_client)  # Base manager for common functions
    } 