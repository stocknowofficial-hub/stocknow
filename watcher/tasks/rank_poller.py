import asyncio
import ujson
from datetime import datetime
from common.config import settings
from common.redis_client import redis_client
from watcher.kis_auth import get_access_token

# ✅ 공통 함수 임포트
from watcher.utils.definitions import check_is_holiday

# ====================================================
# [설정] 브리핑 발송 시간표 (HHMM)
# ====================================================
SCHEDULE_TIMES = ["0840", "1200", "1600"]

async def run_rank_poller(access_token=None):
    """
    [KR 시황 스케줄러] 
    """
    print(f"⏰ [KR-Scheduler] 시황 브리핑 스케줄러 가동 {SCHEDULE_TIMES}")
    
    current_token = access_token
    sent_times = set()
    last_date = datetime.now().strftime("%Y%m%d") # ✅ 마지막 실행 날짜 기록

    while True:
        try:
            now = datetime.now()
            today_str = now.strftime("%Y%m%d")
            current_time = now.strftime("%H%M")
            
            # -----------------------------------------------------------
            # ✅ [보완] 날짜가 바뀌면 발송 기록 초기화 (자정 스킵 문제 해결)
            # -----------------------------------------------------------
            if today_str != last_date:
                print(f"📅 [KR-Scheduler] 날짜 변경 감지 ({last_date} -> {today_str}). 발송 기록 초기화.")
                sent_times.clear()
                last_date = today_str
            # -----------------------------------------------------------

            # 1. 주말 체크 (토/일)
            if now.weekday() >= 5:
                # 주말엔 1시간씩 잠 (API 절약)
                await asyncio.sleep(3600)
                continue

            # 2. 스케줄 도래
            # (1) 정확히 매칭되는 시간 체크
            target_time = None
            if current_time in SCHEDULE_TIMES and current_time not in sent_times:
                target_time = current_time
            
            # (2) 혹은 지난 10분 내에 보냈어야 했는데 안 보낸 게 있는지 체크 (루프 밀림 방지)
            else:
                current_hh = int(current_time[:2])
                current_mm = int(current_time[2:])
                
                for t in SCHEDULE_TIMES:
                    if t in sent_times: continue
                    
                    t_hh = int(t[:2])
                    t_mm = int(t[2:])
                    
                    # 같은 시(HH)이고, 스케줄 시간 < 현재 시간 <= 스케줄 시간 + 10분
                    if current_hh == t_hh and t_mm < current_mm <= t_mm + 10:
                        target_time = t
                        print(f"⏰ [KR-Scheduler] 지연 발송 감지! (Schedule: {t}, Now: {current_time})")
                        break

            if target_time:
                
                # 3. 휴장일 체크
                is_holiday = check_is_holiday(current_token)
                
                # 🔄 토큰 갱신
                if is_holiday == "AUTH_ERROR":
                    print("🔄 [KR-Scheduler] 토큰 만료 감지. 갱신 시도...")
                    new_token = get_access_token()
                    if new_token:
                        current_token = new_token
                        print("✅ [KR-Scheduler] 토큰 갱신 완료! 재시도합니다.")
                        await asyncio.sleep(2)
                        continue 
                
                # 개장일 (False)
                if is_holiday is False:
                    # 매핑으로 명확히 타입 지정
                    type_map = {"0840": "OPENING", "1200": "MID", "1600": "CLOSE"}
                    briefing_type = type_map.get(target_time, "MID")
                    
                    print(f"⏰ [KR-Scheduler] {current_time} -> {briefing_type} 브리핑 요청 발송! (Target: {target_time})")
                    
                    payload = {
                        "type": "MARKET_BRIEFING", 
                        "market": "KR",
                        "subtype": briefing_type,
                        "time": now.strftime("%H:%M")
                    }
                    
                    await redis_client.publish(settings.REDIS_CHANNEL_STOCK, ujson.dumps(payload))
                    sent_times.add(target_time)
                    
                    # 중복 발송 방지를 위해 1분 대기
                    await asyncio.sleep(60)
                
                # 휴장일 (True)
                elif is_holiday is True:
                    print(f"😴 [KR-Scheduler] 휴장일이라 {target_time} 브리핑 생략")
                    sent_times.add(target_time) # 보낸 셈 치고 기록
            
            # 평소엔 10초 대기
            await asyncio.sleep(10)

        except Exception as e:
            print(f"❌ [KR-Scheduler] 에러: {e}")
            await asyncio.sleep(10)