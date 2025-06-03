#!/usr/bin/env python3
"""Debug script to examine telemetry data values stored in the database."""

import sys
import os
import logging

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def debug_telemetry_data():
    """Check telemetry data stored in database."""
    try:
        # Import the database functions
        from Supabase.database import get_laps, get_telemetry_points
        
        # Get some recent laps
        laps, msg = get_laps(limit=5)
        if not laps:
            logger.error(f"Failed to get laps: {msg}")
            return
            
        logger.info(f"Found {len(laps)} laps to examine")
        
        for lap in laps[:2]:  # Check first 2 laps
            lap_id = lap['id']
            lap_time = lap.get('lap_time', 'unknown')
            
            logger.info(f"\n=== Examining Lap {lap_id} (time: {lap_time}) ===")
            
            # Get telemetry points for this lap
            points, points_msg = get_telemetry_points(lap_id)
            if not points:
                logger.warning(f"No telemetry points for lap {lap_id}: {points_msg}")
                continue
                
            logger.info(f"Found {len(points)} telemetry points")
            
            if len(points) > 0:
                # Check first, middle, and last points
                indices_to_check = [0, len(points)//2, -1]
                point_names = ["First", "Middle", "Last"]
                
                for i, name in zip(indices_to_check, point_names):
                    point = points[i]
                    logger.info(f"\n{name} point:")
                    logger.info(f"  Keys: {list(point.keys())}")
                    logger.info(f"  track_position: {point.get('track_position', 'missing')}")
                    logger.info(f"  throttle: {point.get('throttle', 'missing')}")
                    logger.info(f"  brake: {point.get('brake', 'missing')}")
                    logger.info(f"  steering: {point.get('steering', 'missing')}")
                    logger.info(f"  speed: {point.get('speed', 'missing')}")
                
                # Calculate ranges for key telemetry channels
                throttle_values = [p.get('throttle', 0) for p in points if p.get('throttle') is not None]
                brake_values = [p.get('brake', 0) for p in points if p.get('brake') is not None]
                steering_values = [p.get('steering', 0) for p in points if p.get('steering') is not None]
                speed_values = [p.get('speed', 0) for p in points if p.get('speed') is not None]
                
                logger.info(f"\nData ranges for lap {lap_id}:")
                if throttle_values:
                    logger.info(f"  Throttle: {min(throttle_values):.3f} to {max(throttle_values):.3f} (avg: {sum(throttle_values)/len(throttle_values):.3f})")
                if brake_values:
                    logger.info(f"  Brake: {min(brake_values):.3f} to {max(brake_values):.3f} (avg: {sum(brake_values)/len(brake_values):.3f})")
                if steering_values:
                    logger.info(f"  Steering: {min(steering_values):.3f} to {max(steering_values):.3f} (avg: {sum(steering_values)/len(steering_values):.3f})")
                if speed_values:
                    logger.info(f"  Speed: {min(speed_values):.3f} to {max(speed_values):.3f} (avg: {sum(speed_values)/len(speed_values):.3f})")
                
                # Check for suspicious data (all values the same)
                if throttle_values and len(set(throttle_values)) == 1:
                    logger.warning(f"  ⚠️ All throttle values are the same: {throttle_values[0]}")
                if brake_values and len(set(brake_values)) == 1:
                    logger.warning(f"  ⚠️ All brake values are the same: {brake_values[0]}")
                if steering_values and len(set(steering_values)) == 1:
                    logger.warning(f"  ⚠️ All steering values are the same: {steering_values[0]}")
                if speed_values and len(set(speed_values)) == 1:
                    logger.warning(f"  ⚠️ All speed values are the same: {speed_values[0]}")
                    
    except Exception as e:
        logger.error(f"Error examining telemetry data: {e}")
        import traceback
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    debug_telemetry_data() 