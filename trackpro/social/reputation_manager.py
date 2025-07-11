"""Reputation Manager for community standing and moderation system."""

import logging
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from enum import Enum
from ..database.base import DatabaseManager
from ..database.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)

class ReputationEventType(Enum):
    """Reputation event type enumeration."""
    HELPFUL = "helpful"
    SPORTSMANLIKE = "sportsmanlike"
    TOXIC = "toxic"
    SPAM = "spam"
    CHEATING = "cheating"
    MENTORSHIP = "mentorship"
    CONTENT_QUALITY = "content_quality"
    COMMUNITY_CONTRIBUTION = "community_contribution"

class ReputationLevel(Enum):
    """Reputation level enumeration."""
    NEWCOMER = "newcomer"
    MEMBER = "member"
    TRUSTED = "trusted"
    VETERAN = "veteran"
    MENTOR = "mentor"
    LEGEND = "legend"

class ReputationManager(DatabaseManager):
    """Comprehensive reputation and community standing system."""
    
    def __init__(self):
        """Initialize the reputation manager."""
        super().__init__("reputation_events")
        self.supabase = get_supabase_client()
        
        # Reputation point values for different events
        self.reputation_values = {
            ReputationEventType.HELPFUL.value: 5,
            ReputationEventType.SPORTSMANLIKE.value: 3,
            ReputationEventType.TOXIC.value: -10,
            ReputationEventType.SPAM.value: -5,
            ReputationEventType.CHEATING.value: -50,
            ReputationEventType.MENTORSHIP.value: 10,
            ReputationEventType.CONTENT_QUALITY.value: 8,
            ReputationEventType.COMMUNITY_CONTRIBUTION.value: 15
        }
        
        # Reputation level thresholds
        self.reputation_levels = {
            ReputationLevel.NEWCOMER.value: 0,
            ReputationLevel.MEMBER.value: 50,
            ReputationLevel.TRUSTED.value: 200,
            ReputationLevel.VETERAN.value: 500,
            ReputationLevel.MENTOR.value: 1000,
            ReputationLevel.LEGEND.value: 2000
        }
    
    # =====================================================
    # REPUTATION EVENTS
    # =====================================================
    
    def add_reputation_event(self, user_id: str, given_by: str, event_type: ReputationEventType, 
                           reason: str = "", metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """Add a reputation event for a user.
        
        Args:
            user_id: User ID receiving the reputation
            given_by: User ID giving the reputation
            event_type: Type of reputation event
            reason: Reason for the reputation event
            metadata: Additional metadata
            
        Returns:
            Dictionary with success status and reputation change
        """
        try:
            # Prevent self-reputation
            if user_id == given_by:
                return {"success": False, "message": "Cannot give reputation to yourself"}
            
            # Check if giver has permission to give this type of reputation
            if not self._can_give_reputation(given_by, event_type):
                return {"success": False, "message": "Insufficient permissions to give this type of reputation"}
            
            # Check for recent duplicate events from same giver
            if self._has_recent_duplicate(user_id, given_by, event_type):
                return {"success": False, "message": "You have already given this type of reputation recently"}
            
            # Calculate reputation points
            points = self.reputation_values.get(event_type.value, 0)
            
            # Create reputation event
            event_data = {
                'user_id': user_id,
                'given_by': given_by,
                'event_type': event_type.value,
                'points': points,
                'reason': reason,
                'metadata': metadata or {},
                'created_at': datetime.utcnow().isoformat()
            }
            
            response = self.client.from_("reputation_events").insert(event_data).execute()
            if not response.data:
                return {"success": False, "message": "Failed to add reputation event"}
            
            # Update user's total reputation score
            new_reputation = self._update_user_reputation(user_id)
            
            # Check for reputation level changes
            level_change = self._check_reputation_level_change(user_id, new_reputation)
            
            # Create activity if significant reputation change
            if abs(points) >= 10:
                self._create_reputation_activity(user_id, event_type, points, given_by)
            
            logger.info(f"Reputation event {event_type.value} ({points} points) added for user {user_id} by {given_by}")
            
            result = {
                "success": True,
                "points_awarded": points,
                "new_reputation": new_reputation,
                "message": f"Reputation {event_type.value} recorded"
            }
            
            if level_change:
                result["level_change"] = level_change
            
            return result
            
        except Exception as e:
            logger.error(f"Error adding reputation event: {e}")
            return {"success": False, "message": "Failed to add reputation event"}
    
    def get_user_reputation_events(self, user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get reputation events for a user.
        
        Args:
            user_id: User ID
            limit: Maximum number of events
            
        Returns:
            List of reputation events
        """
        try:
            response = self.client.from_("reputation_events").select("""
                *,
                user_profiles!reputation_events_given_by_fkey(username, display_name, avatar_url)
            """).eq("user_id", user_id).order("created_at", desc=True).limit(limit).execute()
            
            return response.data or []
            
        except Exception as e:
            logger.error(f"Error getting user reputation events: {e}")
            return []
    
    def get_reputation_summary(self, user_id: str, days: int = 30) -> Dict[str, Any]:
        """Get reputation summary for a user.
        
        Args:
            user_id: User ID
            days: Number of days to analyze
            
        Returns:
            Reputation summary
        """
        try:
            cutoff_date = (datetime.utcnow() - timedelta(days=days)).isoformat()
            
            # Get events in the time period
            response = self.client.from_("reputation_events").select("event_type, points").eq("user_id", user_id).gte("created_at", cutoff_date).execute()
            
            events = response.data or []
            
            # Calculate summary
            total_points = sum(event['points'] for event in events)
            event_counts = {}
            positive_points = 0
            negative_points = 0
            
            for event in events:
                event_type = event['event_type']
                points = event['points']
                
                event_counts[event_type] = event_counts.get(event_type, 0) + 1
                
                if points > 0:
                    positive_points += points
                else:
                    negative_points += points
            
            # Get current reputation and level
            from .user_manager import enhanced_user_manager
            user_profile = enhanced_user_manager.get_complete_user_profile(user_id)
            current_reputation = user_profile.get('reputation_score', 0) if user_profile else 0
            current_level = self.get_reputation_level(current_reputation)
            
            return {
                'current_reputation': current_reputation,
                'current_level': current_level,
                'period_days': days,
                'total_events': len(events),
                'total_points_change': total_points,
                'positive_points': positive_points,
                'negative_points': negative_points,
                'event_breakdown': event_counts
            }
            
        except Exception as e:
            logger.error(f"Error getting reputation summary: {e}")
            return {}
    
    # =====================================================
    # REPUTATION LEVELS AND RANKINGS
    # =====================================================
    
    def get_reputation_level(self, reputation_score: int) -> str:
        """Get reputation level based on score.
        
        Args:
            reputation_score: Current reputation score
            
        Returns:
            Reputation level
        """
        for level in reversed(list(ReputationLevel)):
            if reputation_score >= self.reputation_levels[level.value]:
                return level.value
        
        return ReputationLevel.NEWCOMER.value
    
    def get_reputation_level_info(self, user_id: str) -> Dict[str, Any]:
        """Get detailed reputation level information for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            Reputation level information
        """
        try:
            # Get current reputation
            from .user_manager import enhanced_user_manager
            user_profile = enhanced_user_manager.get_complete_user_profile(user_id)
            current_reputation = user_profile.get('reputation_score', 0) if user_profile else 0
            
            current_level = self.get_reputation_level(current_reputation)
            
            # Find next level
            next_level = None
            points_to_next = None
            
            for level in ReputationLevel:
                threshold = self.reputation_levels[level.value]
                if threshold > current_reputation:
                    next_level = level.value
                    points_to_next = threshold - current_reputation
                    break
            
            # Calculate progress percentage
            current_threshold = self.reputation_levels[current_level]
            if next_level:
                next_threshold = self.reputation_levels[next_level]
                progress = ((current_reputation - current_threshold) / (next_threshold - current_threshold)) * 100
            else:
                progress = 100  # Max level reached
            
            return {
                'current_reputation': current_reputation,
                'current_level': current_level,
                'next_level': next_level,
                'points_to_next': points_to_next,
                'progress_percentage': min(100, max(0, progress)),
                'level_benefits': self._get_level_benefits(current_level)
            }
            
        except Exception as e:
            logger.error(f"Error getting reputation level info: {e}")
            return {}
    
    def get_reputation_leaderboard(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get reputation leaderboard.
        
        Args:
            limit: Maximum number of users
            
        Returns:
            List of users ordered by reputation
        """
        try:
            response = self.client.from_("user_profiles").select(
                "user_id, username, display_name, avatar_url, reputation_score, level"
            ).order("reputation_score", desc=True).limit(limit).execute()
            
            users = response.data or []
            
            # Add reputation level and rank
            for i, user in enumerate(users):
                user['rank'] = i + 1
                user['reputation_level'] = self.get_reputation_level(user.get('reputation_score', 0))
            
            return users
            
        except Exception as e:
            logger.error(f"Error getting reputation leaderboard: {e}")
            return []
    
    # =====================================================
    # MODERATION AND REPORTING
    # =====================================================
    
    def report_user(self, reporter_id: str, reported_id: str, reason: str, 
                   report_type: str, evidence: Dict[str, Any] = None) -> Dict[str, Any]:
        """Report a user for misconduct.
        
        Args:
            reporter_id: User ID of reporter
            reported_id: User ID of reported user
            reason: Reason for report
            report_type: Type of report (toxic, spam, cheating, etc.)
            evidence: Evidence supporting the report
            
        Returns:
            Dictionary with success status
        """
        try:
            # Prevent self-reporting
            if reporter_id == reported_id:
                return {"success": False, "message": "Cannot report yourself"}
            
            # Check for recent duplicate reports
            recent_cutoff = (datetime.utcnow() - timedelta(hours=24)).isoformat()
            existing_report = self.client.from_("user_reports").select("id").eq("reporter_id", reporter_id).eq("reported_id", reported_id).gte("created_at", recent_cutoff).execute()
            
            if existing_report.data:
                return {"success": False, "message": "You have already reported this user recently"}
            
            # Create report record
            report_data = {
                'reporter_id': reporter_id,
                'reported_id': reported_id,
                'reason': reason,
                'report_type': report_type,
                'evidence': evidence or {},
                'status': 'pending',
                'created_at': datetime.utcnow().isoformat()
            }
            
            # Note: This would require a user_reports table
            # For now, we'll create a negative reputation event
            if report_type in ['toxic', 'spam', 'cheating']:
                event_type = ReputationEventType(report_type)
                self.add_reputation_event(
                    user_id=reported_id,
                    given_by=reporter_id,
                    event_type=event_type,
                    reason=f"Reported for {report_type}: {reason}"
                )
            
            logger.info(f"User {reported_id} reported by {reporter_id} for {report_type}")
            return {"success": True, "message": "Report submitted successfully"}
            
        except Exception as e:
            logger.error(f"Error reporting user: {e}")
            return {"success": False, "message": "Failed to submit report"}
    
    def get_user_standing(self, user_id: str) -> Dict[str, Any]:
        """Get user's community standing and any restrictions.
        
        Args:
            user_id: User ID
            
        Returns:
            User standing information
        """
        try:
            # Get reputation score
            from .user_manager import enhanced_user_manager
            user_profile = enhanced_user_manager.get_complete_user_profile(user_id)
            reputation_score = user_profile.get('reputation_score', 0) if user_profile else 0
            
            # Calculate standing
            standing = "good"
            restrictions = []
            warnings = []
            
            if reputation_score < -50:
                standing = "poor"
                restrictions.extend([
                    "Limited messaging privileges",
                    "Cannot create teams or clubs",
                    "Cannot participate in community events"
                ])
            elif reputation_score < -20:
                standing = "warning"
                warnings.append("Your reputation is low. Please improve your community behavior.")
            elif reputation_score < 0:
                standing = "neutral"
                warnings.append("Your reputation is slightly negative. Consider being more helpful to the community.")
            
            # Check for recent negative events
            recent_cutoff = (datetime.utcnow() - timedelta(days=7)).isoformat()
            recent_negative = self.client.from_("reputation_events").select("points").eq("user_id", user_id).lt("points", 0).gte("created_at", recent_cutoff).execute()
            
            if recent_negative.data and len(recent_negative.data) >= 3:
                warnings.append("You have received multiple negative reputation events recently.")
            
            return {
                'reputation_score': reputation_score,
                'reputation_level': self.get_reputation_level(reputation_score),
                'standing': standing,
                'restrictions': restrictions,
                'warnings': warnings,
                'can_give_reputation': self._can_give_reputation(user_id, ReputationEventType.HELPFUL),
                'can_create_content': reputation_score >= -20,
                'can_moderate': reputation_score >= 100
            }
            
        except Exception as e:
            logger.error(f"Error getting user standing: {e}")
            return {}
    
    # =====================================================
    # UTILITY METHODS
    # =====================================================
    
    def _update_user_reputation(self, user_id: str) -> int:
        """Update user's total reputation score.
        
        Args:
            user_id: User ID
            
        Returns:
            New reputation score
        """
        try:
            # Calculate total reputation from all events
            response = self.client.from_("reputation_events").select("points").eq("user_id", user_id).execute()
            
            events = response.data or []
            total_reputation = sum(event['points'] for event in events)
            
            # Update user profile
            from .user_manager import enhanced_user_manager
            enhanced_user_manager.update_user_profile(user_id, {
                'reputation_score': total_reputation
            })
            
            return total_reputation
            
        except Exception as e:
            logger.error(f"Error updating user reputation: {e}")
            return 0
    
    def _check_reputation_level_change(self, user_id: str, new_reputation: int) -> Optional[Dict[str, Any]]:
        """Check if user's reputation level changed.
        
        Args:
            user_id: User ID
            new_reputation: New reputation score
            
        Returns:
            Level change information or None
        """
        try:
            # Get previous reputation level
            # This would require storing previous level or calculating from history
            # For now, we'll just return the current level
            new_level = self.get_reputation_level(new_reputation)
            
            # Create level change activity if significant
            if new_reputation in self.reputation_levels.values():
                self._create_reputation_level_activity(user_id, new_level, new_reputation)
                return {
                    'new_level': new_level,
                    'reputation_score': new_reputation
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error checking reputation level change: {e}")
            return None
    
    def _can_give_reputation(self, giver_id: str, event_type: ReputationEventType) -> bool:
        """Check if user can give a specific type of reputation.
        
        Args:
            giver_id: User ID of giver
            event_type: Type of reputation event
            
        Returns:
            True if can give, False otherwise
        """
        try:
            # Get giver's reputation
            from .user_manager import enhanced_user_manager
            giver_profile = enhanced_user_manager.get_complete_user_profile(giver_id)
            if not giver_profile:
                return False
            
            giver_reputation = giver_profile.get('reputation_score', 0)
            
            # Basic requirements
            if giver_reputation < 0:
                return False  # Negative reputation users can't give reputation
            
            # Special requirements for certain event types
            if event_type in [ReputationEventType.TOXIC, ReputationEventType.SPAM, ReputationEventType.CHEATING]:
                return giver_reputation >= 50  # Need some reputation to report
            
            if event_type == ReputationEventType.MENTORSHIP:
                return giver_reputation >= 200  # Need high reputation for mentorship
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking reputation permissions: {e}")
            return False
    
    def _has_recent_duplicate(self, user_id: str, given_by: str, event_type: ReputationEventType) -> bool:
        """Check if giver has recently given same type of reputation to user.
        
        Args:
            user_id: User ID receiving reputation
            given_by: User ID giving reputation
            event_type: Type of reputation event
            
        Returns:
            True if recent duplicate exists, False otherwise
        """
        try:
            # Check last 24 hours for duplicates
            cutoff_date = (datetime.utcnow() - timedelta(hours=24)).isoformat()
            
            response = self.client.from_("reputation_events").select("id").eq("user_id", user_id).eq("given_by", given_by).eq("event_type", event_type.value).gte("created_at", cutoff_date).execute()
            
            return len(response.data or []) > 0
            
        except Exception as e:
            logger.error(f"Error checking recent duplicates: {e}")
            return False
    
    def _get_level_benefits(self, level: str) -> List[str]:
        """Get benefits for a reputation level.
        
        Args:
            level: Reputation level
            
        Returns:
            List of benefits
        """
        benefits = {
            ReputationLevel.NEWCOMER.value: [
                "Basic community access"
            ],
            ReputationLevel.MEMBER.value: [
                "Can give positive reputation",
                "Can create teams and clubs"
            ],
            ReputationLevel.TRUSTED.value: [
                "Can report users",
                "Priority in event queues",
                "Special avatar frames"
            ],
            ReputationLevel.VETERAN.value: [
                "Can moderate community content",
                "Exclusive veteran events",
                "Mentorship program access"
            ],
            ReputationLevel.MENTOR.value: [
                "Can mentor new users",
                "Special mentor badge",
                "Early access to features"
            ],
            ReputationLevel.LEGEND.value: [
                "Legendary status badge",
                "Community recognition",
                "Input on community decisions"
            ]
        }
        
        return benefits.get(level, [])
    
    def _create_reputation_activity(self, user_id: str, event_type: ReputationEventType, points: int, given_by: str):
        """Create activity for significant reputation changes."""
        try:
            from .activity_manager import activity_manager, ActivityType
            
            if points > 0:
                title = f"Received {points} reputation points"
                description = f"Recognized for {event_type.value} behavior"
            else:
                title = f"Lost {abs(points)} reputation points"
                description = f"Reported for {event_type.value} behavior"
            
            activity_manager.create_activity(
                user_id=user_id,
                activity_type=ActivityType.PROFILE_UPDATED,
                title=title,
                description=description,
                metadata={
                    'reputation_change': points,
                    'event_type': event_type.value,
                    'given_by': given_by
                }
            )
            
        except Exception as e:
            logger.error(f"Error creating reputation activity: {e}")
    
    def _create_reputation_level_activity(self, user_id: str, new_level: str, reputation_score: int):
        """Create activity for reputation level changes."""
        try:
            from .activity_manager import activity_manager, ActivityType
            
            activity_manager.create_activity(
                user_id=user_id,
                activity_type=ActivityType.LEVEL_UP,
                title=f"Reached {new_level} reputation level!",
                description=f"Achieved {new_level} status with {reputation_score} reputation points",
                metadata={
                    'reputation_level': new_level,
                    'reputation_score': reputation_score
                }
            )
            
        except Exception as e:
            logger.error(f"Error creating reputation level activity: {e}")

# Create a global instance
# Note: Global instance creation removed to prevent import-time initialization
# Use trackpro.social.reputation_manager or trackpro.social.get_reputation_manager() instead 