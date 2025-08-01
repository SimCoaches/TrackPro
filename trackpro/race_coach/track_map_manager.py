"""
Track Map Manager - Save and load track coordinate data to/from Supabase
"""

import time
import json
from typing import List, Tuple, Dict, Optional
from ..database.supabase_client import get_supabase_client
from .pyirsdk import irsdk


class TrackMapManager:
    """Manager for saving and loading track map data to/from Supabase."""
    
    def __init__(self):
        self.track_coordinates = []
    
    def check_existing_track_map(self) -> Optional[dict]:
        """Check if track map data already exists for the current track."""
        try:
            # Connect to iRacing to get track info
            ir = irsdk.IRSDK()
            if not ir.startup() or not ir.is_connected:
                return None
            
            track_name = ir['WeekendInfo']['TrackDisplayName']
            track_config = ir['WeekendInfo']['TrackConfigName']
            ir.shutdown()
            
            # Get Supabase client
            supabase = get_supabase_client()
            if not supabase:
                return None
            
            # Query for existing track data
            track_query = supabase.table('tracks').select('*').eq('name', track_name)
            if track_config and track_config != track_name:
                track_query = track_query.eq('config', track_config)
            
            result = track_query.execute()
            
            if result.data and result.data[0].get('track_map'):
                track_data = result.data[0]
                return {
                    'track_name': track_name,
                    'track_config': track_config,
                    'track_map': track_data['track_map'],
                    'analysis_metadata': track_data.get('analysis_metadata', {}),
                    'last_analysis_date': track_data.get('last_analysis_date'),
                    'total_points': len(track_data['track_map']) if track_data['track_map'] else 0
                }
            
            return None
            
        except Exception as e:
            print(f"Error checking for existing track map: {str(e)}")
            return None
    
    def save_track_map_to_supabase(self, track_coordinates: List[Dict], metadata: Dict = None):
        """Save track map coordinates to Supabase tracks table."""
        try:
            # Get current track info from iRacing
            ir = irsdk.IRSDK()
            if not ir.startup() or not ir.is_connected:
                print("Warning: iRacing not connected, cannot save track map")
                return False
            
            track_name = ir['WeekendInfo']['TrackDisplayName']
            track_config = ir['WeekendInfo']['TrackConfigName'] 
            iracing_track_id = ir['WeekendInfo']['TrackID']
            track_length = ir['WeekendInfo']['TrackLength']
            ir.shutdown()
            
            # Get Supabase client
            supabase = get_supabase_client()
            if not supabase:
                print("Warning: Could not connect to Supabase")
                return False
            
            # Prepare track map data
            track_map_data = track_coordinates
            
            # Prepare analysis metadata
            analysis_metadata = metadata or {}
            analysis_metadata.update({
                'map_generation_timestamp': time.strftime("%Y-%m-%d %H:%M:%S"),
                'total_coordinates': len(track_coordinates),
                'track_length_km': track_length,
                'data_source': 'iracing_velocity_integration'
            })
            
            # Find or create track record
            full_track_name = f"{track_name} - {track_config}" if track_config != track_name else track_name
            
            # Check if track exists
            track_query = supabase.table('tracks').select('*').eq('name', track_name)
            if track_config and track_config != track_name:
                track_query = track_query.eq('config', track_config)
            
            existing_tracks = track_query.execute()
            
            if existing_tracks.data:
                # Update existing track
                track_id = existing_tracks.data[0]['id']
                
                update_data = {
                    'track_map': track_map_data,
                    'analysis_metadata': analysis_metadata,
                    'last_analysis_date': time.strftime("%Y-%m-%d %H:%M:%S"),
                    'length_meters': track_length * 1000,  # Convert km to meters
                    'data_version': 1
                }
                
                supabase.table('tracks').update(update_data).eq('id', track_id).execute()
                print(f"✅ Updated track map for: {full_track_name}")
                return True
                
            else:
                # Create new track record
                new_track = {
                    'name': track_name,
                    'config': track_config if track_config != track_name else None,
                    'iracing_track_id': iracing_track_id,
                    'length_meters': track_length * 1000,  # Convert km to meters
                    'track_map': track_map_data,
                    'analysis_metadata': analysis_metadata,
                    'last_analysis_date': time.strftime("%Y-%m-%d %H:%M:%S"),
                    'data_version': 1
                }
                
                result = supabase.table('tracks').insert(new_track).execute()
                print(f"✅ Created new track record with map data: {full_track_name}")
                return True
                
        except Exception as e:
            print(f"Warning: Could not save track map to Supabase: {str(e)}")
            return False
    
    def load_track_map_from_supabase(self) -> Optional[List[Dict]]:
        """Load track map data from Supabase."""
        existing_data = self.check_existing_track_map()
        if not existing_data:
            return None
        
        return existing_data.get('track_map', [])
    
    def get_track_info_summary(self) -> Optional[Dict]:
        """Get a summary of available track data (corners + map)."""
        try:
            # Connect to iRacing to get track info
            ir = irsdk.IRSDK()
            if not ir.startup() or not ir.is_connected:
                return None
            
            track_name = ir['WeekendInfo']['TrackDisplayName']
            track_config = ir['WeekendInfo']['TrackConfigName']
            ir.shutdown()
            
            # Get Supabase client
            supabase = get_supabase_client()
            if not supabase:
                return None
            
            # Query for existing track data
            track_query = supabase.table('tracks').select('*').eq('name', track_name)
            if track_config and track_config != track_name:
                track_query = track_query.eq('config', track_config)
            
            result = track_query.execute()
            
            if result.data:
                track_data = result.data[0]
                return {
                    'track_name': track_name,
                    'track_config': track_config,
                    'has_corners': bool(track_data.get('corners')),
                    'has_track_map': bool(track_data.get('track_map')),
                    'corners_count': len(track_data.get('corners', [])),
                    'map_points_count': len(track_data.get('track_map', [])),
                    'last_analysis_date': track_data.get('last_analysis_date'),
                    'length_meters': track_data.get('length_meters')
                }
            
            return {
                'track_name': track_name,
                'track_config': track_config,
                'has_corners': False,
                'has_track_map': False,
                'corners_count': 0,
                'map_points_count': 0,
                'last_analysis_date': None,
                'length_meters': None
            }
            
        except Exception as e:
            print(f"Error getting track info summary: {str(e)}")
            return None 