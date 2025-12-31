import asyncio
from watcher.kis_auth import get_approval_key, get_access_token
from common.redis_client import redis_client
from watcher.tasks.vi_watcher import run_vi_watcher
from watcher.tasks.condition_watcher import run_condition_watcher
from watcher.tasks.rank_poller import run_rank_poller 
from watcher.tasks.rank_poller_2 import run_us_rank_poller
from watcher.tasks.condition_watcher_us import run_condition_watcher_us

async def main():
    print("🚀 [Reason Hunter] Watcher 통합 시스템 가동! (실전투자 Ver)")
    
    approval_key = get_approval_key() # 증권사 서버에 접속할 출입증 부터 만듬.
    access_token = get_access_token() # 토큰도.
    
    if not approval_key or not access_token:
        print("🛑 키 발급 실패. .env 설정을 확인하세요.")
        return

    # asyncio.gather는 여러개의 비동기작업을 하나의 바구니에 담아 동시에 실행. 순서대로 실행이아니라 동시에 출발함.
    await asyncio.gather(
        # run_vi_watcher(approval_key),       
        # [수정] access_token도 같이 넘겨줍니다!
        run_condition_watcher(approval_key, access_token), 
        
        run_rank_poller(access_token),      
        run_us_rank_poller(access_token),    
        run_condition_watcher_us(approval_key, access_token) 
    )

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 시스템 종료")
    finally:
        asyncio.run(redis_client.close())