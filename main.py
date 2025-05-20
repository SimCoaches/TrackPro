"""
TrackPro Supabase Integration Demo

This script demonstrates how to use the Supabase integration for user authentication
and profile management in the TrackPro application.
"""

import os
import sys
import getpass
import datetime
from Supabase import auth, database

def clear_screen():
    """Clear the terminal screen."""
    os.system('cls' if os.name == 'nt' else 'clear')

def print_header(title):
    """Print a formatted header."""
    print("\n" + "=" * 50)
    print(f"{title.center(50)}")
    print("=" * 50 + "\n")

def validate_date_of_birth(date_str):
    """
    Validate a date string in YYYY-MM-DD format.
    
    Args:
        date_str: The date string to validate
        
    Returns:
        bool: True if the date is valid, False otherwise
    """
    try:
        if not date_str:
            return False
        
        # Parse the date
        year, month, day = map(int, date_str.split('-'))
        datetime.date(year, month, day)
        
        # Check if date is not in the future
        today = datetime.date.today()
        input_date = datetime.date(year, month, day)
        if input_date > today:
            return False
            
        return True
    except (ValueError, TypeError):
        return False

def signup_menu():
    """Display the signup menu and handle user input."""
    print_header("SIGNUP")
    
    email = input("Email: ")
    password = getpass.getpass("Password: ")
    confirm_password = getpass.getpass("Confirm Password: ")
    
    if password != confirm_password:
        print("\nError: Passwords do not match. Please try again.")
        input("\nPress Enter to continue...")
        return
    
    success, message = auth.signup(email, password)
    print(f"\n{message}")
    
    input("\nPress Enter to continue...")

def login_menu():
    """Display the login menu and handle user input."""
    print_header("LOGIN")
    
    email = input("Email: ")
    password = getpass.getpass("Password: ")
    
    success, message = auth.login(email, password)
    print(f"\n{message}")
    
    if success:
        # If login is successful, prompt for profile details
        print("\nLet's set up your profile:")
        
        username = input("Username: ")
        first_name = input("First Name: ")
        last_name = input("Last Name: ")
        
        date_of_birth = ""
        while not validate_date_of_birth(date_of_birth):
            date_of_birth = input("Date of Birth (YYYY-MM-DD): ")
            if not validate_date_of_birth(date_of_birth):
                print("Invalid date format. Please use YYYY-MM-DD and ensure the date is not in the future.")
        
        profile_success, profile_message = database.create_or_update_profile(
            username, first_name, last_name, date_of_birth
        )
        print(f"\n{profile_message}")
    
    input("\nPress Enter to continue...")
    return success

def profile_menu():
    """Display the profile menu and handle user input."""
    while True:
        clear_screen()
        print_header("PROFILE")
        
        # Get and display profile
        profile_data, message = database.get_profile()
        
        if profile_data:
            print(f"Username: {profile_data.get('username', 'N/A')}")
            print(f"First Name: {profile_data.get('first_name', 'N/A')}")
            print(f"Last Name: {profile_data.get('last_name', 'N/A')}")
            print(f"Date of Birth: {profile_data.get('date_of_birth', 'N/A')}")
            print(f"Email: {profile_data.get('email', 'N/A')}")
            created_at = profile_data.get('created_at', 'N/A')
            print(f"Created At: {created_at}")
        else:
            print(message)
        
        print("\nOptions:")
        print("1. Update Profile")
        print("2. Delete Profile")
        print("3. Logout")
        print("4. Back to Main Menu")
        
        choice = input("\nEnter your choice (1-4): ")
        
        if choice == "1":
            print("\nEnter new profile details (leave blank to keep current):")
            username = input(f"Username [{profile_data.get('username', '')}]: ") or profile_data.get('username', '')
            first_name = input(f"First Name [{profile_data.get('first_name', '')}]: ") or profile_data.get('first_name', '')
            last_name = input(f"Last Name [{profile_data.get('last_name', '')}]: ") or profile_data.get('last_name', '')
            
            current_dob = profile_data.get('date_of_birth', '')
            date_of_birth = input(f"Date of Birth [{current_dob}] (YYYY-MM-DD): ") or current_dob
            
            while date_of_birth and not validate_date_of_birth(date_of_birth):
                print("Invalid date format. Please use YYYY-MM-DD and ensure the date is not in the future.")
                date_of_birth = input(f"Date of Birth [{current_dob}] (YYYY-MM-DD): ") or current_dob
            
            success, message = database.create_or_update_profile(
                username, first_name, last_name, date_of_birth
            )
            print(f"\n{message}")
            input("\nPress Enter to continue...")
        
        elif choice == "2":
            confirm = input("\nAre you sure you want to delete your profile? (y/n): ")
            if confirm.lower() == 'y':
                success, message = database.delete_profile()
                print(f"\n{message}")
                input("\nPress Enter to continue...")
                if success:
                    return
            
        elif choice == "3":
            success, message = auth.logout()
            print(f"\n{message}")
            input("\nPress Enter to continue...")
            return
            
        elif choice == "4":
            return

def main_menu():
    """Display the main menu and handle user input."""
    while True:
        clear_screen()
        print_header("TRACKPRO SUPABASE DEMO")
        
        if auth.is_logged_in():
            user = auth.get_current_user()
            print(f"Logged in as: {user.email if user else 'Unknown'}\n")
            
            print("Options:")
            print("1. View/Edit Profile")
            print("2. Logout")
            print("3. Exit")
            
            choice = input("\nEnter your choice (1-3): ")
            
            if choice == "1":
                profile_menu()
            elif choice == "2":
                success, message = auth.logout()
                print(f"\n{message}")
                input("\nPress Enter to continue...")
            elif choice == "3":
                print("\nExiting TrackPro Supabase Demo. Goodbye!")
                sys.exit(0)
            else:
                print("\nInvalid choice. Please try again.")
                input("\nPress Enter to continue...")
        else:
            print("Options:")
            print("1. Signup")
            print("2. Login")
            print("3. Exit")
            
            choice = input("\nEnter your choice (1-3): ")
            
            if choice == "1":
                signup_menu()
            elif choice == "2":
                login_menu()
            elif choice == "3":
                print("\nExiting TrackPro Supabase Demo. Goodbye!")
                sys.exit(0)
            else:
                print("\nInvalid choice. Please try again.")
                input("\nPress Enter to continue...")

if __name__ == "__main__":
    try:
        main_menu()
    except KeyboardInterrupt:
        print("\n\nProgram interrupted. Exiting...")
        sys.exit(0)
    except Exception as e:
        print(f"\nAn error occurred: {e}")
        input("\nPress Enter to exit...")
        sys.exit(1) 