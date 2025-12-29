import asyncio
import ujson
from telegram import Bot
from common.config import settings
from common.redis_client import redis_client
from worker.modules.news_crawler import NewsCrawler  # 뉴스 크롤러 가져오기

# 뉴스 크롤러 인스턴스 생성 (한 번만 만들어서 계속 씀)
crawler = NewsCrawler()

async def send_telegram_message(bot, message_data):
    """이벤트 + 뉴스 정보를 합쳐서 텔레그램으로 전송"""
    try:
        msg_type = message_data.get("type")
        code = message_data.get('code')
        name = message_data.get('name', '') # VI는 이름이 없을 수도 있음
        
        # 1. 검색 키워드 결정 (이름이 있으면 이름으로, 없으면 코드로)
        search_keyword = name if name else code
        
        # 2. 뉴스 검색 수행 (랭킹 리포트는 뉴스 검색 제외)
        news_text = ""
        if msg_type in ["VI", "CONDITION"] and search_keyword:
            print(f"🔎 [{search_keyword}] 뉴스 찾는 중...")
            news_items = crawler.search_news(search_keyword, display=3)
            
            if news_items:
                news_text = "\n\n📰 **관련 뉴스**"
                for i, item in enumerate(news_items):
                    # HTML 태그 제거된 제목
                    clean_title = item['title']
                    link = item['link']
                    news_text += f"\n[{i+1}] {clean_title}\n🔗 {link}"
            else:
                news_text = "\n\n📭 관련 뉴스 없음"

        # 3. 메시지 본문 조립
        text = ""
        
        # [VI 발동]
        if msg_type == "VI":
            status = message_data.get('status')
            price = message_data.get('price')
            rate = message_data.get('rate', '0')
            time = message_data.get('time')
            emoji = "🔴" if status == "발동" else "🔵"
            
            # 이름이 없으면 코드로 표시
            display_name = name if name else f"종목({code})"

            text = (
                f"{emoji} [VI {status}] {time}\n"
                f"종목: {display_name}\n"
                f"현재가: {price}원 ({rate}%)\n"
                f"{news_text}\n"
                f"#VI발동"
            )

        # [조건검색 포착]
        elif msg_type == "CONDITION":
            rate = message_data.get('rate')
            price = message_data.get('price')

            text = (
                f"🔥 [조건포착] {name}\n"
                f"코드: {code}\n"
                f"등락률: {rate}%\n"
                f"현재가: {price}원\n"
                f"{news_text}\n"
                f"#ReasonHunter"
            )

        # [랭킹 리포트] (뉴스는 너무 많아지니 생략)
        elif msg_type == "RANKING":
            time = message_data.get('time')
            data_list = message_data.get('data', [])
            rank_text = "\n".join(data_list)
            text = (
                f"📊 [랭킹 리포트] {time}\n"
                f"{rank_text}\n"
                f"#시장동향"
            )

        # 4. 전송
        if text:
            await bot.send_message(chat_id=settings.TELEGRAM_CHAT_ID, text=text)
            print(f"🚀 [전송완료] {search_keyword if search_keyword else msg_type}")

    except Exception as e:
        print(f"❌ 메시지 전송 실패: {e}")

async def run_worker():
    print(f"👷 [Worker] 뉴스 기자 모드 가동! (To: {settings.TELEGRAM_CHAT_ID})")
    
    bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
    pubsub = redis_client.pubsub()
    await pubsub.subscribe(settings.REDIS_CHANNEL_STOCK)
    
    print("👂 Redis 채널 수신 대기 중...")

    try:
        async for message in pubsub.listen():
            if message['type'] == 'message':
                data_str = message['data']
                if isinstance(data_str, bytes):
                    data_str = data_str.decode('utf-8')
                
                try:
                    data_json = ujson.loads(data_str)
                    await send_telegram_message(bot, data_json)
                except Exception as e:
                    print(f"⚠️ 파싱 에러: {e}")
                    
    except asyncio.CancelledError:
        print("🛑 Worker 종료")
    finally:
        await redis_client.close()

if __name__ == "__main__":
    try:
        asyncio.run(run_worker())
    except KeyboardInterrupt:
        print("\n🛑 시스템 종료")