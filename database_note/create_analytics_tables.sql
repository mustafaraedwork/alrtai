-- =====================================================
-- Alrt AI - Analytics & Stories Archive Feature
-- Database Schema - Tables Creation
-- تاريخ: 8 ديسمبر 2025
-- =====================================================

-- =====================================================
-- 1. جدول posts (المنشورات)
-- =====================================================
CREATE TABLE IF NOT EXISTS posts (
    id BIGSERIAL PRIMARY KEY,
    client_id BIGINT REFERENCES clients(id) ON DELETE CASCADE,
    instagram_post_id TEXT UNIQUE NOT NULL,
    post_url TEXT,
    thumbnail_url TEXT,
    likes_count INTEGER DEFAULT 0,
    comments_count INTEGER DEFAULT 0,
    caption TEXT,
    hashtags TEXT[],
    posted_at TIMESTAMPTZ,
    fetched_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for posts table
CREATE INDEX IF NOT EXISTS idx_posts_client_id ON posts(client_id);
CREATE INDEX IF NOT EXISTS idx_posts_posted_at ON posts(posted_at);
CREATE INDEX IF NOT EXISTS idx_posts_instagram_id ON posts(instagram_post_id);

-- =====================================================
-- 2. جدول stories (الستوريات)
-- =====================================================
CREATE TABLE IF NOT EXISTS stories (
    id BIGSERIAL PRIMARY KEY,
    client_id BIGINT REFERENCES clients(id) ON DELETE CASCADE,
    instagram_story_id TEXT NOT NULL,
    thumbnail_url TEXT,
    thumbnail_storage_path TEXT,
    story_type TEXT DEFAULT 'image',
    posted_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ,
    fetched_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(client_id, instagram_story_id)
);

-- Indexes for stories table
CREATE INDEX IF NOT EXISTS idx_stories_client_id ON stories(client_id);
CREATE INDEX IF NOT EXISTS idx_stories_posted_at ON stories(posted_at);

-- =====================================================
-- 3. جدول analytics_snapshots (لقطات التحليلات)
-- =====================================================
CREATE TABLE IF NOT EXISTS analytics_snapshots (
    id BIGSERIAL PRIMARY KEY,
    client_id BIGINT REFERENCES clients(id) ON DELETE CASCADE,
    followers_count INTEGER DEFAULT 0,
    following_count INTEGER DEFAULT 0,
    posts_count INTEGER DEFAULT 0,
    avg_likes DECIMAL(10,2) DEFAULT 0,
    avg_comments DECIMAL(10,2) DEFAULT 0,
    engagement_rate DECIMAL(5,2) DEFAULT 0,
    posts_per_day DECIMAL(5,2) DEFAULT 0,
    snapshot_date DATE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(client_id, snapshot_date)
);

-- Index for analytics_snapshots table
CREATE INDEX IF NOT EXISTS idx_analytics_client_date ON analytics_snapshots(client_id, snapshot_date);

-- =====================================================
-- 4. جدول activity_calendar (تقويم النشاط للـ Heatmap)
-- =====================================================
CREATE TABLE IF NOT EXISTS activity_calendar (
    id BIGSERIAL PRIMARY KEY,
    client_id BIGINT REFERENCES clients(id) ON DELETE CASCADE,
    activity_date DATE NOT NULL,
    stories_count INTEGER DEFAULT 0,
    posts_count INTEGER DEFAULT 0,
    has_activity BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(client_id, activity_date)
);

-- Index for activity_calendar table
CREATE INDEX IF NOT EXISTS idx_activity_client_date ON activity_calendar(client_id, activity_date);

-- =====================================================
-- 5. جدول inactivity_alerts (تنبيهات عدم النشاط)
-- =====================================================
CREATE TABLE IF NOT EXISTS inactivity_alerts (
    id BIGSERIAL PRIMARY KEY,
    client_id BIGINT REFERENCES clients(id) ON DELETE CASCADE,
    user_id BIGINT REFERENCES users(id) ON DELETE CASCADE,
    alert_type TEXT DEFAULT 'STORIES_INACTIVE',
    days_inactive INTEGER,
    is_read BOOLEAN DEFAULT FALSE,
    is_dismissed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for inactivity_alerts table
CREATE INDEX IF NOT EXISTS idx_alerts_user ON inactivity_alerts(user_id, is_read);
CREATE INDEX IF NOT EXISTS idx_alerts_client ON inactivity_alerts(client_id);

-- =====================================================
-- 6. تحديث جدول clients (إضافة أعمدة جديدة)
-- =====================================================
ALTER TABLE clients ADD COLUMN IF NOT EXISTS tracking_started_at TIMESTAMPTZ DEFAULT NOW();
ALTER TABLE clients ADD COLUMN IF NOT EXISTS last_story_date TIMESTAMPTZ;
ALTER TABLE clients ADD COLUMN IF NOT EXISTS stories_inactive_days INTEGER DEFAULT 0;
ALTER TABLE clients ADD COLUMN IF NOT EXISTS total_stories_archived INTEGER DEFAULT 0;
ALTER TABLE clients ADD COLUMN IF NOT EXISTS total_posts_tracked INTEGER DEFAULT 0;

-- =====================================================
-- 7. تحديث tracking_started_at للحسابات الموجودة
-- =====================================================
-- تحديث الحسابات الموجودة لتحديد تاريخ بدء التتبع
UPDATE clients
SET tracking_started_at = created_at
WHERE tracking_started_at IS NULL;

-- =====================================================
-- التحقق من إنشاء الجداول
-- =====================================================
-- عرض جميع الجداول المنشأة
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
AND table_name IN ('posts', 'stories', 'analytics_snapshots', 'activity_calendar', 'inactivity_alerts')
ORDER BY table_name;

-- عرض عدد الأعمدة في جدول clients
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'clients'
AND column_name IN ('tracking_started_at', 'last_story_date', 'stories_inactive_days', 'total_stories_archived', 'total_posts_tracked')
ORDER BY column_name;
