import secrets
import csv
import bcrypt
from sqlalchemy.orm import Session
from sqlalchemy import text
from database import SessionLocal, engine, Base, User, Client

def get_password_hash(password):
    # bcrypt requires bytes
    pwd_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pwd_bytes, salt).decode('utf-8')

def migrate():
    print("Starting Alrt AI Migration (Fixed)...")
    
    # 2. Update Schema
    print("1. Creating 'users' table...")
    Base.metadata.create_all(bind=engine) 
    
    db = SessionLocal()
    
    # Check if user_id column exists
    try:
        # Using text() for raw SQL
        db.execute(text("SELECT user_id FROM clients LIMIT 1"))
    except Exception:
        print("WARN: 'user_id' column missing. Adding it via SQL...")
        try:
            with engine.connect() as conn:
                conn.execute(text("ALTER TABLE clients ADD COLUMN user_id INTEGER REFERENCES users(id)"))
                # No commit needed for DDL in some engines, but good practice to close
        except Exception as e:
            print(f"Error adding column (might need full migration): {e}")

    # 3. Create Admin User
    admin_username = "admin"
    admin_password = secrets.token_urlsafe(8)
    admin_hash = get_password_hash(admin_password)
    
    admin_user = db.query(User).filter(User.username == admin_username).first()
    if not admin_user:
        admin_user = User(username=admin_username, hashed_password=admin_hash)
        db.add(admin_user)
        db.commit()
        db.refresh(admin_user)
        print(f"Created Admin User: {admin_username}")
    
    # 4. Migrate Existing Data
    # Assign all orphans to Admin
    orphans = db.query(Client).filter(Client.user_id == None).all()
    count = 0
    for client in orphans:
        client.user_id = admin_user.id
        count += 1
    db.commit()
    print(f"Migrated {count} existing clients to Admin.")
    
    # 5. Generate 100 Guest Accounts
    accounts = []
    accounts.append(["Role", "Username", "Password"])
    accounts.append(["ADMIN", admin_username, admin_password])
    
    print("Generating 100 Guest Accounts...")
    for i in range(1, 101):
        u_name = f"user{i:03d}" # user001..user100
        u_pass = secrets.token_urlsafe(6)
        u_hash = get_password_hash(u_pass)
        
        existing = db.query(User).filter(User.username == u_name).first()
        if not existing:
            new_user = User(username=u_name, hashed_password=u_hash)
            db.add(new_user)
            accounts.append(["GUEST", u_name, u_pass])
    
    db.commit()
    
    # 6. Export to CSV
    with open("accounts.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerows(accounts)
    
    print(f"Credentials exported to 'accounts.csv' ({len(accounts)-1} accounts).")
    print("Done!")

if __name__ == "__main__":
    migrate()
