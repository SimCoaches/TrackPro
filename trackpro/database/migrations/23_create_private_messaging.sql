-- Migration: Create Private Messaging System
-- This adds tables for private messaging between users

-- Create private_conversations table
CREATE TABLE IF NOT EXISTS "private_conversations" (
    "conversation_id" UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    "user1_id" UUID NOT NULL REFERENCES "user_profiles"("user_id") ON DELETE CASCADE,
    "user2_id" UUID NOT NULL REFERENCES "user_profiles"("user_id") ON DELETE CASCADE,
    "created_at" TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    "updated_at" TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(user1_id, user2_id)
);

-- Create private_messages table
CREATE TABLE IF NOT EXISTS "private_messages" (
    "message_id" UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    "conversation_id" UUID NOT NULL REFERENCES "private_conversations"("conversation_id") ON DELETE CASCADE,
    "sender_id" UUID NOT NULL REFERENCES "user_profiles"("user_id") ON DELETE CASCADE,
    "content" TEXT NOT NULL,
    "is_read" BOOLEAN DEFAULT FALSE,
    "created_at" TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    "updated_at" TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_private_conversations_user1_id ON "private_conversations" (user1_id);
CREATE INDEX IF NOT EXISTS idx_private_conversations_user2_id ON "private_conversations" (user2_id);
CREATE INDEX IF NOT EXISTS idx_private_conversations_updated_at ON "private_conversations" (updated_at);
CREATE INDEX IF NOT EXISTS idx_private_messages_conversation_id ON "private_messages" (conversation_id);
CREATE INDEX IF NOT EXISTS idx_private_messages_sender_id ON "private_messages" (sender_id);
CREATE INDEX IF NOT EXISTS idx_private_messages_created_at ON "private_messages" (created_at);
CREATE INDEX IF NOT EXISTS idx_private_messages_is_read ON "private_messages" (is_read);

-- Enable Row Level Security (RLS)
ALTER TABLE "private_conversations" ENABLE ROW LEVEL SECURITY;
ALTER TABLE "private_messages" ENABLE ROW LEVEL SECURITY;

-- RLS Policies for private_conversations
CREATE POLICY "Users can view their own conversations" 
    ON "private_conversations" FOR SELECT 
    USING (auth.uid() = user1_id OR auth.uid() = user2_id);

CREATE POLICY "Authenticated users can create conversations" 
    ON "private_conversations" FOR INSERT 
    WITH CHECK (auth.uid() IS NOT NULL AND (auth.uid() = user1_id OR auth.uid() = user2_id));

CREATE POLICY "Users can update their own conversations" 
    ON "private_conversations" FOR UPDATE 
    USING (auth.uid() = user1_id OR auth.uid() = user2_id);

CREATE POLICY "Users can delete their own conversations" 
    ON "private_conversations" FOR DELETE 
    USING (auth.uid() = user1_id OR auth.uid() = user2_id);

-- RLS Policies for private_messages
CREATE POLICY "Users can view messages in their conversations" 
    ON "private_messages" FOR SELECT 
    USING (
        EXISTS (
            SELECT 1 FROM "private_conversations" 
            WHERE "private_conversations"."conversation_id" = "private_messages"."conversation_id" 
            AND (auth.uid() = "private_conversations"."user1_id" OR auth.uid() = "private_conversations"."user2_id")
        )
    );

CREATE POLICY "Authenticated users can send messages" 
    ON "private_messages" FOR INSERT 
    WITH CHECK (auth.uid() IS NOT NULL);

CREATE POLICY "Users can update their own messages" 
    ON "private_messages" FOR UPDATE 
    USING (auth.uid() = sender_id);

CREATE POLICY "Users can delete their own messages" 
    ON "private_messages" FOR DELETE 
    USING (auth.uid() = sender_id);

-- Allow TEAM/moderator users to delete any private message for moderation
CREATE POLICY "TEAM moderators can delete any private message" 
    ON "private_messages" FOR DELETE 
    USING (
        EXISTS (
            SELECT 1 FROM user_hierarchy uh
            WHERE uh.user_id = auth.uid()
              AND (
                   uh.hierarchy_level = 'TEAM'
                OR uh.is_moderator = TRUE
                OR uh.is_dev = TRUE
              )
        )
    );

-- Create function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create triggers to automatically update updated_at
CREATE TRIGGER update_private_conversations_updated_at 
    BEFORE UPDATE ON "private_conversations" 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_private_messages_updated_at 
    BEFORE UPDATE ON "private_messages" 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Add comments for documentation
COMMENT ON TABLE "private_conversations" IS 'Private conversations between two users';
COMMENT ON TABLE "private_messages" IS 'Messages sent in private conversations';
COMMENT ON COLUMN "private_conversations"."user1_id" IS 'First user in the conversation';
COMMENT ON COLUMN "private_conversations"."user2_id" IS 'Second user in the conversation';
COMMENT ON COLUMN "private_messages"."is_read" IS 'Whether the message has been read by the recipient'; 