import sqlite3
import pandas as pd

def check_recent_logs():
    try:
        con = sqlite3.connect('subscribers.db')
        query = "SELECT category, title, original_url, created_at FROM market_logs WHERE created_at > datetime('now', '-2 hour') ORDER BY created_at DESC"
        df = pd.read_sql_query(query, con)
        con.close()
        
        if df.empty:
            print("❌ No recent logs found.")
        else:
            print(f"✅ Found {len(df)} recent logs:")
            print(df[['category', 'title', 'original_url']])
            
            # Validation
            valid_urls = df['original_url'].str.contains('pdf|http', case=False, na=False)
            if valid_urls.all():
                print("\n✅ Verification SUCCESS: All recent logs have valid URLs (PDF/HTTP).")
            else:
                print("\n⚠️ Verification WARNING: Some logs have missing or invalid URLs.")
                print(df[~valid_urls])

    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    check_recent_logs()
