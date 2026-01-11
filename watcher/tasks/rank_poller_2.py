import asyncio
import ujson
import pytz
from datetime import datetime
from common.config import settings
from common.redis_client import redis_client
from watcher.kis_auth import get_access_token

# ✅ 공통 함수 임포트 (코드 재활용)
from watcher.utils.definitions import check_us_market_open

# ====================================================
# [설정] 미국장 브리핑 시간표 (뉴욕 시간 기준)
# 0850: 개장 20분 전 (프리마켓 이슈 + 거시경제 전략)
# 1240: 점심 시간 (장중 중간 점검)
# 1630: 장 마감 30분 후 (마감 시황)
# ====================================================
SCHEDULE_TIMES_NY = ["0850", "1240", "1630"]

async def run_us_rank_poller(access_token=None):
    """
    [US 시황 스케줄러] (뉴욕 시간 기준)
    """
    print(f"⏰ [US-Scheduler] 스케줄러 가동 (Target NYT: {SCHEDULE_TIMES_NY})")
    
    current_token = access_token
    sent_times = set()
    ny_tz = pytz.timezone('America/New_York')

    while True:
        try:
            now_ny = datetime.now(ny_tz)
            current_time_ny = now_ny.strftime("%H%M")
            
            # 1. 자정 초기화
            if current_time_ny == "0000":
                sent_times.clear()

            # 0. 운영 시간 체크 (뉴욕 04:00 ~ 17:00) 
            # (애프터마켓 이후 한국장 시작 전에는 침묵)
            ny_hour = now_ny.hour
            if not (4 <= ny_hour < 17):
                 # 주말이나 밤에는 불필요한 로그 자제 (5분에 한번 체크)
                await asyncio.sleep(300)
                continue

            # 2. 주말 체크 (토=5, 일=6)
            if now_ny.weekday() >= 5:
                await asyncio.sleep(3600)
                continue

            # 3. 스케줄 도래 (10분 윈도우 적용)
            target_time = None
            
            # (1) 정확히 매칭
            if current_time_ny in SCHEDULE_TIMES_NY and current_time_ny not in sent_times:
                target_time = current_time_ny
            
            # (2) 지연 발송 체크 (지난 10분 내에 보냈어야 했는데 안 보낸 경우)
            else:
                curr_hh = int(current_time_ny[:2])
                curr_mm = int(current_time_ny[2:])
                
                for t in SCHEDULE_TIMES_NY:
                    if t in sent_times: continue
                    
                    t_hh = int(t[:2])
                    t_mm = int(t[2:])
                    
                    # 같은 시(HH)이고, 스케줄 시간 < 현재 시간 <= 스케줄 시간 + 10분
                    if curr_hh == t_hh and t_mm < curr_mm <= t_mm + 10:
                        target_time = t
                        print(f"⏰ [US-Scheduler] 지연 발송 감지! (Schedule: {t}, Now: {current_time_ny})")
                        break

            if target_time:
                # 4. 개장 여부 체크 (+ 토큰 만료 체크)
                # definitions.py의 공통 함수 사용
                market_status = check_us_market_open(current_token)
                
                # 🔄 토큰 만료 시 갱신 로직
                if market_status == "AUTH_ERROR":
                    print("🔄 [US-Scheduler] 토큰 만료 감지. 갱신 시도...")
                    new_token = get_access_token()
                    if new_token:
                        current_token = new_token
                        print("✅ [US-Scheduler] 토큰 갱신 완료! 다시 체크합니다.")
                        await asyncio.sleep(2)
                        continue # 루프 다시 돌아서 재시도
                
                # 개장 확인됨 (True)
                if market_status is True:
                    # 매핑으로 명확히 타입 지정
                    type_map = {"0850": "OPENING", "1240": "MID", "1630": "CLOSE"}
                    briefing_type = type_map.get(target_time, "MID")
                    
                    print(f"⏰ [US-Scheduler] {current_time_ny}(NY) -> {briefing_type} 브리핑 요청!")
                    
                    payload = {
                        "type": "MARKET_BRIEFING", 
                        "market": "US",
                        "subtype": briefing_type,
                        "time": now_ny.strftime("%H:%M") + " (NY)"
                    }
                    
                    await redis_client.publish(settings.REDIS_CHANNEL_STOCK, ujson.dumps(payload))
                    sent_times.add(target_time)
                    await asyncio.sleep(60)
                
                # 휴장일/장전 (False)
                else:
                    print(f"😴 [US-Scheduler] {target_time}이지만 장이 닫혀있음 (Skip)")
                    sent_times.add(target_time) # 계속 체크하지 않도록 보낸 셈 침
            
            await asyncio.sleep(10)

        except Exception as e:
            print(f"❌ [US-Scheduler] 에러: {e}")
            await asyncio.sleep(10)