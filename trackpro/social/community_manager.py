"""Community Manager for comprehensive team, club, and event management."""

import logging
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from enum import Enum
from ..database.base import DatabaseManager
from ..database.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)

class TeamRole(Enum):
    """Team member role enumeration."""
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"

class ClubRole(Enum):
    """Club member role enumeration."""
    OWNER = "owner"
    ADMIN = "admin"
    MODERATOR = "moderator"
    MEMBER = "member"

class EventStatus(Enum):
    """Event status enumeration."""
    UPCOMING = "upcoming"
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class EventType(Enum):
    """Event type enumeration."""
    TIME_TRIAL = "time_trial"
    RACE = "race"
    CHAMPIONSHIP = "championship"
    PRACTICE = "practice"
    TOURNAMENT = "tournament"

class PrivacyLevel(Enum):
    """Privacy level enumeration."""
    PUBLIC = "public"
    PRIVATE = "private"
    INVITE_ONLY = "invite_only"

class CommunityManager(DatabaseManager):
    """Comprehensive community management system."""
    
    def __init__(self):
        """Initialize the community manager."""
        super().__init__("teams")
        self.supabase = get_supabase_client()
    
    # =====================================================
    # TEAM MANAGEMENT
    # =====================================================
    
    def create_team(self, creator_id: str, name: str, description: str = "", 
                   logo_url: str = None, color_scheme: Dict[str, str] = None,
                   max_members: int = 50, privacy_level: PrivacyLevel = PrivacyLevel.PUBLIC) -> Optional[Dict[str, Any]]:
        """Create a new racing team.
        
        Args:
            creator_id: ID of user creating the team
            name: Team name
            description: Team description
            logo_url: Team logo URL
            color_scheme: Team color scheme
            max_members: Maximum number of members
            privacy_level: Team privacy level
            
        Returns:
            Created team data or None
        """
        try:
            # Check if team name is available
            existing_team = self.client.from_("teams").select("id").eq("name", name).execute()
            if existing_team.data:
                logger.warning(f"Team name '{name}' already exists")
                return None
            
            # Create team
            team_data = {
                'name': name,
                'description': description,
                'logo_url': logo_url,
                'color_scheme': color_scheme or {},
                'created_by': creator_id,
                'max_members': max_members,
                'privacy_level': privacy_level.value,
                'created_at': datetime.utcnow().isoformat(),
                'updated_at': datetime.utcnow().isoformat()
            }
            
            response = self.client.from_("teams").insert(team_data).execute()
            if not response.data:
                return None
            
            team = response.data[0]
            team_id = team['id']
            
            # Add creator as owner
            member_data = {
                'team_id': team_id,
                'user_id': creator_id,
                'role': TeamRole.OWNER.value,
                'joined_at': datetime.utcnow().isoformat()
            }
            
            self.client.from_("team_members").insert(member_data).execute()
            
            # Create activity
            self._create_team_activity(creator_id, "team_created", {
                'team_id': team_id,
                'team_name': name
            })
            
            logger.info(f"Team '{name}' created by user {creator_id}")
            return team
            
        except Exception as e:
            logger.error(f"Error creating team: {e}")
            return None
    
    def join_team(self, team_id: str, user_id: str, invited_by: str = None) -> Dict[str, Any]:
        """Join a team.
        
        Args:
            team_id: Team ID
            user_id: User ID
            invited_by: ID of user who invited (for private teams)
            
        Returns:
            Dictionary with success status and message
        """
        try:
            # Get team info
            team_response = self.client.from_("teams").select("*").eq("id", team_id).single().execute()
            if not team_response.data:
                return {"success": False, "message": "Team not found"}
            
            team = team_response.data
            
            # Check if user is already a member
            existing_member = self.client.from_("team_members").select("id").eq("team_id", team_id).eq("user_id", user_id).execute()
            if existing_member.data:
                return {"success": False, "message": "Already a team member"}
            
            # Check privacy and capacity
            if team['privacy_level'] == PrivacyLevel.PRIVATE.value and not invited_by:
                return {"success": False, "message": "This team is private and requires an invitation"}
            
            # Check member count
            member_count = self.get_team_member_count(team_id)
            if member_count >= team['max_members']:
                return {"success": False, "message": "Team is at maximum capacity"}
            
            # Add member
            member_data = {
                'team_id': team_id,
                'user_id': user_id,
                'role': TeamRole.MEMBER.value,
                'joined_at': datetime.utcnow().isoformat()
            }
            
            response = self.client.from_("team_members").insert(member_data).execute()
            if not response.data:
                return {"success": False, "message": "Failed to join team"}
            
            # Create activity
            self._create_team_activity(user_id, "team_joined", {
                'team_id': team_id,
                'team_name': team['name']
            })
            
            logger.info(f"User {user_id} joined team {team_id}")
            return {"success": True, "message": "Successfully joined team"}
            
        except Exception as e:
            logger.error(f"Error joining team: {e}")
            return {"success": False, "message": "Failed to join team"}
    
    def leave_team(self, team_id: str, user_id: str) -> Dict[str, Any]:
        """Leave a team.
        
        Args:
            team_id: Team ID
            user_id: User ID
            
        Returns:
            Dictionary with success status and message
        """
        try:
            # Get member info
            member_response = self.client.from_("team_members").select("*").eq("team_id", team_id).eq("user_id", user_id).single().execute()
            if not member_response.data:
                return {"success": False, "message": "Not a team member"}
            
            member = member_response.data
            
            # Check if user is the owner
            if member['role'] == TeamRole.OWNER.value:
                # Check if there are other members
                other_members = self.client.from_("team_members").select("*").eq("team_id", team_id).neq("user_id", user_id).execute()
                if other_members.data:
                    return {"success": False, "message": "Team owner must transfer ownership or disband team before leaving"}
                else:
                    # Delete the team if owner is the only member
                    self.disband_team(team_id, user_id)
                    return {"success": True, "message": "Team disbanded"}
            
            # Remove member
            delete_response = self.client.from_("team_members").delete().eq("team_id", team_id).eq("user_id", user_id).execute()
            
            if delete_response.data:
                # Create activity
                team_info = self.get_team(team_id)
                self._create_team_activity(user_id, "team_left", {
                    'team_id': team_id,
                    'team_name': team_info.get('name', 'Unknown') if team_info else 'Unknown'
                })
                
                logger.info(f"User {user_id} left team {team_id}")
                return {"success": True, "message": "Successfully left team"}
            
            return {"success": False, "message": "Failed to leave team"}
            
        except Exception as e:
            logger.error(f"Error leaving team: {e}")
            return {"success": False, "message": "Failed to leave team"}
    
    def update_team_member_role(self, team_id: str, user_id: str, new_role: TeamRole, updated_by: str) -> Dict[str, Any]:
        """Update a team member's role.
        
        Args:
            team_id: Team ID
            user_id: User ID whose role to update
            new_role: New role
            updated_by: User ID making the change
            
        Returns:
            Dictionary with success status and message
        """
        try:
            # Check if updater has permission
            updater_role = self.get_team_member_role(team_id, updated_by)
            if not updater_role or updater_role not in [TeamRole.OWNER.value, TeamRole.ADMIN.value]:
                return {"success": False, "message": "Insufficient permissions"}
            
            # Can't change owner role unless you are the owner
            if new_role == TeamRole.OWNER and updater_role != TeamRole.OWNER.value:
                return {"success": False, "message": "Only team owner can assign ownership"}
            
            # Update role
            response = self.client.from_("team_members").update({
                'role': new_role.value
            }).eq("team_id", team_id).eq("user_id", user_id).execute()
            
            if response.data:
                logger.info(f"Team member {user_id} role updated to {new_role.value} in team {team_id}")
                return {"success": True, "message": "Role updated successfully"}
            
            return {"success": False, "message": "Failed to update role"}
            
        except Exception as e:
            logger.error(f"Error updating team member role: {e}")
            return {"success": False, "message": "Failed to update role"}
    
    def get_team(self, team_id: str) -> Optional[Dict[str, Any]]:
        """Get team information.
        
        Args:
            team_id: Team ID
            
        Returns:
            Team data or None
        """
        try:
            response = self.client.from_("teams").select("*").eq("id", team_id).single().execute()
            if response.data:
                team = response.data
                # Add member count
                team['member_count'] = self.get_team_member_count(team_id)
                return team
            return None
            
        except Exception as e:
            logger.error(f"Error getting team: {e}")
            return None
    
    def get_team_members(self, team_id: str) -> List[Dict[str, Any]]:
        """Get team members.
        
        Args:
            team_id: Team ID
            
        Returns:
            List of team members
        """
        try:
            response = self.client.from_("team_members").select("""
                *,
                user_profiles(username, display_name, avatar_url, level)
            """).eq("team_id", team_id).order("joined_at").execute()
            
            return response.data or []
            
        except Exception as e:
            logger.error(f"Error getting team members: {e}")
            return []
    
    def get_user_teams(self, user_id: str) -> List[Dict[str, Any]]:
        """Get teams a user is a member of.
        
        Args:
            user_id: User ID
            
        Returns:
            List of teams
        """
        try:
            response = self.client.from_("team_members").select("""
                role, joined_at,
                teams(*)
            """).eq("user_id", user_id).execute()
            
            teams = []
            for item in response.data or []:
                if item.get('teams'):
                    team = item['teams']
                    team['user_role'] = item['role']
                    team['joined_at'] = item['joined_at']
                    team['member_count'] = self.get_team_member_count(team['id'])
                    teams.append(team)
            
            return teams
            
        except Exception as e:
            logger.error(f"Error getting user teams: {e}")
            return []
    
    # =====================================================
    # CLUB MANAGEMENT
    # =====================================================
    
    def create_club(self, creator_id: str, name: str, description: str = "", 
                   category: str = None, logo_url: str = None,
                   privacy_level: PrivacyLevel = PrivacyLevel.PUBLIC) -> Optional[Dict[str, Any]]:
        """Create a new racing club.
        
        Args:
            creator_id: ID of user creating the club
            name: Club name
            description: Club description
            category: Club category (GT3, Formula, etc.)
            logo_url: Club logo URL
            privacy_level: Club privacy level
            
        Returns:
            Created club data or None
        """
        try:
            # Check if club name is available
            existing_club = self.client.from_("clubs").select("id").eq("name", name).execute()
            if existing_club.data:
                logger.warning(f"Club name '{name}' already exists")
                return None
            
            # Create club
            club_data = {
                'name': name,
                'description': description,
                'category': category,
                'logo_url': logo_url,
                'created_by': creator_id,
                'member_count': 1,
                'privacy_level': privacy_level.value,
                'created_at': datetime.utcnow().isoformat()
            }
            
            response = self.client.from_("clubs").insert(club_data).execute()
            if not response.data:
                return None
            
            club = response.data[0]
            club_id = club['id']
            
            # Add creator as owner
            member_data = {
                'club_id': club_id,
                'user_id': creator_id,
                'role': ClubRole.OWNER.value,
                'joined_at': datetime.utcnow().isoformat()
            }
            
            self.client.from_("club_members").insert(member_data).execute()
            
            # Create activity
            self._create_club_activity(creator_id, "club_created", {
                'club_id': club_id,
                'club_name': name,
                'category': category
            })
            
            logger.info(f"Club '{name}' created by user {creator_id}")
            return club
            
        except Exception as e:
            logger.error(f"Error creating club: {e}")
            return None
    
    def join_club(self, club_id: str, user_id: str) -> Dict[str, Any]:
        """Join a club.
        
        Args:
            club_id: Club ID
            user_id: User ID
            
        Returns:
            Dictionary with success status and message
        """
        try:
            # Get club info
            club_response = self.client.from_("clubs").select("*").eq("id", club_id).single().execute()
            if not club_response.data:
                return {"success": False, "message": "Club not found"}
            
            club = club_response.data
            
            # Check if user is already a member
            existing_member = self.client.from_("club_members").select("id").eq("club_id", club_id).eq("user_id", user_id).execute()
            if existing_member.data:
                return {"success": False, "message": "Already a club member"}
            
            # Check privacy
            if club['privacy_level'] == PrivacyLevel.PRIVATE.value:
                return {"success": False, "message": "This club is private and requires an invitation"}
            
            # Add member
            member_data = {
                'club_id': club_id,
                'user_id': user_id,
                'role': ClubRole.MEMBER.value,
                'joined_at': datetime.utcnow().isoformat()
            }
            
            response = self.client.from_("club_members").insert(member_data).execute()
            if not response.data:
                return {"success": False, "message": "Failed to join club"}
            
            # Update member count
            self.client.from_("clubs").update({
                'member_count': club['member_count'] + 1
            }).eq("id", club_id).execute()
            
            # Create activity
            self._create_club_activity(user_id, "club_joined", {
                'club_id': club_id,
                'club_name': club['name'],
                'category': club.get('category')
            })
            
            logger.info(f"User {user_id} joined club {club_id}")
            return {"success": True, "message": "Successfully joined club"}
            
        except Exception as e:
            logger.error(f"Error joining club: {e}")
            return {"success": False, "message": "Failed to join club"}
    
    def get_club(self, club_id: str) -> Optional[Dict[str, Any]]:
        """Get club information.
        
        Args:
            club_id: Club ID
            
        Returns:
            Club data or None
        """
        try:
            response = self.client.from_("clubs").select("*").eq("id", club_id).single().execute()
            return response.data
            
        except Exception as e:
            logger.error(f"Error getting club: {e}")
            return None
    
    def get_user_clubs(self, user_id: str) -> List[Dict[str, Any]]:
        """Get clubs a user is a member of.
        
        Args:
            user_id: User ID
            
        Returns:
            List of clubs
        """
        try:
            response = self.client.from_("club_members").select("""
                role, joined_at,
                clubs(*)
            """).eq("user_id", user_id).execute()
            
            clubs = []
            for item in response.data or []:
                if item.get('clubs'):
                    club = item['clubs']
                    club['user_role'] = item['role']
                    club['joined_at'] = item['joined_at']
                    clubs.append(club)
            
            return clubs
            
        except Exception as e:
            logger.error(f"Error getting user clubs: {e}")
            return []
    
    # =====================================================
    # EVENT MANAGEMENT
    # =====================================================
    
    def create_event(self, creator_id: str, title: str, description: str = "",
                    event_type: EventType = EventType.TIME_TRIAL, track_id: int = None,
                    car_id: int = None, start_time: datetime = None, end_time: datetime = None,
                    max_participants: int = None, entry_requirements: Dict[str, Any] = None,
                    prizes: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
        """Create a community event.
        
        Args:
            creator_id: ID of user creating the event
            title: Event title
            description: Event description
            event_type: Type of event
            track_id: Track ID for the event
            car_id: Car ID for the event
            start_time: Event start time
            end_time: Event end time
            max_participants: Maximum participants
            entry_requirements: Entry requirements
            prizes: Event prizes
            
        Returns:
            Created event data or None
        """
        try:
            event_data = {
                'title': title,
                'description': description,
                'event_type': event_type.value,
                'track_id': track_id,
                'car_id': car_id,
                'start_time': start_time.isoformat() if start_time else None,
                'end_time': end_time.isoformat() if end_time else None,
                'created_by': creator_id,
                'max_participants': max_participants,
                'entry_requirements': entry_requirements or {},
                'prizes': prizes or {},
                'status': EventStatus.UPCOMING.value,
                'created_at': datetime.utcnow().isoformat()
            }
            
            response = self.client.from_("community_events").insert(event_data).execute()
            if not response.data:
                return None
            
            event = response.data[0]
            
            # Create activity
            self._create_event_activity(creator_id, "event_created", {
                'event_id': event['id'],
                'event_title': title,
                'event_type': event_type.value
            })
            
            logger.info(f"Event '{title}' created by user {creator_id}")
            return event
            
        except Exception as e:
            logger.error(f"Error creating event: {e}")
            return None
    
    def join_event(self, event_id: str, user_id: str) -> Dict[str, Any]:
        """Join an event.
        
        Args:
            event_id: Event ID
            user_id: User ID
            
        Returns:
            Dictionary with success status and message
        """
        try:
            # Get event info
            event_response = self.client.from_("community_events").select("*").eq("id", event_id).single().execute()
            if not event_response.data:
                return {"success": False, "message": "Event not found"}
            
            event = event_response.data
            
            # Check if event is still upcoming
            if event['status'] != EventStatus.UPCOMING.value:
                return {"success": False, "message": "Event registration is closed"}
            
            # Check if user is already registered
            existing_participant = self.client.from_("event_participants").select("id").eq("event_id", event_id).eq("user_id", user_id).execute()
            if existing_participant.data:
                return {"success": False, "message": "Already registered for this event"}
            
            # Check participant limit
            if event['max_participants']:
                participant_count = self.get_event_participant_count(event_id)
                if participant_count >= event['max_participants']:
                    return {"success": False, "message": "Event is at maximum capacity"}
            
            # Check entry requirements
            if event['entry_requirements']:
                if not self._check_event_requirements(user_id, event['entry_requirements']):
                    return {"success": False, "message": "You don't meet the entry requirements"}
            
            # Register participant
            participant_data = {
                'event_id': event_id,
                'user_id': user_id,
                'registration_time': datetime.utcnow().isoformat(),
                'status': 'registered'
            }
            
            response = self.client.from_("event_participants").insert(participant_data).execute()
            if not response.data:
                return {"success": False, "message": "Failed to register for event"}
            
            # Create activity
            self._create_event_activity(user_id, "event_joined", {
                'event_id': event_id,
                'event_title': event['title'],
                'event_type': event['event_type']
            })
            
            logger.info(f"User {user_id} registered for event {event_id}")
            return {"success": True, "message": "Successfully registered for event"}
            
        except Exception as e:
            logger.error(f"Error joining event: {e}")
            return {"success": False, "message": "Failed to register for event"}
    
    def get_event(self, event_id: str) -> Optional[Dict[str, Any]]:
        """Get event information.
        
        Args:
            event_id: Event ID
            
        Returns:
            Event data or None
        """
        try:
            response = self.client.from_("community_events").select("""
                *,
                user_profiles(username, display_name, avatar_url)
            """).eq("id", event_id).single().execute()
            
            if response.data:
                event = response.data
                event['participant_count'] = self.get_event_participant_count(event_id)
                return event
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting event: {e}")
            return None
    
    def get_upcoming_events(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get upcoming events.
        
        Args:
            limit: Maximum number of events
            
        Returns:
            List of upcoming events
        """
        try:
            response = self.client.from_("community_events").select("""
                *,
                user_profiles(username, display_name, avatar_url)
            """).eq("status", EventStatus.UPCOMING.value).order("start_time").limit(limit).execute()
            
            events = response.data or []
            
            # Add participant counts
            for event in events:
                event['participant_count'] = self.get_event_participant_count(event['id'])
            
            return events
            
        except Exception as e:
            logger.error(f"Error getting upcoming events: {e}")
            return []
    
    def get_user_events(self, user_id: str) -> List[Dict[str, Any]]:
        """Get events a user is participating in.
        
        Args:
            user_id: User ID
            
        Returns:
            List of events
        """
        try:
            response = self.client.from_("event_participants").select("""
                registration_time, status,
                community_events(*)
            """).eq("user_id", user_id).execute()
            
            events = []
            for item in response.data or []:
                if item.get('community_events'):
                    event = item['community_events']
                    event['user_registration_time'] = item['registration_time']
                    event['user_status'] = item['status']
                    events.append(event)
            
            return events
            
        except Exception as e:
            logger.error(f"Error getting user events: {e}")
            return []
    
    # =====================================================
    # SEARCH AND DISCOVERY
    # =====================================================
    
    def search_teams(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Search for teams.
        
        Args:
            query: Search query
            limit: Maximum number of results
            
        Returns:
            List of matching teams
        """
        try:
            response = self.client.from_("teams").select("*").or_(
                f"name.ilike.%{query}%,description.ilike.%{query}%"
            ).eq("privacy_level", PrivacyLevel.PUBLIC.value).limit(limit).execute()
            
            teams = response.data or []
            
            # Add member counts
            for team in teams:
                team['member_count'] = self.get_team_member_count(team['id'])
            
            return teams
            
        except Exception as e:
            logger.error(f"Error searching teams: {e}")
            return []
    
    def search_clubs(self, query: str = None, category: str = None, limit: int = 20) -> List[Dict[str, Any]]:
        """Search for clubs.
        
        Args:
            query: Search query
            category: Club category filter
            limit: Maximum number of results
            
        Returns:
            List of matching clubs
        """
        try:
            query_builder = self.client.from_("clubs").select("*").eq("privacy_level", PrivacyLevel.PUBLIC.value)
            
            if query:
                query_builder = query_builder.or_(f"name.ilike.%{query}%,description.ilike.%{query}%")
            
            if category:
                query_builder = query_builder.eq("category", category)
            
            response = query_builder.limit(limit).execute()
            
            return response.data or []
            
        except Exception as e:
            logger.error(f"Error searching clubs: {e}")
            return []
    
    # =====================================================
    # UTILITY METHODS
    # =====================================================
    
    def get_team_member_count(self, team_id: str) -> int:
        """Get team member count.
        
        Args:
            team_id: Team ID
            
        Returns:
            Number of members
        """
        try:
            response = self.client.from_("team_members").select("id", count="exact").eq("team_id", team_id).execute()
            return response.count or 0
        except Exception as e:
            logger.error(f"Error getting team member count: {e}")
            return 0
    
    def get_team_member_role(self, team_id: str, user_id: str) -> Optional[str]:
        """Get user's role in a team.
        
        Args:
            team_id: Team ID
            user_id: User ID
            
        Returns:
            User's role or None
        """
        try:
            response = self.client.from_("team_members").select("role").eq("team_id", team_id).eq("user_id", user_id).single().execute()
            return response.data.get('role') if response.data else None
        except Exception as e:
            logger.error(f"Error getting team member role: {e}")
            return None
    
    def get_event_participant_count(self, event_id: str) -> int:
        """Get event participant count.
        
        Args:
            event_id: Event ID
            
        Returns:
            Number of participants
        """
        try:
            response = self.client.from_("event_participants").select("id", count="exact").eq("event_id", event_id).execute()
            return response.count or 0
        except Exception as e:
            logger.error(f"Error getting event participant count: {e}")
            return 0
    
    def disband_team(self, team_id: str, user_id: str) -> Dict[str, Any]:
        """Disband a team (owner only).
        
        Args:
            team_id: Team ID
            user_id: User ID (must be owner)
            
        Returns:
            Dictionary with success status and message
        """
        try:
            # Verify user is owner
            role = self.get_team_member_role(team_id, user_id)
            if role != TeamRole.OWNER.value:
                return {"success": False, "message": "Only team owner can disband the team"}
            
            # Delete team (this will cascade delete members)
            delete_response = self.client.from_("teams").delete().eq("id", team_id).execute()
            
            if delete_response.data:
                logger.info(f"Team {team_id} disbanded by user {user_id}")
                return {"success": True, "message": "Team disbanded successfully"}
            
            return {"success": False, "message": "Failed to disband team"}
            
        except Exception as e:
            logger.error(f"Error disbanding team: {e}")
            return {"success": False, "message": "Failed to disband team"}
    
    def _check_event_requirements(self, user_id: str, requirements: Dict[str, Any]) -> bool:
        """Check if user meets event entry requirements.
        
        Args:
            user_id: User ID
            requirements: Entry requirements
            
        Returns:
            True if requirements are met, False otherwise
        """
        try:
            # Get user profile and stats
            from .user_manager import enhanced_user_manager
            user_profile = enhanced_user_manager.get_complete_user_profile(user_id)
            if not user_profile:
                return False
            
            # Check various requirements
            for req_type, req_value in requirements.items():
                if req_type == 'min_level':
                    if user_profile.get('level', 1) < req_value:
                        return False
                elif req_type == 'min_reputation':
                    if user_profile.get('reputation_score', 0) < req_value:
                        return False
                elif req_type == 'min_laps':
                    if user_profile.get('total_laps', 0) < req_value:
                        return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking event requirements: {e}")
            return False
    
    def _create_team_activity(self, user_id: str, activity_type: str, metadata: Dict[str, Any]):
        """Create a team-related activity."""
        try:
            from .activity_manager import activity_manager, ActivityType
            
            activity_titles = {
                'team_created': f"Created team '{metadata.get('team_name', 'Unknown')}'",
                'team_joined': f"Joined team '{metadata.get('team_name', 'Unknown')}'",
                'team_left': f"Left team '{metadata.get('team_name', 'Unknown')}'"
            }
            
            activity_manager.create_activity(
                user_id=user_id,
                activity_type=ActivityType.TEAM_JOINED,
                title=activity_titles.get(activity_type, "Team activity"),
                description=f"Team activity: {activity_type}",
                metadata=metadata
            )
            
        except Exception as e:
            logger.error(f"Error creating team activity: {e}")
    
    def _create_club_activity(self, user_id: str, activity_type: str, metadata: Dict[str, Any]):
        """Create a club-related activity."""
        try:
            from .activity_manager import activity_manager, ActivityType
            
            activity_titles = {
                'club_created': f"Created club '{metadata.get('club_name', 'Unknown')}'",
                'club_joined': f"Joined club '{metadata.get('club_name', 'Unknown')}'"
            }
            
            activity_manager.create_activity(
                user_id=user_id,
                activity_type=ActivityType.GROUP_JOINED,
                title=activity_titles.get(activity_type, "Club activity"),
                description=f"Club activity: {activity_type}",
                metadata=metadata
            )
            
        except Exception as e:
            logger.error(f"Error creating club activity: {e}")
    
    def _create_event_activity(self, user_id: str, activity_type: str, metadata: Dict[str, Any]):
        """Create an event-related activity."""
        try:
            from .activity_manager import activity_manager, ActivityType
            
            activity_titles = {
                'event_created': f"Created event '{metadata.get('event_title', 'Unknown')}'",
                'event_joined': f"Registered for event '{metadata.get('event_title', 'Unknown')}'"
            }
            
            activity_manager.create_activity(
                user_id=user_id,
                activity_type=ActivityType.EVENT_PARTICIPATED,
                title=activity_titles.get(activity_type, "Event activity"),
                description=f"Event activity: {activity_type}",
                metadata=metadata
            )
            
        except Exception as e:
            logger.error(f"Error creating event activity: {e}")

# Create a global instance
community_manager = CommunityManager() 