from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

db_path = "sqlite:///./subscribers.db"
engine = create_engine(db_path)
Session = sessionmaker(bind=engine)
session = Session()

try:
    print("🧹 Clearing Stock and Market logs...")
    session.execute(text("DELETE FROM stock_logs"))
    session.execute(text("DELETE FROM market_logs"))
    session.commit()
    print("✅ Logs cleared successfully.")
except Exception as e:
    print(f"❌ Error clearing logs: {e}")
finally:
    session.close()
