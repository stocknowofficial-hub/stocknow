import redis.asyncio as redis
from common.config import settings

class RedisClient:
    def __init__(self):
        # Redis 클라이언트 생성 (연결은 실제 명령 때 맺어짐)
        self.client = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            decode_responses=True
        )

    async def publish(self, channel, message):
        """메시지 발행 (Watcher용)"""
        await self.client.publish(channel, message)

    def pubsub(self):
        """[추가됨] 구독 객체 반환 (Worker용)"""
        return self.client.pubsub()

    async def close(self):
        """연결 종료"""
        await self.client.close()

# 전역에서 쓸 싱글톤 객체
redis_client = RedisClient()