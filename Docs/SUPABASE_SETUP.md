# Alrt AI - Supabase Database Setup Guide

## 🎯 Quick Setup Instructions

### Step 1: Get Your Supabase Credentials

1. Go to [Supabase Dashboard](https://app.supabase.com)
2. Select your project or create a new one
3. Go to **Settings** → **API**
4. Copy the following values:
   - **Project URL** (e.g., `https://xxxxx.supabase.co`)
   - **anon/public key** (starts with `eyJhbGci...`)

### Step 2: Update Your .env File

Open your `.env` file and replace the placeholders:

```env
# --- Supabase Configuration ---
SUPABASE_URL=https://YOUR_PROJECT_ID.supabase.co
SUPABASE_ANON_KEY=eyJhbGci...YOUR_ACTUAL_KEY_HERE

# --- Database URL (Optional - for direct PostgreSQL connection) ---
# Uncomment this line if you want to use PostgreSQL instead of SQLite
# DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@YOUR_PROJECT_ID.supabase.co:6543/postgres?sslmode=require
```

**Example:**
```env
SUPABASE_URL=https://xcvbcmaqmctnfmgvyjcl.supabase.co
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InhjdmJjbWFxbWN0bmZtZ3Z5amNsIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjUwNzk0NjMsImV4cCI6MjA4MDY1NTQ2M30.Yr9Bn9fYmvoG-vvJi4GdEdXvqDIvCXz_rGbsrdW1ZKA
```

---

## 📊 Step 3: Run This SQL in Supabase SQL Editor

1. Go to **SQL Editor** in your Supabase dashboard
2. Click **New Query**
3. Copy and paste the following SQL code
4. Click **Run** or press `Ctrl+Enter`

```sql
-- ============================================
-- Alrt AI Database Schema for Supabase
-- ============================================

-- Create Users Table
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create index on username for faster lookups
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);

-- ============================================

-- Create Clients Table
CREATE TABLE IF NOT EXISTS clients (
    id SERIAL PRIMARY KEY,
    username VARCHAR(255) NOT NULL,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    -- Custom Metadata
    custom_label VARCHAR(255),
    notes TEXT,
    lead_status VARCHAR(50) DEFAULT 'NEW_LEAD',

    -- Facebook Integration
    facebook_page_url TEXT,
    ads_status VARCHAR(50) DEFAULT 'UNKNOWN',
    ads_count INTEGER DEFAULT 0,

    -- Tracking Data
    last_check_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_post_date VARCHAR(255),
    days_inactive INTEGER DEFAULT 0,

    -- Advanced Metrics
    followers_count INTEGER DEFAULT 0,
    avg_posting_interval INTEGER DEFAULT 0,

    -- Status Indicators
    status_signal VARCHAR(20) DEFAULT 'RED',
    last_check_status VARCHAR(50) DEFAULT 'pending',
    last_error_message TEXT,

    -- Additional Fields
    post_url TEXT,
    is_tracked BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_clients_username ON clients(username);
CREATE INDEX IF NOT EXISTS idx_clients_user_id ON clients(user_id);
CREATE INDEX IF NOT EXISTS idx_clients_is_tracked ON clients(is_tracked);

-- IMPORTANT: Composite index for user-specific queries (Performance boost!)
CREATE INDEX IF NOT EXISTS ix_client_user_username ON clients(user_id, username);

-- ============================================

-- Verify Tables Were Created
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
AND table_name IN ('users', 'clients');

-- Check Indexes
SELECT indexname, tablename
FROM pg_indexes
WHERE schemaname = 'public'
AND tablename IN ('users', 'clients');
```

---

## ✅ Verification Steps

After running the SQL:

1. You should see a success message
2. Check the **Tables** section in Supabase:
   - You should see `users` table
   - You should see `clients` table

3. Verify indexes exist:
   - Run this query to see all indexes:
     ```sql
     SELECT indexname, tablename
     FROM pg_indexes
     WHERE schemaname = 'public';
     ```

---

## 🔄 To Use PostgreSQL Instead of SQLite

If you want your app to connect directly to Supabase PostgreSQL:

1. Get your database password from **Settings** → **Database**
2. In your `.env` file, **uncomment** this line:
   ```env
   DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@YOUR_PROJECT_ID.supabase.co:6543/postgres?sslmode=require
   ```
3. Replace `YOUR_PASSWORD` and `YOUR_PROJECT_ID` with actual values

**Example:**
```env
DATABASE_URL=postgresql://postgres:MySecurePass123!@xcvbcmaqmctnfmgvyjcl.supabase.co:6543/postgres?sslmode=require
```

---

## 🚀 Optional: Create a Test User

You can create a test user directly in Supabase SQL Editor:

```sql
-- Create test user (password: testpass123)
-- Password hash generated using bcrypt
INSERT INTO users (username, hashed_password)
VALUES (
    'testuser',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5KeOKZ3K3nZ7q'
);

-- Verify user was created
SELECT id, username FROM users WHERE username = 'testuser';
```

Then login with:
- Username: `testuser`
- Password: `testpass123`

---

## 📝 Notes

- **SQLite vs PostgreSQL**: By default, the app uses SQLite (local file database). This is fine for development and small deployments.
- **For Production**: Use PostgreSQL (Supabase) by setting the `DATABASE_URL` environment variable.
- **Performance**: The composite index `ix_client_user_username` significantly speeds up queries when users have many tracked accounts.
- **Security**: Never commit your `.env` file to Git! It's already in `.gitignore`.

---

## 🛠️ Troubleshooting

**Error: "relation already exists"**
- This means the tables are already created. You can safely ignore this error.

**Error: "password authentication failed"**
- Check your database password in Supabase Settings → Database
- Make sure you URL-encode special characters in the password (e.g., `$` becomes `%24`)

**Error: "SECRET_KEY environment variable is required"**
- Generate a new secret key:
  ```bash
  python -c "import secrets; print(secrets.token_urlsafe(32))"
  ```
- Add it to your `.env` file

---

## 🎉 You're Done!

Your database is now set up and ready to use. Start the app with:

```bash
uvicorn main:app --reload
```

Visit: http://localhost:8000
