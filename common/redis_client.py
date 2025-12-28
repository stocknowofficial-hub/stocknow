import redis.asyncio as redis
from common.config import settings

class RedisClient:
    def __init__(self):
        # 비동기 Redis 클라이언트 생성
        # decode_responses=True : 데이터를 받을 때 bytes가 아닌 str(문자열)로 자동 변환
        self.redis = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            decode_responses=True
        )

    async def publish(self, channel: str, message: str):
        """지정된 채널로 메시지를 전송(Pub)합니다."""
        try:
            await self.redis.publish(channel, message)
        except Exception as e:
            print(f"❌ [Redis Error] Publish 실패: {e}")

    async def close(self):
        """연결 종료"""
        await self.redis.close()

# 전역 객체 생성 (다른 파일에서 import redis_client 해서 사용)
redis_client = RedisClient()