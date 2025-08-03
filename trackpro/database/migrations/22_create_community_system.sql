-- Migration: Create Community System Tables
-- This adds tables for community channels and messages

-- Create community_channels table
CREATE TABLE IF NOT EXISTS "community_channels" (
    "channel_id" UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    "name" TEXT NOT NULL,
    "description" TEXT,
    "channel_type" TEXT NOT NULL DEFAULT 'text' CHECK (channel_type IN ('text', 'voice')),
    "is_private" BOOLEAN DEFAULT FALSE,
    "created_by" UUID REFERENCES "user_profiles"("user_id") ON DELETE SET NULL,
    "created_at" TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    "updated_at" TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create community_messages table
CREATE TABLE IF NOT EXISTS "community_messages" (
    "message_id" UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    "channel_id" UUID NOT NULL REFERENCES "community_channels"("channel_id") ON DELETE CASCADE,
    "sender_id" UUID NOT NULL REFERENCES "user_profiles"("user_id") ON DELETE CASCADE,
    "content" TEXT NOT NULL,
    "message_type" TEXT DEFAULT 'text' CHECK (message_type IN ('text', 'system', 'join', 'leave')),
    "created_at" TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    "updated_at" TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create community_participants table for voice channels
CREATE TABLE IF NOT EXISTS "community_participants" (
    "participant_id" UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    "channel_id" UUID NOT NULL REFERENCES "community_channels"("channel_id") ON DELETE CASCADE,
    "user_id" UUID NOT NULL REFERENCES "user_profiles"("user_id") ON DELETE CASCADE,
    "joined_at" TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    "left_at" TIMESTAMP WITH TIME ZONE,
    "is_muted" BOOLEAN DEFAULT FALSE,
    "is_deafened" BOOLEAN DEFAULT FALSE,
    "is_speaking" BOOLEAN DEFAULT FALSE,
    UNIQUE(channel_id, user_id)
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_community_channels_type ON "community_channels" (channel_type);
CREATE INDEX IF NOT EXISTS idx_community_channels_created_by ON "community_channels" (created_by);
CREATE INDEX IF NOT EXISTS idx_community_messages_channel_id ON "community_messages" (channel_id);
CREATE INDEX IF NOT EXISTS idx_community_messages_sender_id ON "community_messages" (sender_id);
CREATE INDEX IF NOT EXISTS idx_community_messages_created_at ON "community_messages" (created_at);
CREATE INDEX IF NOT EXISTS idx_community_participants_channel_id ON "community_participants" (channel_id);
CREATE INDEX IF NOT EXISTS idx_community_participants_user_id ON "community_participants" (user_id);
CREATE INDEX IF NOT EXISTS idx_community_participants_active ON "community_participants" (channel_id, user_id) WHERE left_at IS NULL;

-- Enable Row Level Security (RLS)
ALTER TABLE "community_channels" ENABLE ROW LEVEL SECURITY;
ALTER TABLE "community_messages" ENABLE ROW LEVEL SECURITY;
ALTER TABLE "community_participants" ENABLE ROW LEVEL SECURITY;

-- RLS Policies for community_channels
CREATE POLICY "Anyone can view public channels" 
    ON "community_channels" FOR SELECT 
    USING (is_private = FALSE);

CREATE POLICY "Authenticated users can view private channels" 
    ON "community_channels" FOR SELECT 
    USING (is_private = TRUE AND auth.uid() IS NOT NULL);

CREATE POLICY "Authenticated users can create channels" 
    ON "community_channels" FOR INSERT 
    WITH CHECK (auth.uid() IS NOT NULL);

CREATE POLICY "Channel creators can update their channels" 
    ON "community_channels" FOR UPDATE 
    USING (auth.uid() = created_by);

CREATE POLICY "Channel creators can delete their channels" 
    ON "community_channels" FOR DELETE 
    USING (auth.uid() = created_by);

-- RLS Policies for community_messages
CREATE POLICY "Anyone can view messages in public channels" 
    ON "community_messages" FOR SELECT 
    USING (
        EXISTS (
            SELECT 1 FROM "community_channels" 
            WHERE "community_channels"."channel_id" = "community_messages"."channel_id" 
            AND "community_channels"."is_private" = FALSE
        )
    );

CREATE POLICY "Authenticated users can view messages in private channels" 
    ON "community_messages" FOR SELECT 
    USING (
        EXISTS (
            SELECT 1 FROM "community_channels" 
            WHERE "community_channels"."channel_id" = "community_messages"."channel_id" 
            AND "community_channels"."is_private" = TRUE
        ) AND auth.uid() IS NOT NULL
    );

CREATE POLICY "Authenticated users can send messages" 
    ON "community_messages" FOR INSERT 
    WITH CHECK (auth.uid() IS NOT NULL);

CREATE POLICY "Users can update their own messages" 
    ON "community_messages" FOR UPDATE 
    USING (auth.uid() = sender_id);

CREATE POLICY "Users can delete their own messages" 
    ON "community_messages" FOR DELETE 
    USING (auth.uid() = sender_id);

-- RLS Policies for community_participants
CREATE POLICY "Anyone can view participants in public channels" 
    ON "community_participants" FOR SELECT 
    USING (
        EXISTS (
            SELECT 1 FROM "community_channels" 
            WHERE "community_channels"."channel_id" = "community_participants"."channel_id" 
            AND "community_channels"."is_private" = FALSE
        )
    );

CREATE POLICY "Authenticated users can view participants in private channels" 
    ON "community_participants" FOR SELECT 
    USING (
        EXISTS (
            SELECT 1 FROM "community_channels" 
            WHERE "community_channels"."channel_id" = "community_participants"."channel_id" 
            AND "community_channels"."is_private" = TRUE
        ) AND auth.uid() IS NOT NULL
    );

CREATE POLICY "Authenticated users can join channels" 
    ON "community_participants" FOR INSERT 
    WITH CHECK (auth.uid() IS NOT NULL);

CREATE POLICY "Users can update their own participation" 
    ON "community_participants" FOR UPDATE 
    USING (auth.uid() = user_id);

CREATE POLICY "Users can leave channels" 
    ON "community_participants" FOR DELETE 
    USING (auth.uid() = user_id);

-- Insert default channels
INSERT INTO "community_channels" ("name", "description", "channel_type", "is_private") VALUES
    ('general', 'General discussion for all TrackPro users', 'text', FALSE),
    ('racing', 'Racing tips, strategies, and discussions', 'text', FALSE),
    ('voice-general', 'Voice channel for general chat', 'voice', FALSE),
    ('voice-racing', 'Voice channel for racing discussions', 'voice', FALSE)
ON CONFLICT DO NOTHING;

-- Create function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create triggers to automatically update updated_at
CREATE TRIGGER update_community_channels_updated_at 
    BEFORE UPDATE ON "community_channels" 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_community_messages_updated_at 
    BEFORE UPDATE ON "community_messages" 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Add comments for documentation
COMMENT ON TABLE "community_channels" IS 'Community channels for text and voice communication';
COMMENT ON TABLE "community_messages" IS 'Messages sent in community channels';
COMMENT ON TABLE "community_participants" IS 'Users participating in voice channels';
COMMENT ON COLUMN "community_channels"."channel_type" IS 'Type of channel: text or voice';
COMMENT ON COLUMN "community_channels"."is_private" IS 'Whether the channel is private (requires authentication)';
COMMENT ON COLUMN "community_messages"."message_type" IS 'Type of message: text, system, join, or leave';
COMMENT ON COLUMN "community_participants"."is_speaking" IS 'Whether the user is currently speaking in voice channel'; 