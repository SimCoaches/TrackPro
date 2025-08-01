-- Migration to add auth user deletion function for complete account deletion
-- This ensures full compliance with data deletion requirements

-- Create a function that can delete users from auth.users table
-- This function runs with elevated privileges (security definer)
CREATE OR REPLACE FUNCTION public.delete_auth_user_complete(user_uuid UUID)
RETURNS BOOLEAN
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    -- Delete from auth.users table (requires elevated privileges)
    DELETE FROM auth.users WHERE id = user_uuid;
    
    -- Check if deletion was successful
    IF NOT FOUND THEN
        RAISE NOTICE 'Auth user % not found or already deleted', user_uuid;
        RETURN FALSE;
    END IF;
    
    RAISE NOTICE 'Successfully deleted auth user %', user_uuid;
    RETURN TRUE;
EXCEPTION
    WHEN OTHERS THEN
        RAISE NOTICE 'Error deleting auth user %: %', user_uuid, SQLERRM;
        RETURN FALSE;
END;
$$;

-- Grant execute permission to authenticated users
GRANT EXECUTE ON FUNCTION public.delete_auth_user_complete(UUID) TO authenticated;

-- Add comment for documentation
COMMENT ON FUNCTION public.delete_auth_user_complete(UUID) IS 
'Deletes a user from auth.users table. This function runs with elevated privileges to ensure complete account deletion for compliance purposes.'; 