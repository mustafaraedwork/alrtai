import secrets
import csv
import bcrypt
import sqlite3
import os
from sqlalchemy.orm import Session
from sqlalchemy import text
from database import SessionLocal, engine, Base, User, Client, init_db

def get_password_hash(password):
    pwd_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pwd_bytes, salt).decode('utf-8')

def parse_date(date_str):
    if not date_str:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    return datetime.utcnow()

def migrate_and_fix():
    print("Starting Fix Migration (v5 -> v6)...")
    
    if os.path.exists("instagram_v6.db"):
        os.remove("instagram_v6.db")
    
    init_db() 
    print("Initialized new database (v6).")
    
    db = SessionLocal()
    
    # 2. Setup Admin
    admin_username = "admin"
    admin_password = secrets.token_urlsafe(8)
    admin_hash = get_password_hash(admin_password)
    
    admin_user = User(username=admin_username, hashed_password=admin_hash)
    db.add(admin_user)
    db.commit()
    print(f"Re-created Admin: {admin_username}")
    
    # 3. Copy Data from Old DB (v5)
    if os.path.exists("instagram_v5.db"):
        print("Migrating data from instagram_v5.db...")
        try:
            old_conn = sqlite3.connect("instagram_v5.db")
            old_cursor = old_conn.cursor()
            cols = "username, custom_label, notes, lead_status, facebook_page_url, ads_status, ads_count, last_check_date, last_post_date, days_inactive, followers_count, avg_posting_interval, status_signal, last_check_status, last_error_message, post_url, is_tracked, created_at"
            
            old_cursor.execute(f"SELECT {cols} FROM clients")
            rows = old_cursor.fetchall()
            
            count = 0
            for row in rows:
                new_client = Client(
                    username=row[0],
                    custom_label=row[1],
                    notes=row[2],
                    lead_status=row[3],
                    facebook_page_url=row[4],
                    ads_status=row[5],
                    ads_count=row[6],
                    last_check_date=parse_date(row[7]),
                    last_post_date=row[8],
                    days_inactive=row[9],
                    followers_count=row[10],
                    avg_posting_interval=row[11],
                    status_signal=row[12],
                    last_check_status=row[13],
                    last_error_message=row[14],
                    post_url=row[15],
                    is_tracked=bool(row[16]),
                    created_at=parse_date(row[17]),
                    user_id=admin_user.id
                )
                db.add(new_client)
                count += 1
                
            db.commit()
            old_conn.close()
            print(f"Migrated {count} clients from v5 to v6.")
        except Exception as e:
            print(f"Error reading old DB: {e}")
            print("Proceeding...")
    else:
        print("Old database (v5) not found. Starting fresh.")

    # 4. Generate 100 Guest Accounts
    accounts = []
    accounts.append(["Role", "Username", "Password"])
    accounts.append(["ADMIN", admin_username, admin_password])
    
    print("Generating 100 Guest Accounts...")
    for i in range(1, 101):
        u_name = f"user{i:03d}"
        u_pass = secrets.token_urlsafe(6)
        u_hash = get_password_hash(u_pass)
        
        new_user = User(username=u_name, hashed_password=u_hash)
        db.add(new_user)
        accounts.append(["GUEST", u_name, u_pass])
    
    db.commit()
    
    # 5. Export to CSV
    with open("accounts.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerows(accounts)
    
    print(f"Exported credentials to 'accounts.csv'.")
    print("Done!")

from datetime import datetime

if __name__ == "__main__":
    migrate_and_fix()
