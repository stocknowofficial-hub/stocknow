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

async def check_weekly_reports():
    """네이버 금융 - 'weekly' 키워드로 전 증권사 주간 리포트 수집"""
    SEARCH_KEYWORDS = ["weekly", "주간전략"]

    loop = asyncio.get_running_loop()
    collected = []  # { title, broker, url, date, pdf_url }

    for keyword in SEARCH_KEYWORDS:
        try:
            target_url = f"https://finance.naver.com/research/invest_list.naver?searchType=keyword&keyword={keyword}"
            print(f"🔎 [WeeklyReport] Searching keyword='{keyword}'...")

            resp = await loop.run_in_executor(None, lambda u=target_url: requests.get(u, headers=headers, timeout=10))
            soup = BeautifulSoup(resp.content.decode('euc-kr', 'replace'), 'html.parser')
            rows = soup.select("table.type_1 tr")

            for row in rows:
                tds = row.find_all('td')
                if len(tds) < 5:
                    continue

                title_link = row.find('a', href=True)
                if not title_link:
                    continue

                title_text = title_link.text.strip()
                broker_text = tds[1].text.strip() if len(tds) > 1 else ""
                date_text = tds[3].text.strip() if len(tds) > 3 else ""

                # 날짜 필터: 7일 이내 리포트만 처리 (네이버 날짜 형식: yy.mm.dd)
                if date_text:
                    try:
                        report_date = datetime.strptime("20" + date_text.strip(), "%Y.%m.%d")
                        if (datetime.now() - report_date).days > 1:
                            break  # 날짜순 정렬이므로 이후는 모두 오래된 것 → 조기 종료
                    except ValueError:
                        pass

                # 이미 수집한 제목은 중복 스킵
                if any(c['title'] == title_text for c in collected):
                    continue

                detail_url = "https://finance.naver.com/research/" + title_link['href']
                detail_resp = await loop.run_in_executor(None, lambda u=detail_url: requests.get(u, headers=headers, timeout=10))
                detail_soup = BeautifulSoup(detail_resp.content.decode('euc-kr', 'replace'), 'html.parser')

                final_pdf_url = None
                for a in detail_soup.find_all('a', href=True):
                    if a['href'].lower().endswith('.pdf'):
                        final_pdf_url = a['href']
                        break

                if not final_pdf_url:
                    continue

                collected.append({
                    "title": title_text,
                    "broker": broker_text,
                    "url": detail_url,
                    "date": date_text,
                    "pdf_url": final_pdf_url,
                })
                print(f"   📋 Found: [{broker_text}] {title_text} ({date_text})")

        except Exception as e:
            print(f"❌ [WeeklyReport] keyword='{keyword}' 오류: {e}")

    # ── 불필요 리포트 필터링 ──────────────────────────────
    # 제외: ESG 스코어링 → 종목 방향성 예측 불가
    # 제외: China Weekly → 중국 내수주 중심, 국내/미국 직접 매매 종목 아님
    EXCLUDE_KEYWORDS = ["ESG Weekly", "ESG WEEKLY", "China Weekly", "china weekly"]
    before = len(collected)
    collected = [
        c for c in collected
        if not any(kw.lower() in c['title'].lower() for kw in EXCLUDE_KEYWORDS)
    ]
    excluded = before - len(collected)
    if excluded:
        print(f"🚫 [WeeklyReport] {excluded}개 리포트 필터링됨")

    print(f"📊 [WeeklyReport] 분석 대상: {len(collected)}개 리포트")

    # 각 리포트 다운로드 + Redis 발행 (미처리된 것만)
    for item in collected:
        try:
            if is_url_processed(item['pdf_url']):
                print(f"   💨 Skip (이미 처리됨): {item['title']}")
                continue

            print(f"📥 Downloading: [{item['broker']}] {item['title']}")
            pdf_resp = await loop.run_in_executor(None, lambda u=item['pdf_url']: requests.get(u, headers=headers, timeout=15))

            broker_slug = item['broker'].replace(' ', '_').replace('증권', '').lower()
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            saved_path = os.path.join(DOWNLOAD_DIR, f"{broker_slug}_{timestamp}.pdf")

            with open(saved_path, "wb") as f:
                f.write(pdf_resp.content)

            print(f"💾 Saved: {saved_path}")

            payload = {
                "type": "REPORT_ANALYSIS",
                "source": item['broker'],
                "title": item['title'],
                "file_path": saved_path,
                "url": item['pdf_url'],
                "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            await redis_client.publish(settings.REDIS_CHANNEL_STOCK, ujson.dumps(payload))
            print(f"🚀 Sent to Redis: {item['title']}")

            # 요청 간 짧은 딜레이 (서버 부하 방지)
            await asyncio.sleep(1)

        except Exception as e:
            print(f"❌ [WeeklyReport] 다운로드 오류 [{item['title']}]: {e}")

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
    cleanup_old_reports()
    print("🚀 [Startup] Running initial check...")
    await check_blackrock()
    await check_weekly_reports()
    while True:
        try:
            now_kr = datetime.now(pytz.timezone('Asia/Seoul'))
            now_ny = datetime.now(pytz.timezone('America/New_York'))
            if now_ny.weekday() == 0 and 8 <= now_ny.hour <= 18:
                await check_blackrock()
            if now_kr.weekday() < 5 and 9 <= now_kr.hour <= 18:
                await check_weekly_reports()
            await asyncio.sleep(3600)
        except Exception as e:
            print(f"❌ [Report Watcher] Loop Error: {e}")
            await asyncio.sleep(60)
