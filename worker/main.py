import asyncio
import os
import sys
import ujson
import redis.asyncio as redis
from telegram import Bot

# 프로젝트 루트 경로 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + '/..')

from common.config import settings
from worker.modules.news_worker import NewsWorker

# 텔레그램 타겟 ID 파싱
raw_ids = settings.TELEGRAM_CHAT_ID.split(',')
RECIPIENT_LIST = [int(x.strip()) for x in raw_ids if x.strip()]

print(f"📤 [Worker System] 초기화 중... (Target: {len(RECIPIENT_LIST)}명)")

# ==============================================================================
# 🤖 1. 텔레그램 봇 로직 (메시지 수신 -> 발송)
# ==============================================================================
async def run_telegram_bot():
    print(f"📡 [Bot] 가동! Redis 구독 시작...")
    
    bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
    r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
    pubsub = r.pubsub()
    
    # 두 채널 구독 (stock_alert: 속보, news_alert: 브리핑/분석결과)
    # stock_channel = getattr(settings, 'REDIS_CHANNEL_STOCK', 'stock_alert')
    # await pubsub.subscribe(stock_channel, "news_alert")
    
    # ✅ [변경] 속보(stock_alert)는 봇이 직접 듣지 않음. (AI 거친 것만 수신)
    await pubsub.subscribe("news_alert")
    
    try:
        async for message in pubsub.listen():
            if message['type'] == 'message':
                try:
                    data_json = ujson.loads(message['data'])
                    await send_message_to_user(bot, data_json)
                except Exception as e:
                    print(f"⚠️ [Bot] 메시지 처리 에러: {e}")
                    
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

        # -----------------------------------------------------
        # 1. 속보 (CONDITION) - Watcher가 직접 보낸 급등 알림
        # -----------------------------------------------------
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

        # -----------------------------------------------------
        # 2. 뉴스/브리핑 (NEWS_SUMMARY) - Watcher 브리핑 or Gemini 분석
        # -----------------------------------------------------
        elif msg_type == "NEWS_SUMMARY":
            summary = message_data.get('summary', '')
            sentiment = message_data.get('sentiment', 'Neutral')
            link = message_data.get('link', '')
            
            # [A] 단순 브리핑 (Watcher가 보낸 것)
            # "브리핑"이라는 단어가 제목에 포함되면 무조건 단순 포맷
            if "브리핑" in name:
                text = (
                    f"{name}\n"
                    f"------------------------------\n"
                    f"{summary}\n"
                    f"------------------------------\n"
                    f"🔗 [전체 현황판 보기]({link})\n" 
                )
            
            # [B] AI 심층 분석 (Gemini가 보낸 것)
            else:
                sent_emoji = "😐"
                if "Positive" in sentiment or "호재" in sentiment: sent_emoji = "😍 (호재)"
                elif "Negative" in sentiment or "악재" in sentiment: sent_emoji = "😱 (악재)"
                
                # NewsWorker가 넘겨준 Price/Rate가 있다면 표시
                price = message_data.get('price')
                rate = message_data.get('rate')
                market_info = ""
                
                if price and rate:
                    rate_emoji = "🚀" if float(rate) > 0 else "💧"
                    market_info = f"{rate_emoji} 등락률: {rate}% | 💰 현재가: {price}\n------------------------------\n"

                judgment_line = f"📊 판단: {sent_emoji}\n" if sentiment != "Neutral" else ""

                if sentiment == "Unknown" or not summary:
                    # ⚠️ [뉴스 없음] 수급 포착 알림만 전송
                    text = (
                        f"🚨 [수급 포착] {name}\n"
                        f"------------------------------\n"
                        f"{market_info}"
                        f"⚠️ 특이사항 없음 (최근 24시간 내 관련 뉴스 부재)\n"
                        f"------------------------------\n"
                        f"🔗 [직접 검색 확인]({link})\n" 
                    )
                else:
                    # 💡 [정상 분석]
                    judgment_line = f"📊 판단: {sent_emoji}\n" if sentiment != "Neutral" else ""
                    text = (
                        f"💡 [AI 심층분석] {name}\n"
                        f"------------------------------\n"
                        f"{market_info}"
                        f"{summary}\n"
                        f"------------------------------\n"
                        f"{judgment_line}"
                        f"🔗 [관련 뉴스]({link})\n" 
                    )

        # -----------------------------------------------------
        # 3. 내부 신호 (MARKET_BRIEFING) - 봇은 무시해야 함
        # -----------------------------------------------------
        elif msg_type == "MARKET_BRIEFING":
            # 이건 Worker가 처리할 메시지이지, 사용자한테 보낼 메시지가 아님
            return 

        # 전송 로직
        if text:
            should_pin = message_data.get('should_pin', False)

            for chat_id in RECIPIENT_LIST:
                try:
                    sent_msg = await bot.send_message(
                        chat_id=chat_id, 
                        text=text,
                        disable_web_page_preview=True 
                    )
                    
                    # 📌 [Pinning] 중요 메시지 고정
                    if should_pin:
                        try:
                            await bot.pin_chat_message(chat_id, sent_msg.message_id)
                            print(f"📌 [Bot] 메시지 고정 완료 (Chat: {chat_id})")
                        except Exception as e:
                            print(f"⚠️ [Bot] 고정 실패: {e}")

                except Exception: pass # 전송 실패는 조용히 넘김 (로그 생략)
            
            # 전송 성공 로그 (한 번만 출력)
            print(f"🚀 [Bot] 전송 완료: {name}")

    except Exception as e:
        print(f"❌ [Bot] 포맷팅 에러: {e}")

# ==============================================================================
# 🕵️ 2. 뉴스 워커 로직
# ==============================================================================
async def run_news_worker():
    worker = NewsWorker()
    await worker.run()

# ==============================================================================
# 🚀 메인 실행기
# ==============================================================================
async def main():
    print("🚀 [Worker System] 통합 가동 시작...")
    await asyncio.gather(
        run_telegram_bot(),
        run_news_worker()
    )

if __name__ == "__main__":
    try:
        if sys.platform == 'win32':
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 시스템 종료")