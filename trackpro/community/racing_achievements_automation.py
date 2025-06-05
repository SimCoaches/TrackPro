"""
Automated Racing Achievement System for TrackPro
Monitors racing telemetry and automatically posts achievements to the social feed.
"""

import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from PyQt5.QtCore import QObject, pyqtSignal, QTimer
import logging

logger = logging.getLogger(__name__)

class RacingAchievementMonitor(QObject):
    """Monitors racing data and automatically posts achievements to the social feed."""
    
    # Signals
    achievement_posted = pyqtSignal(str, str, dict)  # achievement_type, message, metadata
    connection_status_changed = pyqtSignal(bool)  # connected status
    
    def __init__(self, user_id: str, db_managers: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.user_id = user_id
        self.db_managers = db_managers
        self.supabase = None
        
        # Initialize Supabase connection
        if 'social_manager' in db_managers:
            self.supabase = db_managers['social_manager'].supabase
        
        # Achievement tracking
        self.user_records = {
            'best_lap_times': {},  # track_id -> best_time
            'lap_counts': {},      # track_id -> total_laps
            'total_laps': 0,
            'achievements_unlocked': set(),
            'last_achievement_time': 0
        }
        
        # Load existing user records
        self.load_user_records()
        
        logger.info(f"✅ Racing Achievement Monitor initialized for user {user_id}")
        
    def load_user_records(self):
        """Load user's existing racing records from database."""
        try:
            if not self.supabase:
                return
                
            # Load personal best records
            pb_response = self.supabase.from_("user_personal_bests") \
                .select("track_id, best_lap_time") \
                .eq("user_id", self.user_id) \
                .execute()
                
            for pb in pb_response.data:
                track_id = pb['track_id']
                best_time = float(pb['best_lap_time'])
                self.user_records['best_lap_times'][track_id] = best_time
            
            # Load racing stats  
            stats_response = self.supabase.from_("user_racing_stats") \
                .select("total_laps, achievement_count") \
                .eq("user_id", self.user_id) \
                .single() \
                .execute()
                
            if stats_response.data:
                self.user_records['total_laps'] = stats_response.data.get('total_laps', 0)
                
            # Load recent achievements to avoid duplicates
            recent_achievements = self.supabase.from_("racing_achievements") \
                .select("achievement_type, metadata") \
                .eq("user_id", self.user_id) \
                .gte("created_at", (datetime.now() - timedelta(hours=1)).isoformat()) \
                .execute()
                
            for achievement in recent_achievements.data:
                achievement_key = f"{achievement['achievement_type']}_{achievement.get('metadata', {}).get('track_id', 'unknown')}"
                self.user_records['achievements_unlocked'].add(achievement_key)
                
            logger.info(f"📊 Loaded user records: {len(self.user_records['best_lap_times'])} PBs, {self.user_records['total_laps']} total laps")
            
        except Exception as e:
            logger.error(f"❌ Error loading user records: {e}")
    
    def on_lap_completed(self, lap_data: Dict[str, Any]):
        """Process a completed lap and check for achievements."""
        try:
            # Prevent too frequent achievement posting
            current_time = time.time()
            if current_time - self.user_records['last_achievement_time'] < 5:  # 5 second cooldown
                return
                
            lap_time = lap_data.get('lap_time', 0)
            track_id = str(lap_data.get('track_id', 'unknown'))
            track_name = lap_data.get('track_name', 'Unknown Track')
            car_name = lap_data.get('car_name', 'Unknown Car')
            lap_number = lap_data.get('lap_number', 0)
            is_valid = lap_data.get('is_valid', True)
            
            # Skip invalid laps or unrealistic times
            if not is_valid or lap_time <= 0 or lap_time > 600:  # 10 minute max
                return
                
            logger.info(f"🏁 Processing lap completion: {lap_time:.3f}s at {track_name}")
            
            # Check for personal best
            self.check_personal_best(lap_time, track_id, track_name, car_name, lap_data)
            
            # Check for lap milestones
            self.check_lap_milestones(track_id, track_name, lap_number)
            
            # Update total lap count
            self.user_records['total_laps'] += 1
            
            # Check for global milestones
            self.check_global_milestones()
            
            self.user_records['last_achievement_time'] = current_time
            
        except Exception as e:
            logger.error(f"❌ Error processing lap completion: {e}")
    
    def check_personal_best(self, lap_time: float, track_id: str, track_name: str, car_name: str, lap_data: Dict[str, Any]):
        """Check if this lap is a personal best."""
        try:
            current_best = self.user_records['best_lap_times'].get(track_id)
            
            # First lap at this track
            if current_best is None:
                self.post_personal_best(lap_time, track_id, track_name, car_name, None, lap_data)
                self.user_records['best_lap_times'][track_id] = lap_time
                return
            
            # Check for improvement
            improvement_seconds = current_best - lap_time
            if improvement_seconds > 0.001:  # At least 1ms improvement
                improvement_ms = int(improvement_seconds * 1000)
                self.post_personal_best(lap_time, track_id, track_name, car_name, improvement_ms, lap_data)
                self.user_records['best_lap_times'][track_id] = lap_time
                
        except Exception as e:
            logger.error(f"❌ Error checking personal best: {e}")
    
    def post_personal_best(self, lap_time: float, track_id: str, track_name: str, car_name: str, improvement_ms: Optional[int], lap_data: Dict[str, Any]):
        """Post a personal best achievement."""
        try:
            if not self.supabase:
                return
                
            # Get sector times if available
            sector_times = lap_data.get('sector_times', [])
            
            # Call the database function
            result = self.supabase.rpc('post_personal_best_achievement', {
                'p_user_id': self.user_id,
                'p_track_id': track_id,
                'p_track_name': track_name,
                'p_car_name': car_name,
                'p_lap_time': lap_time,
                'p_improvement_ms': improvement_ms,
                'p_sector_times': sector_times
            }).execute()
            
            if result.data:
                achievement_type = "personal_best"
                if improvement_ms:
                    message = f"New PB at {track_name}: {lap_time:.3f}s (-{improvement_ms}ms!)"
                else:
                    message = f"First lap time at {track_name}: {lap_time:.3f}s"
                    
                metadata = {
                    'track_id': track_id,
                    'track_name': track_name,
                    'car_name': car_name,
                    'lap_time': lap_time,
                    'improvement_ms': improvement_ms
                }
                
                self.achievement_posted.emit(achievement_type, message, metadata)
                logger.info(f"🎉 Posted personal best achievement: {message}")
                
        except Exception as e:
            logger.error(f"❌ Error posting personal best: {e}")
    
    def check_lap_milestones(self, track_id: str, track_name: str, lap_number: int):
        """Check for lap count milestones."""
        try:
            # Update track lap count
            if track_id not in self.user_records['lap_counts']:
                self.user_records['lap_counts'][track_id] = 0
            self.user_records['lap_counts'][track_id] += 1
            
            track_laps = self.user_records['lap_counts'][track_id]
            
            # Check for milestones (10, 25, 50, 100, 250, 500, 1000)
            milestones = [10, 25, 50, 100, 250, 500, 1000]
            
            if track_laps in milestones:
                self.post_lap_milestone(track_id, track_name, track_laps)
                
        except Exception as e:
            logger.error(f"❌ Error checking lap milestones: {e}")
    
    def post_lap_milestone(self, track_id: str, track_name: str, lap_count: int):
        """Post a lap milestone achievement."""
        try:
            if not self.supabase:
                return
                
            # Prevent duplicate milestone posts
            milestone_key = f"lap_milestone_{track_id}_{lap_count}"
            if milestone_key in self.user_records['achievements_unlocked']:
                return
                
            # Call the database function
            result = self.supabase.rpc('post_lap_milestone_achievement', {
                'p_user_id': self.user_id,
                'p_track_id': track_id,
                'p_track_name': track_name,
                'p_lap_number': lap_count
            }).execute()
            
            if result.data:
                achievement_type = "lap_milestone"
                message = f"Completed {lap_count} laps at {track_name}"
                metadata = {
                    'track_id': track_id,
                    'track_name': track_name,
                    'lap_count': lap_count
                }
                
                self.user_records['achievements_unlocked'].add(milestone_key)
                self.achievement_posted.emit(achievement_type, message, metadata)
                logger.info(f"🎯 Posted lap milestone: {message}")
                
        except Exception as e:
            logger.error(f"❌ Error posting lap milestone: {e}")
    
    def check_global_milestones(self):
        """Check for global lap count milestones."""
        try:
            global_milestones = [100, 500, 1000, 5000, 10000]
            
            if self.user_records['total_laps'] in global_milestones:
                self.post_global_milestone(self.user_records['total_laps'])
                
        except Exception as e:
            logger.error(f"❌ Error checking global milestones: {e}")
    
    def post_global_milestone(self, total_laps: int):
        """Post a global lap milestone achievement."""
        try:
            if not self.supabase:
                return
                
            milestone_key = f"global_milestone_{total_laps}"
            if milestone_key in self.user_records['achievements_unlocked']:
                return
                
            # Call the achievement unlock function
            result = self.supabase.rpc('post_achievement_unlock', {
                'p_user_id': self.user_id,
                'p_achievement_name': f"Total Laps: {total_laps}",
                'p_rarity': 'epic' if total_laps >= 5000 else 'rare' if total_laps >= 1000 else 'common',
                'p_xp_gained': total_laps // 10,  # 1 XP per 10 laps
                'p_metadata': {'total_laps': total_laps}
            }).execute()
            
            if result.data:
                achievement_type = "global_milestone"
                message = f"Reached {total_laps} total laps across all tracks!"
                metadata = {'total_laps': total_laps}
                
                self.user_records['achievements_unlocked'].add(milestone_key)
                self.achievement_posted.emit(achievement_type, message, metadata)
                logger.info(f"🌟 Posted global milestone: {message}")
                
        except Exception as e:
            logger.error(f"❌ Error posting global milestone: {e}")
    
    def on_race_completed(self, race_data: Dict[str, Any]):
        """Process a completed race and check for achievements."""
        try:
            track_id = str(race_data.get('track_id', 'unknown'))
            track_name = race_data.get('track_name', 'Unknown Track')
            car_name = race_data.get('car_name', 'Unknown Car')
            position = race_data.get('position', 0)
            total_participants = race_data.get('total_participants', 0)
            
            if position > 0 and total_participants > 1:  # Valid race result
                self.post_race_result(track_id, track_name, car_name, position, total_participants)
                
        except Exception as e:
            logger.error(f"❌ Error processing race completion: {e}")
    
    def post_race_result(self, track_id: str, track_name: str, car_name: str, position: int, total_participants: int):
        """Post a race result achievement."""
        try:
            if not self.supabase:
                return
                
            # Call the database function
            result = self.supabase.rpc('post_race_result_achievement', {
                'p_user_id': self.user_id,
                'p_track_id': track_id,
                'p_track_name': track_name,
                'p_car_name': car_name,
                'p_race_position': position,
                'p_total_participants': total_participants
            }).execute()
            
            if result.data:
                achievement_type = "race_result"
                if position == 1:
                    message = f"Victory at {track_name}! 🥇"
                elif position <= 3:
                    message = f"Podium finish (P{position}) at {track_name}! 🏆"
                else:
                    message = f"Finished P{position}/{total_participants} at {track_name}"
                    
                metadata = {
                    'track_id': track_id,
                    'track_name': track_name,
                    'car_name': car_name,
                    'position': position,
                    'total_participants': total_participants
                }
                
                self.achievement_posted.emit(achievement_type, message, metadata)
                logger.info(f"🏁 Posted race result: {message}")
                
        except Exception as e:
            logger.error(f"❌ Error posting race result: {e}")
    
    def diagnose_connection(self):
        """Diagnose the connection status and print debug information."""
        try:
            logger.info("🔍 RACING ACHIEVEMENT SYSTEM DIAGNOSTICS")
            logger.info("=" * 50)
            
            if self.supabase:
                logger.info("✅ Supabase connection: ACTIVE")
                
                # Test database connection
                test_result = self.supabase.from_("racing_achievements").select("COUNT(*)").execute()
                logger.info(f"✅ Database connection: WORKING ({len(test_result.data)} achievements in system)")
                
                # Show user records
                logger.info(f"📊 Personal bests loaded: {len(self.user_records['best_lap_times'])}")
                logger.info(f"📊 Total laps recorded: {self.user_records['total_laps']}")
                logger.info(f"📊 Recent achievements cached: {len(self.user_records['achievements_unlocked'])}")
                
                self.connection_status_changed.emit(True)
            else:
                logger.info("❌ Supabase connection: NOT AVAILABLE")
                self.connection_status_changed.emit(False)
                
            logger.info("🏁 Complete real laps in iRacing to see automated achievements!")
            
        except Exception as e:
            logger.error(f"❌ Connection diagnostic failed: {e}")
            self.connection_status_changed.emit(False)


def create_racing_achievement_monitor(user_id: str, db_managers: Dict[str, Any], parent=None) -> RacingAchievementMonitor:
    """Factory function to create a racing achievement monitor."""
    return RacingAchievementMonitor(user_id, db_managers, parent) 