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

async def main():
    logger.info("🚀 [Reason Hunter] Watcher 통합 시스템 가동! (Simple & Strong)")
    
    # 1. KIS 접근 토큰 발급 (출입증)
    approval_key = get_approval_key() 
    access_token = get_access_token() 
    
    if not approval_key or not access_token:
        logger.error("🛑 키 발급 실패. .env 설정을 확인하세요.")
        return

    logger.info("✅ [System] 인증 성공. 감시 요원들을 투입합니다...")

    # 2. 5대 감시자 동시 실행
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
        run_report_watcher()
    )

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("🛑 시스템 종료")
    finally:
        # Redis 연결 안전하게 종료
        asyncio.run(redis_client.close())