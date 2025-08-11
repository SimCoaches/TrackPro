"""
Supabase Gamification Module

This module provides functions to interact with the gamification system tables in Supabase,
including user profiles, quests, race pass seasons, and rewards.
"""

from typing import Optional, Dict, Any, List, Tuple, Union
import logging
import json
from datetime import datetime, timedelta

# Import Supabase client and auth
from trackpro.database.supabase_client import supabase
from Supabase import auth

# Set up logging
logger = logging.getLogger(__name__)

# Table names for gamification system
USER_PROFILES_TABLE = "user_profiles"
QUESTS_TABLE = "quests"
USER_QUESTS_TABLE = "user_quests"
RACE_PASS_SEASONS_TABLE = "race_pass_seasons"
RACE_PASS_REWARDS_TABLE = "race_pass_rewards"

# ----- User Profile Functions -----

def get_user_profile() -> Tuple[Optional[Dict[str, Any]], str]:
    """
    Get the current user's gamification profile.
    
    Returns:
        Tuple[Optional[Dict[str, Any]], str]: A tuple containing profile data (or None) and a message
    """
    if not supabase.is_authenticated():
        return None, "Not logged in. Please log in to view your profile"
    
    try:
        user = supabase.get_user()
        user_id = None
        
        if user:
            if hasattr(user, 'id'):
                user_id = user.id
            elif hasattr(user, 'user') and hasattr(user.user, 'id'):
                user_id = user.user.id
                
        if not user_id:
            return None, "User ID not found"
        
        # Get user gamification profile
        result = supabase.client.table(USER_PROFILES_TABLE) \
            .select("*") \
            .eq("user_id", user_id) \
            .execute()
        
        if result.data and len(result.data) > 0:
            return result.data[0], "Profile retrieved successfully"
        else:
            return None, "Profile not found"
    except Exception as e:
        logger.error(f"Failed to retrieve user profile: {e}")
        return None, f"Failed to retrieve profile: {e}"

def award_xp(xp_amount: int, race_pass_xp: int = 0) -> Tuple[bool, str]:
    """
    Award XP to the current user.
    
    Args:
        xp_amount: Amount of XP to award
        race_pass_xp: Amount of Race Pass XP to award (defaults to 0)
        
    Returns:
        Tuple[bool, str]: Success flag and message
    """
    if not supabase.is_authenticated():
        return False, "Not logged in. Please log in to award XP"
    
    try:
        user = supabase.get_user()
        user_id = None
        
        if user:
            if hasattr(user, 'id'):
                user_id = user.id
            elif hasattr(user, 'user') and hasattr(user.user, 'id'):
                user_id = user.user.id
                
        if not user_id:
            return False, "User ID not found"
        
        # Call Supabase RPC function to award XP
        result = supabase.client.rpc('award_xp', {
            'p_user_id': user_id,
            'p_xp_amount': xp_amount,
            'p_race_pass_xp': race_pass_xp
        }).execute()
        
        if result.data:
            return True, f"Awarded {xp_amount} XP and {race_pass_xp} Race Pass XP"
        else:
            return False, "Failed to award XP"
    except Exception as e:
        logger.error(f"Failed to award XP: {e}")
        return False, f"Failed to award XP: {e}"

# ----- Quest Functions -----

def get_user_quests() -> Tuple[Optional[List[Dict[str, Any]]], str]:
    """
    Get all active quests for the current user.
    
    Returns:
        Tuple[Optional[List[Dict[str, Any]]], str]: A tuple containing quest data (or None) and a message
    """
    if not supabase.is_authenticated():
        return None, "Not logged in. Please log in to view quests"
    
    try:
        user = supabase.get_user()
        user_id = None
        
        if user:
            if hasattr(user, 'id'):
                user_id = user.id
            elif hasattr(user, 'user') and hasattr(user.user, 'id'):
                user_id = user.user.id
                
        if not user_id:
            return None, "User ID not found"
        
        # Call Supabase RPC function to get user quests
        result = supabase.client.rpc('get_user_quests', {
            'p_user_id': user_id
        }).execute()
        
        if result.data:
            return result.data, "Quests retrieved successfully"
        else:
            return [], "No active quests found"
    except Exception as e:
        level = logging.INFO if "Not logged in" in str(e) else logging.ERROR
        logger.log(level, f"Failed to retrieve user quests: {e}")
        return None, f"Failed to retrieve quests: {e}"

def update_quest_progress(user_quest_id: str, progress: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Update progress for a specific user quest.
    
    Args:
        user_quest_id: ID of the user quest to update
        progress: Dictionary containing progress data
        
    Returns:
        Tuple[bool, str]: Success flag and message
    """
    if not supabase.is_authenticated():
        return False, "Not logged in. Please log in to update quest progress"
    
    try:
        # Get current progress first
        current_result = supabase.client.table(USER_QUESTS_TABLE) \
            .select("progress") \
            .eq("user_quest_id", user_quest_id) \
            .execute()
        
        if not (current_result.data and len(current_result.data) > 0):
            return False, "Quest not found"
        
        # Merge existing progress with new progress
        current_progress = current_result.data[0].get("progress", {})
        merged_progress = {**current_progress, **progress}
        
        # Update the quest progress
        result = supabase.client.table(USER_QUESTS_TABLE) \
            .update({"progress": merged_progress}) \
            .eq("user_quest_id", user_quest_id) \
            .execute()
        
        if result.data and len(result.data) > 0:
            return True, "Quest progress updated successfully"
        else:
            return False, "Failed to update quest progress"
    except Exception as e:
        logger.error(f"Failed to update quest progress: {e}")
        return False, f"Failed to update quest progress: {e}"

def claim_quest_reward(user_quest_id: str) -> Tuple[bool, str, Dict[str, Any]]:
    """
    Claim the reward for a completed quest.
    
    Args:
        user_quest_id: ID of the user quest to claim
        
    Returns:
        Tuple[bool, str, Dict[str, Any]]: Success flag, message, and reward info
    """
    if not supabase.is_authenticated():
        return False, "Not logged in. Please log in to claim quest rewards", {}
    
    try:
        # First verify that the quest is complete and not already claimed
        verify_result = supabase.client.table(USER_QUESTS_TABLE) \
            .select("*") \
            .eq("user_quest_id", user_quest_id) \
            .execute()
        
        if not (verify_result.data and len(verify_result.data) > 0):
            return False, "Quest not found", {}
        
        quest_data = verify_result.data[0]
        current_user_id = quest_data.get("user_id") # Get user_id from the quest_data

        if not current_user_id:
            # This should ideally not happen if data integrity is maintained
            # but good to have a fallback or raise an error
            logger.error("User ID not found in user_quest_data during claim.")
            return False, "Critical error: User ID missing for quest.", {}
        
        if not quest_data.get("is_complete", False):
            return False, "Quest is not complete", {}
            
        if quest_data.get("is_claimed", False):
            return False, "Quest reward already claimed", {}
        
        # Get quest details to return reward info
        quest_id = quest_data.get("quest_id")
        quest_result = supabase.client.table(QUESTS_TABLE) \
            .select("*") \
            .eq("quest_id", quest_id) \
            .execute()
            
        quest_details = quest_result.data[0] if quest_result.data else {}
        
        # Update the quest to claimed status
        result = supabase.client.table(USER_QUESTS_TABLE) \
            .update({"is_claimed": True, "claimed_at": datetime.utcnow().isoformat()}) \
            .eq("user_quest_id", user_quest_id) \
            .execute()
        
        if result.data and len(result.data) > 0:
            # Quest marked as claimed. Now, award the XP by calling the RPC.
            xp_to_award = quest_details.get("xp_reward", 0)
            rp_xp_to_award = quest_details.get("race_pass_xp_reward", 0)

            logger.info(f"Attempting to award {xp_to_award} XP and {rp_xp_to_award} RP XP to user {current_user_id} via RPC.")
            
            try:
                # Call the RPC function to award XP
                award_result = supabase.client.rpc('award_xp', {
                    'p_user_id': current_user_id,
                    'p_xp_amount': xp_to_award,
                    'p_race_pass_xp': rp_xp_to_award
                }).execute()

                # Check if the RPC call was successful
                if award_result.data:
                    # Parse the response data
                    response_data = award_result.data
                    if isinstance(response_data, list) and len(response_data) > 0:
                        response_data = response_data[0]
                    
                    if isinstance(response_data, dict) and response_data.get('success'):
                        logger.info(f"XP awarded successfully via RPC")
                        
                        reward_info = {
                            "xp_reward": xp_to_award,
                            "race_pass_xp_reward": rp_xp_to_award,
                            "other_reward": quest_details.get("other_reward", {}),
                            "new_total_xp": response_data.get('new_total_xp'),
                            "new_level": response_data.get('new_level'),
                            "old_level": response_data.get('old_level', response_data.get('new_level', 1))
                        }
                        return True, "Quest reward claimed and XP awarded successfully!", reward_info
                    else:
                        logger.warning(f"RPC returned unsuccessful response: {response_data}")
                        # Quest is still claimed, just XP award failed
                        return True, "Quest reward claimed, but XP award may have failed", {
                            "xp_reward": xp_to_award,
                            "race_pass_xp_reward": rp_xp_to_award,
                            "other_reward": quest_details.get("other_reward", {})
                        }
                else:
                    logger.warning(f"RPC returned no data: {award_result}")
                    # Quest is still claimed, just XP award failed
                    return True, "Quest reward claimed, but XP award may have failed", {
                        "xp_reward": xp_to_award,
                        "race_pass_xp_reward": rp_xp_to_award,
                        "other_reward": quest_details.get("other_reward", {})
                    }
                    
            except Exception as rpc_e:
                logger.error(f"RPC call to 'award_xp' failed: {type(rpc_e).__name__} - {str(rpc_e)}")
                # Quest is still claimed, just XP award failed
                return True, f"Quest reward claimed, but XP award failed: {str(rpc_e)}", {
                    "xp_reward": xp_to_award,
                    "race_pass_xp_reward": rp_xp_to_award,
                    "other_reward": quest_details.get("other_reward", {})
                }

        else:
            logger.error(f"Failed to mark quest as claimed in DB. Result: {result.data}, Error: {result.error}")
            return False, "Failed to claim quest reward (DB update failed)", {}
    except Exception as e:
        logger.error(f"Exception in claim_quest_reward: {type(e).__name__} - {str(e)}")
        return False, f"Failed to claim quest reward due to an internal error: {str(e)}", {}

def assign_daily_quests(count: int = 3) -> Tuple[bool, str]:
    """
    Assign new daily quests to the current user.
    
    Args:
        count: Number of daily quests to assign
        
    Returns:
        Tuple[bool, str]: Success flag and message
    """
    return _assign_quests("daily", count, timedelta(days=1))

def assign_weekly_quests(count: int = 3) -> Tuple[bool, str]:
    """
    Assign new weekly quests to the current user.
    
    Args:
        count: Number of weekly quests to assign
        
    Returns:
        Tuple[bool, str]: Success flag and message
    """
    return _assign_quests("weekly", count, timedelta(days=7))

def _assign_quests(quest_type: str, count: int, expires_delta: timedelta) -> Tuple[bool, str]:
    """
    Helper function to assign quests to the current user.
    
    Args:
        quest_type: Type of quests to assign ('daily', 'weekly', etc.)
        count: Number of quests to assign
        expires_delta: Timedelta for expiration date
        
    Returns:
        Tuple[bool, str]: Success flag and message
    """
    if not supabase.is_authenticated():
        return False, "Not logged in. Please log in to assign quests"
    
    try:
        user = supabase.get_user()
        user_id = None
        
        if user:
            if hasattr(user, 'id'):
                user_id = user.id
            elif hasattr(user, 'user') and hasattr(user.user, 'id'):
                user_id = user.user.id
                
        if not user_id:
            return False, "User ID not found"
        
        # First, get random quests using RPC function
        quests_result = supabase.client.rpc('get_random_quests', {
            'p_quest_type': quest_type,
            'p_count': count
        }).execute()
        
        if not quests_result.data:
            return False, f"No {quest_type} quests available"
        
        # Calculate expiration date
        expires_at = datetime.now() + expires_delta
        
        # Remove any existing quests of this type that are not claimed
        existing_result = supabase.client.table(USER_QUESTS_TABLE) \
            .delete() \
            .eq("user_id", user_id) \
            .eq("is_claimed", False) \
            .eq("is_complete", False) \
            .not_.is_("expires_at", None) \
            .lte("expires_at", datetime.now()) \
            .execute()
        
        # Insert new user quests
        inserts = []
        for quest in quests_result.data:
            inserts.append({
                "user_id": user_id,
                "quest_id": quest["quest_id"],
                "progress": {},
                "expires_at": expires_at
            })
        
        if inserts:
            result = supabase.client.table(USER_QUESTS_TABLE) \
                .upsert(inserts) \
                .execute()
            
            if result.data:
                return True, f"Assigned {len(inserts)} {quest_type} quests"
            else:
                return False, f"Failed to assign {quest_type} quests"
        else:
            return False, "No quests to assign"
    except Exception as e:
        level = logging.INFO if "Not logged in" in str(e) else logging.ERROR
        logger.log(level, f"Failed to assign {quest_type} quests: {e}")
        return False, f"Failed to assign quests: {e}"

# ----- Race Pass Functions -----

def get_current_season() -> Tuple[Optional[Dict[str, Any]], str]:
    """
    Get the current active Race Pass season.
    
    Returns:
        Tuple[Optional[Dict[str, Any]], str]: A tuple containing season data (or None) and a message
    """
    try:
        # Call Supabase function to get current season ID (pass empty params dict per client API)
        season_id_result = supabase.client.rpc('get_current_season', {}).execute()
        
        if not season_id_result.data:
            return None, "No active season found"
        
        current_season_id = season_id_result.data
        
        # Get season details
        season_result = supabase.client.table(RACE_PASS_SEASONS_TABLE) \
            .select("*") \
            .eq("season_id", current_season_id) \
            .execute()
        
        if season_result.data and len(season_result.data) > 0:
            return season_result.data[0], "Season retrieved successfully"
        else:
            return None, "Season details not found"
    except Exception as e:
        # Downgrade to info when unauthenticated to reduce noise during startup
        level = logging.INFO if "Not logged in" in str(e) else logging.ERROR
        logger.log(level, f"Failed to retrieve current season: {e}")
        return None, f"Failed to retrieve current season: {e}"

def get_race_pass_rewards(season_id: str = None) -> Tuple[Optional[List[Dict[str, Any]]], str]:
    """
    Get all rewards for a Race Pass season.
    
    Args:
        season_id: Season ID to get rewards for (defaults to current season)
        
    Returns:
        Tuple[Optional[List[Dict[str, Any]]], str]: A tuple containing rewards data (or None) and a message
    """
    try:
        # If no season ID provided, get current season
        if not season_id:
            season_result = get_current_season()
            if not season_result[0]:
                return None, "No active season found"
            season_id = season_result[0].get("season_id")
        
        # Get rewards for the season
        rewards_result = supabase.client.table(RACE_PASS_REWARDS_TABLE) \
            .select("*") \
            .eq("season_id", season_id) \
            .order("tier", {"ascending": True}) \
            .execute()
        
        if rewards_result.data:
            return rewards_result.data, "Rewards retrieved successfully"
        else:
            return [], "No rewards found for this season"
    except Exception as e:
        logger.error(f"Failed to retrieve race pass rewards: {e}")
        return None, f"Failed to retrieve rewards: {e}"

def get_user_race_pass_progress() -> Tuple[Optional[Dict[str, Any]], str]:
    """
    Get the current user's Race Pass progress and available rewards.
    
    Returns:
        Tuple[Optional[Dict[str, Any]], str]: A tuple containing progress data (or None) and a message
    """
    if not supabase.is_authenticated():
        return None, "Not logged in. Please log in to view race pass progress"
    
    try:
        # Get user profile to check race pass status
        profile_result = get_user_profile()
        if not profile_result[0]:
            return None, profile_result[1]
        
        profile = profile_result[0]
        season_id = profile.get("race_pass_season_id")
        
        if not season_id:
            # No active season for this user
            return {
                "has_active_season": False,
                "season": None,
                "tier": 0,
                "xp": 0,
                "is_premium": False,
                "rewards": []
            }, "User has no active race pass season"
        
        # Get season details
        season_result = supabase.client.table(RACE_PASS_SEASONS_TABLE) \
            .select("*") \
            .eq("season_id", season_id) \
            .execute()
        
        if not (season_result.data and len(season_result.data) > 0):
            return None, "Season not found"
        
        season = season_result.data[0]
        
        # Get user's available rewards
        user = supabase.get_user()
        user_id = None
        
        if user:
            if hasattr(user, 'id'):
                user_id = user.id
            elif hasattr(user, 'user') and hasattr(user.user, 'id'):
                user_id = user.user.id
        
        rewards_result = supabase.client.rpc('get_user_available_rewards', {
            'p_user_id': user_id
        }).execute()
        
        # Compile the race pass progress data
        race_pass_data = {
            "has_active_season": True,
            "season": season,
            "tier": profile.get("race_pass_tier", 0),
            "xp": profile.get("race_pass_xp", 0),
            "is_premium": profile.get("is_premium_pass_active", False),
            "level": profile.get("level", 1),
            "current_xp": profile.get("current_xp", 0),
            "total_xp_needed": profile.get("total_xp_needed", None),
            "rewards": rewards_result.data if rewards_result.data else []
        }
        
        return race_pass_data, "Race pass progress retrieved successfully"
    except Exception as e:
        level = logging.INFO if "Not logged in" in str(e) else logging.ERROR
        logger.log(level, f"Failed to retrieve race pass progress: {e}")
        return None, f"Failed to retrieve race pass progress: {e}"

def claim_race_pass_reward(reward_id: str) -> Tuple[bool, str]:
    """Claim a race pass reward via RPC. Returns success and message."""
    if not supabase.is_authenticated():
        return False, "Not logged in. Please log in to claim rewards"
    try:
        result = supabase.client.rpc('claim_race_pass_reward', { 'p_reward_id': reward_id }).execute()
        if result.data and isinstance(result.data, list) and len(result.data) > 0:
            row = result.data[0]
            return bool(row.get('success', False)), row.get('message', '')
        return False, "Unexpected response"
    except Exception as e:
        logger.error(f"Failed to claim race pass reward: {e}")
        return False, f"Failed to claim reward: {e}"

def get_trackcoins_balance() -> Tuple[Optional[int], str]:
    """Return the current user's TrackCoins balance."""
    if not supabase.is_authenticated():
        return None, "Not logged in"
    try:
        profile, _ = get_user_profile()
        if profile is None:
            return None, "Profile not found"
        return int(profile.get('trackcoins_balance', 0)), "OK"
    except Exception as e:
        logger.error(f"Failed to fetch TrackCoins balance: {e}")
        return None, f"{e}"

def spend_trackcoins(amount: int, reason: str = 'purchase', metadata: Dict[str, Any] | None = None) -> Tuple[bool, str]:
    """Spend TrackCoins via RPC."""
    if not supabase.is_authenticated():
        return False, "Not logged in"
    try:
        user = supabase.get_user()
        user_id = getattr(user, 'id', None) or (getattr(user, 'user', None).id if getattr(user, 'user', None) else None)
        if not user_id:
            return False, "User ID not found"
        meta = metadata or {}
        res = supabase.client.rpc('spend_trackcoins', {
            'p_user_id': user_id,
            'p_amount': amount,
            'p_reason': reason,
            'p_meta': json.dumps(meta)
        }).execute()
        if res.data and isinstance(res.data, list) and len(res.data) > 0:
            row = res.data[0]
            return bool(row.get('success', False)), row.get('message', '')
        return False, "Unexpected response"
    except Exception as e:
        logger.error(f"Failed to spend TrackCoins: {e}")
        return False, f"{e}"

def unlock_premium_with_trackcoins(cost: int = 1000) -> Tuple[bool, str]:
    """Spend TrackCoins and activate premium RP for the current user."""
    if not supabase.is_authenticated():
        return False, "Not logged in"
    ok, msg = spend_trackcoins(cost, 'premium_unlock')
    if not ok:
        return False, msg or "Insufficient TrackCoins"
    try:
        user = supabase.get_user()
        user_id = getattr(user, 'id', None) or (getattr(user, 'user', None).id if getattr(user, 'user', None) else None)
        if not user_id:
            return False, "User ID not found"
        res = supabase.client.table(USER_PROFILES_TABLE).update({
            'is_premium_pass_active': True
        }).eq('user_id', user_id).execute()
        if res.data:
            return True, "Premium unlocked"
        return False, "Failed to activate premium"
    except Exception as e:
        logger.error(f"Failed to unlock premium: {e}")
        return False, f"{e}"

def activate_race_pass_season(season_id: str) -> Tuple[bool, str]:
    """
    Activate a Race Pass season for the current user.
    
    Args:
        season_id: ID of the season to activate
        
    Returns:
        Tuple[bool, str]: Success flag and message
    """
    if not supabase.is_authenticated():
        return False, "Not logged in. Please log in to activate a race pass season"
    
    try:
        user = supabase.get_user()
        user_id = None
        
        if user:
            if hasattr(user, 'id'):
                user_id = user.id
            elif hasattr(user, 'user') and hasattr(user.user, 'id'):
                user_id = user.user.id
                
        if not user_id:
            return False, "User ID not found"
        
        # Verify season exists and is active
        season_result = supabase.client.table(RACE_PASS_SEASONS_TABLE) \
            .select("*") \
            .eq("season_id", season_id) \
            .eq("is_active", True) \
            .execute()
        
        if not (season_result.data and len(season_result.data) > 0):
            return False, "Season not found or not active"
        
        # Update user profile with new season
        result = supabase.client.table(USER_PROFILES_TABLE) \
            .update({
                "race_pass_season_id": season_id,
                "race_pass_tier": 0,
                "race_pass_xp": 0
            }) \
            .eq("user_id", user_id) \
            .execute()
        
        if result.data and len(result.data) > 0:
            return True, "Race pass season activated successfully"
        else:
            return False, "Failed to activate race pass season"
    except Exception as e:
        logger.error(f"Failed to activate race pass season: {e}")
        return False, f"Failed to activate race pass season: {e}"

def purchase_premium_race_pass() -> Tuple[bool, str]:
    """
    Mark the current user's race pass as premium.
    
    Returns:
        Tuple[bool, str]: Success flag and message
    """
    if not supabase.is_authenticated():
        return False, "Not logged in. Please log in to purchase premium race pass"
    
    try:
        user = supabase.get_user()
        user_id = None
        
        if user:
            if hasattr(user, 'id'):
                user_id = user.id
            elif hasattr(user, 'user') and hasattr(user.user, 'id'):
                user_id = user.user.id
                
        if not user_id:
            return False, "User ID not found"
        
        # Update user profile
        result = supabase.client.table(USER_PROFILES_TABLE) \
            .update({"is_premium_pass_active": True}) \
            .eq("user_id", user_id) \
            .execute()
        
        if result.data and len(result.data) > 0:
            return True, "Premium race pass purchased successfully"
        else:
            return False, "Failed to purchase premium race pass"
    except Exception as e:
        logger.error(f"Failed to purchase premium race pass: {e}")
        return False, f"Failed to purchase premium race pass: {e}" 