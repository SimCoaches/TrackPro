# TrackPro Supabase Integration

This folder contains all the code needed to interact with Supabase for authentication and database operations in the TrackPro application.

## Overview

The Supabase integration provides the following functionality:

- User authentication (signup, login, logout)
- User profile management (create, update, retrieve, delete)
- Secure database operations with Row-Level Security (RLS)

## File Structure

- `__init__.py`: Makes Supabase a Python package
- `client.py`: Initializes the Supabase client
- `auth.py`: Handles authentication (signup, login, logout)
- `database.py`: Handles database operations (e.g., profiles)

## Setup

1. Ensure you have the required dependencies installed:
   ```
   pip install supabase python-dotenv
   ```

2. Create a `.env` file in the root directory with your Supabase credentials:
   ```
   SUPABASE_URL=your_supabase_url
   SUPABASE_KEY=your_supabase_anon_key
   ```

3. Set up a `profiles` table in your Supabase project with the following columns:
   - `id` (UUID, primary key, references auth.users(id))
   - `username` (text, unique)
   - `created_at` (timestamp, default NOW())

4. Enable Row-Level Security (RLS) with a policy that allows users to only access their own profile:
   ```sql
   CREATE POLICY "Users can only access their own profile"
   ON profiles
   FOR ALL
   USING (auth.uid() = id);
   ```

## Usage

### Authentication

```python
from Supabase import auth

# Signup
success, message = auth.signup("user@example.com", "password123")
print(message)  # "Signup successful, please verify your email"

# Login
success, message = auth.login("user@example.com", "password123")
print(message)  # "Login successful"

# Check if logged in
if auth.is_logged_in():
    user = auth.get_current_user()
    print(f"Logged in as: {user.email}")

# Logout
success, message = auth.logout()
print(message)  # "Logout successful"
```

### Database Operations

```python
from Supabase import database

# Create or update profile
success, message = database.create_or_update_profile("username123")
print(message)  # "Profile created successfully" or "Profile updated successfully"

# Get profile
profile, message = database.get_profile()
if profile:
    print(f"Username: {profile.get('username')}")
    print(f"Created At: {profile.get('created_at')}")
else:
    print(message)  # "Profile not found" or error message

# Delete profile
success, message = database.delete_profile()
print(message)  # "Profile deleted successfully"
```

## Demo

A demo application is provided in the root directory (`main.py`) that demonstrates how to use the Supabase integration for user authentication and profile management.

To run the demo:
```
python main.py
```

## Security Considerations

- Keep your `.env` file secure and don't commit it to version control (add to `.gitignore`).
- Use the anon key for client-side operations; for server-side scripts, consider using the service role key with caution.
- Ensure Row-Level Security (RLS) is properly configured to protect user data.

## Error Handling

All functions return a tuple containing a success flag (boolean) and a message (string) to help with error handling and user feedback.

## Future Enhancements

- Password recovery
- Additional profile fields
- Session token refresh for long-lived sessions
- Multi-factor authentication 