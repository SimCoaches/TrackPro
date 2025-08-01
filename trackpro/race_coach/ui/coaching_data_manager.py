"""Coaching Data Manager - Provides performance analysis for racing engineer debriefs.

This module handles fetching session data and calculating performance metrics 
for the racing engineer's debrief room functionality.
"""

import logging
import sqlite3
import statistics
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


class CoachingDataManager:
    """Manages coaching data for racing engineer debriefs and analysis."""
    
    def __init__(self, supabase_client=None, user_id=None):
        """Initialize the coaching data manager.
        
        Args:
            supabase_client: Optional Supabase client for cloud data
            user_id: User ID for personalized data
        """
        self.supabase_client = supabase_client
        self.user_id = user_id
        self._local_db_path = "race_coach.db"
        
    def get_session_summary(self) -> Dict[str, Any]:
        """Get the most recent session summary for racing engineer analysis.
        
        Returns:
            Dictionary containing session data or None if no data available
        """
        try:
            # Try cloud data first
            if self.supabase_client and self.user_id:
                return self._get_cloud_session_summary()
            
            # Fallback to local data
            return self._get_local_session_summary()
            
        except Exception as e:
            logger.error(f"Error getting session summary: {e}")
            return self._get_sample_session_data()
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get detailed performance metrics for racing engineer analysis.
        
        Returns:
            Dictionary containing performance metrics
        """
        try:
            # Try cloud data first
            if self.supabase_client and self.user_id:
                return self._get_cloud_performance_metrics()
            
            # Fallback to local data
            return self._get_local_performance_metrics()
            
        except Exception as e:
            logger.error(f"Error getting performance metrics: {e}")
            return self._get_sample_performance_metrics()
    
    def _get_cloud_session_summary(self) -> Optional[Dict[str, Any]]:
        """Get session summary from Supabase cloud database."""
        try:
            # Get most recent session
            result = self.supabase_client.table("sessions").select(
                "*, laps!inner(lap_time, is_valid)"
            ).eq("user_id", self.user_id).order(
                "session_date", desc=True
            ).limit(1).execute()
            
            if not result.data:
                return None
                
            session = result.data[0]
            laps = session.get('laps', [])
            
            # Calculate session metrics
            valid_laps = [lap for lap in laps if lap.get('is_valid', False)]
            lap_times = [lap['lap_time'] for lap in valid_laps if lap['lap_time'] > 0]
            
            if not lap_times:
                return None
            
            return {
                'session_id': session.get('session_id'),
                'session_date': session.get('session_date'),
                'track_name': session.get('track_name', 'Unknown Track'),
                'car_name': session.get('car_name', 'Unknown Car'),
                'total_laps': len(laps),
                'valid_laps': len(valid_laps),
                'best_lap': min(lap_times),
                'average_lap': statistics.mean(lap_times),
                'duration': self._format_duration(session.get('duration', 0))
            }
            
        except Exception as e:
            logger.error(f"Error fetching cloud session data: {e}")
            return None
    
    def _get_local_session_summary(self) -> Optional[Dict[str, Any]]:
        """Get session summary from local SQLite database."""
        try:
            conn = sqlite3.connect(self._local_db_path)
            cursor = conn.cursor()
            
            # Get most recent session with laps
            cursor.execute("""
                SELECT s.session_id, s.session_date, s.track_name, s.car_name, s.duration,
                       COUNT(l.lap_id) as total_laps,
                       COUNT(CASE WHEN l.is_valid = 1 THEN 1 END) as valid_laps,
                       MIN(CASE WHEN l.is_valid = 1 THEN l.lap_time END) as best_lap,
                       AVG(CASE WHEN l.is_valid = 1 THEN l.lap_time END) as avg_lap
                FROM sessions s
                LEFT JOIN laps l ON s.session_id = l.session_id
                WHERE s.session_date IS NOT NULL
                GROUP BY s.session_id
                HAVING total_laps > 0
                ORDER BY s.session_date DESC
                LIMIT 1
            """)
            
            row = cursor.fetchone()
            conn.close()
            
            if not row:
                return None
            
            return {
                'session_id': row[0],
                'session_date': row[1],
                'track_name': row[2] or 'Unknown Track',
                'car_name': row[3] or 'Unknown Car',
                'total_laps': row[5] or 0,
                'valid_laps': row[6] or 0,
                'best_lap': row[7],
                'average_lap': row[8],
                'duration': self._format_duration(row[4] or 0)
            }
            
        except Exception as e:
            logger.error(f"Error fetching local session data: {e}")
            return None
    
    def _get_cloud_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics from cloud database."""
        try:
            # Get recent laps for analysis
            result = self.supabase_client.table("laps").select(
                "lap_time, is_valid, lap_number, sessions!inner(session_date)"
            ).eq("user_id", self.user_id).eq("is_valid", True).order(
                "sessions.session_date", desc=True
            ).limit(50).execute()
            
            if not result.data:
                return self._get_sample_performance_metrics()
            
            laps = result.data
            lap_times = [lap['lap_time'] for lap in laps if lap['lap_time'] > 0]
            
            return self._calculate_performance_metrics(lap_times)
            
        except Exception as e:
            logger.error(f"Error fetching cloud performance metrics: {e}")
            return self._get_sample_performance_metrics()
    
    def _get_local_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics from local database."""
        try:
            conn = sqlite3.connect(self._local_db_path)
            cursor = conn.cursor()
            
            # Get recent valid laps
            cursor.execute("""
                SELECT l.lap_time, l.lap_number
                FROM laps l
                JOIN sessions s ON l.session_id = s.session_id
                WHERE l.is_valid = 1 AND l.lap_time > 0
                ORDER BY s.session_date DESC, l.lap_number DESC
                LIMIT 50
            """)
            
            rows = cursor.fetchall()
            conn.close()
            
            if not rows:
                return self._get_sample_performance_metrics()
            
            lap_times = [row[0] for row in rows]
            return self._calculate_performance_metrics(lap_times)
            
        except Exception as e:
            logger.error(f"Error fetching local performance metrics: {e}")
            return self._get_sample_performance_metrics()
    
    def _calculate_performance_metrics(self, lap_times: List[float]) -> Dict[str, Any]:
        """Calculate detailed performance metrics from lap times."""
        if not lap_times or len(lap_times) < 2:
            return self._get_sample_performance_metrics()
        
        try:
            # Basic statistics
            best_lap = min(lap_times)
            avg_lap = statistics.mean(lap_times)
            std_dev = statistics.stdev(lap_times) if len(lap_times) > 1 else 0
            
            # Consistency score (inverted coefficient of variation)
            consistency_score = max(0, 100 - (std_dev / avg_lap * 100 * 10))
            
            # Session improvement (comparing first and last few laps)
            session_improvement = 0
            if len(lap_times) >= 6:
                early_laps = lap_times[-3:]  # First 3 laps (reversed order)
                late_laps = lap_times[:3]    # Last 3 laps
                early_avg = statistics.mean(early_laps)
                late_avg = statistics.mean(late_laps)
                session_improvement = early_avg - late_avg  # Positive = improved
            
            # Pace window analysis
            pace_window = avg_lap - best_lap
            
            return {
                'best_lap': best_lap,
                'average_lap': avg_lap,
                'consistency_score': consistency_score,
                'session_improvement': session_improvement,
                'pace_window': pace_window,
                'std_deviation': std_dev,
                'total_laps_analyzed': len(lap_times)
            }
            
        except Exception as e:
            logger.error(f"Error calculating performance metrics: {e}")
            return self._get_sample_performance_metrics()
    
    def _get_sample_session_data(self) -> Dict[str, Any]:
        """Get sample session data when no real data is available."""
        return {
            'session_id': 'sample',
            'session_date': datetime.now().isoformat(),
            'track_name': 'TrackPro Test Circuit',
            'car_name': 'Practice Car',
            'total_laps': 0,
            'valid_laps': 0,
            'best_lap': None,
            'average_lap': None,
            'duration': '00:00:00'
        }
    
    def _get_sample_performance_metrics(self) -> Dict[str, Any]:
        """Get sample performance metrics when no real data is available."""
        return {
            'best_lap': None,
            'average_lap': None,
            'consistency_score': 0,
            'session_improvement': 0,
            'pace_window': 0,
            'std_deviation': 0,
            'total_laps_analyzed': 0
        }
    
    def _format_duration(self, seconds: float) -> str:
        """Format duration in seconds to HH:MM:SS format."""
        if not seconds or seconds <= 0:
            return "00:00:00"
        
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    
    def get_coaching_insights(self, session_data: Dict[str, Any] = None) -> List[str]:
        """Generate coaching insights based on session performance.
        
        Args:
            session_data: Session data to analyze
            
        Returns:
            List of coaching insight strings
        """
        insights = []
        
        if not session_data or session_data.get('total_laps', 0) == 0:
            insights.append("Complete a racing session to unlock personalized coaching insights!")
            return insights
        
        # Get performance metrics
        performance = self.get_performance_metrics()
        
        # Consistency insights
        consistency = performance.get('consistency_score', 0)
        if consistency > 95:
            insights.append("🎯 Outstanding consistency! Your lap times are remarkably stable.")
        elif consistency > 85:
            insights.append("✅ Strong consistency showing good racecraft fundamentals.")
        elif consistency > 70:
            insights.append("📈 Work on consistency for more predictable lap times.")
        else:
            insights.append("🔧 Focus on consistent driving before chasing ultimate pace.")
        
        # Pace insights
        best_lap = performance.get('best_lap')
        avg_lap = performance.get('average_lap')
        if best_lap and avg_lap:
            gap = avg_lap - best_lap
            if gap < 0.3:
                insights.append("🚀 Excellent pace control - very tight lap time window!")
            elif gap < 0.8:
                insights.append("📊 Good pace with opportunity to tighten your lap time window.")
            else:
                insights.append(f"🎯 Large pace window: {gap:.3f}s between best and average lap.")
        
        # Session length insights
        total_laps = session_data.get('total_laps', 0)
        if total_laps >= 30:
            insights.append("💪 Excellent session length provides great data for analysis.")
        elif total_laps >= 15:
            insights.append("👍 Good session length for meaningful analysis.")
        elif total_laps >= 5:
            insights.append("📋 Moderate session - consider longer runs for better insights.")
        
        # Improvement insights
        improvement = performance.get('session_improvement', 0)
        if improvement > 0.2:
            insights.append(f"📈 Great progress! Improved by {improvement:.3f}s during session.")
        elif improvement < -0.2:
            insights.append("🛑 Times got slower - consider taking breaks during long sessions.")
        
        return insights
    
    # Legacy methods for backward compatibility
    def get_recent_laps(self) -> List[Dict[str, Any]]:
        """Get recent laps data (legacy method)."""
        return []
    
    def get_session_stats(self) -> Dict[str, Any]:
        """Get session statistics (legacy method)."""
        return self.get_session_summary() or {}
    
    def get_insights(self) -> List[str]:
        """Get performance insights (legacy method)."""
        session_data = self.get_session_summary()
        return self.get_coaching_insights(session_data) 