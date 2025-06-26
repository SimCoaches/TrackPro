"""Achievements Manager for comprehensive gamification and achievement system."""

import logging
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timedelta, date
from enum import Enum
from ..database.base import DatabaseManager
from ..database.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)

class AchievementRarity(Enum):
    """Achievement rarity enumeration."""
    COMMON = "common"
    RARE = "rare"
    EPIC = "epic"
    LEGENDARY = "legendary"

class AchievementCategory(Enum):
    """Achievement category enumeration."""
    RACING = "racing"
    SOCIAL = "social"
    COLLECTION = "collection"
    MILESTONE = "milestone"
    SPECIAL = "special"

class StreakType(Enum):
    """Streak type enumeration."""
    LOGIN = "login"
    PRACTICE = "practice"
    IMPROVEMENT = "improvement"
    SOCIAL = "social"
    CHALLENGE = "challenge"

class XPType(Enum):
    """XP type enumeration."""
    RACING = "racing"
    SOCIAL = "social"
    LEARNING = "learning"
    COACHING = "coaching"

class AchievementsManager(DatabaseManager):
    """Comprehensive achievements and gamification system."""
    
    def __init__(self):
        """Initialize the achievements manager."""
        super().__init__("achievements")
        self.supabase = get_supabase_client()
    
    # =====================================================
    # ACHIEVEMENT MANAGEMENT
    # =====================================================
    
    def unlock_achievement(self, user_id: str, achievement_id: str, progress_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """Unlock an achievement for a user.
        
        Args:
            user_id: User ID
            achievement_id: Achievement ID
            progress_data: Achievement progress data
            
        Returns:
            Dictionary with success status and achievement data
        """
        try:
            # Get achievement info
            achievement_response = self.client.from_("achievements").select("*").eq("id", achievement_id).single().execute()
            if not achievement_response.data:
                return {"success": False, "message": "Achievement not found"}
            
            achievement = achievement_response.data
            
            # Check if user already has this achievement
            existing_achievement = self.client.from_("user_achievements").select("*").eq("user_id", user_id).eq("achievement_id", achievement_id).single().execute()
            if existing_achievement.data and existing_achievement.data.get('unlocked_at'):
                return {"success": False, "message": "Achievement already unlocked"}
            
            # Unlock achievement
            unlock_data = {
                'user_id': user_id,
                'achievement_id': achievement_id,
                'progress': progress_data or {},
                'unlocked_at': datetime.utcnow().isoformat(),
                'is_showcased': achievement['rarity'] in [AchievementRarity.EPIC.value, AchievementRarity.LEGENDARY.value]
            }
            
            if existing_achievement.data:
                # Update existing record
                response = self.client.from_("user_achievements").update(unlock_data).eq("user_id", user_id).eq("achievement_id", achievement_id).execute()
            else:
                # Insert new record
                response = self.client.from_("user_achievements").insert(unlock_data).execute()
            
            if not response.data:
                return {"success": False, "message": "Failed to unlock achievement"}
            
            # Award XP
            xp_reward = achievement.get('xp_reward', 0)
            if xp_reward > 0:
                self.award_xp(user_id, xp_reward, XPType.RACING, f"Achievement: {achievement['name']}")
            
            # Create activity
            from .activity_manager import activity_manager
            activity_manager.create_achievement_activity(
                user_id=user_id,
                achievement_id=achievement_id,
                achievement_name=achievement['name'],
                achievement_rarity=achievement['rarity']
            )
            
            logger.info(f"Achievement '{achievement['name']}' unlocked for user {user_id}")
            return {
                "success": True,
                "message": "Achievement unlocked!",
                "achievement": achievement,
                "xp_reward": xp_reward
            }
            
        except Exception as e:
            logger.error(f"Error unlocking achievement: {e}")
            return {"success": False, "message": "Failed to unlock achievement"}
    
    def update_achievement_progress(self, user_id: str, achievement_id: str, progress_data: Dict[str, Any]) -> bool:
        """Update progress towards an achievement.
        
        Args:
            user_id: User ID
            achievement_id: Achievement ID
            progress_data: Progress data to update
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get or create user achievement record
            existing_record = self.client.from_("user_achievements").select("*").eq("user_id", user_id).eq("achievement_id", achievement_id).single().execute()
            
            if existing_record.data:
                # Update existing progress
                current_progress = existing_record.data.get('progress', {})
                current_progress.update(progress_data)
                
                response = self.client.from_("user_achievements").update({
                    'progress': current_progress
                }).eq("user_id", user_id).eq("achievement_id", achievement_id).execute()
            else:
                # Create new progress record
                progress_record = {
                    'user_id': user_id,
                    'achievement_id': achievement_id,
                    'progress': progress_data,
                    'unlocked_at': None,
                    'is_showcased': False
                }
                
                response = self.client.from_("user_achievements").insert(progress_record).execute()
            
            # Check if achievement should be unlocked
            if self._check_achievement_completion(user_id, achievement_id):
                self.unlock_achievement(user_id, achievement_id, progress_data)
            
            return bool(response.data)
            
        except Exception as e:
            logger.error(f"Error updating achievement progress: {e}")
            return False
    
    def get_user_achievements(self, user_id: str, unlocked_only: bool = False) -> List[Dict[str, Any]]:
        """Get user's achievements.
        
        Args:
            user_id: User ID
            unlocked_only: If True, only return unlocked achievements
            
        Returns:
            List of user achievements
        """
        try:
            query = self.client.from_("user_achievements").select("""
                *,
                achievements(*)
            """).eq("user_id", user_id)
            
            if unlocked_only:
                query = query.not_.is_("unlocked_at", "null")
            
            response = query.order("unlocked_at", desc=True).execute()
            
            achievements = []
            for item in response.data or []:
                if item.get('achievements'):
                    achievement = item['achievements']
                    achievement['user_progress'] = item['progress']
                    achievement['unlocked_at'] = item['unlocked_at']
                    achievement['is_showcased'] = item['is_showcased']
                    achievement['is_unlocked'] = bool(item['unlocked_at'])
                    achievements.append(achievement)
            
            return achievements
            
        except Exception as e:
            logger.error(f"Error getting user achievements: {e}")
            return []
    
    def get_showcased_achievements(self, user_id: str) -> List[Dict[str, Any]]:
        """Get user's showcased achievements.
        
        Args:
            user_id: User ID
            
        Returns:
            List of showcased achievements
        """
        try:
            response = self.client.from_("user_achievements").select("""
                *,
                achievements(*)
            """).eq("user_id", user_id).eq("is_showcased", True).not_.is_("unlocked_at", "null").execute()
            
            achievements = []
            for item in response.data or []:
                if item.get('achievements'):
                    achievement = item['achievements']
                    achievement['unlocked_at'] = item['unlocked_at']
                    achievements.append(achievement)
            
            return achievements
            
        except Exception as e:
            logger.error(f"Error getting showcased achievements: {e}")
            return []
    
    def toggle_achievement_showcase(self, user_id: str, achievement_id: str) -> Dict[str, Any]:
        """Toggle achievement showcase status.
        
        Args:
            user_id: User ID
            achievement_id: Achievement ID
            
        Returns:
            Dictionary with success status and new showcase status
        """
        try:
            # Get current status
            response = self.client.from_("user_achievements").select("is_showcased, unlocked_at").eq("user_id", user_id).eq("achievement_id", achievement_id).single().execute()
            
            if not response.data or not response.data.get('unlocked_at'):
                return {"success": False, "message": "Achievement not unlocked"}
            
            current_showcased = response.data.get('is_showcased', False)
            new_showcased = not current_showcased
            
            # Update showcase status
            update_response = self.client.from_("user_achievements").update({
                'is_showcased': new_showcased
            }).eq("user_id", user_id).eq("achievement_id", achievement_id).execute()
            
            if update_response.data:
                return {
                    "success": True,
                    "is_showcased": new_showcased,
                    "message": "Showcased" if new_showcased else "Removed from showcase"
                }
            
            return {"success": False, "message": "Failed to update showcase status"}
            
        except Exception as e:
            logger.error(f"Error toggling achievement showcase: {e}")
            return {"success": False, "message": "Failed to update showcase status"}
    
    # =====================================================
    # XP AND LEVELING SYSTEM
    # =====================================================
    
    def award_xp(self, user_id: str, amount: int, xp_type: XPType, reason: str = "") -> Dict[str, Any]:
        """Award XP to a user.
        
        Args:
            user_id: User ID
            amount: XP amount to award
            xp_type: Type of XP
            reason: Reason for XP award
            
        Returns:
            Dictionary with XP award results
        """
        try:
            # Get current user profile
            from .user_manager import enhanced_user_manager
            user_profile = enhanced_user_manager.get_complete_user_profile(user_id)
            if not user_profile:
                return {"success": False, "message": "User not found"}
            
            # Calculate new XP values
            current_total_xp = user_profile.get('total_xp', 0)
            current_type_xp = user_profile.get(f'{xp_type.value}_xp', 0)
            current_level = user_profile.get('level', 1)
            
            new_total_xp = current_total_xp + amount
            new_type_xp = current_type_xp + amount
            
            # Calculate new level
            new_level = self._calculate_level_from_xp(new_total_xp)
            level_up = new_level > current_level
            
            # Update user profile
            update_data = {
                'total_xp': new_total_xp,
                f'{xp_type.value}_xp': new_type_xp,
                'level': new_level
            }
            
            enhanced_user_manager.update_user_profile(user_id, update_data)
            
            # Create XP award record
            xp_record = {
                'user_id': user_id,
                'amount': amount,
                'xp_type': xp_type.value,
                'reason': reason,
                'awarded_at': datetime.utcnow().isoformat()
            }
            
            # Note: This would require an xp_awards table in the database
            # For now, we'll just log it
            logger.info(f"Awarded {amount} {xp_type.value} XP to user {user_id}: {reason}")
            
            result = {
                "success": True,
                "xp_awarded": amount,
                "new_total_xp": new_total_xp,
                "new_level": new_level,
                "level_up": level_up
            }
            
            # Handle level up
            if level_up:
                result.update(self._handle_level_up(user_id, current_level, new_level))
            
            return result
            
        except Exception as e:
            logger.error(f"Error awarding XP: {e}")
            return {"success": False, "message": "Failed to award XP"}
    
    def _calculate_level_from_xp(self, total_xp: int) -> int:
        """Calculate level from total XP.
        
        Args:
            total_xp: Total XP amount
            
        Returns:
            User level
        """
        # Simple formula: level = sqrt(total_xp / 1000) + 1
        # This creates a curve where each level requires more XP
        import math
        return max(1, int(math.sqrt(total_xp / 1000)) + 1)
    
    def _handle_level_up(self, user_id: str, old_level: int, new_level: int) -> Dict[str, Any]:
        """Handle level up rewards and notifications.
        
        Args:
            user_id: User ID
            old_level: Previous level
            new_level: New level
            
        Returns:
            Level up rewards and info
        """
        try:
            # Create level up activity
            from .activity_manager import activity_manager, ActivityType
            activity_manager.create_activity(
                user_id=user_id,
                activity_type=ActivityType.LEVEL_UP,
                title=f"Reached level {new_level}!",
                description=f"Leveled up from {old_level} to {new_level}",
                metadata={'old_level': old_level, 'new_level': new_level}
            )
            
            # Check for level-based achievement unlocks
            self._check_level_achievements(user_id, new_level)
            
            # Calculate rewards (could include XP bonus, avatar frames, etc.)
            rewards = []
            if new_level % 5 == 0:  # Every 5 levels
                rewards.append(f"Milestone reward for reaching level {new_level}")
            
            if new_level % 10 == 0:  # Every 10 levels
                rewards.append("Special avatar frame unlocked")
            
            logger.info(f"User {user_id} leveled up from {old_level} to {new_level}")
            
            return {
                "level_up_rewards": rewards,
                "milestone_reached": new_level % 5 == 0
            }
            
        except Exception as e:
            logger.error(f"Error handling level up: {e}")
            return {}
    
    # =====================================================
    # STREAK SYSTEM
    # =====================================================
    
    def update_streak(self, user_id: str, streak_type: StreakType) -> Dict[str, Any]:
        """Update a user's streak.
        
        Args:
            user_id: User ID
            streak_type: Type of streak
            
        Returns:
            Dictionary with streak information
        """
        try:
            today = date.today()
            
            # Get current streak
            streak_response = self.client.from_("user_streaks").select("*").eq("user_id", user_id).eq("streak_type", streak_type.value).single().execute()
            
            if streak_response.data:
                streak = streak_response.data
                last_activity_date = datetime.fromisoformat(streak['last_activity_date']).date() if streak['last_activity_date'] else None
                
                if last_activity_date == today:
                    # Already updated today
                    return {
                        "success": True,
                        "current_count": streak['current_count'],
                        "best_count": streak['best_count'],
                        "already_updated": True
                    }
                elif last_activity_date == today - timedelta(days=1):
                    # Continue streak
                    new_count = streak['current_count'] + 1
                    new_best = max(streak['best_count'], new_count)
                else:
                    # Streak broken, start new
                    new_count = 1
                    new_best = streak['best_count']
                
                # Update streak
                update_data = {
                    'current_count': new_count,
                    'best_count': new_best,
                    'last_activity_date': today.isoformat()
                }
                
                response = self.client.from_("user_streaks").update(update_data).eq("user_id", user_id).eq("streak_type", streak_type.value).execute()
            else:
                # Create new streak
                new_count = 1
                new_best = 1
                
                streak_data = {
                    'user_id': user_id,
                    'streak_type': streak_type.value,
                    'current_count': new_count,
                    'best_count': new_best,
                    'last_activity_date': today.isoformat(),
                    'started_at': datetime.utcnow().isoformat()
                }
                
                response = self.client.from_("user_streaks").insert(streak_data).execute()
            
            # Check for streak milestones
            milestone_reached = self._check_streak_milestones(user_id, streak_type, new_count)
            
            # Award XP for streak
            if new_count > 1:
                xp_amount = min(new_count * 10, 100)  # Cap at 100 XP
                self.award_xp(user_id, xp_amount, XPType.SOCIAL, f"{streak_type.value.title()} streak day {new_count}")
            
            return {
                "success": True,
                "current_count": new_count,
                "best_count": new_best,
                "milestone_reached": milestone_reached,
                "xp_awarded": min(new_count * 10, 100) if new_count > 1 else 0
            }
            
        except Exception as e:
            logger.error(f"Error updating streak: {e}")
            return {"success": False, "message": "Failed to update streak"}
    
    def get_user_streaks(self, user_id: str) -> List[Dict[str, Any]]:
        """Get user's current streaks.
        
        Args:
            user_id: User ID
            
        Returns:
            List of user streaks
        """
        try:
            response = self.client.from_("user_streaks").select("*").eq("user_id", user_id).execute()
            
            streaks = response.data or []
            
            # Check if streaks are still active (not broken)
            today = date.today()
            for streak in streaks:
                last_activity = datetime.fromisoformat(streak['last_activity_date']).date() if streak['last_activity_date'] else None
                if last_activity and (today - last_activity).days > 1:
                    streak['is_active'] = False
                else:
                    streak['is_active'] = True
            
            return streaks
            
        except Exception as e:
            logger.error(f"Error getting user streaks: {e}")
            return []
    
    def _check_streak_milestones(self, user_id: str, streak_type: StreakType, count: int) -> bool:
        """Check if streak milestone was reached.
        
        Args:
            user_id: User ID
            streak_type: Streak type
            count: Current streak count
            
        Returns:
            True if milestone reached, False otherwise
        """
        try:
            milestones = [7, 14, 30, 60, 100, 365]  # Days
            
            if count in milestones:
                # Create streak milestone activity
                from .activity_manager import activity_manager, ActivityType
                activity_manager.create_activity(
                    user_id=user_id,
                    activity_type=ActivityType.STREAK_MILESTONE,
                    title=f"{count}-day {streak_type.value} streak!",
                    description=f"Reached a {count}-day streak milestone",
                    metadata={'streak_type': streak_type.value, 'count': count}
                )
                
                # Award bonus XP for milestones
                bonus_xp = count * 5
                self.award_xp(user_id, bonus_xp, XPType.SOCIAL, f"{count}-day {streak_type.value} streak milestone")
                
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking streak milestones: {e}")
            return False
    
    # =====================================================
    # ACHIEVEMENT CHECKING AND AUTOMATION
    # =====================================================
    
    def check_racing_achievements(self, user_id: str, lap_data: Dict[str, Any]) -> List[str]:
        """Check and unlock racing-related achievements.
        
        Args:
            user_id: User ID
            lap_data: Lap data (time, track_id, car_id, etc.)
            
        Returns:
            List of unlocked achievement IDs
        """
        try:
            unlocked_achievements = []
            
            # Get user stats
            from .user_manager import enhanced_user_manager
            user_profile = enhanced_user_manager.get_complete_user_profile(user_id)
            if not user_profile:
                return unlocked_achievements
            
            total_laps = user_profile.get('total_laps', 0)
            lap_time = lap_data.get('lap_time')
            track_id = lap_data.get('track_id')
            
            # Check lap count achievements
            lap_milestones = [1, 10, 50, 100, 500, 1000, 5000]
            for milestone in lap_milestones:
                if total_laps == milestone:
                    achievement_id = self._get_achievement_by_criteria('racing', 'laps', milestone)
                    if achievement_id:
                        result = self.unlock_achievement(user_id, achievement_id, {'laps': total_laps})
                        if result.get('success'):
                            unlocked_achievements.append(achievement_id)
            
            # Check lap time achievements (track-specific)
            if lap_time and track_id:
                # This would check against predefined lap time targets for each track
                time_achievements = self._check_lap_time_achievements(user_id, track_id, lap_time)
                unlocked_achievements.extend(time_achievements)
            
            return unlocked_achievements
            
        except Exception as e:
            logger.error(f"Error checking racing achievements: {e}")
            return []
    
    def check_social_achievements(self, user_id: str, social_action: str, metadata: Dict[str, Any] = None) -> List[str]:
        """Check and unlock social-related achievements.
        
        Args:
            user_id: User ID
            social_action: Type of social action
            metadata: Additional metadata
            
        Returns:
            List of unlocked achievement IDs
        """
        try:
            unlocked_achievements = []
            
            if social_action == "friend_added":
                # Check friend count achievements
                from .friends_manager import friends_manager
                friend_count = friends_manager.get_friend_count(user_id)
                
                friend_milestones = [1, 5, 10, 25, 50, 100]
                for milestone in friend_milestones:
                    if friend_count == milestone:
                        achievement_id = self._get_achievement_by_criteria('social', 'friends', milestone)
                        if achievement_id:
                            result = self.unlock_achievement(user_id, achievement_id, {'friends': friend_count})
                            if result.get('success'):
                                unlocked_achievements.append(achievement_id)
            
            elif social_action == "message_sent":
                # Check messaging achievements
                # This would require tracking message counts
                pass
            
            return unlocked_achievements
            
        except Exception as e:
            logger.error(f"Error checking social achievements: {e}")
            return []
    
    def _check_achievement_completion(self, user_id: str, achievement_id: str) -> bool:
        """Check if achievement requirements are met.
        
        Args:
            user_id: User ID
            achievement_id: Achievement ID
            
        Returns:
            True if achievement should be unlocked, False otherwise
        """
        try:
            # Get achievement requirements
            achievement_response = self.client.from_("achievements").select("requirements").eq("id", achievement_id).single().execute()
            if not achievement_response.data:
                return False
            
            requirements = achievement_response.data.get('requirements', {})
            if not requirements:
                return True  # No requirements means auto-unlock
            
            # Get user progress
            progress_response = self.client.from_("user_achievements").select("progress").eq("user_id", user_id).eq("achievement_id", achievement_id).single().execute()
            progress = progress_response.data.get('progress', {}) if progress_response.data else {}
            
            # Check each requirement
            for req_key, req_value in requirements.items():
                user_value = progress.get(req_key, 0)
                if user_value < req_value:
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking achievement completion: {e}")
            return False
    
    def _check_level_achievements(self, user_id: str, level: int):
        """Check for level-based achievements.
        
        Args:
            user_id: User ID
            level: New level
        """
        try:
            level_milestones = [5, 10, 25, 50, 100]
            if level in level_milestones:
                achievement_id = self._get_achievement_by_criteria('milestone', 'level', level)
                if achievement_id:
                    self.unlock_achievement(user_id, achievement_id, {'level': level})
                    
        except Exception as e:
            logger.error(f"Error checking level achievements: {e}")
    
    def _get_achievement_by_criteria(self, category: str, criteria_type: str, value: int) -> Optional[str]:
        """Get achievement ID by criteria.
        
        Args:
            category: Achievement category
            criteria_type: Type of criteria
            value: Criteria value
            
        Returns:
            Achievement ID or None
        """
        try:
            # This would query achievements based on criteria
            # For now, return None as placeholder
            return None
            
        except Exception as e:
            logger.error(f"Error getting achievement by criteria: {e}")
            return None
    
    def _check_lap_time_achievements(self, user_id: str, track_id: int, lap_time: float) -> List[str]:
        """Check lap time achievements for a specific track.
        
        Args:
            user_id: User ID
            track_id: Track ID
            lap_time: Lap time in seconds
            
        Returns:
            List of unlocked achievement IDs
        """
        try:
            # This would check against predefined lap time targets
            # For now, return empty list as placeholder
            return []
            
        except Exception as e:
            logger.error(f"Error checking lap time achievements: {e}")
            return []

# Create a global instance
achievements_manager = AchievementsManager() 