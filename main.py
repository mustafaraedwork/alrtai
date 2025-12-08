import os
import re
import asyncio
from datetime import datetime, timedelta
from typing import Optional
from fastapi import FastAPI, Depends, HTTPException, status, Request, Form, File, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse, StreamingResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.staticfiles import StaticFiles
from jose import JWTError, jwt
import bcrypt
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import csv
import io
import httpx

from database import supabase, init_db
from scheduler import scheduler

# ============================================
# Configuration & Security
# ============================================
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise ValueError("SECRET_KEY environment variable is required! Generate one using: python -c \"import secrets; print(secrets.token_urlsafe(32))\"")

ALGORITHM = "HS256"
# NO TOKEN EXPIRATION - Tokens never expire

# Account limits
MAX_ACCOUNTS_BRONZE = int(os.getenv("MAX_ACCOUNTS_BRONZE", 15))
MAX_ACCOUNTS_SILVER = int(os.getenv("MAX_ACCOUNTS_SILVER", 50))
MAX_ACCOUNTS_GOLD = int(os.getenv("MAX_ACCOUNTS_GOLD", 100))

# Initialize database
init_db()

# ============================================
# FastAPI App Setup
# ============================================
app = FastAPI(title="Alrt AI", version="2.0")

# Rate Limiting Setup
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# OAuth2
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# ============================================
# Helper Functions
# ============================================
def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a bcrypt hash"""
    return bcrypt.checkpw(
        plain_password.encode('utf-8'),
        hashed_password.encode('utf-8')
    )


def get_password_hash(password: str) -> str:
    """Hash a password using bcrypt"""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    # NO EXPIRATION - Token never expires
    # Remove the "exp" field completely so token works forever
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def validate_instagram_username(username: str) -> bool:
    """Validate Instagram username format"""
    if not username:
        return False
    # Instagram: 1-30 chars, letters, numbers, periods, underscores
    pattern = r'^[a-zA-Z0-9._]{1,30}$'
    return bool(re.match(pattern, username))


async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    # Query user from Supabase
    result = supabase.table('users').select('*').eq('username', username).execute()
    if not result.data:
        raise credentials_exception
    return result.data[0]


# ============================================
# Startup Event
# ============================================
@app.on_event("startup")
async def startup_event():
    """Start the scheduler when app starts"""
    await scheduler.start()
    print("Scheduler started successfully!")


# ============================================
# Authentication Endpoints
# ============================================
@app.post("/token")
@limiter.limit("10/minute")
async def login_for_access_token(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends()
):
    # Query user from Supabase
    result = supabase.table('users').select('*').eq('username', form_data.username).execute()
    user = result.data[0] if result.data else None

    if not user or not verify_password(form_data.password, user['hashed_password']):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    # Create token with NO expiration
    access_token = create_access_token(data={"sub": user['username']})
    return {"access_token": access_token, "token_type": "bearer"}


@app.post("/register")
@limiter.limit("5/hour")
async def register(
    request: Request,
    username: str = Form(...),
    password: str = Form(...)
):
    # Check if user exists
    result = supabase.table('users').select('*').eq('username', username).execute()
    if result.data:
        raise HTTPException(status_code=400, detail="Username already registered")

    # Create new user
    hashed_password = get_password_hash(password)
    new_user = {
        "username": username,
        "hashed_password": hashed_password,
        "created_at": datetime.utcnow().isoformat()
    }
    supabase.table('users').insert(new_user).execute()

    return {"status": "success", "message": "User registered successfully"}


# ============================================
# Main Pages
# ============================================
@app.get("/", response_class=HTMLResponse)
async def root_page():
    with open("login.html", "r", encoding="utf-8") as f:
        return f.read()


@app.get("/login", response_class=HTMLResponse)
async def login_page():
    with open("login.html", "r", encoding="utf-8") as f:
        return f.read()


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page():
    with open("dashboard.html", "r", encoding="utf-8") as f:
        return f.read()


@app.get("/client.html", response_class=HTMLResponse)
async def client_page():
    """Serve the client analytics page"""
    file_path = os.path.join(os.path.dirname(__file__), "client.html")
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Client page not found")


# ============================================
# Image Proxy to bypass CORS
# ============================================
@app.get("/proxy/image")
async def proxy_image(url: str):
    """Proxy Instagram images to bypass CORS restrictions"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                url,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    "Referer": "https://www.instagram.com/"
                }
            )
            response.raise_for_status()

            # Return image with proper headers
            return StreamingResponse(
                io.BytesIO(response.content),
                media_type=response.headers.get("content-type", "image/jpeg"),
                headers={
                    "Cache-Control": "public, max-age=86400",  # Cache for 24 hours
                    "Access-Control-Allow-Origin": "*"
                }
            )
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Failed to fetch image: {str(e)}")


# ============================================
# API Endpoints for Dashboard
# ============================================
@app.get("/api/me")
async def get_current_user_info(user: dict = Depends(get_current_user)):
    """Get current user information"""
    return {
        "username": user['username'],
        "id": user['id']
    }


@app.get("/data/dashboard")
async def get_dashboard_data(user: dict = Depends(get_current_user)):
    """Get dashboard data including stats and clients list"""
    # Get all clients for this user from Supabase
    result = supabase.table('clients').select('*').eq('user_id', user['id']).eq('is_tracked', True).execute()
    clients = result.data

    # Calculate stats
    total_tracked = len(clients)
    green_count = sum(1 for c in clients if c.get('status_signal') == "GREEN")
    yellow_count = sum(1 for c in clients if c.get('status_signal') == "YELLOW")
    red_count = sum(1 for c in clients if c.get('status_signal') == "RED")

    # Queue status
    queue_info = scheduler.get_queue_status()

    # Prepare clients list
    clients_list = [
        {
            "id": c['id'],
            "username": c['username'],
            "custom_label": c.get('custom_label'),
            "notes": c.get('notes'),
            "lead_status": c.get('lead_status'),
            "last_post_date": c.get('last_post_date'),
            "days_inactive": c.get('days_inactive'),
            "followers_count": c.get('followers_count'),
            "avg_posting_interval": c.get('avg_posting_interval'),
            "status_signal": c.get('status_signal'),
            "last_check_status": c.get('last_check_status'),
            "last_error_message": c.get('last_error_message'),
            "post_url": c.get('post_url'),
            "facebook_page_url": c.get('facebook_page_url'),
            "ads_status": c.get('ads_status'),
            "ads_count": c.get('ads_count'),
            "profile_pic_url": c.get('profile_pic_url'),
            "created_at": c.get('created_at')
        }
        for c in clients
    ]

    return {
        "stats": {
            "total_tracked": total_tracked,
            "green": green_count,
            "yellow": yellow_count,
            "red": red_count,
            "queue_size": queue_info.get("instagram_queue", 0),
            "ads_queue_size": queue_info.get("ads_queue", 0)
        },
        "clients_list": clients_list
    }


# ============================================
# Client Management Endpoints
# ============================================
@app.post("/add_target")
@limiter.limit("30/minute")
async def add_target(
    request: Request,
    username: str,
    user: dict = Depends(get_current_user)
):
    # Clean and validate username
    username = username.strip().lower().lstrip('@')
    if not validate_instagram_username(username):
        raise HTTPException(status_code=400, detail="Invalid Instagram username format")

    # Check account limit
    count_result = supabase.table('clients').select('id', count='exact').eq('user_id', user['id']).execute()
    user_client_count = count_result.count if hasattr(count_result, 'count') else len(count_result.data)
    if user_client_count >= MAX_ACCOUNTS_BRONZE:
        raise HTTPException(status_code=400, detail=f"Account limit reached ({MAX_ACCOUNTS_BRONZE})")

    # Check if exists FOR THIS USER
    existing_result = supabase.table('clients').select('*').eq('username', username).eq('user_id', user['id']).execute()
    if existing_result.data:
        return {"status": "error", "message": "You are already tracking this account"}

    # Create new client
    new_client = {
        "username": username,
        "user_id": user['id'],
        "is_tracked": True,
        "tracking_started_at": datetime.utcnow().isoformat(),
        "created_at": datetime.utcnow().isoformat()
    }
    insert_result = supabase.table('clients').insert(new_client).execute()
    new_client_id = insert_result.data[0]['id']

    # Add to queue using ID (not username)
    await scheduler.add_instagram_task(new_client_id)

    # Auto-trigger analytics and stories for immediate data
    await scheduler.stories_queue.put(new_client_id)
    asyncio.create_task(scheduler.process_analytics_job(new_client_id))

    return {"status": "success", "message": f"@{username} added to tracking queue"}


@app.post("/bulk_add_targets")
@limiter.limit("5/minute")
async def bulk_add_targets(
    request: Request,
    user: dict = Depends(get_current_user)
):
    """Bulk add accounts from JSON array"""
    data = await request.json()
    usernames = data.get("usernames", [])

    if not usernames:
        raise HTTPException(status_code=400, detail="No usernames provided")

    if len(usernames) > 50:
        raise HTTPException(status_code=400, detail="Maximum 50 usernames allowed")

    added = []
    errors = []

    for username in usernames:
        username = username.strip().lower().lstrip('@')

        if not validate_instagram_username(username):
            errors.append(f"{username}: Invalid format")
            continue

        # Check if already exists
        existing_result = supabase.table('clients').select('*').eq('username', username).eq('user_id', user['id']).execute()
        if existing_result.data:
            errors.append(f"{username}: Already tracked")
            continue

        # Add new client
        new_client = {
            "username": username,
            "user_id": user['id'],
            "is_tracked": True,
            "tracking_started_at": datetime.utcnow().isoformat(),
            "created_at": datetime.utcnow().isoformat()
        }
        insert_result = supabase.table('clients').insert(new_client).execute()
        new_client_id = insert_result.data[0]['id']

        await scheduler.add_instagram_task(new_client_id)

        # Auto-trigger analytics and stories
        await scheduler.stories_queue.put(new_client_id)
        asyncio.create_task(scheduler.process_analytics_job(new_client_id))

        added.append(username)

    return {
        "status": "success",
        "message": f"Added {len(added)} accounts. {len(errors)} errors.",
        "added": len(added),
        "errors": errors
    }


@app.get("/targets")
async def get_targets(user: dict = Depends(get_current_user)):
    """Get all tracked accounts for current user"""
    result = supabase.table('clients').select('*').eq('user_id', user['id']).eq('is_tracked', True).execute()
    clients = result.data

    return [
        {
            "id": c['id'],
            "username": c['username'],
            "custom_label": c.get('custom_label'),
            "notes": c.get('notes'),
            "lead_status": c.get('lead_status'),
            "last_post_date": c.get('last_post_date'),
            "days_inactive": c.get('days_inactive'),
            "followers_count": c.get('followers_count'),
            "avg_posting_interval": c.get('avg_posting_interval'),
            "status_signal": c.get('status_signal'),
            "last_check_status": c.get('last_check_status'),
            "last_error_message": c.get('last_error_message'),
            "post_url": c.get('post_url'),
            "facebook_page_url": c.get('facebook_page_url'),
            "ads_status": c.get('ads_status'),
            "ads_count": c.get('ads_count'),
            "created_at": c.get('created_at')
        }
        for c in clients
    ]


@app.delete("/remove_target/{client_id}")
@limiter.limit("30/minute")
async def remove_target(
    request: Request,
    client_id: int,
    user: dict = Depends(get_current_user)
):
    """Remove a tracked account"""
    result = supabase.table('clients').select('*').eq('id', client_id).eq('user_id', user['id']).execute()

    if not result.data:
        raise HTTPException(status_code=404, detail="Account not found")

    supabase.table('clients').delete().eq('id', client_id).execute()

    return {"status": "success", "message": "Account removed"}


@app.post("/refresh_target/{client_id}")
@limiter.limit("20/minute")
async def refresh_target(
    request: Request,
    client_id: int,
    user: dict = Depends(get_current_user)
):
    """Manually refresh a single account"""
    result = supabase.table('clients').select('*').eq('id', client_id).eq('user_id', user['id']).execute()

    if not result.data:
        raise HTTPException(status_code=404, detail="Account not found")

    await scheduler.add_instagram_task(client_id)

    return {"status": "success", "message": "Refresh queued"}


@app.post("/update_client_metadata/{client_id}")
@limiter.limit("30/minute")
async def update_client_metadata(
    request: Request,
    client_id: int,
    custom_label: Optional[str] = None,
    notes: Optional[str] = None,
    lead_status: Optional[str] = None,
    facebook_page_url: Optional[str] = None,
    user: dict = Depends(get_current_user)
):
    """Update client metadata (label, notes, CRM status, etc.)"""
    result = supabase.table('clients').select('*').eq('id', client_id).eq('user_id', user['id']).execute()

    if not result.data:
        raise HTTPException(status_code=404, detail="Account not found")

    # Build update dict
    update_data = {}
    if custom_label is not None:
        update_data['custom_label'] = custom_label
    if notes is not None:
        update_data['notes'] = notes
    if lead_status is not None:
        update_data['lead_status'] = lead_status
    if facebook_page_url is not None:
        update_data['facebook_page_url'] = facebook_page_url

    if update_data:
        supabase.table('clients').update(update_data).eq('id', client_id).execute()

    return {"status": "success", "message": "Metadata updated"}


@app.put("/link_facebook")
@limiter.limit("30/minute")
async def link_facebook(
    request: Request,
    username: str,
    fb_url: str,
    user: dict = Depends(get_current_user)
):
    """Link Facebook page to Instagram account and auto-check ads"""
    result = supabase.table('clients').select('*').eq('username', username).eq('user_id', user['id']).execute()

    if not result.data:
        raise HTTPException(status_code=404, detail="Account not found")

    client = result.data[0]

    # Update Facebook URL
    supabase.table('clients').update({'facebook_page_url': fb_url}).eq('id', client['id']).execute()

    # Automatically add to ads check queue
    await scheduler.add_ads_task(client['id'])

    return {"status": "success", "message": "Facebook page linked and ads check queued"}


@app.post("/check_facebook_ads/{client_id}")
@limiter.limit("10/minute")
async def check_facebook_ads(
    request: Request,
    client_id: int,
    user: dict = Depends(get_current_user)
):
    """Check Facebook Ads for a client"""
    result = supabase.table('clients').select('*').eq('id', client_id).eq('user_id', user['id']).execute()

    if not result.data:
        raise HTTPException(status_code=404, detail="Account not found")

    client = result.data[0]
    if not client.get('facebook_page_url'):
        raise HTTPException(status_code=400, detail="No Facebook page URL set")

    await scheduler.add_ads_task(client_id)

    return {"status": "success", "message": "Ads check queued"}


@app.get("/queue_status")
async def get_queue_status(user: dict = Depends(get_current_user)):
    """Get current queue status for monitoring"""
    return scheduler.get_queue_status()


@app.put("/update_client_crm")
@limiter.limit("50/minute")
async def update_client_crm(
    request: Request,
    user: dict = Depends(get_current_user)
):
    """Update client CRM metadata"""
    data = await request.json()
    username = data.get("username")

    result = supabase.table('clients').select('*').eq('username', username).eq('user_id', user['id']).execute()

    if not result.data:
        raise HTTPException(status_code=404, detail="Account not found")

    client = result.data[0]

    # Build update dict
    update_data = {}
    if "custom_label" in data:
        update_data['custom_label'] = data["custom_label"]
    if "notes" in data:
        update_data['notes'] = data["notes"]
    if "lead_status" in data:
        update_data['lead_status'] = data["lead_status"]
    if "facebook_page_url" in data:
        update_data['facebook_page_url'] = data["facebook_page_url"]

    if update_data:
        supabase.table('clients').update(update_data).eq('id', client['id']).execute()

    return {"status": "success", "message": "Updated successfully"}


@app.post("/logout")
async def logout():
    """Logout endpoint (client-side handles token removal)"""
    return {"status": "success", "message": "Logged out"}


# ============================================
# Analytics & Stories API Endpoints
# ============================================

@app.get("/api/client/{client_id}")
@limiter.limit("100/minute")
async def get_client_details(
    request: Request,
    client_id: int,
    user: dict = Depends(get_current_user)
):
    """Get full client details with analytics"""
    # Fetch client
    result = supabase.table('clients').select('*').eq('id', client_id).eq('user_id', user['id']).execute()

    if not result.data:
        raise HTTPException(status_code=404, detail="Client not found")

    client = result.data[0]

    # Get latest analytics snapshot
    analytics_result = supabase.table('analytics_snapshots').select('*').eq(
        'client_id', client_id
    ).order('snapshot_date', desc=True).limit(1).execute()

    latest_analytics = analytics_result.data[0] if analytics_result.data else None

    # Get total stories and posts count
    stories_count_result = supabase.table('stories').select('id', count='exact').eq('client_id', client_id).execute()
    posts_count_result = supabase.table('posts').select('id', count='exact').eq('client_id', client_id).execute()

    stories_count = stories_count_result.count if stories_count_result.count else 0
    posts_count = posts_count_result.count if posts_count_result.count else 0

    return {
        "status": "success",
        "client": client,
        "analytics": latest_analytics,
        "total_stories": stories_count,
        "total_posts": posts_count
    }


@app.get("/api/client/{client_id}/heatmap")
@limiter.limit("100/minute")
async def get_client_heatmap(
    request: Request,
    client_id: int,
    year: int = datetime.now().year,
    user: dict = Depends(get_current_user)
):
    """Get activity heatmap data for a client"""
    # Verify ownership
    result = supabase.table('clients').select('id', 'tracking_started_at').eq(
        'id', client_id
    ).eq('user_id', user['id']).execute()

    if not result.data:
        raise HTTPException(status_code=404, detail="Client not found")

    client = result.data[0]
    tracking_started = client.get('tracking_started_at')

    # Fetch activity calendar for the year
    start_date = f"{year}-01-01"
    end_date = f"{year}-12-31"

    activity_result = supabase.table('activity_calendar').select('*').eq(
        'client_id', client_id
    ).gte('activity_date', start_date).lte('activity_date', end_date).execute()

    return {
        "status": "success",
        "year": year,
        "tracking_started_at": tracking_started,
        "activity_data": activity_result.data
    }


@app.get("/api/client/{client_id}/activity/{date}")
@limiter.limit("100/minute")
async def get_client_activity_by_date(
    request: Request,
    client_id: int,
    date: str,
    user: dict = Depends(get_current_user)
):
    """Get stories and posts for a specific date"""
    # Verify ownership
    result = supabase.table('clients').select('id').eq('id', client_id).eq('user_id', user['id']).execute()

    if not result.data:
        raise HTTPException(status_code=404, detail="Client not found")

    # Parse date
    try:
        target_date = datetime.fromisoformat(date).date()
        next_day = target_date + timedelta(days=1)
    except:
        raise HTTPException(status_code=400, detail="Invalid date format")

    # Fetch stories for that date
    stories_result = supabase.table('stories').select('*').eq(
        'client_id', client_id
    ).gte('posted_at', str(target_date)).lt('posted_at', str(next_day)).execute()

    # Fetch posts for that date
    posts_result = supabase.table('posts').select('*').eq(
        'client_id', client_id
    ).gte('posted_at', str(target_date)).lt('posted_at', str(next_day)).execute()

    return {
        "status": "success",
        "date": str(target_date),
        "stories": stories_result.data,
        "posts": posts_result.data
    }


@app.get("/api/client/{client_id}/analytics")
@limiter.limit("100/minute")
async def get_client_analytics_history(
    request: Request,
    client_id: int,
    days: int = 30,
    user: dict = Depends(get_current_user)
):
    """Get analytics history for trending charts"""
    # Verify ownership
    result = supabase.table('clients').select('id').eq('id', client_id).eq('user_id', user['id']).execute()

    if not result.data:
        raise HTTPException(status_code=404, detail="Client not found")

    # Calculate date range
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=days)

    # Fetch analytics snapshots
    analytics_result = supabase.table('analytics_snapshots').select('*').eq(
        'client_id', client_id
    ).gte('snapshot_date', str(start_date)).lte('snapshot_date', str(end_date)).order(
        'snapshot_date', desc=False
    ).execute()

    return {
        "status": "success",
        "days": days,
        "analytics": analytics_result.data
    }


@app.get("/api/client/{client_id}/posts")
@limiter.limit("100/minute")
async def get_client_posts(
    request: Request,
    client_id: int,
    page: int = 1,
    limit: int = 50,
    user: dict = Depends(get_current_user)
):
    """Get paginated posts archive (grouped by date)"""
    # Verify ownership
    result = supabase.table('clients').select('id').eq('id', client_id).eq('user_id', user['id']).execute()

    if not result.data:
        raise HTTPException(status_code=404, detail="Client not found")

    # Calculate offset
    offset = (page - 1) * limit

    # Fetch posts with pagination
    posts_result = supabase.table('posts').select('*').eq(
        'client_id', client_id
    ).order('posted_at', desc=True).range(offset, offset + limit - 1).execute()

    # Get total count
    count_result = supabase.table('posts').select('id', count='exact').eq('client_id', client_id).execute()
    total_count = count_result.count if count_result.count else 0

    # Group posts by date
    posts_by_date = {}
    for post in posts_result.data:
        if post.get('posted_at'):
            post_date = post['posted_at'][:10]  # YYYY-MM-DD
            if post_date not in posts_by_date:
                posts_by_date[post_date] = []
            posts_by_date[post_date].append(post)

    return {
        "status": "success",
        "page": page,
        "limit": limit,
        "total": total_count,
        "posts_by_date": posts_by_date,
        "posts": posts_result.data
    }


@app.get("/api/client/{client_id}/stories")
@limiter.limit("100/minute")
async def get_client_stories(
    request: Request,
    client_id: int,
    page: int = 1,
    limit: int = 50,
    user: dict = Depends(get_current_user)
):
    """Get paginated stories archive (grouped by date)"""
    # Verify ownership
    result = supabase.table('clients').select('id').eq('id', client_id).eq('user_id', user['id']).execute()

    if not result.data:
        raise HTTPException(status_code=404, detail="Client not found")

    # Calculate offset
    offset = (page - 1) * limit

    # Fetch stories with pagination
    stories_result = supabase.table('stories').select('*').eq(
        'client_id', client_id
    ).order('posted_at', desc=True).range(offset, offset + limit - 1).execute()

    # Get total count
    count_result = supabase.table('stories').select('id', count='exact').eq('client_id', client_id).execute()
    total_count = count_result.count if count_result.count else 0

    # Group stories by date
    stories_by_date = {}
    for story in stories_result.data:
        if story.get('posted_at'):
            story_date = story['posted_at'][:10]  # YYYY-MM-DD
            if story_date not in stories_by_date:
                stories_by_date[story_date] = []
            stories_by_date[story_date].append(story)

    return {
        "status": "success",
        "page": page,
        "limit": limit,
        "total": total_count,
        "stories_by_date": stories_by_date,
        "stories": stories_result.data
    }


@app.get("/api/alerts")
@limiter.limit("100/minute")
async def get_user_alerts(
    request: Request,
    unread_only: bool = True,
    user: dict = Depends(get_current_user)
):
    """Get user alerts (inactivity notifications)"""
    query = supabase.table('inactivity_alerts').select(
        '*, clients(username, profile_pic_url)'
    ).eq('user_id', user['id'])

    if unread_only:
        query = query.eq('is_read', False)

    result = query.order('created_at', desc=True).limit(50).execute()

    return {
        "status": "success",
        "alerts": result.data
    }


@app.put("/api/alerts/{alert_id}/read")
@limiter.limit("100/minute")
async def mark_alert_as_read(
    request: Request,
    alert_id: int,
    user: dict = Depends(get_current_user)
):
    """Mark an alert as read"""
    # Verify ownership
    result = supabase.table('inactivity_alerts').select('id').eq(
        'id', alert_id
    ).eq('user_id', user['id']).execute()

    if not result.data:
        raise HTTPException(status_code=404, detail="Alert not found")

    # Update alert
    supabase.table('inactivity_alerts').update({'is_read': True}).eq('id', alert_id).execute()

    return {"status": "success", "message": "Alert marked as read"}


@app.put("/api/alerts/{alert_id}/dismiss")
@limiter.limit("100/minute")
async def dismiss_alert(
    request: Request,
    alert_id: int,
    user: dict = Depends(get_current_user)
):
    """Dismiss an alert"""
    # Verify ownership
    result = supabase.table('inactivity_alerts').select('id').eq(
        'id', alert_id
    ).eq('user_id', user['id']).execute()

    if not result.data:
        raise HTTPException(status_code=404, detail="Alert not found")

    # Update alert
    supabase.table('inactivity_alerts').update({
        'is_dismissed': True,
        'is_read': True
    }).eq('id', alert_id).execute()

    return {"status": "success", "message": "Alert dismissed"}


# ============================================
# Error Handlers
# ============================================
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"status": "error", "message": exc.detail}
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
