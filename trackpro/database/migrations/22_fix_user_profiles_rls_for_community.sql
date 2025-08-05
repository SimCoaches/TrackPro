-- Migration: Fix user_profiles RLS policies for community functionality
-- This allows users to view other users' profiles for community messages

-- Drop the restrictive SELECT policy
DROP POLICY IF EXISTS "Users can view own profile" ON "user_profiles";

-- Create a new policy that allows authenticated users to view all profiles
-- This is needed for community messages to show sender names
CREATE POLICY "Authenticated users can view all profiles" 
    ON "user_profiles" FOR SELECT 
    USING (auth.role() = 'authenticated');

-- Keep the existing UPDATE policy (users can only update their own profile)
-- The existing policy is fine: "Users can update own profile"

-- Add a policy for INSERT (users can only insert their own profile)
CREATE POLICY "Users can insert own profile" 
    ON "user_profiles" FOR INSERT 
    WITH CHECK (auth.uid() = user_id);

-- Add a policy for DELETE (users can only delete their own profile)
CREATE POLICY "Users can delete own profile" 
    ON "user_profiles" FOR DELETE 
    USING (auth.uid() = user_id); 