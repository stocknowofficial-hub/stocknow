from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

db_path = "sqlite:///./subscribers.db"
engine = create_engine(db_path)
Session = sessionmaker(bind=engine)
session = Session()

print("\n🔍 [DB Verification]")
try:
    # 1. Check Market Logs
    count_market = session.execute(text("SELECT COUNT(*) FROM market_logs")).scalar()
    print(f"\n🌍 Market Logs: {count_market} rows")
    if count_market > 0:
        rows = session.execute(text("SELECT title, sentiment, sectors, topics, created_at FROM market_logs ORDER BY created_at DESC LIMIT 3")).fetchall()
        for r in rows:
            print(f"   - {r[0]} | {r[1]}")
            print(f"     └─ [Sectors]: {r[2]}")
            print(f"     └─ [Topics]: {r[3]}")

    # 2. Check Stock Logs
    count_stock = session.execute(text("SELECT COUNT(*) FROM stock_logs")).scalar()
    print(f"\n📊 Stock Logs: {count_stock} rows")
    if count_stock > 0:
        rows = session.execute(text("SELECT name, rate, summary, created_at FROM stock_logs ORDER BY created_at DESC LIMIT 1")).fetchall()
        for r in rows:
            print(f"   - {r[0]} {r[1]}% ({r[3]})")
            print(f"     📝 Summary:\n{r[2]}")

except Exception as e:
    print(f"❌ Error: {e}")
finally:
    session.close()
