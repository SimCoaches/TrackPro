# TrackPro Gamification Plan

## 1. Overall Vision

- [ ] **Goal:** Increase user engagement, provide a sense of progression, and reward consistent usage of TrackPro through gamified elements.
- [ ] **Core Features:** Introduce a leveling system, daily/weekly/achievement-based Quests, and a seasonal "Race Pass".
- [ ] **Integration Point:** The primary user-facing elements will be integrated into the "Race Coach Overview" tab.

## 2. Core Mechanics

### 2.1. Leveling System

- [ ] **XP Source Definition:** Define actions that grant Experience Points (XP).
    - [ ] Laps Completed (scaled by track complexity/length?)
    - [ ] Sessions Completed (Race, Qualify, Practice)
    - [ ] Personal Bests (PB) achieved (per track/car combo)
    - [ ] Quest Completion (see section 2.2)
    - [ ] Race Pass Challenge Completion (see section 2.3)
    - [ ] Time spent actively practicing/racing (requires careful definition)
- [ ] **XP Curve Design:** Determine the XP required for each level. Implement an increasing curve (e.g., `required_xp = base_xp * (level ^ exponent)`).
- [ ] **Level Cap:** Decide on an initial level cap (or if it should be uncapped).
- [ ] **Level-Up Rewards:** Define rewards for reaching new levels.
    - [ ] Profile Titles/Badges
    - [ ] UI Customization unlocks (e.g., themes, chart color palettes) - *Optional V2*
    - [ ] Race Pass Tier Skips - *Optional*

### 2.2. Quests

- [ ] **Quest Types:**
    - [ ] **Dailies:** Simple tasks resetting every 24 hours (e.g., "Complete 10 laps", "Run a clean lap at [Track]").
    - [ ] **Weeklies:** More involved tasks resetting weekly (e.g., "Complete 50 laps at [Track]", "Set a PB in [Car Class]", "Finish 3 races").
    - [ ] **Achievements/Milestones:** One-time, long-term goals (e.g., "Reach Level 50", "Drive 1000 laps", "Master 5 different tracks" - defined by setting a PB?).
    - [ ] **Event Quests:** Time-limited quests tied to specific real-world racing events or TrackPro promotions. - *Optional V2*
- [ ] **Quest Generation/Assignment:**
    - [ ] Determine if quests are the same for all users or personalized.
    - [ ] Define logic for selecting daily/weekly quests (random pool?).
- [ ] **Quest Tracking:** Implement logic to detect quest completion based on processed iRacing telemetry/session data.
- [ ] **Quest Rewards:**
    - [ ] XP
    - [ ] Race Pass Progress (e.g., specific Race Pass XP or Stars)
    - [ ] Potentially unique cosmetics/badges for difficult achievements. - *Optional V2*

### 2.3. Race Pass

- [ ] **Seasonal Structure:** Define the length of a Race Pass Season (e.g., 8 weeks, 12 weeks).
- [ ] **Tier System:** Define the number of tiers per season (e.g., 50, 100).
- [ ] **Progression Mechanic:** How users advance tiers.
    - [ ] Earning Season XP (separate from Level XP, or linked?)
    - [ ] Completing specific Race Pass Challenges (subset of Quests, or dedicated list?)
- [ ] **Free vs. Premium Tracks:**
    - [ ] **Free:** Basic rewards available to all users at certain tiers.
    - [ ] **Premium:** Additional/better rewards for users who purchase the pass. Requires payment processing integration.
- [ ] **Reward Types:** Define rewards per tier for both Free and Premium tracks.
    - [ ] Profile Titles/Badges
    - [ ] UI Customizations (Themes, Colors, Fonts)
    - [ ] Unique Telemetry Chart Overlays/Visuals?
    - [ ] Potentially small amounts of virtual currency (if implementing a shop later) - *Optional V2*
- [ ] **Purchase Mechanism:** Plan how users purchase the Premium Race Pass (Stripe integration, etc.). - *Requires external integration*

## 3. Technical Implementation Plan

### 3.1. Database Schema (Supabase/Postgres)

- [ ] **`user_profiles` Table:**
    - `user_id` (FK to auth.users)
    - `level` (integer, default 1)
    - `current_xp` (integer, default 0)
    - `total_xp_needed` (integer, calculated based on level)
    - `race_pass_season_id` (FK to `race_pass_seasons`)
    - `race_pass_tier` (integer, default 0)
    - `race_pass_xp` (integer, default 0)
    - `is_premium_pass_active` (boolean, default false)
    - `selected_title` (text, nullable)
    - `unlocked_titles` (jsonb or array)
    - `unlocked_cosmetics` (jsonb or array) - *Optional V2*
    - `created_at`, `updated_at`
- [ ] **`quests` Table (Quest Definitions):**
    - `quest_id` (PK)
    - `quest_type` (enum: 'daily', 'weekly', 'achievement', 'event')
    - `name` (text)
    - `description` (text)
    - `completion_criteria` (jsonb: e.g., `{ "action": "complete_laps", "count": 10, "track_id": 5, "car_id": 12 }`)
    - `xp_reward` (integer)
    - `race_pass_xp_reward` (integer, nullable)
    - `other_reward` (jsonb, nullable)
    - `is_active` (boolean)
- [ ] **`user_quests` Table (Tracking Active Quests):**
    - `user_quest_id` (PK)
    - `user_id` (FK)
    - `quest_id` (FK)
    - `progress` (jsonb: e.g., `{ "laps_completed": 5 }`)
    - `is_complete` (boolean, default false)
    - `is_claimed` (boolean, default false)
    - `assigned_at` (timestamp)
    - `expires_at` (timestamp, nullable for achievements)
- [ ] **`race_pass_seasons` Table:**
    - `season_id` (PK)
    - `name` (text, e.g., "Season 1 - Genesis")
    - `start_date` (timestamp)
    - `end_date` (timestamp)
    - `tier_count` (integer)
- [ ] **`race_pass_rewards` Table:**
    - `reward_id` (PK)
    - `season_id` (FK)
    - `tier` (integer)
    - `is_premium_reward` (boolean)
    - `reward_type` (enum: 'title', 'badge', 'cosmetic', 'currency')
    - `reward_details` (jsonb: e.g., `{ "title_name": "Grid Starter" }` or `{ "cosmetic_id": "theme_carbon" }`)
- [ ] **Modify Existing Tables?**
    - [ ] Consider adding `xp_awarded` columns to tables like `lap_data` or `session_summary` after processing.

### 3.2. Backend Logic (Python - likely integrated with existing data processing)

- [ ] **XP Awarding Service:**
    - [ ] Hook into lap completion events.
    - [ ] Hook into session completion events.
    - [ ] Hook into PB detection logic.
    - [ ] Calculate XP based on defined rules.
    - [ ] Update `user_profiles` table.
    - [ ] Handle level-ups and update `total_xp_needed`.
- [ ] **Quest Service:**
    - [ ] **Generation:** Job (daily/weekly) to assign new quests to users (populate `user_quests`).
    - [ ] **Tracking:** Monitor user actions (laps, sessions, PBs) and update `progress` in `user_quests`. Mark `is_complete` when criteria met.
    - [ ] **Claiming:** Endpoint for user to claim completed quest rewards (update `is_claimed`, award XP/items).
- [ ] **Race Pass Service:**
    - [ ] **Progression:** Update `race_pass_xp` based on awarded XP or quest completion.
    - [ ] **Tier Calculation:** Determine current tier based on `race_pass_xp` (or stars/challenges).
    - [ ] **Reward Unlocking:** Logic to determine which rewards are unlocked based on tier and `is_premium_pass_active`.
- [ ] **API Endpoints (e.g., using Flask/FastAPI):**
    - [ ] `GET /profile/{user_id}`: Fetch level, XP, Race Pass status, selected title, etc.
    - [ ] `GET /quests/{user_id}`: Fetch active daily, weekly, achievement quests and their progress.
    - [ ] `POST /quests/{user_quest_id}/claim`: Claim rewards for a completed quest.
    - [ ] `GET /racepass/{user_id}`: Fetch current season info, user's tier, progress, and unlocked rewards.
    - [ ] `GET /racepass/rewards/{season_id}`: Fetch the full reward list for a season (for display).
    - [ ] `POST /racepass/purchase`: Handle premium pass purchase callback. - *Requires payment provider integration*

### 3.3. Frontend Integration (PyQt/QML - Race Coach Overview Tab)

- [x] **Display User Level & XP:** Add a visual element (e.g., progress bar, text) showing current level and XP towards the next level.
- [x] **Display Active Quests:** Show a summary of active Daily/Weekly quests and their progress.
- [x] **Display Race Pass Summary:** Show current season, user's tier, and progress towards the next tier.
- [x] **Dedicated Quest View:** Create a new widget/dialog to view all active quests (Dailies, Weeklies, Achievements) in detail and potentially claim rewards.
- [x] **Dedicated Race Pass View:** Create a new widget/dialog showing the full Race Pass track (Free/Premium) with rewards for each tier, highlighting unlocked ones.
- [ ] **Profile Customization:** Allow users to select unlocked titles/badges to display. - *Optional V2*
- [x] **Notifications:** Implement visual feedback for:
    - [x] Level Up
    - [x] Quest Complete
    - [x] Race Pass Tier Up
    - [x] Reward Unlocked/Claimed

## 4. Phased Rollout Plan

- [ ] **Phase 1: Backend Foundation & Leveling**
    - [ ] Implement DB schema (`user_profiles`).
    - [ ] Implement basic XP awarding logic for laps/sessions.
    - [ ] Implement leveling calculations.
    - [ ] Basic API for profile data.
    - [ ] Simple frontend display of Level/XP on Overview tab.
- [ ] **Phase 2: Quest System**
    - [ ] Implement DB schema (`quests`, `user_quests`).
    - [ ] Implement Quest generation/assignment logic.
    - [ ] Implement Quest tracking logic for a few core quest types.
    - [ ] Implement Quest claiming logic & rewards (XP only initially).
    - [ ] API endpoints for quests.
    - [ ] Frontend display for active quests & claiming.
- [ ] **Phase 3: Race Pass Core**
    - [ ] Implement DB schema (`race_pass_seasons`, `race_pass_rewards`).
    - [ ] Implement seasonal structure.
    - [ ] Implement Race Pass progression logic (tied to XP/Quests).
    - [ ] Implement reward definitions (titles/badges initially).
    - [ ] API endpoints for Race Pass data.
    - [ ] Frontend display for Race Pass summary & dedicated view (visual track).
- [ ] **Phase 4: Polish & Premium**
    - [ ] Refine UI/UX for all features.
    - [ ] Add more diverse Quests and Rewards (cosmetics?).
    - [ ] Implement Premium Race Pass purchase flow (if desired).
    - [x] Add notifications system.
- [ ] **Phase 5: Ongoing**
    - [ ] New Seasons, Quests, Rewards.
    - [ ] Monitor system performance and user feedback.
    - [ ] Balance XP/rewards based on data. 