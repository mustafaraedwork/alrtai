
import asyncio
from sqlalchemy.orm import Session
from database import SessionLocal, Client
from scraper import ApifyScraper
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler

class ScrapeScheduler:
    def __init__(self):
        self.queue = asyncio.Queue()
        self.scraper = ApifyScraper()
        self.is_running = False
        self.scheduler = AsyncIOScheduler()

    async def start(self):
        if not self.is_running:
            self.is_running = True
            
            # Start Queue Worker
            asyncio.create_task(self.process_queue())
            
            # Start Background Scheduler for 12H refresh
            self.scheduler.add_job(self.refresh_all_targets, 'interval', hours=12)
            self.scheduler.start()
            
            print("🚀 Scheduler started: Queue Worker + 12H Refresh Loop.")

    async def add_task(self, username: str):
        db: Session = SessionLocal()
        try:
           clients = db.query(Client).filter(Client.username == username).all()
           for client in clients:
               client.last_check_status = "queued"
           db.commit()
        finally:
            db.close()
        
        await self.queue.put(username)
        print(f"📥 Added @{username} to queue.")

    async def refresh_all_targets(self):
        print("⏰ Triggering 12H Global Refresh...")
        db: Session = SessionLocal()
        try:
            # We need unique usernames to avoid duplicate queue items
            # SQLite doesn't support distinct on field easily with ORM in this structure without grouping
            # Simpler: Get all, extract usernames set.
            clients = db.query(Client.username).filter(Client.is_tracked == True).distinct().all()
            for (username,) in clients:
                await self.add_task(username)
        finally:
            db.close()

    async def process_queue(self):
        while True:
            username = await self.queue.get()
            print(f"⚙️ Processing @{username}...")
            
            db: Session = SessionLocal()
            try:
                clients = db.query(Client).filter(Client.username == username).all()
                for client in clients:
                    client.last_check_status = "processing"
                db.commit()
            except:
                pass
            finally:
                db.close()

            result = await self.scraper.get_profile_data(username)

            db = SessionLocal()
            try:
                clients = db.query(Client).filter(Client.username == username).all()
                if clients:
                    if result["status"] == "success":
                        data = result["data"]
                        for client in clients:
                            client.last_post_date = data["last_post_date"]
                            client.days_inactive = data["days_inactive"]
                            client.followers_count = data["followers_count"]       # V2
                            client.avg_posting_interval = data["avg_posting_interval"] # V2
                            client.status_signal = data["status_signal"]
                            client.post_url = data["post_url"]
                            client.last_check_status = "success"
                            client.last_check_date = datetime.utcnow()
                            client.last_error_message = None
                    else:
                        for client in clients:
                            client.last_check_status = "failed"
                            client.last_error_message = result.get("message", "Unknown error")
                    
                    db.commit()
            except Exception as e:
                print(f"DB Error: {e}")
            finally:
                db.close()

            self.queue.task_done()
            print("⏳ Cooling down (5s)...")
            await asyncio.sleep(5) 

scheduler = ScrapeScheduler()
