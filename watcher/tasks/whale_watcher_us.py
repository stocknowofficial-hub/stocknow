import asyncio
import ujson
import time
import pytz
from datetime import datetime, timedelta
from common.config import settings
from common.redis_client import redis_client
from watcher.kis_auth import get_access_token
from watcher.utils.definitions import (
    check_us_market_open, 
    fetch_overseas_volume_rank, 
    fetch_overseas_volume_rank, 
    fetch_overseas_time_sales,
    update_telegraph_board,
    setup_telegraph_account
)
import os

# 🐳 고래 포착 설정
MIN_BIG_TICK_AMOUNT = 1000000  # $1,000,000 (약 14억)
BIG_TICK_COUNT_THRESHOLD = 3   # 1분 내 3건 이상 포착 시 알림
SCAN_INTERVAL = 20            # 20초마다 스캔

# 📊 Dashboard State
TELEGRAPH_CONFIG_PATH = "telegraph_config_us.json"
telegraph_config = {"access_token": "", "path": "", "url": "", "path_saved": False}
last_dashboard_update = 0
last_dashboard_link_sent = 0
sent_slots = set()
whale_score_map = {} # Code -> {"count": int, "total": float, "name": str}

# Load Config
if os.path.exists(TELEGRAPH_CONFIG_PATH):
    try:
        with open(TELEGRAPH_CONFIG_PATH, "r") as f:
            saved = ujson.load(f)
            telegraph_config.update(saved)
            telegraph_config["path_saved"] = True
    except: pass
else:
    setup_telegraph_account(telegraph_config)


# 중복 알림 방지 (최근 1시간 내 동일 종목 알림 금지)
alert_history = {} 

async def run_whale_watcher_us(approval_key, access_token=None):
    """
    🐳 [Whale Hunter] 미국 주식 수급 포착 (거래량 급증 & Big Tick)
    """
    global alert_history, whale_score_map, last_dashboard_update, last_dashboard_link_sent, sent_slots, processed_ticks
    
    # Init accumulation set
    processed_ticks = set()
    
    current_token = access_token
    print(f"🐳 [Whale Hunter] 가동 시작 (Threshold: ${MIN_BIG_TICK_AMOUNT:,})")

    while True:
        try:
            # 1. 미국장 개장 체크
            ny_tz = pytz.timezone('America/New_York')
            now_ny = datetime.now(ny_tz)
            
            # 장 운영 시간 (04:00 ~ 20:00 - 프리마켓 포함 전체 감시)
            if not (4 <= now_ny.hour < 20):
                 alert_history.clear()
                 whale_score_map.clear() # Reset Daily Score
                 await asyncio.sleep(60)
                 continue

            if now_ny.weekday() >= 5: # 주말
                whale_score_map.clear()
                await asyncio.sleep(3600)
                continue

            # 시장 개장 여부 (API Check)
            if check_us_market_open(current_token) is False:
                await asyncio.sleep(60)
                continue
            
            # 2. 거래량 급증/상위 종목 스캔 (NAS/NYS/AMS)
            candidates = []
            loop = asyncio.get_event_loop()
            
            # 거래소별 Top 10 스캔
            for excd in ["NAS", "NYS", "AMS"]:
                stocks = await loop.run_in_executor(
                    None, fetch_overseas_volume_rank, current_token, excd
                )
                if stocks:
                    candidates.extend(stocks[:10])
                await asyncio.sleep(0.5)

            # ✅ [Data Correction] candidates의 데이터를 'fetch_prices_by_codes'로 갱신 (정확한 Volume 확보)
            # Fetch Batch details for accuracy (tvol, price)
            candidate_codes = list(set([c.get('symb') or c.get('code') for c in candidates if c.get('symb') or c.get('code')]))
            if candidate_codes:
                from watcher.utils.definitions import fetch_prices_by_codes
                # Split into chunks of 15 (API limit usually 20?)
                details_map = {}
                for i in range(0, len(candidate_codes), 15):
                    chunk = candidate_codes[i:i+15]
                    details = await loop.run_in_executor(None, fetch_prices_by_codes, current_token, chunk)
                    for d in details:
                        details_map[d['code']] = d
                
                # Merge Details back to candidates
                # Filter candidates -> Only keep those successfully fetched or original?
                # Using fetched details is safer.
                # Rebuild candidates list from details_map to ensure data quality (but we lose rank order?)
                # We can iterate selection and update.
                updated_candidates = []
                for c in candidates:
                    code = c.get('symb') or c.get('code')
                    if code in details_map:
                        d = details_map[code]
                        # Merge vital fields
                        c['price'] = d.get('price')
                        c['rate'] = d.get('rate')
                        c['tvol'] = d.get('tvol') # Accurate Volume
                        
                        # [Naming] Prioritize Korean Name (nam) from Condition Search
                        # Format: "KoreanName (Ticker)" or "EnglishName (Ticker)"
                        kor_name = c.get('nam')
                        eng_name = d.get('name') or c.get('ename')
                        ticker = code
                        
                        if kor_name:
                            final_name = f"{kor_name} ({ticker})"
                        elif eng_name:
                            # Clean English Name (remove internal codes if any)
                            final_name = f"{eng_name} ({ticker})"
                        else:
                            final_name = ticker # Fallback
                            
                        c['name'] = final_name
                        updated_candidates.append(c)
                candidates = updated_candidates

            # 3. 정밀 분석 (Big Tick Check) - [Disabled by User Request]
            # 실시간 알림을 보내지 않으므로, 굳이 Big Tick을 누적하여 보여줄 필요가 없다는 피드백 반영.
            # Step 2에서 확보한 Volume Rank 데이터만 대시보드에 표출.
            pass 

            # ---------------------------------------------------------
            # 📊 [Dashboard Update] Every 5 minutes
            # ---------------------------------------------------------
            if time.time() - last_dashboard_update > 300:
                try:
                    # 1. Volume Leaders (candidates Updated)
                    vol_top_10 = []
                    for c in candidates[:10]:
                        c_copy = c.copy()
                        c_copy['name'] = c.get('name')
                        
                        # Use 'rate' for US
                        c_copy['rate'] = c.get('rate')
                        if 'chgrate' in c_copy: del c_copy['chgrate']
                        
                        # Accurate Volume from tvol
                        vol_val = c.get('tvol') or c.get('vol') or 0
                        try:
                            vol_int = int(vol_val)
                            c_copy['name'] = f"{c_copy['name']}\n   👉 📊 거래량: {vol_int:,}주"
                        except: pass

                        c_copy['price'] = c.get('price')
                        vol_top_10.append(c_copy)
                        
                    # 2. Construct List (Only Volume)
                    dashboard_list = []
                    # Header: � 실시간 거래량 상위 Top 10 (Real-time)
                    dashboard_list.append({"name": "📈 실시간 거래량 상위 Top 10 (Real-time)", "is_header": True})
                    dashboard_list.extend(vol_top_10)

                    # 4. Update
                    # Title: 미국 증시 실시간 수급 현황판
                    url = update_telegraph_board(telegraph_config, "🇺🇸 미국 증시 실시간 수급 현황판 (Live)", dashboard_list, subtitle="실시간 거래량 상위 현황")
                    
                    # Call Notification Logic (omitted for brevity, handled by existing code flow if structure preserved)
                    pass 
                    
                    # ✅ [Reset Accumulation]
                    whale_score_map.clear()
                    processed_ticks.clear()

                    
                    if url:
                         if not telegraph_config.get("path_saved"):
                             try:
                                 with open(TELEGRAPH_CONFIG_PATH, "w") as f:
                                     ujson.dump(telegraph_config, f)
                                 telegraph_config["path_saved"] = True
                             except: pass

                         # 5. [Notification] Scheduled Link Sending
                         # User Request: NY 09:40 (Open+10m), 12:40 (Mid), 15:40 (Close)
                         # Use NY Time logic
                         
                         # Reset Daily Slots (At NY 08:00, before market open)
                         if now_ny.hour == 8: sent_slots.clear()
                         
                         current_slot = None
                         # Window: 10 mins (40~50)
                         if 40 <= now_ny.minute < 50:
                             if now_ny.hour == 9: current_slot = "OPEN"
                             elif now_ny.hour == 12: current_slot = "MID"
                             elif now_ny.hour == 15: current_slot = "CLOSE"
                             
                         # [Change] Remove 'First Run' alert. Only Scheduled Slots.
                         if current_slot and (current_slot not in sent_slots):
                             payload = {
                                 "type": "WHALE_BOARD_UPDATE",
                                 "title": "🇺🇸 미국 증시 실시간 수급 현황판",
                                 "link": url
                             }
                             await redis_client.publish("news_alert", ujson.dumps(payload))
                             
                             sent_slots.add(current_slot)
                             print(f"📡 [Dashboard] Link Sent ({current_slot}): {url}")
                             # last_dashboard_link_sent not strictly needed for logic anymore but kept for compat if referenced elsewhere
                             last_dashboard_link_sent = time.time()
                             
                    last_dashboard_update = time.time()

                except Exception as e:
                    print(f"⚠️ [Dashboard Error] {e}")

            await asyncio.sleep(SCAN_INTERVAL)

        except Exception as e:
            print(f"⚠️ [Whale Watcher Error] {e}")
            await asyncio.sleep(10)
