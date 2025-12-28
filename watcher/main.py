import asyncio
from watcher.kis_auth import get_approval_key, get_access_token
from common.redis_client import redis_client
# 파일명을 condition_watcher.py로 고쳐야 이 import가 작동합니다!
from watcher.tasks.vi_watcher import run_vi_watcher
from watcher.tasks.condition_watcher import run_condition_watcher
from watcher.tasks.rank_poller import run_rank_poller

async def main():
    print("🚀 [Reason Hunter] Watcher 통합 시스템 가동!")
    
    # 1. 키 발급 (웹소켓키 + REST토큰)
    approval_key = get_approval_key()
    access_token = get_access_token()
    
    if not approval_key or not access_token:
        print("🛑 키 발급 실패. .env 설정을 확인하세요.")
        return

    # 2. 3개 태스크 동시 실행 (비동기)
    # asyncio.gather를 쓰면 3개의 무한루프 함수를 동시에 돌릴 수 있습니다.
    await asyncio.gather(
        run_vi_watcher(approval_key),       # VI 팀
        run_condition_watcher(approval_key),# 조건 팀 (000번)
        run_rank_poller(access_token)       # 랭킹 팀
    )

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 시스템 종료")
    finally:
        asyncio.run(redis_client.close())