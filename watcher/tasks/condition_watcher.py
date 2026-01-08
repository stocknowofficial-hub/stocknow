import asyncio
import ujson
import time
from datetime import datetime
from common.config import settings
from common.redis_client import redis_client
from watcher.kis_auth import get_access_token

# ✅ 분리한 함수들 임포트
from watcher.utils.definitions import (
    check_is_holiday,
    update_telegraph_board,
    fetch_condition_stocks
)

# =========================================================
# 👇 [설정]
POLLING_INTERVAL = 60
TARGET_SEQ = "0"
# =========================================================

# ✅ 전역 변수 (상태 관리)
alert_history = {}
telegraph_info = {"access_token": None, "path": None, "url": None}
last_telegraph_update = 0
is_briefing_sent = False
last_holiday_check_date = None 

async def run_condition_watcher(approval_key, access_token=None):
    """국내 조건팀 Main Loop"""
    global alert_history, last_telegraph_update, is_briefing_sent, last_holiday_check_date
    
    current_token = access_token
    print(f"🕵️ [국내 조건팀] Top 200 감시 시작 (Definitions Ver.)")

    MY_HTS_ID = settings.KIS_HTS_ID or "chh6518"

    while True:
        try:
            now = datetime.now()
            today_str = now.strftime("%Y%m%d")
            current_time_str = now.strftime("%H%M")
            
            # 1. 휴장일 체크
            if last_holiday_check_date != today_str:
                is_holiday = check_is_holiday(current_token) # utils 함수 호출
                
                if is_holiday == "AUTH_ERROR":
                    print("🔄 [시스템] 토큰 만료. 갱신 시도...")
                    new_token = get_access_token()
                    if new_token:
                        current_token = new_token
                        await asyncio.sleep(2)
                        continue

                if is_holiday is True:
                    last_holiday_check_date = today_str
                    # 🚨 [수정] 24시간(86400) -> 1시간(3600)으로 변경
                    # 이유: 일요일 밤에 실행했을 때 월요일 아침을 놓치지 않기 위함
                    print("😴 휴장일이므로 1시간 대기합니다...")
                    await asyncio.sleep(3600)
                    continue
                
                if is_holiday is False:
                    last_holiday_check_date = today_str

            # 2. 시간 체크 (08:30 ~ 16:00)
            if not ("0830" <= current_time_str <= "1600"):
                await asyncio.sleep(60)
                continue

            # 3. 08:30 초기화
            if current_time_str == "0830":
                alert_history.clear()
                is_briefing_sent = False
                telegraph_info["path"] = None

            # 4. API 조회 (utils 함수 호출)
            loop = asyncio.get_event_loop()
            stock_list = await loop.run_in_executor(
                None, 
                fetch_condition_stocks, 
                current_token, 
                MY_HTS_ID, 
                TARGET_SEQ
            )
            
            if stock_list == "AUTH_ERROR":
                print("🔄 [시스템] 토큰 만료. 재발급 대기...")
                new_token = get_access_token()
                if new_token: current_token = new_token
                await asyncio.sleep(2)
                continue

            if isinstance(stock_list, list):
                # A. 09:10 모닝 브리핑
                if not is_briefing_sent and "0910" <= current_time_str < "1530":
                    # telegraph_info를 인자로 넘겨줍니다
                    page_url = await loop.run_in_executor(
                        None, 
                        update_telegraph_board, 
                        telegraph_info, 
                        f"{now.month}/{now.day} 장초반 급등 현황", 
                        stock_list
                    )
                    
                    if page_url:
                        # 1. 등락률 순으로 정렬 (상승률 상위)
                        sorted_list = sorted(stock_list, key=lambda x: float(x['chgrate']), reverse=True)
                        
                        top_summary = ""
                        for i, item in enumerate(sorted_list[:5]):
                            rate_val = float(item['chgrate'])
                            # 2. 포맷팅 수정 (소수점 2자리, 공백 제거)
                            top_summary += f"{i+1}. {item['name']} ({rate_val:.2f}%)\n"
                        
                        payload = {
                            "type": "NEWS_SUMMARY",
                            "name": "📢 [장 초반 브리핑]",
                            "summary": f"수급이 쏠리는 종목입니다 (±3% 이상 / 시총 200위 이내)\n\n{top_summary}\n...전체 리스트는 아래 링크 확인",
                            "sentiment": "Neutral",
                            "link": page_url,
                            "should_pin": True # 📌 메시지 고정 요청
                        }
                        await redis_client.publish("news_alert", ujson.dumps(payload))
                        print("📢 [브리핑] 09:10 모닝 브리핑 전송 완료")
                        is_briefing_sent = True

                # B. 실시간 현황판 업데이트
                if time.time() - last_telegraph_update > 300:
                    if stock_list:
                        await loop.run_in_executor(
                            None, 
                            update_telegraph_board, 
                            telegraph_info, 
                            f"{now.month}/{now.day} 실시간 급등 현황", 
                            stock_list
                        )
                        last_telegraph_update = time.time()

                # C. AI 저격 (마일스톤) - 스로틀링 적용 (Top 3 Rising / Top 3 Falling)
                if current_time_str >= "0910":
                    candidates = []
                    
                    # 1. 대상 후보군 수집
                    for idx, item in enumerate(stock_list):
                        try:
                            code = item['code']
                            name = item['name']
                            price = item['price'] # 원본 가격 문자열
                            rate = float(item['chgrate'])
                            
                            rank = idx + 1
                            milestones = [5.0, 8.0, 12.0, 29.0] if rank <= 100 else [10.0, 20.0, 29.0]
                            
                            last_milestone = alert_history.get(code, {}).get("last_milestone", 0.0)
                            target_milestone = 0.0
                            
                            for ms in milestones:
                                if abs(rate) >= ms and abs(last_milestone) < ms:
                                    target_milestone = ms
                            
                            if target_milestone > 0.0:
                                candidates.append({
                                    "code": code,
                                    "name": name,
                                    "price": price,
                                    "rate": rate,
                                    "target_milestone": target_milestone
                                })
                        except: continue

                    # 2. 우선순위 선정 (상승 3개, 하락 3개)
                    rising_candidates = [x for x in candidates if x['rate'] > 0]
                    falling_candidates = [x for x in candidates if x['rate'] < 0]

                    rising_selected = sorted(rising_candidates, key=lambda x: x['rate'], reverse=True)[:3]
                    falling_selected = sorted(falling_candidates, key=lambda x: x['rate'])[:3] # 가장 많이 떨어진 순
                    
                    # 선정된 종목들의 코드를 집합으로 만듦 (빠른 조회)
                    selected_codes = {item['code'] for item in rising_selected + falling_selected}
                    
                    # 3. 처리 (전송 or Skip and Update)
                    # candidates에 있는 모든 종목에 대해 'history update'는 필수 (재진입 방지)
                    for item in candidates:
                        code = item['code']
                        name = item['name']
                        rate_val = item['rate']
                        target_ms = item['target_milestone']
                        
                        # 히스토리 업데이트 (공통)
                        alert_history[code] = {"last_milestone": target_ms}
                        
                        # 선정된 종목만 실제 전송
                        if code in selected_codes:
                            # ✅ 포맷팅 (사용자 요청)
                            formatted_rate = f"{int(rate_val * 100) / 100}" 
                            
                            try:
                                formatted_price = str(int(float(item['price'])))
                            except:
                                formatted_price = item['price']
                            
                            print(f"🔥 [AI 저격] {name} ({formatted_rate}%) -> {target_ms}% 구간 돌파!")
                            
                            payload = {
                                "type": "CONDITION",
                                "code": code,
                                "name": name,
                                "price": formatted_price,
                                "rate": formatted_rate,
                                "market": "KR"
                            }
                            await redis_client.publish(settings.REDIS_CHANNEL_STOCK, ujson.dumps(payload))
                        else:
                            # 탈락한 종목은 로그만 찍고 넘어감 (History는 업데이트됐으므로 다음 루프에서 무시됨)
                            print(f"🚫 [AI 저격 Skip] {name} ({rate_val}%) -> {target_ms}% (순위 밀림)")

            await asyncio.sleep(POLLING_INTERVAL)

        except Exception as e:
            print(f"❌ [Watcher 에러] {e}")
            await asyncio.sleep(10)