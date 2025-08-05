-- Migration: Fix user_details RLS policies for community functionality
-- This allows users to view other users' details for community messages

-- Drop the restrictive SELECT policy
DROP POLICY IF EXISTS "Users can view own details" ON "user_details";

-- Create a new policy that allows authenticated users to view all details
-- This is needed for community messages to show sender names
CREATE POLICY "Authenticated users can view all details" 
    ON "user_details" FOR SELECT 
    USING (auth.role() = 'authenticated');

-- Keep the existing UPDATE policy (users can only update their own details)
-- The existing policy is fine: "Users can update own details"

-- Keep the existing INSERT policy (users can only insert their own details)
-- The existing policy is fine: "Users can insert own details" 