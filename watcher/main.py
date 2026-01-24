import asyncio
import sys

# 윈도우에서 'RuntimeError: Event loop is closed' 방지용 (필요시 사용)
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from watcher.kis_auth import get_approval_key, get_access_token
from common.redis_client import redis_client

# ✅ [유지] 정예 요원 5명 (+트럼프 마크맨)
from watcher.tasks.condition_watcher import run_condition_watcher
from watcher.tasks.rank_poller import run_rank_poller 
from watcher.tasks.rank_poller_2 import run_us_rank_poller
from watcher.tasks.condition_watcher_us import run_condition_watcher_us
from watcher.tasks.trump_watcher import run_trump_watcher
from watcher.tasks.report_watcher import run_report_watcher # ✅ New
from common.logger import setup_logger # ✅ Logger Import

logger = setup_logger("Watcher", "logs/watcher", "watcher.log")


# ==============================================================================
# 🔄 [Self-Healing] 정기 재기동 스케줄러 (오전 7시 / 오후 7시)
# ==============================================================================
async def run_scheduled_restarter():
    """
    매일 07:00, 19:00에 프로세스를 종료합니다. (Watcher)
    Docker의 'restart: always' 정책에 의해 즉시 재기동됩니다.
    """
    import sys
    import random
    from datetime import datetime
    
    logger.info("📅 [Restarter] 정기 재기동 스케줄러 가동 (Target: 07:00, 19:00 KST)")
    
    while True:
        now = datetime.now()
        hour = now.hour
        minute = now.minute
        
        # 07:00 ~ 07:05 or 19:00 ~ 19:05 (5분 여유)
        if (hour == 7 or hour == 19) and minute < 5:
            wait_sec = random.randint(1, 60) # 동시성 이슈 방지
            logger.warning(f"🛑 [Self-Destruct] 정기 점검 시간입니다. {wait_sec}초 후 Watcher를 재기동합니다...")
            
            await asyncio.sleep(wait_sec)
            logger.warning("💣 [Goodbye] Watcher 시스템 종료. (Docker will revive me!)")
            sys.exit(0) 
            
        await asyncio.sleep(60)

async def main():
    logger.info("🚀 [Reason Hunter] Watcher 통합 시스템 가동! (Simple & Strong)")
    
    # 1. KIS 접근 토큰 발급 (출입증)
    # 1. KIS 접근 토큰 발급 (출입증)
    # [안정성 패치] 실패 시 즉시 종료하지 않고 무한 재시도 (Crash Loop 방지)
    while True:
        approval_key = get_approval_key() 
        
        # ✅ [Fix] API Rate Limit (1분 제한) 회피를 위한 딜레이
        if approval_key:
             logger.info("⏳ 토큰 발급을 위해 1초 대기...")
             await asyncio.sleep(1.5)
             
        access_token = get_access_token() 
        
        if approval_key and access_token:
            break
            
        logger.error("🛑 키 발급 실패. 60초 후 재시도합니다... (API Rate Limit 방지)")
        await asyncio.sleep(60)

    logger.info("✅ [System] 인증 성공. 감시 요원들을 투입합니다...")

    # 2. 5대 감시자 + 재기동 스케줄러 동시 실행
    await asyncio.gather(
        # 🇰🇷 국내장 급등 포착 (조건검색)
        run_condition_watcher(approval_key, access_token), 
        
        # 🇰🇷 국내장 랭킹 (시황 브리핑)
        run_rank_poller(access_token),       
        
        # 🇺🇸 미국장 랭킹 (시황 브리핑)
        run_us_rank_poller(access_token), 
        
        # 🇺🇸 미국장 급등 포착 (조건검색)
        run_condition_watcher_us(approval_key, access_token),

        # 🗽 트럼프 SNS 감시
        run_trump_watcher(),

        # 📑 리포트 감시 (BlackRock / Kiwoom)
        run_report_watcher(),
        
        # 🔄 스케줄러
        run_scheduled_restarter()
    )

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("🛑 시스템 종료")
    finally:
        # Redis 연결 안전하게 종료
        asyncio.run(redis_client.close())