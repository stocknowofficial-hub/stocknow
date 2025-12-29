import asyncio
from watcher.kis_auth import get_approval_key, get_access_token
from common.redis_client import redis_client
from watcher.tasks.vi_watcher import run_vi_watcher
from watcher.tasks.condition_watcher import run_condition_watcher
from watcher.tasks.rank_poller import run_rank_poller 
from watcher.tasks.rank_poller_2 import run_us_rank_poller # [추가]

async def main():
    print("🚀 [Reason Hunter] Watcher 통합 시스템 가동! (실전투자 Ver)")
    
    approval_key = get_approval_key()
    access_token = get_access_token()
    
    if not approval_key or not access_token:
        print("🛑 키 발급 실패. .env 설정을 확인하세요.")
        return

    # 4개 팀 동시 가동!
    await asyncio.gather(
        run_vi_watcher(approval_key),       # 1. 국내 VI
        run_condition_watcher(approval_key),# 2. 국내 조건검색
        run_rank_poller(access_token),      # 3. 국내 대장주
        run_us_rank_poller(access_token)    # 4. [NEW] 미국 대장주
    )

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 시스템 종료")
    finally:
        asyncio.run(redis_client.close())