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
    fetch_us_stocks_by_condition
)

# =========================================================
# 👇 [설정]
POLLING_INTERVAL = 60
MIN_MARKET_CAP = "70000000" # $100B (단위: 1,000달러 -> 1억 * 1000 = 1000억불)
TARGET_EXCHANGES = ["NAS", "NYS"]
MILESTONES = [5.0, 10.0, 15.0, 30.0] 
# =========================================================

# ✅ 전역 변수
alert_history = {}
telegraph_info = {"access_token": None, "path": None, "url": None}
last_telegraph_update = 0
is_premarket_briefing_sent = False
is_open_briefing_sent = False # ✅ 장초반 브리핑 플래그 추가

async def run_condition_watcher_us(approval_key, access_token=None):
    """미국 조건팀 Main Loop"""
    global alert_history, is_premarket_briefing_sent, is_open_briefing_sent, last_telegraph_update
    
    current_token = access_token
    print(f"🇺🇸 [해외 조건팀] Giant Watcher 가동 ($100B↑ & ±3%↑)")

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
            collected_data = []
            loop = asyncio.get_event_loop()
            
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
                            if abs(rate) < 3.0: continue
                            
                            collected_data.append({
                                "code": item.get('symb') or item.get('rsym') or item.get('code'), # ✅ [수정] Clean Ticker (symb 우선)
                                "name": item.get('name') or item.get('ename'),
                                "price": item.get('last') or item.get('price'),
                                "rate": rate,
                                "excd": excd
                            })
                        except: continue
                await asyncio.sleep(0.5)

            # 3. 현황판 업데이트 (데이터 없어도 시간 갱신 위해 수행)
            if time.time() - last_telegraph_update > 300:
                page_url = await loop.run_in_executor(
                    None, 
                    update_telegraph_board, 
                    telegraph_info, 
                    f"🇺🇸 {now_ny.month}/{now_ny.day} US Market Live", 
                    collected_data 
                )
                last_telegraph_update = time.time()
                
                # 4-1. 프리마켓 브리핑 (08:40 NYT) - 시간 변경
                if not is_premarket_briefing_sent and current_time_ny >= "0840" and current_time_ny < "0910":
                    if page_url and collected_data: # 데이터 있을 때만 브리핑
                        rising_top = sorted([x for x in collected_data if x['rate'] > 0], key=lambda x: x['rate'], reverse=True)[:3]
                        falling_top = sorted([x for x in collected_data if x['rate'] < 0], key=lambda x: x['rate'])[:3]
                        
                        summary_text = "📈 [급등]\n"
                        for s in rising_top: summary_text += f"• {s['name']} ({s['rate']}%)\n"
                        if not rising_top: summary_text += "• 특이사항 없음\n"

                        summary_text += "\n📉 [급락]\n"
                        for s in falling_top: summary_text += f"• {s['name']} ({s['rate']}%)\n"
                        if not falling_top: summary_text += "• 특이사항 없음\n"

                        payload = {
                            "type": "NEWS_SUMMARY",
                            "name": "🇺🇸 [프리마켓 브리핑]",
                            "summary": f"오늘 밤 장전 주요 움직임입니다 (±3% 이상 / 시총 1,000억불 이상).\n\n{summary_text}\n...전체 현황판은 아래 링크 클릭",
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
                        rising_top = sorted([x for x in collected_data if x['rate'] > 0], key=lambda x: x['rate'], reverse=True)[:3]
                        falling_top = sorted([x for x in collected_data if x['rate'] < 0], key=lambda x: x['rate'])[:3]
                        
                        summary_text = "📈 [급등]\n"
                        for s in rising_top: summary_text += f"• {s['name']} ({s['rate']}%)\n"
                        if not rising_top: summary_text += "• 특이사항 없음\n"

                        summary_text += "\n📉 [급락]\n"
                        for s in falling_top: summary_text += f"• {s['name']} ({s['rate']}%)\n"
                        if not falling_top: summary_text += "• 특이사항 없음\n"

                        payload = {
                            "type": "NEWS_SUMMARY",
                            "name": "🇺🇸 [장 초반 브리핑]",
                            "summary": f"장 초반 수급 집중 종목입니다 (±3% 이상 / 시총 1,000억불 이상).\n\n{summary_text}\n...전체 현황판은 아래 링크 클릭",
                            "sentiment": "Neutral",
                            "link": page_url,
                            "should_pin": True # 📌 고정 (최신으로 덮어씀)
                        }
                        await redis_client.publish("news_alert", ujson.dumps(payload))
                        is_open_briefing_sent = True
                        print("📢 [US] 장 초반 브리핑 전송 완료")

            # 5. AI 저격 (본장 시작 후: 09:41 NYT) - 시간 변경
            if current_time_ny >= "0941":
                for item in collected_data:
                    code = item['code']
                    name = item['name']
                    rate = float(item['rate'])
                    price = item['price']
                    
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