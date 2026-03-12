import sqlite3
import os

# DB Path (Docker Volume or Local)
# In Docker, it's likely /app/subscribers.db or similar.
# But we can run this script inside the container.
DB_PATH = "subscribers.db"

def migrate_db():
    if not os.path.exists(DB_PATH):
        print(f"⚠️ DB file not found at {DB_PATH}. Skipping migration.")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # 1. Check if 'referrer_id' column exists
        cursor.execute("PRAGMA table_info(subscribers)")
        columns = [info[1] for info in cursor.fetchall()]
        
        if "referrer_id" not in columns:
            print("🚀 Adding 'referrer_id' column to 'subscribers' table...")
            cursor.execute("ALTER TABLE subscribers ADD COLUMN referrer_id TEXT")
            conn.commit()
            print("✅ Migration Successful: 'referrer_id' column added.")
        else:
            print("✅ 'referrer_id' column already exists.")
            
    except Exception as e:
        print(f"❌ Migration Failed: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    migrate_db()
