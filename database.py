from supabase import create_client, Client as SupabaseClient
import os
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

# ============================================
# Supabase Configuration
# ============================================
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError(
        "SUPABASE_URL and SUPABASE_ANON_KEY are required!\n"
        "Please check your .env file."
    )

# Create Supabase client
supabase: SupabaseClient = create_client(SUPABASE_URL, SUPABASE_KEY)


def init_db():
    """Initialize database tables in Supabase (if they don't exist)"""
    # Tables will be created through Supabase SQL Editor
    # This function is kept for compatibility
    pass
