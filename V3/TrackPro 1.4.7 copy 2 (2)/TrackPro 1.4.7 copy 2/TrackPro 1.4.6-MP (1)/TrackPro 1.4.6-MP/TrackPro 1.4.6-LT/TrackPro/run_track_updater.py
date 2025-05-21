#!/usr/bin/env python3
"""
Track Updater

This script runs when a user enters a track in iRacing and ensures the track information
is properly updated in the database, including location and iRacing ID.

Usage:
    python run_track_updater.py --track_id <iracing_track_id> --track_name "Track Name"
"""

import os
import sys
import argparse
import logging
from track_data_sync import TrackDataSynchronizer

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("track_updater")

def update_track(track_id, track_name=None):
    """
    Update a specific track's information in the database.
    
    Args:
        track_id: The iRacing track ID
        track_name: Optional track name for logging
    """
    logger.info(f"Updating track {track_name or track_id} (ID: {track_id})")
    
    # Initialize the track data synchronizer
    sync = TrackDataSynchronizer(force_update=False)
    
    # Connect to services
    if not sync.connect():
        logger.error("Failed to connect to required services")
        return False
        
    # Load existing tracks from database
    sync._load_tracks_from_db()
    
    # Get track data from iRacing or embedded data
    all_tracks = sync.get_tracks_from_iracing()
    if not all_tracks:
        logger.error("No track data available")
        return False
    
    # Find the specific track we want to update
    track_data = None
    for track in all_tracks:
        if str(track.get("track_id")) == str(track_id):
            track_data = track
            break
    
    if not track_data:
        logger.error(f"Track with ID {track_id} not found in iRacing data")
        return False
    
    # Update just this track
    sync.sync_track(track_data)
    
    logger.info(f"Track {track_name or track_id} updated successfully")
    return True

def main():
    """Main function to run the track updater."""
    parser = argparse.ArgumentParser(description="Update a specific track's information in the database")
    parser.add_argument("--track_id", required=True, help="iRacing track ID")
    parser.add_argument("--track_name", help="Track name (for logging)")
    args = parser.parse_args()
    
    logger.info("Starting track update")
    
    success = update_track(args.track_id, args.track_name)
    
    if success:
        logger.info("Track update completed successfully")
        return 0
    else:
        logger.error("Track update failed")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 