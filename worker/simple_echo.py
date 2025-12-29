import asyncio
import ujson
from telegram import Bot
from common.config import settings
from common.redis_client import redis_client

async def send_telegram_message(bot, message_data):
    """데이터 타입에 따라 예쁘게 포맷팅해서 전송"""
    try:
        msg_type = message_data.get("type")
        text = ""

        # 1. VI 발동 (긴급!)
        if msg_type == "VI":
            code = message_data.get('code')
            status = message_data.get('status') # 발동/해제
            price = message_data.get('price')
            rate = message_data.get('rate', '0')
            time = message_data.get('time')
            
            emoji = "🔴" if status == "발동" else "🔵"
            text = (
                f"{emoji} [VI {status}] {time}\n"
                f"종목: {code}\n"
                f"현재가: {price}원 ({rate}%)\n"
                f"#VI발동"
            )

        # 2. 조건검색 포착 (관심)
        elif msg_type == "CONDITION":
            code = message_data.get('code')
            name = message_data.get('name')
            rate = message_data.get('rate')
            price = message_data.get('price')

            text = (
                f"🔥 [조건포착] {name}\n"
                f"코드: {code}\n"
                f"등락률: {rate}%\n"
                f"현재가: {price}원\n"
                f"#ReasonHunter"
            )

        # 3. 랭킹 리포트 (정보)
        elif msg_type == "RANKING":
            time = message_data.get('time')
            data_list = message_data.get('data', [])
            
            rank_text = "\n".join(data_list)
            text = (
                f"📊 [랭킹 리포트] {time}\n"
                f"{rank_text}\n"
                f"#시장동향"
            )

        # 텔레그램 전송
        if text:
            await bot.send_message(chat_id=settings.TELEGRAM_CHAT_ID, text=text)
            print(f"🚀 [텔레그램 전송] {text.splitlines()[0]}...")

    except Exception as e:
        print(f"❌ 메시지 전송 실패: {e}")

async def run_worker():
    print(f"👷 [Worker] 단순 중계 모드 시작! (To: {settings.TELEGRAM_CHAT_ID})")
    
    # 텔레그램 봇 초기화
    bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
    
    # Redis 구독 (Pub/Sub)
    pubsub = redis_client.pubsub()
    await pubsub.subscribe(settings.REDIS_CHANNEL_STOCK)
    
    print("👂 Redis 채널 수신 대기 중...")

    try:
        async for message in pubsub.listen():
            if message['type'] == 'message':
                # Redis에서 온 데이터 꺼내기
                data_str = message['data']
                if isinstance(data_str, bytes):
                    data_str = data_str.decode('utf-8')
                
                try:
                    data_json = ujson.loads(data_str)
                    # 텔레그램 전송 함수 호출
                    await send_telegram_message(bot, data_json)
                except Exception as e:
                    print(f"⚠️ 데이터 파싱 에러: {e}")
                    
    except asyncio.CancelledError:
        print("🛑 Worker 종료")
    finally:
        await redis_client.close()

if __name__ == "__main__":
    try:
        asyncio.run(run_worker())
    except KeyboardInterrupt:
        print("\n🛑 시스템 종료")