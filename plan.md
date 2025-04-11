# TrackPro Authentication System Overhaul Plan

## Phase 1: Fix Basic Authentication (Priority)

### Step 1: Create a New Supabase Project
- Create a new Supabase project through the dashboard
- Note the new project URL and API keys (anon and service_role)
- Update application configuration with new credentials

### Step 2: Set Up Required Database Schema
- Create the `user_details` table:
  ```sql
  CREATE TABLE public.user_details (
    id UUID PRIMARY KEY REFERENCES auth.users(id),
    username TEXT,
    first_name TEXT,
    last_name TEXT,
    date_of_birth DATE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL
  );
  ```

- Create the `user_profiles` table (if needed):
  ```sql
  CREATE TABLE public.user_profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id),
    email TEXT NOT NULL,
    display_name TEXT,
    settings JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL
  );
  ```

### Step 3: Create Database Triggers
- Create trigger to automatically create user_details record when a user registers:
  ```sql
  CREATE OR REPLACE FUNCTION public.handle_new_user()
  RETURNS TRIGGER AS $$
  BEGIN
    INSERT INTO public.user_details (
      id, 
      username, 
      first_name, 
      last_name, 
      date_of_birth
    ) VALUES (
      NEW.id, 
      COALESCE(NEW.raw_user_meta_data->>'username', split_part(NEW.email, '@', 1)), 
      COALESCE(NEW.raw_user_meta_data->>'first_name', 'User'),
      COALESCE(NEW.raw_user_meta_data->>'last_name', ''),
      COALESCE((NEW.raw_user_meta_data->>'date_of_birth')::date, CURRENT_DATE - INTERVAL '18 years')
    );
    RETURN NEW;
  END;
  $$ LANGUAGE plpgsql SECURITY DEFINER;

  CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();
  ```

### Step 4: Set Up RLS Policies
- Add proper Row Level Security (RLS) policies:
  ```sql
  -- Enable RLS on tables
  ALTER TABLE public.user_details ENABLE ROW LEVEL SECURITY;
  ALTER TABLE public.user_profiles ENABLE ROW LEVEL SECURITY;

  -- User can read/write their own data
  CREATE POLICY "Users can view their own data" 
  ON public.user_details FOR SELECT 
  USING (auth.uid() = id);

  CREATE POLICY "Users can modify their own data" 
  ON public.user_details FOR UPDATE 
  USING (auth.uid() = id);

  -- Similar policies for user_profiles
  CREATE POLICY "Users can view their own profile" 
  ON public.user_profiles FOR SELECT 
  USING (auth.uid() = id);

  CREATE POLICY "Users can modify their own profile" 
  ON public.user_profiles FOR UPDATE 
  USING (auth.uid() = id);
  ```

### Step 5: Update Application Config
- Modify the config.py file to point to the new Supabase project
- Test basic email/password signup and login

## Phase 2: Add Social Login Providers (After Phase 1 Complete)

### Step 1: Set Up Google OAuth
1. Create OAuth credentials in Google Cloud Console:
   - Create a new project (or use existing)
   - Configure OAuth consent screen
   - Create OAuth client ID (Web application type)
   - Add authorized redirect URIs: `https://[PROJECT_REF].supabase.co/auth/v1/callback`

2. Configure Google Provider in Supabase:
   - Go to Authentication → Providers
   - Enable Google provider
   - Enter Client ID and Client Secret from Google
   - Save changes

### Step 2: Set Up Discord OAuth
1. Create OAuth application in Discord Developer Portal:
   - Go to https://discord.com/developers/applications
   - Create a new application
   - Go to OAuth2 settings
   - Add redirect URL: `https://[PROJECT_REF].supabase.co/auth/v1/callback`
   - Copy Client ID and Client Secret

2. Configure Discord Provider in Supabase:
   - Go to Authentication → Providers
   - Enable Discord provider
   - Enter Client ID and Client Secret from Discord
   - Save changes

### Step 3: Update Application Code for Social Login
1. Add social login buttons to the login UI:
   - Add Google login button
   - Add Discord login button

2. Implement social login handlers:
   ```python
   # For Google login
   def sign_in_with_google(self):
       try:
           response = supabase.auth.sign_in_with_oauth({
               "provider": "google",
               "options": {
                   "redirect_to": "app://callback"  # For desktop apps
               }
           })
           # Handle response and redirect
           return response
       except Exception as e:
           logger.error(f"Google login error: {e}")
           raise

   # For Discord login
   def sign_in_with_discord(self):
       try:
           response = supabase.auth.sign_in_with_oauth({
               "provider": "discord",
               "options": {
                   "redirect_to": "app://callback"  # For desktop apps
               }
           })
           # Handle response and redirect
           return response
       except Exception as e:
           logger.error(f"Discord login error: {e}")
           raise
   ```

3. Implement OAuth callback handler for desktop app:
   - Create a custom URL scheme handler (app://callback)
   - Extract token from URL
   - Complete the OAuth flow with Supabase

### Step 4: Update User Management for Social Logins
1. Handle first-time social login to populate user_details:
   - Check if additional details are needed after social login
   - Prompt for any missing required information

2. Update sign-up dialog to include social options
   - Add social login buttons to signup_dialog.py
   - Implement switching between traditional and social signup

## Phase 3: Testing and Validation

### Email/Password Authentication Tests
- Test user registration
- Test login with registered credentials
- Test password reset flow

### Social Login Tests
- Test Google login flow
- Test Discord login flow
- Test account linking (if implemented)
- Test logout and re-login

### Edge Cases
- Test handling of users who signed up with email then try social login
- Test handling of social login users who try to use email login
- Test token refresh and session persistence

## Phase 4: Production Deployment
- Ensure all secrets are properly stored in environment variables
- Review and optimize RLS policies
- Set up appropriate email templates for auth flows
- Monitor auth logs for any issues

---

**Note:** Keep track of the credentials and configuration details for each service:
- Supabase Project URL
- Supabase anon key and service_role key
- Google OAuth Client ID and Secret
- Discord OAuth Client ID and Secret 