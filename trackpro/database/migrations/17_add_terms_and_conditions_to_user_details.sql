DO $$
BEGIN
  IF NOT EXISTS(SELECT 1 FROM information_schema.columns WHERE table_name='user_details' AND column_name='terms_accepted') THEN
    ALTER TABLE public.user_details ADD COLUMN terms_accepted BOOLEAN DEFAULT FALSE;
  END IF;
  IF NOT EXISTS(SELECT 1 FROM information_schema.columns WHERE table_name='user_details' AND column_name='terms_version_accepted') THEN
    ALTER TABLE public.user_details ADD COLUMN terms_version_accepted TEXT DEFAULT '';
  END IF;
END $$; 