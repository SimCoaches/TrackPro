CREATE OR REPLACE FUNCTION public.delete_user_and_related(p_user_id UUID)
RETURNS VOID
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
  -- Scrub unique username to immediately free the original
  UPDATE public.user_profiles
  SET username = 'deleted_' || LEFT(p_user_id::text, 8),
      display_name = 'Deleted User',
      bio = NULL,
      avatar_url = NULL
  WHERE user_id = p_user_id;

  -- Remove dependent data (best-effort; ignore if tables are missing)
  BEGIN
    DELETE FROM public.user_stats WHERE user_id = p_user_id;
  EXCEPTION WHEN undefined_table THEN NULL; END;

  BEGIN
    DELETE FROM public.user_details WHERE user_id = p_user_id;
  EXCEPTION WHEN undefined_table THEN NULL; END;

  BEGIN
    DELETE FROM public.private_messages WHERE sender_id = p_user_id;
  EXCEPTION WHEN undefined_table THEN NULL; END;

  BEGIN
    DELETE FROM public.private_conversations
    WHERE conversation_id IN (
      SELECT conversation_id FROM public.conversation_participants WHERE user_id = p_user_id
    );
  EXCEPTION WHEN undefined_table THEN NULL; END;

  BEGIN
    DELETE FROM public.conversation_participants WHERE user_id = p_user_id;
  EXCEPTION WHEN undefined_table THEN NULL; END;

  BEGIN
    DELETE FROM public.friendships WHERE requester_id = p_user_id OR addressee_id = p_user_id;
  EXCEPTION WHEN undefined_table THEN NULL; END;

  BEGIN
    DELETE FROM public.user_friends WHERE user_id = p_user_id OR friend_id = p_user_id;
  EXCEPTION WHEN undefined_table THEN NULL; END;

  BEGIN
    DELETE FROM public.community_messages WHERE sender_id = p_user_id;
  EXCEPTION WHEN undefined_table THEN NULL; END;

  BEGIN
    DELETE FROM public.community_participants WHERE user_id = p_user_id;
  EXCEPTION WHEN undefined_table THEN NULL; END;

  -- Finally, remove the profile row
  DELETE FROM public.user_profiles WHERE user_id = p_user_id;
END;
$$;

GRANT EXECUTE ON FUNCTION public.delete_user_and_related(UUID) TO authenticated;

