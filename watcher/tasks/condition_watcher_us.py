import asyncio
import ujson
import time
import pytz
from datetime import datetime
from common.config import settings
from common.redis_client import redis_client
from watcher.kis_auth import get_access_token

# ✅ 공통 함수 임포트
from watcher.utils.definitions import (
    check_us_market_open,
    update_telegraph_board, 
    fetch_us_stocks_by_condition,
    fetch_prices_by_codes # ✅ 추가
)

# =========================================================
# 👇 [설정]
POLLING_INTERVAL = 60
MIN_MARKET_CAP = "10000000" # $10B
TARGET_EXCHANGES = ["NAS", "NYS"]
MILESTONES = [5.0, 10.0, 15.0, 30.0] 

# 1. 💎 Big 7 (별도 섹션)
BIG_TECH = ["NVDA", "TSLA", "AAPL", "MSFT", "AMZN", "GOOGL", "META"]

# 2. 📊 Major Indices (1배수 위주)
# User requested 1x for Semis -> SOXX (iShares Semiconductor) instead of SOXL
MAJOR_INDICES = ["QQQ", "SPY", "SOXX", "DIA", "IWM"] 

# 3. 🌍 Sector Watch List (시총 무관, Force Fetch)
# 여기에 있는 것들은 '조건검색'에 안 떠도 강제로 긁어옴
SECTOR_ETFS = MAJOR_INDICES + [
    "GLD", "SLV", # 귀금속
    "USO", "UNG", # 에너지
    "ITA", "XAR", # 방산
    "URA", "TAN", # 원전/태양광
    "IBIT",       # 비트코인
    "XLF", "XLV", "SMH" # 금융/헬스/반도체(SMH도 1배수)
]

# ✅ 모든 Key Tickers (Big Tech + Major Indices)
KEY_TICKERS = BIG_TECH + MAJOR_INDICES

# ✅ 섹터 한글 별칭 매핑 (User Request: "금 현물 ETF(GLD)" 형식 희망)
SECTOR_NAME_MAP = {
    "GLD": "금 현물(Gold)",
    "SLV": "은 현물(Silver)",
    "USO": "WTI 원유(Oil)",
    "UNG": "천연가스(Gas)",
    "ITA": "우주방산(Defense)",
    "XAR": "항공우주(Aero)",
    "URA": "원자력(Nuclear)",
    "TAN": "태양광(Solar)",
    "IBIT": "비트코인(Bitcoin)",
    "XLF": "금융(Finance)",
    "XLV": "헬스케어(Health)",
    "SMH": "반도체(Semi)",
    "SOXX": "필라델피아반도체",
    "QQQ": "나스닥100",
    "SPY": "S&P500",
    "DIA": "다우존스(Dow)",
    "IWM": "러셀2000(SmallCap)"
}

# =========================================================

# ✅ 전역 변수
alert_history = {}
telegraph_info = {"access_token": None, "path": None, "url": None}
last_telegraph_update = 0
is_premarket_briefing_sent = False
is_open_briefing_sent = False 

async def run_condition_watcher_us(approval_key, access_token=None):
    """미국 조건팀 Main Loop"""
    global alert_history, is_premarket_briefing_sent, is_open_briefing_sent, last_telegraph_update
    
    current_token = access_token
    print(f"🇺🇸 [해외 조건팀] Giant Watcher 가동 (Big7/Indices/Sectors)")

    while True:
        try:
            ny_tz = pytz.timezone('America/New_York')
            now_ny = datetime.now(ny_tz)
            current_time_ny = now_ny.strftime("%H%M")
            
            # 0. 운영 시간 체크 (뉴욕 04:00 ~ 17:00) 
            # (기존 20:00은 애프터마켓까지 포함인데, 한국장 시작과 겹침)
            ny_hour = now_ny.hour
            if not (4 <= ny_hour < 17):
                alert_history.clear()
                is_premarket_briefing_sent = False
                is_open_briefing_sent = False # 초기화
                telegraph_info["path"] = None
                print(f"💤 [US Market] 정규장 마감 ( ~ 17:00 NYT). 1시간 대기 ({now_ny.strftime('%H:%M')})...")
                await asyncio.sleep(3600)
                continue

            # -------------------------------------------------------------
            # ✅ [최적화] 주말 체크 (API 호출 낭비 방지)
            # -------------------------------------------------------------
            # 5=토요일, 6=일요일 -> 1시간 푹 잡니다.
            if now_ny.weekday() >= 5:
                print(f"💤 [US Market] 주말입니다 ({now_ny.strftime('%A')}). 1시간 대기...")
                await asyncio.sleep(3600)
                continue
            # -------------------------------------------------------------

            # 1. 휴장일/장운영 여부 체크 (평일 휴장일 등 체크용)
            is_open = check_us_market_open(current_token)
            
            if is_open == "AUTH_ERROR":
                print("🔄 [US] 토큰 만료. 갱신 시도...")
                current_token = get_access_token()
                await asyncio.sleep(2)
                continue
                
            if is_open is False:
                # 평일인데 아직 장이 안 열렸거나(새벽 4시 직전), 휴장일인 경우
                print("💤 [US Market] 거래량 없음 (장전/휴장). 1분 대기...")
                await asyncio.sleep(60)
                continue

            # 2. 데이터 수집
            loop = asyncio.get_event_loop()
            collected_data = [] # 조건검색 결과 (Mega Cap)
            sector_data = []    # 지정 종목 결과 (Sector ETFs)
            
            # A. 조건검색 (Giant Watcher)
            for excd in TARGET_EXCHANGES:
                items = await loop.run_in_executor(
                    None, 
                    fetch_us_stocks_by_condition, 
                    current_token, 
                    excd, 
                    MIN_MARKET_CAP
                )
                
                if isinstance(items, list):
                    for item in items:
                        try:
                            rate = float(item.get('rate') or item.get('diff'))
                            # 🚨 [Removed] 3% Pre-filter removed to catch ETFs
                            
                            collected_data.append({
                                "code": item.get('symb') or item.get('rsym') or item.get('code'), # ✅ [수정] Clean Ticker (symb 우선)
                                "name": item.get('name') or item.get('ename'),
                                "price": item.get('last') or item.get('price'),
                                "rate": rate,
                                "excd": excd,
                                "market_cap": float(item.get('valx') or item.get('tomv') or 0) # ✅ 시총 수집
                            })
                        except: continue
                await asyncio.sleep(0.5)

            # B. 섹터 ETF 지정 조회 (New)
            sector_items = await loop.run_in_executor(
                None,
                fetch_prices_by_codes,
                current_token,
                SECTOR_ETFS
            )
            if sector_items:
                sector_data = sector_items


            # 3. 현황판 업데이트 (데이터 없어도 시간 갱신 위해 수행)
            if time.time() - last_telegraph_update > 300:
                
                # ✅ [Merge & Deduplicate] 조건검색 + 지정조회 합치기
                merged_map = {}
                for item in collected_data:
                    merged_map[item['code']] = item
                for item in sector_data:
                    # 지정조회 데이터가 더 최신/정확할 수 있으므로 덮어쓰거나, 없는 경우 추가
                    if item['code'] in merged_map:
                        merged_map[item['code']].update(item)
                    else:
                        merged_map[item['code']] = item
                
                all_items = list(merged_map.values())

                # ✅ [Name Override] 별칭 적용 Use SECTOR_NAME_MAP
                for item in all_items:
                    code = item['code']
                    if code in SECTOR_NAME_MAP:
                        # "금 현물(Gold)" 처럼 변경
                        # 주의: update_telegraph_board에서 "Name(Code)" 형식으로 붙이므로,
                        # 여기서는 "Title" 부분만 바꿔주면 됨.
                        item['name'] = SECTOR_NAME_MAP[code]

                # ✅ [Display Logic] Construct Categorized List
                display_list = []
                
                # A. 📊 Major Indices (시장 지표)
                index_items = [x for x in all_items if x['code'] in MAJOR_INDICES]
                if index_items:
                    display_list.append({"name": "📊 Major Indices & ETFs", "is_header": True})
                    # 정렬: 사용자가 정의한 순서(MAJOR_INDICES)대로 보여주고 싶을 수 있음 or 등락률 순
                    # 일단 등락률 순 유지
                    index_items.sort(key=lambda x: x['rate'], reverse=True)
                    for k in index_items: k['no_rank'] = True 
                    display_list.extend(index_items)

                # B. 💎 Big 7 (주도주)
                tech_items = [x for x in all_items if x['code'] in BIG_TECH]
                if tech_items:
                    display_list.append({"name": "💎 Big 7 Tech", "is_header": True})
                    tech_items.sort(key=lambda x: x['rate'], reverse=True)
                    for k in tech_items: k['no_rank'] = True 
                    display_list.extend(tech_items)
                
                # C. 🌍 Global Sectors (Watch List)
                # SECTOR_ETFS에 있지만 Indices/BigTech에는 없는 것들
                exclude_main = MAJOR_INDICES + BIG_TECH
                sector_only_items = [x for x in all_items if x['code'] in SECTOR_ETFS and x['code'] not in exclude_main]
                
                if sector_only_items:
                    display_list.append({"name": "🌍 Global Sectors (Watch List)", "is_header": True})
                    sector_only_items.sort(key=lambda x: x['rate'], reverse=True)
                    for s in sector_only_items: s['no_rank'] = True
                    display_list.extend(sector_only_items)
                
                # D. Top Gainers (> 3%) (Key/Sector 제외)
                # SECTOR_ETFS 전체(이미 나온 Indices 포함) + Big Tech 제외
                exclude_all_special = SECTOR_ETFS + BIG_TECH
                risers = [x for x in all_items if x['rate'] >= 3.0 and x['code'] not in exclude_all_special]
                
                if risers:
                    display_list.append({"name": "🔥 Top Gainers (Over 3%)", "is_header": True})
                    risers.sort(key=lambda x: x['rate'], reverse=True)
                    display_list.extend(risers[:20]) # Top 20
                
                # E. Top Losers (< -3%)
                fallers = [x for x in all_items if x['rate'] <= -3.0 and x['code'] not in exclude_all_special]
                if fallers:
                    display_list.append({"name": "💧 Top Losers (Below -3%)", "is_header": True})
                    fallers.sort(key=lambda x: x['rate']) # Most negative first
                    display_list.extend(fallers[:20]) # Top 20

                page_url = await loop.run_in_executor(
                    None, 
                    update_telegraph_board, 
                    telegraph_info, 
                    f"🇺🇸 {now_ny.month}/{now_ny.day} US Market Live", 
                    display_list # Pass structured list
                )
                last_telegraph_update = time.time()
                
                # 4-1. 프리마켓 브리핑 (08:40 NYT) - 시간 변경
                if not is_premarket_briefing_sent and current_time_ny >= "0840" and current_time_ny < "0910":
                    if page_url and collected_data: # 데이터 있을 때만 브리핑
                        # 브리핑용 요약은 3% 이상인 것들만 대상으로 함
                        rising_top = sorted([x for x in collected_data if x['rate'] >= 3.0], key=lambda x: x['rate'], reverse=True)[:3]
                        falling_top = sorted([x for x in collected_data if x['rate'] <= -3.0], key=lambda x: x['rate'])[:3]
                        
                        summary_text = "📈 [급등 (3% 이상)]\n"
                        for s in rising_top: summary_text += f"• {s['name']}({s['code']}) ({s['rate']}%)\n"
                        if not rising_top: summary_text += "• 특이사항 없음\n"

                        summary_text += "\n📉 [급락 (-3% 이하)]\n"
                        for s in falling_top: summary_text += f"• {s['name']}({s['code']}) ({s['rate']}%)\n"
                        if not falling_top: summary_text += "• 특이사항 없음\n"

                        payload = {
                            "type": "NEWS_SUMMARY",
                            "name": "🇺🇸 [프리마켓 브리핑]",
                            "summary": f"오늘 밤 장전 주요 움직임입니다 (±3% 이상 / 시총 $10B 이상).\n\n{summary_text}\n...전체 현황판(ETF 포함)은 아래 링크 클릭",
                            "sentiment": "Neutral",
                            "link": page_url,
                            "should_pin": True # 📌 고정
                        }
                        await redis_client.publish("news_alert", ujson.dumps(payload))
                        is_premarket_briefing_sent = True
                        print("📢 [US] 프리마켓 브리핑 전송 완료")
                
                # 4-2. 장 초반 브리핑 (09:35 NYT) - 신규 추가
                if not is_open_briefing_sent and current_time_ny >= "0935":
                    if page_url and collected_data: # 데이터 있을 때만 브리핑
                        rising_top = sorted([x for x in collected_data if x['rate'] >= 3.0], key=lambda x: x['rate'], reverse=True)[:3]
                        falling_top = sorted([x for x in collected_data if x['rate'] <= -3.0], key=lambda x: x['rate'])[:3]
                        
                        summary_text = "📈 [급등 (3% 이상)]\n"
                        for s in rising_top: summary_text += f"• {s['name']}({s['code']}) ({s['rate']}%)\n"
                        if not rising_top: summary_text += "• 특이사항 없음\n"

                        summary_text += "\n📉 [급락 (-3% 이하)]\n"
                        for s in falling_top: summary_text += f"• {s['name']}({s['code']}) ({s['rate']}%)\n"
                        if not falling_top: summary_text += "• 특이사항 없음\n"

                        payload = {
                            "type": "NEWS_SUMMARY",
                            "name": "🇺🇸 [장 초반 브리핑]",
                            "summary": f"장 초반 수급 집중 종목입니다 (±3% 이상 / 시총 $10B 이상).\n\n{summary_text}\n...전체 현황판(ETF 포함)은 아래 링크 클릭",
                            "sentiment": "Neutral",
                            "link": page_url,
                            "should_pin": True # 📌 고정 (최신으로 덮어씀)
                        }
                        await redis_client.publish("news_alert", ujson.dumps(payload))
                        is_open_briefing_sent = True
                        print("📢 [US] 장 초반 브리핑 전송 완료")

            # 5. AI 저격 (본장 시작 후: 09:41 NYT)
            if current_time_ny >= "0941":
                # ✅ [Update] 조건검색(Giant) + 섹터ETF(Sector) 모두 감시
                all_targets = collected_data + sector_data
                
                for item in all_targets:
                    code = item['code']
                    name = item['name']
                    rate = float(item['rate'])
                    price = item['price']
                    market_cap = item.get('market_cap', 0.0)
                    is_sector = item.get('is_sector', False)

                    # 🚨 [Safety] 3% 미만은 절대 안 보냄
                    if abs(rate) < 3.0:
                        continue

                    # 🚨 [필터링] 
                    # 1. 일반 종목: 시총 $10B 미만이면 Skip
                    # 2. 섹터 ETF: 시총 무관하게 감시 (is_sector=True)
                    if not is_sector and market_cap < 10000000:
                        continue
                    
                    target_ms = 0.0
                    last_ms = alert_history.get(code, {}).get("last_milestone", 0.0)
                    
                    for ms in MILESTONES:
                        if abs(rate) >= ms and abs(last_ms) < ms:
                            target_ms = ms
                    
                    if target_ms > 0.0:
                        print(f"🔥 [US AI 저격] {name} ({rate}%) -> {target_ms}% 돌파!")
                        payload = {
                            "type": "CONDITION_US",
                            "code": code,
                            "name": name,
                            "price": price,
                            "rate": str(rate),
                            "market": "US"
                        }
                        await redis_client.publish(settings.REDIS_CHANNEL_STOCK, ujson.dumps(payload))
                        alert_history[code] = {"last_milestone": target_ms}

            await asyncio.sleep(POLLING_INTERVAL)

        except Exception as e:
            print(f"❌ [US 폴링 에러] {e}")
            await asyncio.sleep(10)