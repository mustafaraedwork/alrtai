from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

from sqlalchemy import event

# Database setup
# Using a file-based SQLite with WAL mode for high concurrency.
SQLALCHEMY_DATABASE_URL = "sqlite:///./instagram_v6.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, 
    connect_args={"check_same_thread": False, "timeout": 30} # Increase timeout to wait for locks
)

# Enable Write-Ahead Logging (WAL) for concurrency
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship

# ... (Previous imports)

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)

    clients = relationship("Client", back_populates="owner")

class Client(Base):
    __tablename__ = "clients"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, index=True) # Removed unique=True to allow different users to track same handle? No, unique per user but for simplicity maybe composite unique? Let's just remove global unique.
    
    user_id = Column(Integer, ForeignKey("users.id")) # NEW: Link to User
    owner = relationship("User", back_populates="clients")

    # Custom Metadata
    custom_label = Column(String, nullable=True)                     # User-defined Tag/Label (e.g. "Restaurant")
    notes = Column(String, nullable=True)                            # NEW: CRM Notes
    lead_status = Column(String, default="NEW_LEAD")                 # NEW: CRM Status
    
    facebook_page_url = Column(String, nullable=True)                # NEW: Linked Facebook Page
    ads_status = Column(String, default="UNKNOWN")                   # NEW: ACTIVE, INACTIVE, UNKNOWN
    ads_count = Column(Integer, default=0)                           # NEW: Number of active ads

    # Tracking Data
    last_check_date = Column(DateTime, default=datetime.utcnow)      # When we checked
    last_post_date = Column(String)                                  # The extracted date (string for flexibility)
    days_inactive = Column(Integer, default=0)                       # Calculated metric
    
    # Advanced Metrics (V2)
    followers_count = Column(Integer, default=0)                     # New: Followers
    avg_posting_interval = Column(Integer, default=0)                # New: Average days between posts
    
    # Status Indicators
    status_signal = Column(String, default="RED")                    # RED, YELLOW, GREEN
    last_check_status = Column(String, default="pending")            # pending, queued, processing, success, error
    last_error_message = Column(String, nullable=True)               # To show why it failed
    
    post_url = Column(String, nullable=True)
    is_tracked = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow) # NEW: For "Date Added" sorting

def init_db():
    Base.metadata.create_all(bind=engine)