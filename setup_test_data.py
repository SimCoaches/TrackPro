#!/usr/bin/env python3
"""
Setup test data for TrackPro Community Features
This script creates test users, friendships, activities, teams, clubs, and events
"""

import uuid
from datetime import datetime, timedelta
from supabase import create_client

# Supabase configuration
SUPABASE_URL = "https://xbfotxwpntqplvvsffrr.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InhiZm90eHdwbnRxcGx2dnNmZnJyIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDQzMTM5NjUsImV4cCI6MjA1OTg4OTk2NX0.AwLUhaxQQn9xnpTwgOrRIdWQYsVI9-ikC2Qb-6SR2h8"

def main():
    # Initialize Supabase client
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    print("Setting up TrackPro Community test data...")
    
    # Create test user profiles (these would normally be created through signup)
    test_users = [
        {
            "user_id": str(uuid.uuid4()),
            "username": "speedster123",
            "email": "speedster123@example.com",
            "display_name": "Alex Speedster",
            "bio": "Professional sim racer and setup expert",
            "level": 15,
            "social_xp": 2500,
            "reputation_score": 85
        },
        {
            "user_id": str(uuid.uuid4()),
            "username": "racingpro",
            "email": "racingpro@example.com", 
            "display_name": "Maria Racing",
            "bio": "Formula 1 enthusiast and data analyst",
            "level": 12,
            "social_xp": 1800,
            "reputation_score": 72
        },
        {
            "user_id": str(uuid.uuid4()),
            "username": "trackmaster",
            "email": "trackmaster@example.com",
            "display_name": "Track Master",
            "bio": "Endurance racing specialist",
            "level": 18,
            "social_xp": 3200,
            "reputation_score": 91
        }
    ]
    
    try:
        # Insert test users
        print("Creating test user profiles...")
        supabase.table("user_profiles").insert(test_users).execute()
        
        # Create user stats for each user
        user_stats = []
        for user in test_users:
            user_stats.append({
                "user_id": user["user_id"],
                "total_laps": 500 + (hash(user["username"]) % 1000),
                "total_distance_km": 1500.5 + (hash(user["username"]) % 2000),
                "total_time_seconds": 180000 + (hash(user["username"]) % 50000),
                "best_lap_time": 95.234 + (hash(user["username"]) % 20),
                "last_active": (datetime.now() - timedelta(minutes=hash(user["username"]) % 120)).isoformat()
            })
        
        print("Creating user stats...")
        supabase.table("user_stats").insert(user_stats).execute()
        
        # Create some friendships
        friendships = [
            {
                "requester_id": test_users[0]["user_id"],
                "addressee_id": test_users[1]["user_id"], 
                "status": "accepted",
                "created_at": (datetime.now() - timedelta(days=5)).isoformat()
            },
            {
                "requester_id": test_users[1]["user_id"],
                "addressee_id": test_users[2]["user_id"],
                "status": "accepted", 
                "created_at": (datetime.now() - timedelta(days=3)).isoformat()
            },
            {
                "requester_id": test_users[0]["user_id"],
                "addressee_id": test_users[2]["user_id"],
                "status": "pending",
                "created_at": (datetime.now() - timedelta(hours=2)).isoformat()
            }
        ]
        
        print("Creating friendships...")
        supabase.table("friendships").insert(friendships).execute()
        
        # Create some user activities
        activities = [
            {
                "user_id": test_users[0]["user_id"],
                "activity_type": "personal_best",
                "title": "New Personal Best!",
                "description": "Just set a new PB at Silverstone GP with a 1:28.456!",
                "metadata": {"track": "Silverstone GP", "car": "McLaren MP4-30", "time": "1:28.456"},
                "privacy_level": "friends",
                "created_at": (datetime.now() - timedelta(hours=3)).isoformat()
            },
            {
                "user_id": test_users[1]["user_id"],
                "activity_type": "achievement",
                "title": "Achievement Unlocked",
                "description": "Earned the 'Speed Demon' achievement for 100 clean laps!",
                "metadata": {"achievement": "Speed Demon", "laps": 100},
                "privacy_level": "friends",
                "created_at": (datetime.now() - timedelta(hours=6)).isoformat()
            },
            {
                "user_id": test_users[2]["user_id"],
                "activity_type": "setup_shared",
                "title": "Shared New Setup", 
                "description": "Posted a new Monaco setup for the Ferrari SF70H - check it out!",
                "metadata": {"track": "Monaco", "car": "Ferrari SF70H", "setup_type": "Qualifying"},
                "privacy_level": "friends",
                "created_at": (datetime.now() - timedelta(hours=8)).isoformat()
            }
        ]
        
        print("Creating user activities...")
        supabase.table("user_activities").insert(activities).execute()
        
        # Create some racing teams
        teams = [
            {
                "name": "Apex Legends Racing",
                "description": "Elite sim racing team focused on Formula 1 championships",
                "created_by": test_users[0]["user_id"],
                "max_members": 25,
                "privacy_level": "public"
            },
            {
                "name": "Endurance Masters",
                "description": "Dedicated to long-distance endurance racing events",
                "created_by": test_users[2]["user_id"],
                "max_members": 30,
                "privacy_level": "public"
            }
        ]
        
        print("Creating racing teams...")
        team_response = supabase.table("teams").insert(teams).execute()
        created_teams = team_response.data
        
        # Add team members
        team_members = [
            {
                "team_id": created_teams[0]["id"],
                "user_id": test_users[0]["user_id"],
                "role": "leader"
            },
            {
                "team_id": created_teams[0]["id"],
                "user_id": test_users[1]["user_id"],
                "role": "member"
            },
            {
                "team_id": created_teams[1]["id"],
                "user_id": test_users[2]["user_id"],
                "role": "leader"
            }
        ]
        
        print("Adding team members...")
        supabase.table("team_members").insert(team_members).execute()
        
        # Create some racing clubs
        clubs = [
            {
                "name": "F1 Fanatics",
                "description": "Discussion and events for Formula 1 enthusiasts",
                "category": "Formula 1",
                "created_by": test_users[1]["user_id"],
                "member_count": 157,
                "privacy_level": "public"
            },
            {
                "name": "GT Racing Society", 
                "description": "GT car racing events and championships",
                "category": "GT Racing",
                "created_by": test_users[0]["user_id"],
                "member_count": 89,
                "privacy_level": "public"
            },
            {
                "name": "Oval Masters",
                "description": "NASCAR and oval racing specialists",
                "category": "Oval Racing", 
                "created_by": test_users[2]["user_id"],
                "member_count": 63,
                "privacy_level": "public"
            }
        ]
        
        print("Creating racing clubs...")
        club_response = supabase.table("clubs").insert(clubs).execute()
        created_clubs = club_response.data
        
        # Add club members
        club_members = [
            {
                "club_id": created_clubs[0]["id"],
                "user_id": test_users[1]["user_id"],
                "role": "founder"
            },
            {
                "club_id": created_clubs[0]["id"],
                "user_id": test_users[0]["user_id"],
                "role": "member"
            },
            {
                "club_id": created_clubs[1]["id"],
                "user_id": test_users[0]["user_id"],
                "role": "founder"
            }
        ]
        
        print("Adding club members...")
        supabase.table("club_members").insert(club_members).execute()
        
        # Create some community events
        events = [
            {
                "title": "Monaco Grand Prix Championship",
                "description": "Prestigious Formula 1 race at the legendary Monaco circuit",
                "event_type": "Championship",
                "start_time": (datetime.now() + timedelta(days=7)).isoformat(),
                "end_time": (datetime.now() + timedelta(days=7, hours=2)).isoformat(),
                "created_by": test_users[1]["user_id"],
                "max_participants": 20,
                "entry_requirements": {"min_level": 10, "min_races": 50},
                "prizes": {"first": "1000 XP", "second": "500 XP", "third": "250 XP"},
                "status": "upcoming"
            },
            {
                "title": "24 Hours of Le Mans Endurance",
                "description": "Epic 24-hour endurance race for dedicated teams",
                "event_type": "Endurance",
                "start_time": (datetime.now() + timedelta(days=14)).isoformat(),
                "end_time": (datetime.now() + timedelta(days=15)).isoformat(),
                "created_by": test_users[2]["user_id"],
                "max_participants": 60,
                "entry_requirements": {"min_level": 15, "team_required": True},
                "prizes": {"first": "5000 XP", "second": "2500 XP", "third": "1000 XP"},
                "status": "upcoming"
            }
        ]
        
        print("Creating community events...")
        event_response = supabase.table("community_events").insert(events).execute()
        created_events = event_response.data
        
        # Add some event participants
        event_participants = [
            {
                "event_id": created_events[0]["id"],
                "user_id": test_users[0]["user_id"],
                "status": "registered"
            },
            {
                "event_id": created_events[0]["id"],
                "user_id": test_users[1]["user_id"],
                "status": "registered"
            },
            {
                "event_id": created_events[1]["id"],
                "user_id": test_users[2]["user_id"],
                "status": "registered"
            }
        ]
        
        print("Adding event participants...")
        supabase.table("event_participants").insert(event_participants).execute()
        
        # Create some achievements
        achievements = [
            {
                "name": "Speed Demon",
                "description": "Complete 100 clean laps without incidents",
                "category": "Racing",
                "rarity": "rare",
                "xp_reward": 500,
                "requirements": {"clean_laps": 100}
            },
            {
                "name": "Social Butterfly",
                "description": "Add 10 friends to your network",
                "category": "Social", 
                "rarity": "common",
                "xp_reward": 250,
                "requirements": {"friends": 10}
            },
            {
                "name": "Track Master",
                "description": "Set personal bests on 20 different tracks",
                "category": "Racing",
                "rarity": "epic",
                "xp_reward": 1000,
                "requirements": {"track_pbs": 20}
            }
        ]
        
        print("Creating achievements...")
        achievement_response = supabase.table("achievements").insert(achievements).execute()
        created_achievements = achievement_response.data
        
        # Grant some achievements to users
        user_achievements = [
            {
                "user_id": test_users[1]["user_id"],
                "achievement_id": created_achievements[0]["id"],
                "unlocked_at": (datetime.now() - timedelta(days=2)).isoformat(),
                "is_showcased": True
            },
            {
                "user_id": test_users[0]["user_id"],
                "achievement_id": created_achievements[1]["id"],
                "unlocked_at": (datetime.now() - timedelta(days=1)).isoformat(),
                "is_showcased": True
            }
        ]
        
        print("Granting achievements...")
        supabase.table("user_achievements").insert(user_achievements).execute()
        
        print("\n✅ Test data setup complete!")
        print("\nTest users created:")
        for user in test_users:
            print(f"  - {user['display_name']} (@{user['username']}) - Level {user['level']}")
        
        print(f"\nCreated:")
        print(f"  - {len(friendships)} friendships")
        print(f"  - {len(activities)} user activities") 
        print(f"  - {len(teams)} racing teams")
        print(f"  - {len(clubs)} racing clubs")
        print(f"  - {len(events)} community events")
        print(f"  - {len(achievements)} achievements")
        
        print("\nYou can now test the community features with these accounts!")
        print("To see the data, create an account in TrackPro or sign in as one of the test users.")
        
    except Exception as e:
        print(f"❌ Error setting up test data: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 