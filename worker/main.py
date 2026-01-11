import asyncio
import os
import sys
import ujson
import redis.asyncio as redis
import aiohttp
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# 프로젝트 루트 경로 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + '/..')

from common.config import settings
from common.logger import setup_logger # ✅ Logger Import
from worker.modules.news_worker import NewsWorker

# ✅ Logger Setup
logger = setup_logger("Worker", "logs/worker", "worker.log")

BACKEND_URL = "http://127.0.0.1:8000"

logger.info(f"📤 [Worker System] 초기화 중... (Backend: {BACKEND_URL})")

# ==============================================================================
# 🤖 1. 텔레그램 봇 로직 (수신 + 발송)
# ==============================================================================
async def fetch_recipients():
    """백엔드에서 구독자 목록 가져오기"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{BACKEND_URL}/subscribers") as resp:
                if resp.status == 200:
                    return await resp.json()
    except Exception as e:
        logger.error(f"⚠️ [API] 구독자 조회 실패: {e}")
    return []

async def register_subscriber(chat_id, name, username):
    """구독자 등록 요청"""
    try:
        async with aiohttp.ClientSession() as session:
            payload = {"chat_id": str(chat_id), "name": name, "username": username}
            async with session.post(f"{BACKEND_URL}/subscribers", json=payload) as resp:
                return resp.status == 200
    except Exception:
        return False

# Command Handler: /start
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat_id = update.effective_chat.id
    name = user.full_name or "Unknown"
    
    # ✅ Username 추출 (@붙임)
    username = f"@{user.username}" if user.username else None
    
    success = await register_subscriber(chat_id, name, username)
    if success:
        await update.message.reply_text(f"✅ 환영합니다, {name}님!\nReason Hunter 구독이 시작되었습니다. 🚀\n이제 실시간 AI 분석 알림을 받으실 수 있습니다.")
        logger.info(f"👤 [New User] {name} ({chat_id}) 등록 완료")
    else:
        await update.message.reply_text("⚠️ 구독 등록 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.")

async def run_telegram_bot(app):
    """Redis 리스너 (봇 기능과 병행 실행)"""
    logger.info(f"📡 [Bot] Redis 리스너 가동...")
    
    r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
    pubsub = r.pubsub()
    await pubsub.subscribe("news_alert")
    
    try:
        async for message in pubsub.listen():
            if message['type'] == 'message':
                try:
                    data_json = ujson.loads(message['data'])
                    await send_message_to_user(app.bot, data_json)
                except Exception as e:
                    logger.error(f"⚠️ [Bot] 메시지 처리 에러: {e}")
    except asyncio.CancelledError:
        logger.info("🛑 [Redis Listener] 종료")
    finally:
        await r.aclose()

async def send_message_to_user(bot, message_data):
    """동적 구독자에게 메시지 전송"""
    try:
        # 1. 구독자 목록 최신화 (매번 조회 or 캐싱 가능)
        recipient_list = await fetch_recipients()
        if not recipient_list:
            # 백엔드 죽었을 때 대비용 하드코딩 (옵션)
            raw_ids = settings.TELEGRAM_CHAT_ID.split(',')
            recipient_list = [x.strip() for x in raw_ids if x.strip()]
            
        msg_type = message_data.get("type")
        name = message_data.get('name', '알 수 없음')
        text = ""

        # ... (기존 포맷팅 로직 유지: 생략된 부분은 위와 동일하다고 가정하고, 핵심만 교체) ...
        # (⚠ NOTE: 위쪽 로직이 너무 길어서 diff block 안에서 그대로 재사용해야 함. 
        #  replace_file_content는 전체 교체가 아니므로 주의. 
        #  하지만 여기서는 구조가 많이 바뀌어서 전체를 덮어쓰거나 MultiReplace를 써야 안전함.
        #  기존 send_message_to_user 내부 로직은 살려야 함.)
        
        # (전략: 기존 포맷팅 로직 복사)
        if msg_type in ["CONDITION", "CONDITION_US"]:
            price = message_data.get('price', '0')
            rate = message_data.get('rate', '0')
            emoji = "🚀" if float(rate) > 0 else "💧"
            header = f"🇺🇸 [미국 포착]" if msg_type == "CONDITION_US" else f"🔥 [국내 포착]"
            text = f"{header} {name}\n{emoji} 등락률: {rate}%\n💰 현재가: {price}\n#속보"

        elif msg_type == "NEWS_SUMMARY":
            summary = message_data.get('summary', '')
            sentiment = message_data.get('sentiment', 'Neutral')
            link = message_data.get('link', '')
            
            if "브리핑" in name:
                text = f"{name}\n------------------------------\n{summary}\n------------------------------\n🔗 [전체 현황판 보기]({link})\n"
            else:
                sent_emoji = "😐"
                if "Positive" in sentiment or "호재" in sentiment: sent_emoji = "😍 (호재)"
                elif "Negative" in sentiment or "악재" in sentiment: sent_emoji = "😱 (악재)"
                
                price = message_data.get('price')
                rate = message_data.get('rate')
                market_info = ""
                if price and rate:
                    rate_emoji = "🚀" if float(rate) > 0 else "💧"
                    market_info = f"{rate_emoji} 등락률: {rate}% | 💰 현재가: {price}\n------------------------------\n"
                
                judgment_line = f"📊 판단: {sent_emoji}\n" if sentiment != "Neutral" else ""
                
                # Link Label Customization
                link_label = "관련 뉴스"
                if "pdf" in link.lower() or "📑" in name:
                    link_label = "Original Report"

                if sentiment == "Unknown" or not summary:
                    text = f"🚨 [수급 포착] {name}\n------------------------------\n{market_info}⚠️ 특이사항 없음 (최근 24시간 내 관련 뉴스 부재)\n------------------------------\n🔗 [직접 검색 확인]({link})\n"
                else:
                    text = f"💡 [AI 심층분석] {name}\n------------------------------\n{market_info}{summary}\n------------------------------\n{judgment_line}🔗 [{link_label}]({link})\n"

        elif msg_type == "SNS_SUMMARY":
            # 트럼프 분석 전용 포맷
            summary = message_data.get('summary', '')
            link = message_data.get('link', '')
            # 제목 이미 "🏛️ [트럼프 긴급 포착]" 등으로 설정되어 옴
            text = f"{name}\n------------------------------\n{summary}\n------------------------------\n🔗 [원문 보기]({link})\n"

        elif msg_type == "MARKET_BRIEFING":
            return 

        # 전송 로직
        if text:
            should_pin = message_data.get('should_pin', False)
            for chat_id in recipient_list:
                try:
                    sent_msg = await bot.send_message(chat_id=chat_id, text=text, disable_web_page_preview=True)
                    if should_pin:
                        try:
                            await bot.pin_chat_message(chat_id, sent_msg.message_id)
                        except: pass
                except Exception: pass
            logger.info(f"🚀 [Bot] 전송 완료: {name} (To {len(recipient_list)} users)")

    except Exception as e:
        logger.error(f"❌ [Bot] 포맷팅 에러: {e}")

# ==============================================================================
# 🚀 메인 실행기 (Application 방식)
# ==============================================================================
async def main():
    logger.info("🚀 [Worker System] 통합 가동 시작...")
    
    # 1. Telegram App 초기화 (네트워크 타임아웃 보강)
    # httpx.ReadError 방지를 위해 타임아웃을 넉넉하게 설정
    app = (
        ApplicationBuilder()
        .token(settings.TELEGRAM_BOT_TOKEN)
        .read_timeout(60)
        .write_timeout(60)
        .connect_timeout(60)
        .pool_timeout(60)
        .get_updates_read_timeout(60) # Polling 타임아웃
        .connection_pool_size(16) # Pool Size 증가
        .build()
    )
    app.add_handler(CommandHandler("start", start_command))
    
    await app.initialize()
    await app.start()
    
    # Polling 시작 
    # bootstrap_retries=-1 : 무제한 재시도 (네트워크 끊겨도 안 죽게)
    # read_timeout과 get_updates_read_timeout을 맞추는 게 좋음
    await app.updater.start_polling(
        allowed_updates=Update.ALL_TYPES,
        poll_interval=2.0, # 2초 간격 (부하 감소)
        bootstrap_retries=-1
    )
    
    logger.info("🤖 [Bot] Polling Started...")

    # 2. Redis 리스너 & 뉴스 워커 병렬 실행
    # (Note: updater.start_polling() doesn't block forever, it starts a task)
    
    worker = NewsWorker()
    
    # Run forever
    await asyncio.gather(
        run_telegram_bot(app), # Redis Listener
        worker.run()           # News Worker
        # Polling is already running via updater
    )
    
    # Cleanup
    await app.updater.stop()
    await app.shutdown()

if __name__ == "__main__":
    try:
        if sys.platform.startswith("win"):
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("🛑 시스템 종료")
    except Exception as e:
        logger.error(f"⚠️ [Main Error] {e}")