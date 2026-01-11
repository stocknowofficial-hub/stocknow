import asyncio
import ujson
from datetime import datetime
from common.config import settings
from common.redis_client import redis_client
from watcher.kis_auth import get_access_token

# ✅ 공통 함수 임포트
from watcher.utils.definitions import check_today_actionable

# ====================================================
# [설정] 브리핑 발송 시간표 (HHMM)
# ====================================================
# ====================================================
# [설정] 브리핑 발송 시간표 (HHMM)
# ====================================================
SCHEDULE_TIMES = ["0905", "1200", "1600"]

async def run_rank_poller(access_token=None):
    """
    [KR 시황 스케줄러] 
    """
    print(f"⏰ [KR-Scheduler] 시황 브리핑 스케줄러 가동 {SCHEDULE_TIMES}")
    
    current_token = access_token
    sent_times = set()
    last_date = datetime.now().strftime("%Y%m%d") # ✅ 마지막 실행 날짜 기록

    # ✅ 상태 관리
    current_status = "UNKNOWN"
    last_check_date = None
    is_morning_rechecked = False

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
                is_morning_rechecked = False # 날짜 바뀌면 리체크 플래그 초기화
            # -----------------------------------------------------------

            # 1. 날짜 변경 감지 -> 상태 점검
            if last_check_date != today_str:
                print(f"📅 [KR-Scheduler] 날짜 변경 -> 상태 점검 ({today_str})")
                status_result = check_today_actionable(current_token)
                
                if status_result == "AUTH_ERROR":
                     print("🔄 [KR-Scheduler] 토큰 만료. 갱신 시도...")
                     new_token = get_access_token()
                     if new_token: current_token = new_token; await asyncio.sleep(2); continue

                current_status = status_result
                last_check_date = today_str
                print(f"✅ [KR-Scheduler] 오늘 상태 확정: {current_status}")

            # 2. 아침(08:00~08:15) 더블체크 (새벽 오류 방지)
            if "0800" <= current_time <= "0815" and not is_morning_rechecked:
                print(f"🕵️ [KR-Scheduler] 아침 정기점검 수행 ({current_time})")
                status_result = check_today_actionable(current_token)
                
                if status_result == "AUTH_ERROR":
                     print("🔄 [KR-Scheduler] 토큰 만료. 갱신 시도...")
                     new_token = get_access_token()
                     if new_token: current_token = new_token; await asyncio.sleep(2); continue

                current_status = status_result
                print(f"✅ [KR-Scheduler] 아침 점검 결과: {current_status}")
                is_morning_rechecked = True

            # 3. 휴장/주말이면 -> 긴 잠
            if current_status != "OPEN":
                await asyncio.sleep(3600)
                continue

            # --- 🚦 아래는 "개장일(OPEN)"일 때만 실행됨 ---

            # 3. 스케줄 도래 확인
            target_time = None
            if current_time in SCHEDULE_TIMES and current_time not in sent_times:
                target_time = current_time
            else:
                current_hh = int(current_time[:2])
                current_mm = int(current_time[2:])
                for t in SCHEDULE_TIMES:
                    if t in sent_times: continue
                    t_hh = int(t[:2])
                    t_mm = int(t[2:])
                    if current_hh == t_hh and t_mm < current_mm <= t_mm + 10:
                        target_time = t
                        print(f"⏰ [KR-Scheduler] 지연 발송 감지! (Schedule: {t}, Now: {current_time})")
                        break
            
            if target_time:
                # 이미 current_status == OPEN 이므로 바로 발송
                type_map = {"0905": "OPENING", "1200": "MID", "1600": "CLOSE"}
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
                
                # 중복 발송 방지
                await asyncio.sleep(60)

            # 평소 대기
            await asyncio.sleep(10)

        except Exception as e:
            print(f"❌ [KR-Scheduler] 에러: {e}")
            await asyncio.sleep(10)