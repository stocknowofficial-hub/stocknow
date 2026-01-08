import asyncio
import sys

# 윈도우에서 'RuntimeError: Event loop is closed' 방지용 (필요시 사용)
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from watcher.kis_auth import get_approval_key, get_access_token
from common.redis_client import redis_client

# ✅ [유지] 정예 요원 4명
from watcher.tasks.condition_watcher import run_condition_watcher
from watcher.tasks.rank_poller import run_rank_poller 
from watcher.tasks.rank_poller_2 import run_us_rank_poller
from watcher.tasks.condition_watcher_us import run_condition_watcher_us

async def main():
    print("🚀 [Reason Hunter] Watcher 통합 시스템 가동! (Simple & Strong)")
    
    # 1. KIS 접근 토큰 발급 (출입증)
    approval_key = get_approval_key() 
    access_token = get_access_token() 
    
    if not approval_key or not access_token:
        print("🛑 키 발급 실패. .env 설정을 확인하세요.")
        return

    print("✅ [System] 인증 성공. 감시 요원들을 투입합니다...")

    # 2. 4대 감시자 동시 실행
    await asyncio.gather(
        # 🇰🇷 국내장 급등 포착 (조건검색)
        run_condition_watcher(approval_key, access_token), 
        
        # 🇰🇷 국내장 랭킹 (시황 브리핑)
        run_rank_poller(access_token),       
        
        # 🇺🇸 미국장 랭킹 (시황 브리핑)
        run_us_rank_poller(access_token), # (파일명이 rank_poller_2 맞으시죠? us_rank_poller로 바꾸셔도 좋습니다)
        
        # 🇺🇸 미국장 급등 포착 (조건검색)
        run_condition_watcher_us(approval_key, access_token) 
    )

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 시스템 종료")
    finally:
        # Redis 연결 안전하게 종료
        asyncio.run(redis_client.close())