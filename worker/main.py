import asyncio
import os
import sys
import ujson
import redis.asyncio as redis
from telegram import Bot

# 프로젝트 루트 경로 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + '/..')

from common.config import settings
from worker.modules.news_crawler import NewsCrawler
from worker.modules.news_worker import NewsWorker

raw_ids = settings.TELEGRAM_CHAT_ID.split(',')
RECIPIENT_LIST = [int(x.strip()) for x in raw_ids if x.strip()]
print(f"📤 [Main System] 텔레그램 봇 가동! (Target: {RECIPIENT_LIST})")
# ==============================================================================
# 🤖 1. 텔레그램 봇 로직 (메시지 수신 -> 발송)
# ==============================================================================
async def run_telegram_bot():
    print(f"📡 [Main System] 텔레그램 봇 가동! (Target: {settings.TELEGRAM_CHAT_ID})")
    
    bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
    
    # Redis 연결 (봇 전용)
    r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
    pubsub = r.pubsub()
    
    # 두 개의 채널을 동시에 구독 (속보 + 뉴스분석)
    await pubsub.subscribe(settings.REDIS_CHANNEL_STOCK, "news_alert")
    
    print("👂 [Bot] 'stock_alert' & 'news_alert' 채널 구독 중...")

    try:
        async for message in pubsub.listen():
            if message['type'] == 'message':
                data_str = message['data']
                try:
                    data_json = ujson.loads(data_str)
                    await send_message_to_user(bot, data_json)
                except Exception as e:
                    print(f"⚠️ [Bot] JSON 파싱 에러: {e}")
                    
    except asyncio.CancelledError:
        print("🛑 [Bot] 종료")
    finally:
        await r.aclose()

async def send_message_to_user(bot, message_data):
    """메시지 타입별 텍스트 포맷팅 및 전송"""
    try:
        msg_type = message_data.get("type")
        name = message_data.get('name', '알 수 없음')
        text = ""

        # 1. 속보 (CONDITION)
        if msg_type in ["CONDITION", "CONDITION_US"]:
            price = message_data.get('price', '0')
            rate = message_data.get('rate', '0')
            emoji = "🚀" if float(rate) > 0 else "💧"
            header = f"🇺🇸 [미국 포착]" if msg_type == "CONDITION_US" else f"🔥 [국내 포착]"
            
            text = (
                f"{header} {name}\n"
                f"{emoji} 등락률: {rate}%\n"
                f"💰 현재가: {price}\n"
                f"#속보"
            )

        # 2. AI 분석 (NEWS_SUMMARY)
        elif msg_type == "NEWS_SUMMARY":
            summary = message_data.get('summary', '요약 없음')
            sentiment = message_data.get('sentiment', 'Neutral')
            link = message_data.get('link', '')
            
            sent_emoji = "😐"
            if "Positive" in sentiment or "호재" in sentiment: sent_emoji = "😍 (호재)"
            elif "Negative" in sentiment or "악재" in sentiment: sent_emoji = "😱 (악재)"

            text = (
                f"💡 [AI 분석] {name}\n"
                f"------------------------------\n"
                f"{summary}\n"
                f"------------------------------\n"
                f"📊 판단: {sent_emoji}\n"
                f"🔗 [기사 원문]({link})\n"
                f"#AI요약"
            )
            
        # ==========================================
        # 3. [NEW] 랭킹 리포트 (RANKING) - VI 대체
        # ==========================================
        elif msg_type in ["RANKING", "RANKING_US"]:
            time_str = message_data.get('time', '') # 예: 🇺🇸 23:40
            data_list = message_data.get('data', [])
            
            # 리스트 내용을 줄바꿈으로 합치기
            rank_text = "\n".join(data_list)
            
            # 타이틀 설정
            title = "📊 [주요 시세 브리핑]"
            
            text = (
                f"{title} {time_str}\n"
                f"{rank_text}\n"
                f"#시장동향"
            )

        if text:
            for chat_id in RECIPIENT_LIST:
                try:
                    await bot.send_message(
                        chat_id=chat_id, 
                        text=text,
                        disable_web_page_preview=True
                    )
                    print(f"🚀 [Bot 전송] {name} -> ID: {chat_id} 성공")
                except Exception as e:
                    # 한 명이 차단했거나 오류가 나도, 다른 사람은 받아야 하므로 continue
                    print(f"❌ [전송 실패] ID: {chat_id} | 에러: {e}")

    except Exception as e:
        print(f"❌ [Bot] 전송 실패: {e}")

# ==============================================================================
# 🕵️ 2. 뉴스 워커 로직 (크롤러 실행)
# ==============================================================================
async def run_news_crawler():
    # 이미 news_crawler.py 안에 run() 메소드가 무한 루프로 구현되어 있음
    # crawler = NewsCrawler()
    # await crawler.run()
    worker = NewsWorker()
    await worker.run()

# ==============================================================================
# 🚀 메인 실행기 (통합)
# ==============================================================================
async def main():
    print("🚀 [System] 통합 시스템 시작 (Bot + NewsCrawler)...")
    
    # 두 개의 무한 루프(봇, 크롤러)를 동시에 실행
    await asyncio.gather(
        run_telegram_bot(),
        run_news_crawler()
    )

if __name__ == "__main__":
    try:
        # 윈도우 환경 asyncio 정책 설정
        if sys.platform == 'win32':
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
            
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 시스템 종료")