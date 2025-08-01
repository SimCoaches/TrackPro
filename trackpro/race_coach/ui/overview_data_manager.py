"""Data manager for the driver coaching overview.

This module handles fetching, analyzing, and presenting performance data
for the coaching dashboard.
"""

import logging
import statistics
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import json

logger = logging.getLogger(__name__)


class CoachingDataManager:
    """Manages data analysis and insights for the coaching overview."""
    
    def __init__(self, supabase_client=None, user_id=None):
        """Initialize the coaching data manager.
        
        Args:
            supabase_client: The Supabase client for database access
            user_id: The current user's ID
        """
        self.supabase_client = supabase_client
        self.user_id = user_id
        self.cache = {}
        self.cache_timestamp = None
        self.cache_duration = 300  # 5 minutes
        
    def get_session_summary(self, session_id: str = None) -> Dict:
        """Get summary data for the current or specified session.
        
        Args:
            session_id: Session ID (if None, gets the most recent session)
            
        Returns:
            Dictionary with session summary data
        """
        try:
            if not self.supabase_client:
                return self._get_mock_session_summary()
                
            # Get session info
            if session_id:
                session_query = self.supabase_client.table("sessions").select(
                    "*, tracks(name, length_meters), cars(name)"
                ).eq("id", session_id).single()
            else:
                session_query = self.supabase_client.table("sessions").select(
                    "*, tracks(name, length_meters), cars(name)"
                ).eq("user_id", self.user_id).order("created_at", desc=True).limit(1).single()
            
            session_result = session_query.execute()
            if not session_result.data:
                return self._get_mock_session_summary()
                
            session = session_result.data
            
            # Get laps for this session
            laps_result = self.supabase_client.table("laps").select("*").eq(
                "session_id", session["id"]
            ).eq("is_valid", True).order("lap_number").execute()
            
            laps = laps_result.data if laps_result.data else []
            
            # Calculate session statistics
            lap_times = [lap["lap_time"] for lap in laps if lap["lap_time"] > 0]
            
            summary = {
                "track_name": session.get("tracks", {}).get("name", "Unknown Track"),
                "car_name": session.get("cars", {}).get("name", "Unknown Car"),
                "session_date": session.get("session_date"),
                "duration": self._calculate_session_duration(session),
                "total_laps": len(laps),
                "valid_laps": len(lap_times),
                "best_lap": min(lap_times) if lap_times else None,
                "average_lap": statistics.mean(lap_times) if lap_times else None,
                "session_type": session.get("session_type", "Practice")
            }
            
            return summary
            
        except Exception as e:
            logger.error(f"Error getting session summary: {e}")
            return self._get_mock_session_summary()
    
    def get_performance_metrics(self, track_id: str = None, car_id: str = None) -> Dict:
        """Get performance metrics for analysis.
        
        Args:
            track_id: Track ID to filter by
            car_id: Car ID to filter by
            
        Returns:
            Dictionary with performance metrics
        """
        try:
            if not self.supabase_client:
                return self._get_mock_performance_metrics()
                
            # Get recent laps for analysis
            query = self.supabase_client.table("laps").select(
                "*, sessions!inner(track_id, car_id, session_date)"
            ).eq("user_id", self.user_id).eq("is_valid", True)
            
            if track_id:
                query = query.eq("sessions.track_id", track_id)
            if car_id:
                query = query.eq("sessions.car_id", car_id)
                
            result = query.order("sessions.session_date", desc=True).limit(50).execute()
            
            if not result.data:
                return self._get_mock_performance_metrics()
                
            laps = result.data
            lap_times = [lap["lap_time"] for lap in laps if lap["lap_time"] > 0]
            
            # Calculate consistency score (based on standard deviation)
            if len(lap_times) > 1:
                std_dev = statistics.stdev(lap_times)
                mean_time = statistics.mean(lap_times)
                consistency_score = max(0, 100 - (std_dev / mean_time * 100 * 10))  # Scale it
            else:
                consistency_score = 0
                
            # Calculate improvement trend
            if len(lap_times) >= 5:
                recent_avg = statistics.mean(lap_times[:5])  # Most recent 5 laps
                older_avg = statistics.mean(lap_times[-5:])   # Oldest 5 laps
                improvement = older_avg - recent_avg
            else:
                improvement = 0
                
            # Get sector performance (mock for now)
            sector_performance = self._calculate_sector_performance(laps)
            
            metrics = {
                "consistency_score": round(consistency_score, 1),
                "session_improvement": improvement,
                "sector_performance": sector_performance,
                "total_laps_analyzed": len(lap_times),
                "best_lap": min(lap_times) if lap_times else None,
                "average_lap": statistics.mean(lap_times) if lap_times else None
            }
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error getting performance metrics: {e}")
            return self._get_mock_performance_metrics()
    
    def get_progress_data(self, days: int = 7) -> Dict:
        """Get progress data for the specified time period.
        
        Args:
            days: Number of days to look back
            
        Returns:
            Dictionary with progress data
        """
        try:
            if not self.supabase_client:
                return self._get_mock_progress_data()
                
            # Calculate date range
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            # Get sessions in date range
            result = self.supabase_client.table("sessions").select(
                "*, laps!inner(lap_time, is_valid)"
            ).eq("user_id", self.user_id).gte(
                "session_date", start_date.isoformat()
            ).lte("session_date", end_date.isoformat()).execute()
            
            if not result.data:
                return self._get_mock_progress_data()
                
            # Group by day and calculate best lap times
            daily_data = {}
            for session in result.data:
                session_date = datetime.fromisoformat(session["session_date"].replace('Z', '+00:00'))
                day_key = session_date.strftime('%Y-%m-%d')
                
                valid_laps = [lap["lap_time"] for lap in session.get("laps", []) 
                             if lap["is_valid"] and lap["lap_time"] > 0]
                
                if valid_laps:
                    best_lap = min(valid_laps)
                    if day_key not in daily_data or best_lap < daily_data[day_key]:
                        daily_data[day_key] = best_lap
            
            # Convert to lists for charting
            sorted_days = sorted(daily_data.keys())
            labels = [datetime.fromisoformat(day).strftime('%a') for day in sorted_days[-7:]]
            values = [daily_data[day] for day in sorted_days[-7:]]
            
            progress = {
                "daily_labels": labels,
                "daily_values": values,
                "total_improvement": values[0] - values[-1] if len(values) >= 2 else 0,
                "days_analyzed": len(values)
            }
            
            return progress
            
        except Exception as e:
            logger.error(f"Error getting progress data: {e}")
            return self._get_mock_progress_data()
    
    def get_coaching_insights(self, session_data: Dict, performance_data: Dict) -> List[Dict]:
        """Generate coaching insights based on performance data.
        
        Args:
            session_data: Current session data
            performance_data: Performance metrics
            
        Returns:
            List of insight dictionaries
        """
        insights = []
        
        try:
            # Consistency analysis
            consistency = performance_data.get("consistency_score", 0)
            if consistency < 70:
                insights.append({
                    "icon": "🎯",
                    "category": "Focus Area",
                    "message": f"Work on consistency - your lap times vary quite a bit (Score: {consistency:.0f}%)"
                })
            elif consistency > 90:
                insights.append({
                    "icon": "🎯", 
                    "category": "Strength",
                    "message": f"Excellent consistency! Your lap times are very stable (Score: {consistency:.0f}%)"
                })
            
            # Improvement analysis
            improvement = performance_data.get("session_improvement", 0)
            if improvement > 0.5:
                insights.append({
                    "icon": "📈",
                    "category": "Strength", 
                    "message": f"Great progress! You've improved by {improvement:.1f}s this session"
                })
            elif improvement < -0.3:
                insights.append({
                    "icon": "⚠️",
                    "category": "Watch Out",
                    "message": f"Times are getting slower - take a break or check your approach"
                })
            
            # Lap count analysis
            total_laps = session_data.get("total_laps", 0)
            if total_laps > 20:
                insights.append({
                    "icon": "💪",
                    "category": "Endurance",
                    "message": f"Great practice session! {total_laps} laps completed"
                })
            elif total_laps < 5:
                insights.append({
                    "icon": "🏁",
                    "category": "Suggestion",
                    "message": "Try to complete more laps to get better data for analysis"
                })
            
            # Goal setting
            best_lap = performance_data.get("best_lap")
            if best_lap:
                target_time = best_lap - 0.5
                insights.append({
                    "icon": "🏆",
                    "category": "Goal",
                    "message": f"Target: Break {self._format_time(target_time)} (0.5s improvement)"
                })
                
            # If no insights generated, add a default encouraging one
            if not insights:
                insights.append({
                    "icon": "🚗",
                    "category": "Keep Going",
                    "message": "Keep practicing! More data will help generate better insights"
                })
                
        except Exception as e:
            logger.error(f"Error generating coaching insights: {e}")
            insights = [{
                "icon": "🚗",
                "category": "Keep Going", 
                "message": "Keep practicing to get personalized coaching insights!"
            }]
        
        return insights
    
    def _calculate_session_duration(self, session: Dict) -> str:
        """Calculate and format session duration."""
        try:
            start_time = datetime.fromisoformat(session["session_date"].replace('Z', '+00:00'))
            # For now, estimate duration based on lap count (will be better with real end times)
            estimated_minutes = session.get("total_laps", 0) * 2  # Assume 2 min per lap
            return f"{estimated_minutes} min"
        except:
            return "Unknown"
    
    def _calculate_sector_performance(self, laps: List[Dict]) -> Dict:
        """Calculate sector performance comparison."""
        # This is a mock implementation - real implementation would use sector_times table
        return {
            "sector_1_delta": "+0.2s",
            "sector_2_delta": "-0.1s", 
            "sector_3_delta": "+0.4s"
        }
    
    def _format_time(self, time_seconds: float) -> str:
        """Format time in seconds to MM:SS.mmm format."""
        if time_seconds is None or time_seconds <= 0:
            return "--:--.---"
        minutes = int(time_seconds // 60)
        seconds = time_seconds % 60
        return f"{minutes:01d}:{seconds:06.3f}"
    
    # Mock data methods for when database is not available
    def _get_mock_session_summary(self) -> Dict:
        """Get mock session summary for testing."""
        return {
            "track_name": "Watkins Glen International",
            "car_name": "Formula 3.5",
            "session_date": datetime.now().isoformat(),
            "duration": "45 min",
            "total_laps": 23,
            "valid_laps": 21,
            "best_lap": 83.542,
            "average_lap": 84.123,
            "session_type": "Practice"
        }
    
    def _get_mock_performance_metrics(self) -> Dict:
        """Get mock performance metrics for testing."""
        return {
            "consistency_score": 87.3,
            "session_improvement": 1.2,
            "sector_performance": {
                "sector_1_delta": "+0.2s",
                "sector_2_delta": "-0.1s",
                "sector_3_delta": "+0.4s"
            },
            "total_laps_analyzed": 45,
            "best_lap": 83.542,
            "average_lap": 84.256
        }
    
    def _get_mock_progress_data(self) -> Dict:
        """Get mock progress data for testing."""
        return {
            "daily_labels": ["Mon", "Tue", "Wed", "Thu", "Fri"],
            "daily_values": [85.2, 84.8, 84.5, 84.1, 83.9],
            "total_improvement": 1.3,
            "days_analyzed": 5
        } 