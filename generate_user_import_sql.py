"""
Generate SQL file with properly hashed passwords from accounts.csv
This creates a ready-to-use SQL file for Supabase import.
"""

import csv
import bcrypt


def hash_password(password: str) -> str:
    """Hash a password using bcrypt"""
    # Encode password and hash it
    password_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode('utf-8')


def generate_sql_from_csv(csv_file: str = "accounts.csv", output_file: str = "import_users_READY.sql"):
    """
    Generate SQL file with properly hashed passwords.
    This SQL can be directly run in Supabase.
    """

    print("Hashing passwords and generating SQL...")
    print("   This may take a minute...\n")

    # Read CSV and hash all passwords
    users = []
    with open(csv_file, 'r', encoding='utf-8') as f:
        csv_reader = csv.DictReader(f)
        for idx, row in enumerate(csv_reader, 1):
            username = row['Username'].strip()
            password = row['Password'].strip()
            role = row['Role'].strip()

            print(f"   [{idx}/101] Hashing {username}...")

            hashed = hash_password(password)
            users.append({
                'username': username,
                'password': password,
                'hashed': hashed,
                'role': role
            })

    print(f"\nAll {len(users)} passwords hashed successfully!")

    # Generate SQL file
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("""-- ============================================
-- Alrt AI - User Import SQL
-- Auto-generated with REAL bcrypt hashes
-- Run this in Supabase SQL Editor
-- ============================================

-- This file was automatically generated from accounts.csv
-- All passwords are properly hashed with bcrypt
-- You can login immediately after running this SQL

""")

        # Write users in batches of 30
        batch_size = 30
        for i in range(0, len(users), batch_size):
            batch = users[i:i + batch_size]

            if i == 0:
                f.write(f"-- Admin and first batch (users 1-{min(batch_size, len(users))})\n")
            else:
                f.write(f"\n-- Batch {i//batch_size + 1}: Users {i+1}-{min(i+batch_size, len(users))}\n")

            f.write("INSERT INTO users (username, hashed_password) VALUES\n")

            for j, user in enumerate(batch):
                comma = "," if j < len(batch) - 1 else ";"
                # Add comment with actual password for reference
                f.write(f"('{user['username']}', '{user['hashed']}'){comma}  -- Password: {user['password']}\n")

            f.write("\n")

        # Add verification queries
        f.write("""-- ============================================
-- Verification Queries
-- ============================================

-- Count total users
SELECT COUNT(*) as total_users FROM users;

-- List all users
SELECT id, username FROM users ORDER BY username;

-- ============================================
-- Login Credentials Reference
-- ============================================

""")

        # Write login reference
        f.write("/*\n")
        f.write("LOGIN CREDENTIALS:\n")
        f.write("="*60 + "\n\n")

        for user in users:
            f.write(f"Username: {user['username']:<15} | Password: {user['password']}\n")

        f.write("\n" + "="*60 + "\n")
        f.write("*/\n")

    print(f"\nSQL file generated: {output_file}")
    print(f"   Total users: {len(users)}")
    print(f"\nNext steps:")
    print(f"   1. Open Supabase SQL Editor")
    print(f"   2. Copy and paste the entire {output_file} file")
    print(f"   3. Click 'Run' or press Ctrl+Enter")
    print(f"   4. All {len(users)} users will be imported!")
    print(f"\nLogin credentials are included as comments in the SQL file")


if __name__ == "__main__":
    print("Generating Supabase import SQL from accounts.csv\n")
    generate_sql_from_csv()
    print("\nDone!")
