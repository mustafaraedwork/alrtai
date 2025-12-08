-- إنشاء جداول Supabase
-- شغل هذا الملف في Supabase SQL Editor

-- جدول المستخدمين
CREATE TABLE IF NOT EXISTS users (
    id BIGSERIAL PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    hashed_password TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- جدول العملاء (الحسابات المتتبعة)
CREATE TABLE IF NOT EXISTS clients (
    id BIGSERIAL PRIMARY KEY,
    username TEXT NOT NULL,
    user_id BIGINT REFERENCES users(id) ON DELETE CASCADE,

    -- Custom Metadata
    custom_label TEXT,
    notes TEXT,
    lead_status TEXT DEFAULT 'NEW_LEAD',

    -- Facebook Integration
    facebook_page_url TEXT,
    ads_status TEXT DEFAULT 'UNKNOWN',
    ads_count INTEGER DEFAULT 0,

    -- Tracking Data
    last_check_date TIMESTAMPTZ DEFAULT NOW(),
    last_post_date TEXT,
    days_inactive INTEGER DEFAULT 0,

    -- Advanced Metrics
    followers_count INTEGER DEFAULT 0,
    avg_posting_interval INTEGER DEFAULT 0,

    -- Status Indicators
    status_signal TEXT DEFAULT 'RED',
    last_check_status TEXT DEFAULT 'pending',
    last_error_message TEXT,

    post_url TEXT,
    is_tracked BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),

    -- Index for performance
    UNIQUE(user_id, username)
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_clients_user_id ON clients(user_id);
CREATE INDEX IF NOT EXISTS idx_clients_username ON clients(username);
CREATE INDEX IF NOT EXISTS idx_clients_user_username ON clients(user_id, username);

-- عرض عدد المستخدمين
SELECT COUNT(*) as total_users FROM users;
