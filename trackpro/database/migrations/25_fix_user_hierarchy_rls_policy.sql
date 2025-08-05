-- Fix infinite recursion in user_hierarchy RLS policy
-- The current policy causes infinite recursion because it queries the same table it's protecting

-- Drop the problematic policy
DROP POLICY IF EXISTS "Dev users can modify hierarchy" ON "user_hierarchy";

-- Create a new policy that doesn't cause infinite recursion
-- Instead of checking if user is dev in the same table, we'll use a simpler approach
-- Only allow users to modify their own hierarchy or use a function-based approach
CREATE POLICY "Users can modify own hierarchy" 
    ON "user_hierarchy" FOR ALL 
    USING (auth.uid() = user_id);

-- Create a function to check if user is dev without causing recursion
CREATE OR REPLACE FUNCTION public.is_user_dev_safe(user_uuid UUID)
RETURNS BOOLEAN AS $$
BEGIN
    -- Use a direct query without RLS to avoid recursion
    RETURN EXISTS (
        SELECT 1 FROM user_hierarchy 
        WHERE user_id = user_uuid AND is_dev = TRUE
    );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Create a policy for dev users that uses the safe function
CREATE POLICY "Dev users can modify any hierarchy" 
    ON "user_hierarchy" FOR ALL 
    USING (public.is_user_dev_safe(auth.uid()));

-- Add comment explaining the fix
COMMENT ON FUNCTION public.is_user_dev_safe IS 'Safe function to check if user is dev without causing RLS recursion'; 