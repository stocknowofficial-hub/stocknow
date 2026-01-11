import asyncio
import requests
import io
import ujson
import os
import time
from datetime import datetime
import pytz
from bs4 import BeautifulSoup
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from common.redis_client import redis_client
from common.config import settings

# DB Access
DB_URL = "sqlite:///./subscribers.db"
engine = create_engine(DB_URL)
Session = sessionmaker(bind=engine)

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

DOWNLOAD_DIR = os.path.abspath("data/reports")
if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR)

def is_url_processed(url):
    """Check if URL processed (Duplicate Guard)"""
    session = Session()
    try:
        exists = session.execute(
            text("SELECT 1 FROM market_logs WHERE original_url = :url"), 
            {"url": url}
        ).fetchone()
        return exists is not None
    except Exception as e:
        print(f"⚠️ [DB Check Fail] {e}")
        return False
    finally:
        session.close()

async def check_blackrock():
    """BlackRock (Requests + PDF Save)"""
    try:
        target_url = "https://www.blackrock.com/us/individual/insights/blackrock-investment-institute/weekly-commentary"
        print(f"🔎 [BlackRock] Checking...")
        
        loop = asyncio.get_running_loop()
        resp = await loop.run_in_executor(None, lambda: requests.get(target_url, headers=headers, timeout=10))
        
        if resp.status_code != 200: return

        soup = BeautifulSoup(resp.text, 'html.parser')
        pdf_link = None
        for a in soup.find_all('a', href=True):
            if "Download full commentary" in a.text or ("weekly-commentary" in a['href'] and a['href'].endswith('.pdf')):
                link = a['href']
                if not link.startswith('http'): link = "https://www.blackrock.com" + link
                pdf_link = link
                break
        
        if not pdf_link: return
        
        # ✅ Persistence Check
        if is_url_processed(pdf_link):
            print(f"   💨 [BlackRock] Skip (Already Processed): {pdf_link}")
            return

        print(f"📥 [BlackRock] Downloading: {pdf_link}")
        pdf_resp = await loop.run_in_executor(None, lambda: requests.get(pdf_link, headers=headers, timeout=15))
        
        # Save File
        timestamp = datetime.now().strftime("%Y%m%d")
        saved_path = os.path.join(DOWNLOAD_DIR, f"blackrock_{timestamp}.pdf")
        
        with open(saved_path, "wb") as f:
            f.write(pdf_resp.content)
            
        print(f"💾 [BlackRock] Saved: {saved_path}")

        # Publish
        payload = {
            "type": "REPORT_ANALYSIS",
            "source": "BlackRock",
            "title": "BlackRock Weekly Commentary", 
            "file_path": saved_path, 
            "url": pdf_link,
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        await redis_client.publish(settings.REDIS_CHANNEL_STOCK, ujson.dumps(payload))
        print(f"🚀 [BlackRock] Sent to Redis!")

    except Exception as e:
        print(f"❌ [BlackRock] Error: {e}")

async def check_kiwoom():
    """Kiwoom (Via Naver Finance) - No Selenium"""
    try:
        # Broker 39 = Kiwoom, Keyword = "Kiwoom Weekly"
        target_url = "https://finance.naver.com/research/invest_list.naver?searchType=keyword&keyword=kiwoom+Weekly&brokerCode=39"
        print(f"🔎 [Kiwoom] Checking via Naver Finance (Filtered: 'Kiwoom Weekly')...")
        
        loop = asyncio.get_running_loop()
        resp = await loop.run_in_executor(None, lambda: requests.get(target_url, headers=headers, timeout=10))
        
        soup = BeautifulSoup(resp.content.decode('euc-kr', 'replace'), 'html.parser')
        
        # Find Request List Table
        # Structure: div.box_type_m table.type_1 tr
        rows = soup.select("table.type_1 tr")
        
        target_row = None
        for row in rows:
            tds = row.find_all('td')
            if len(tds) < 3: continue 
            
            title_link = row.find('a', href=True)
            if not title_link: continue
            
            title_text = title_link.text.strip()
            # Date is in 3rd last column? Or verify specific column for date
            # Naver Invest List: Title | Writer | File | Date | Views
            date_text = tds[4].text.strip() if len(tds) > 4 else datetime.now().strftime("%y.%m.%d")

            print(f"   🔎 Checking Candidate: {title_text} ({date_text})")
            
            # Fetch Detail Page to check for PDF
            detail_url = "https://finance.naver.com/research/" + title_link['href']
            detail_resp = await loop.run_in_executor(None, lambda: requests.get(detail_url, headers=headers))
            detail_soup = BeautifulSoup(detail_resp.content.decode('euc-kr', 'replace'), 'html.parser')
            
            # Find PDF Link
            final_pdf_url = None
            for a in detail_soup.find_all('a', href=True):
                if a['href'].lower().endswith('.pdf'):
                    final_pdf_url = a['href']
                    break
            
            if not final_pdf_url:
                print(f"   ⚠️ No PDF for '{title_text}'. Finding next...")
                continue # Try next row
            
            # ✅ Success: Found a valid report with PDF
            target_row = {
                "title": title_text,
                "url": detail_url,
                "date": date_text,
                "pdf_url": final_pdf_url
            }
            break # Stop searching
            
        if not target_row:
            print("⚠️ [Kiwoom] No valid PDF reports found (Checked top list).")
            return

        print(f"   🔗 PDF URL Found: {target_row['pdf_url']}")
        
        if is_url_processed(target_row['pdf_url']):
            print(f"   💨 [Kiwoom] Skip (Already Processed): {target_row['title']}")
            return

        print(f"📥 [Kiwoom] Downloading: {target_row['title']}")
        
        # Download PDF
        pdf_resp = await loop.run_in_executor(None, lambda: requests.get(target_row['pdf_url'], headers=headers))
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        saved_path = os.path.join(DOWNLOAD_DIR, f"kiwoom_{timestamp}.pdf")
        
        with open(saved_path, "wb") as f:
            f.write(pdf_resp.content)
            
        print(f"💾 [Kiwoom] Saved: {saved_path}")
        
        # Publish
        payload = {
            "type": "REPORT_ANALYSIS",
            "source": "Kiwoom",
            "title": target_row['title'], 
            "file_path": saved_path, 
            # ✅ Valid URL for Telegram Link
            "url": target_row['pdf_url'], 
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        await redis_client.publish(settings.REDIS_CHANNEL_STOCK, ujson.dumps(payload))
        print(f"🚀 [Kiwoom] Sent to Redis!")

    except Exception as e:
        print(f"❌ [Kiwoom] Error: {e}")

    except Exception as e:
        print(f"❌ [Kiwoom] Error: {e}")

def cleanup_old_reports(days=30):
    """Delete report files older than 'days'."""
    try:
        now = time.time()
        cutoff = now - (days * 86400)
        
        for f in os.listdir(DOWNLOAD_DIR):
            f_path = os.path.join(DOWNLOAD_DIR, f)
            if os.path.isfile(f_path):
                mtime = os.path.getmtime(f_path)
                if mtime < cutoff:
                    os.remove(f_path)
                    print(f"🧹 [Cleanup] Deleted old report: {f}")
    except Exception as e:
        print(f"⚠️ [Cleanup] Error: {e}")

async def run_report_watcher():
    print("📑 [Report Watcher] Global Insight collecting started...")
    
    # Check cleanup at startup
    cleanup_old_reports()
    
    # 🚀 Run immediately on startup (Check for missed reports)
    print("🚀 [Startup] Running initial check...")
    await check_blackrock()
    await check_kiwoom()
    
    while True:
        try:
            # 1. Korea Time (KST) for Kiwoom
            now_kr = datetime.now(pytz.timezone('Asia/Seoul'))
            run_kiwoom = False
            # Mon 08-18 (Hourly) OR Daily around 9 AM
            if (now_kr.weekday() == 0 and 8 <= now_kr.hour <= 18) or (now_kr.hour == 9):
                run_kiwoom = True

            # 2. New York Time (NYT) for BlackRock
            now_ny = datetime.now(pytz.timezone('America/New_York'))
            run_blackrock = False
            # Mon 08-18 NY Time (Hourly) OR Daily around 9 AM NY Time
            if (now_ny.weekday() == 0 and 8 <= now_ny.hour <= 18) or (now_ny.hour == 9):
                run_blackrock = True
            
            # Execute if flags are set
            if run_blackrock:
                await check_blackrock()
                
            if run_kiwoom:
                await check_kiwoom()
            
            await asyncio.sleep(3600) 

        except Exception as e:
            print(f"❌ [Report Watcher] Loop Error: {e}")
            await asyncio.sleep(60)
