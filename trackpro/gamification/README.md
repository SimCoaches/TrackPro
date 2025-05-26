# TrackPro Gamification System

This directory contains the implementation of the gamification system for TrackPro, which includes a leveling system, quests, and Race Pass features.

## Overview

The gamification system consists of:

1. **Leveling System**: Users gain XP from completing laps, sessions, and quests
2. **Quest System**: Daily, weekly, and achievement-based challenges
3. **Race Pass**: Seasonal progression with rewards on both free and premium tiers

## Components

### Database Schema (Supabase)

The gamification system uses the following Supabase tables:

- **user_profiles**: Tracks user level, XP, and Race Pass progress
- **quests**: Defines quest parameters and rewards
- **user_quests**: Tracks quest progress for each user
- **race_pass_seasons**: Defines seasons for the Race Pass
- **race_pass_rewards**: Defines rewards for each tier of a Race Pass

### Backend Integration

- `supabase_gamification.py`: API to interact with Supabase tables
- `run_migrations.py`: Tool to set up the database schema

### Frontend Components

- `overview_elements.py`: UI components for the gamification overview panel
- `quest_view.py`: Dedicated view for managing and claiming quests
- `race_pass_view.py`: View for Race Pass progress and rewards
- `notifications.py`: Notification system for achievements and rewards

## Setup Instructions

1. **Database Migration**

   Run the database migration script to set up the Supabase tables:

   ```
   python -m trackpro.database.run_migrations
   ```

   This will create all needed tables, functions, and triggers.

2. **Create Initial Data**

   After setting up the tables, you'll need to create:

   - Quests (daily, weekly, achievements)
   - A Race Pass season
   - Rewards for the Race Pass

   Example SQL for creating quests:

   ```sql
   INSERT INTO quests (quest_type, name, description, completion_criteria, xp_reward, race_pass_xp_reward)
   VALUES 
     ('daily', 'Complete 10 Laps', 'Complete 10 laps in any car/track combination', 
      '{"action": "complete_laps", "count": 10}', 100, 50),
     ('weekly', 'Set a PB at Monza', 'Set a personal best lap time at Monza', 
      '{"action": "earn_pb", "track_id": "monza"}', 250, 100),
     ('achievement', 'Drive 1000 Laps', 'Complete a total of 1000 laps', 
      '{"action": "lifetime_laps", "count": 1000}', 1000, 500);
   ```

3. **Integrate in the UI**

   The gamification system is already integrated into the Race Coach Overview tab.

## Development

### Adding New Quests

To add new quests, insert rows into the `quests` table. Quest completion is tracked through the `completion_criteria` field which should contain a JSON object with parameters that define completion conditions.

Example completion criteria formats:

- For lap-based quests: `{"action": "complete_laps", "count": 10, "track_id": "spa"}`
- For PB quests: `{"action": "earn_pb", "track_id": "monza"}`
- For session quests: `{"action": "complete_race", "count": 3}`

### Creating a Race Pass Season

To create a new Race Pass season:

1. Insert a season record:

   ```sql
   INSERT INTO race_pass_seasons (name, description, start_date, end_date, tier_count, is_active)
   VALUES ('Season 1', 'Genesis Season', '2023-06-01', '2023-09-01', 50, TRUE);
   ```

2. Add rewards for each tier:

   ```sql
   INSERT INTO race_pass_rewards (season_id, tier, is_premium_reward, reward_type, reward_details)
   VALUES 
     ('your-season-id', 1, FALSE, 'xp_boost', '{"boost_percentage": 5}'),
     ('your-season-id', 1, TRUE, 'title', '{"title": "Rookie"}');
   ```

## Integration with Race Data

The system provides hooks to award XP for:

- Completed laps
- Session completions
- Personal bests

These can be integrated by calling the appropriate functions from `supabase_gamification.py` when these events occur.

Example: 

```python
from trackpro.gamification.supabase_gamification import award_xp

# Award XP for completing a lap
award_xp(10)  # 10 XP for a standard lap

# Award XP for a personal best
award_xp(100, 50)  # 100 XP and 50 Race Pass XP for a PB
```

## Troubleshooting

- If quests aren't showing up, check that you've assigned quests to the user with `assign_daily_quests()` and `assign_weekly_quests()`
- If XP isn't updating, verify the user has an entry in the `user_profiles` table
- For database issues, run migrations with the `--force` flag to recreate tables 