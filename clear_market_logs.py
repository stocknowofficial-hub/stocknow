from sqlalchemy import create_engine, text
engine = create_engine('sqlite:///./subscribers.db')
with engine.connect() as conn:
    result = conn.execute(text("DELETE FROM market_logs WHERE original_url LIKE '%.pdf'"))
    conn.commit()
    print(f'Done - {result.rowcount}개 삭제됨')
