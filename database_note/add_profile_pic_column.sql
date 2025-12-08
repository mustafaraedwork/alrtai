-- Add profile_pic_url column to clients table
-- Run this in Supabase SQL Editor

ALTER TABLE clients ADD COLUMN IF NOT EXISTS profile_pic_url TEXT;

-- Verify the column was added
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'clients' AND column_name = 'profile_pic_url';
