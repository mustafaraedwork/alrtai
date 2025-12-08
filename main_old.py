import os
import re
from datetime import datetime, timedelta
from typing import Optional
from fastapi import FastAPI, Depends, HTTPException, status, Request, Form, File, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.staticfiles import StaticFiles
from jose import JWTError, jwt
import bcrypt
from sqlalchemy.orm import Session
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import csv
import io

from database import SessionLocal, engine, Client, User, Base, init_db
from scheduler import scheduler

# ============================================
# Configuration & Security
# ============================================
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise ValueError("SECRET_KEY environment variable is required! Generate one using: python -c \"import secrets; print(secrets.token_urlsafe(32))\"")

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

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
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


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
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def validate_instagram_username(username: str) -> bool:
    """Validate Instagram username format"""
    if not username:
        return False
    # Instagram: 1-30 chars, letters, numbers, periods, underscores
    pattern = r'^[a-zA-Z0-9._]{1,30}$'
    return bool(re.match(pattern, username))


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
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

    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise credentials_exception
    return user


# ============================================
# Startup Event
# ============================================
@app.on_event("startup")
async def startup_event():
    """Start the scheduler when app starts"""
    await scheduler.start()
    print("✅ Scheduler started successfully!")


# ============================================
# Authentication Endpoints
# ============================================
@app.post("/token")
@limiter.limit("10/minute")
async def login_for_access_token(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


@app.post("/register")
@limiter.limit("5/hour")
async def register(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    # Check if user exists
    existing_user = db.query(User).filter(User.username == username).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already registered")

    # Create new user
    hashed_password = get_password_hash(password)
    new_user = User(username=username, hashed_password=hashed_password)
    db.add(new_user)
    db.commit()

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


# ============================================
# API Endpoints for Dashboard
# ============================================
@app.get("/api/me")
async def get_current_user_info(user: User = Depends(get_current_user)):
    """Get current user information"""
    return {
        "username": user.username,
        "id": user.id
    }


@app.get("/data/dashboard")
async def get_dashboard_data(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get dashboard data including stats and clients list"""
    # Get all clients for this user
    clients = db.query(Client).filter(
        Client.user_id == user.id,
        Client.is_tracked == True
    ).all()

    # Calculate stats
    total_tracked = len(clients)
    green_count = sum(1 for c in clients if c.status_signal == "GREEN")
    yellow_count = sum(1 for c in clients if c.status_signal == "YELLOW")
    red_count = sum(1 for c in clients if c.status_signal == "RED")

    # Queue status
    queue_info = scheduler.get_queue_status()

    # Prepare clients list
    clients_list = [
        {
            "id": c.id,
            "username": c.username,
            "custom_label": c.custom_label,
            "notes": c.notes,
            "lead_status": c.lead_status,
            "last_post_date": c.last_post_date,
            "days_inactive": c.days_inactive,
            "followers_count": c.followers_count,
            "avg_posting_interval": c.avg_posting_interval,
            "status_signal": c.status_signal,
            "last_check_status": c.last_check_status,
            "last_error_message": c.last_error_message,
            "post_url": c.post_url,
            "facebook_page_url": c.facebook_page_url,
            "ads_status": c.ads_status,
            "ads_count": c.ads_count,
            "created_at": c.created_at.isoformat() if c.created_at else None
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
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Clean and validate username
    username = username.strip().lower().lstrip('@')
    if not validate_instagram_username(username):
        raise HTTPException(status_code=400, detail="Invalid Instagram username format")

    # Check account limit
    user_client_count = db.query(Client).filter(Client.user_id == user.id).count()
    if user_client_count >= MAX_ACCOUNTS_BRONZE:
        raise HTTPException(status_code=400, detail=f"Account limit reached ({MAX_ACCOUNTS_BRONZE})")

    # Check if exists FOR THIS USER
    existing = db.query(Client).filter(
        Client.username == username,
        Client.user_id == user.id
    ).first()
    if existing:
        return {"status": "error", "message": "You are already tracking this account"}

    # Create new client
    new_client = Client(username=username, user_id=user.id)
    db.add(new_client)
    db.commit()
    db.refresh(new_client)

    # Add to queue using ID (not username)
    await scheduler.add_instagram_task(new_client.id)

    return {"status": "success", "message": f"@{username} added to tracking queue"}


@app.post("/bulk_add_targets")
@limiter.limit("5/minute")
async def bulk_add_targets(
    request: Request,
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Bulk add accounts from CSV file"""
    contents = await file.read()
    decoded = contents.decode("utf-8")
    csv_reader = csv.DictReader(io.StringIO(decoded))

    added = []
    errors = []

    for row in csv_reader:
        username = row.get("username", "").strip().lower().lstrip('@')

        if not validate_instagram_username(username):
            errors.append(f"{username}: Invalid format")
            continue

        # Check if already exists
        existing = db.query(Client).filter(
            Client.username == username,
            Client.user_id == user.id
        ).first()
        if existing:
            errors.append(f"{username}: Already tracked")
            continue

        # Add new client
        new_client = Client(username=username, user_id=user.id)
        db.add(new_client)
        db.commit()
        db.refresh(new_client)

        await scheduler.add_instagram_task(new_client.id)
        added.append(username)

    return {
        "status": "success",
        "added": len(added),
        "errors": errors
    }


@app.get("/targets")
async def get_targets(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all tracked accounts for current user"""
    clients = db.query(Client).filter(
        Client.user_id == user.id,
        Client.is_tracked == True
    ).all()

    return [
        {
            "id": c.id,
            "username": c.username,
            "custom_label": c.custom_label,
            "notes": c.notes,
            "lead_status": c.lead_status,
            "last_post_date": c.last_post_date,
            "days_inactive": c.days_inactive,
            "followers_count": c.followers_count,
            "avg_posting_interval": c.avg_posting_interval,
            "status_signal": c.status_signal,
            "last_check_status": c.last_check_status,
            "last_error_message": c.last_error_message,
            "post_url": c.post_url,
            "facebook_page_url": c.facebook_page_url,
            "ads_status": c.ads_status,
            "ads_count": c.ads_count,
            "created_at": c.created_at.isoformat() if c.created_at else None
        }
        for c in clients
    ]


@app.delete("/remove_target/{client_id}")
@limiter.limit("30/minute")
async def remove_target(
    request: Request,
    client_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Remove a tracked account"""
    client = db.query(Client).filter(
        Client.id == client_id,
        Client.user_id == user.id
    ).first()

    if not client:
        raise HTTPException(status_code=404, detail="Account not found")

    db.delete(client)
    db.commit()

    return {"status": "success", "message": "Account removed"}


@app.post("/refresh_target/{client_id}")
@limiter.limit("20/minute")
async def refresh_target(
    request: Request,
    client_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Manually refresh a single account"""
    client = db.query(Client).filter(
        Client.id == client_id,
        Client.user_id == user.id
    ).first()

    if not client:
        raise HTTPException(status_code=404, detail="Account not found")

    await scheduler.add_instagram_task(client.id)

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
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update client metadata (label, notes, CRM status, etc.)"""
    client = db.query(Client).filter(
        Client.id == client_id,
        Client.user_id == user.id
    ).first()

    if not client:
        raise HTTPException(status_code=404, detail="Account not found")

    if custom_label is not None:
        client.custom_label = custom_label
    if notes is not None:
        client.notes = notes
    if lead_status is not None:
        client.lead_status = lead_status
    if facebook_page_url is not None:
        client.facebook_page_url = facebook_page_url

    db.commit()

    return {"status": "success", "message": "Metadata updated"}


@app.post("/check_facebook_ads/{client_id}")
@limiter.limit("10/minute")
async def check_facebook_ads(
    request: Request,
    client_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Check Facebook Ads for a client"""
    client = db.query(Client).filter(
        Client.id == client_id,
        Client.user_id == user.id
    ).first()

    if not client:
        raise HTTPException(status_code=404, detail="Account not found")

    if not client.facebook_page_url:
        raise HTTPException(status_code=400, detail="No Facebook page URL set")

    await scheduler.add_ads_task(client.id)

    return {"status": "success", "message": "Ads check queued"}


@app.get("/queue_status")
async def get_queue_status(user: User = Depends(get_current_user)):
    """Get current queue status for monitoring"""
    return scheduler.get_queue_status()


@app.put("/update_client_crm")
@limiter.limit("50/minute")
async def update_client_crm(
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update client CRM metadata"""
    data = await request.json()
    username = data.get("username")

    client = db.query(Client).filter(
        Client.username == username,
        Client.user_id == user.id
    ).first()

    if not client:
        raise HTTPException(status_code=404, detail="Account not found")

    if "custom_label" in data:
        client.custom_label = data["custom_label"]
    if "notes" in data:
        client.notes = data["notes"]
    if "lead_status" in data:
        client.lead_status = data["lead_status"]
    if "facebook_page_url" in data:
        client.facebook_page_url = data["facebook_page_url"]

    db.commit()

    return {"status": "success", "message": "Updated successfully"}


@app.post("/logout")
async def logout():
    """Logout endpoint (client-side handles token removal)"""
    return {"status": "success", "message": "Logged out"}


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
