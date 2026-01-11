from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

db_path = "sqlite:///./subscribers.db"
engine = create_engine(db_path)
Session = sessionmaker(bind=engine)
session = Session()

try:
    print("🚧 Migrating DB (Adding 'sectors' and 'topics' to market_logs)...")
    try:
        session.execute(text("ALTER TABLE market_logs ADD COLUMN sectors VARCHAR"))
        print("✅ Added 'sectors' column.")
    except Exception as e:
        print(f"ℹ️ 'sectors' column might already exist: {e}")

    try:
        session.execute(text("ALTER TABLE market_logs ADD COLUMN topics VARCHAR"))
        print("✅ Added 'topics' column.")
    except Exception as e:
        print(f"ℹ️ 'topics' column might already exist: {e}")

    session.commit()
    print("🎉 Migration Complete.")
except Exception as e:
    print(f"❌ Migration Error: {e}")
finally:
    session.close()
