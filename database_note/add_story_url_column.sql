-- Add story_url column to stories table
-- This column stores the direct link to the story media (image or video)

ALTER TABLE stories
ADD COLUMN IF NOT EXISTS story_url TEXT;

-- Add comment
COMMENT ON COLUMN stories.story_url IS 'Direct URL to the story media (image or video file)';
