#!/usr/bin/env python3
"""
Script to add missing voice channels to the database.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from trackpro.database.supabase_client import get_supabase_client
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def add_voice_channels():
    """Add missing voice channels to the database."""
    try:
        client = get_supabase_client()
        if not client:
            logger.error("Failed to get Supabase client")
            return False
        
        # Voice channels to add (let database generate UUIDs)
        voice_channels = [
            {
                "name": "Voice General",
                "description": "Voice channel for general chat",
                "channel_type": "voice",
                "is_private": False
            },
            {
                "name": "Voice Racing",
                "description": "Voice channel for racing discussions",
                "channel_type": "voice",
                "is_private": False
            }
        ]
        
        logger.info("Adding voice channels to database...")
        
        for channel in voice_channels:
            try:
                response = client.table("community_channels").insert(channel).execute()
                if response.data:
                    logger.info(f"✅ Added voice channel: {channel['name']}")
                else:
                    logger.warning(f"⚠️ No response data for channel: {channel['name']}")
            except Exception as e:
                if "duplicate key" in str(e).lower():
                    logger.info(f"ℹ️ Channel already exists: {channel['name']}")
                else:
                    logger.error(f"❌ Failed to add channel {channel['name']}: {e}")
        
        logger.info("✅ Voice channels script completed")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error in add_voice_channels: {e}")
        return False

if __name__ == "__main__":
    add_voice_channels() 