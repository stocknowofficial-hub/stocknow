import asyncio
import os
import sys
import ujson
import redis.asyncio as redis
import aiohttp
from datetime import datetime, timedelta # ✅ Added for Expiry Check
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# 프로젝트 루트 경로 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + '/..')

from common.config import settings
from common.logger import setup_logger # ✅ Logger Import
from worker.modules.news_worker import NewsWorker

# ✅ Logger Setup
logger = setup_logger("Worker", "logs/worker", "worker.log")

BACKEND_URL = settings.BACKEND_URL

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

async def register_subscriber(chat_id, name, username, referrer_id=None):
    """구독자 등록 요청"""
    try:
        async with aiohttp.ClientSession() as session:
            payload = {
                "chat_id": str(chat_id), 
                "name": name, 
                "username": username,
                "referrer_id": referrer_id # ✅ Pass Referrer
            }
            async with session.post(f"{BACKEND_URL}/subscribers", json=payload) as resp:
                return resp.status == 200
    except Exception:
        return False

async def backend_update_subscriber(chat_id, payload):
    """구독자 정보 업데이트 (Backend PUT)"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.put(f"{BACKEND_URL}/subscribers/{chat_id}", json=payload) as resp:
                return resp.status == 200
    except Exception as e:
        logger.error(f"⚠️ [API] Update 실패: {e}")
        return False

# Command Handler: /start
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat_id = update.effective_chat.id
    name = user.full_name or "Unknown"
    
    # ✅ Username 추출 (@붙임)
    username = f"@{user.username}" if user.username else None
    
    # ✅ [Referral] 추천인 코드 파싱 (start ref_12345)
    # ✅ [Referral] 추천인 코드 파싱 (start ref_12345)
    referrer_id = None
    if context.args and context.args[0].startswith("ref_"):
        try:
            ref_code = context.args[0].replace("ref_", "")
            # 자기 자신 추천 방지
            if ref_code != str(chat_id):
                referrer_id = ref_code
                logger.info(f"🔗 [Referral] {name} invited by {referrer_id}")
        except: pass

    # ✅ [Advanced Payment] 시크릿 링크 처리 (req_1m_SECRET...)
    # t.me/bot?start=req_1m_SECRET123
    secret_plan = None
    if context.args and context.args[0].startswith("req_"):
        arg = context.args[0]
        # Common Config에서 시크릿 키 검증
        for plan, secret in settings.PAYMENT_SECRETS.items():
            # arg format: {plan}_{secret} (e.g. req_1m_SECRET123)
            expected_arg = f"{plan}_{secret}"
            if arg == expected_arg:
                secret_plan = plan
                break
    
    if secret_plan:
        # 1. 만료일 계산
        now = datetime.now()
        if secret_plan == "req_1m":
            days = 33 # 1개월 + 3일 여유
            plan_name = "1개월권"
        elif secret_plan == "req_6m":
            days = 186 # 6개월 (3+3 이벤트) + 6일 여유
            plan_name = "6개월권 (3+3 이벤트)"
        elif secret_plan == "req_1y":
            days = 368 # 1년 + 3일 여유
            plan_name = "1년권"
        else:
            days = 14 # Default
            plan_name = "체험권"

        new_expiry = now + timedelta(days=days)
        
        # 2. Backend Update (Register if new, Update if exists)
        # 먼저 등록 시도 (신규일 수 있으므로)
        await register_subscriber(chat_id, name, username, referrer_id)
        
        # 그리고 만료일 업데이트 (강제 덮어쓰기)
        payload = {
            "tier": "PRO",
            "is_active": True,
            "expiry_date": new_expiry.isoformat()
        }
        if await backend_update_subscriber(chat_id, payload):
            success_msg = (
                f"🎉 **{plan_name} 인증 성공!**\n\n"
                f"✅ 만료일이 **{new_expiry.strftime('%Y-%m-%d')}**까지 연장되었습니다.\n"
                f"VIP 채널에서 최고의 정보를 받아보세요!"
            )
            await update.message.reply_text(success_msg)
            
            # 3. Admin Notification (To Maintainer)
            logger.info(f"💰 [Payment] {name} activated {plan_name}")
            try:
                if settings.TELEGRAM_CHAT_ID:
                    admin_msg = f"💰 **[매출 알림]**\n{name} ({chat_id}) 님이 **{plan_name}**을 활성화했습니다!\n(만료일: {new_expiry.strftime('%Y-%m-%d')})"
                    await context.bot.send_message(chat_id=settings.TELEGRAM_CHAT_ID, text=admin_msg)
            except: pass
            
            # VIP 채널 링크 발송
            try:
                invite = await context.bot.create_chat_invite_link(settings.TELEGRAM_VIP_CHANNEL_ID, member_limit=1)
                await update.message.reply_text(f"👉 [VIP 채널 입장]\n{invite.invite_link}")
            except: pass
            
            return # 종료 (Start 로직 건너뜀)
        else:
            await update.message.reply_text("⚠️ 처리 중 오류가 발생했습니다. 관리자에게 문의해주세요.")
            return

    success = await register_subscriber(chat_id, name, username, referrer_id)
    if success:
        # 🎁 VIP 채널 초대 링크 생성 (1회용)
        try:
            invite_link = await context.bot.create_chat_invite_link(
                chat_id=settings.TELEGRAM_VIP_CHANNEL_ID, 
                member_limit=1,
                expire_date=None # 유효기간 없음 (들어올 때까지) or datetime.now() + 1 hour
            )
            link_url = invite_link.invite_link
        except Exception as e:
            logger.error(f"⚠️ 초대 링크 생성 실패: {e}")
            link_url = "https://t.me/+..." # Fallback (혹은 관리자 문의)

        msg = (
            f"🎉 환영합니다, {name}님!\n\n"
            f"Stock Now VIP(Pro) 2주 무료 체험이 시작되었습니다.\n"
            f"지금 바로 입장해서 실시간AI 분석 정보를 받아보세요!\n\n"
            f"유명한 증시 주간 리포트, 트럼프 SNS 분석, 일일 브리핑 등 수많은 정보 제공!\n\n"
            f"👉 [VIP 채널 입장하기]\n{link_url}\n\n"
            f" 주의: 알림을 계속 받으려면 이 봇을 차단하지 마세요!"
        )
        await update.message.reply_text(msg)
        logger.info(f"👤 [New User] {name} ({chat_id}) 등록 완료 & 초대장 발송")
        
        # Admin Notification (신규 가입)
        try:
            if settings.TELEGRAM_CHAT_ID:
                admin_msg = f"👤 **[신규 유저]**\n{name} ({chat_id}) 님이 무료 체험을 시작했습니다!"
                await context.bot.send_message(chat_id=settings.TELEGRAM_CHAT_ID, text=admin_msg)
        except: pass
    else:
        await update.message.reply_text("⚠️ 구독 등록 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.")

async def run_telegram_bot(app, shutdown_event=None):
    """Redis 리스너 (봇 기능과 병행 실행) - Manual Polling"""
    logger.info(f"📡 [Bot] Redis 리스너 가동...")
    
    r = redis.Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=0, decode_responses=True)
    
    try:
        # ✅ Use Async Context Manager for automatic cleanup
        async with r.pubsub() as pubsub:
            await pubsub.subscribe("news_alert")
            
            # ✅ Manual Polling (No GeneratorExit)
            while True:
                if shutdown_event and shutdown_event.is_set():
                    break
                    
                message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                if message:
                    if message['type'] == 'message':
                        try:
                            data_json = ujson.loads(message['data'])
                            await broadcast_message(app.bot, data_json)
                        except Exception as e:
                            logger.error(f"⚠️ [Bot] 메시지 처리 에러: {e}")
                
                await asyncio.sleep(0.01)

    except asyncio.CancelledError:
        logger.info("🛑 [Redis Listener] 종료")
    finally:
        await r.aclose()

async def broadcast_message(bot, message_data):
    """채널 브로드캐스팅 (Pro -> All, Free -> Partial)"""
    try:
        # 1. 구독자 조회 로직 제거 (채널 전송으로 변경)
            
        msg_type = message_data.get("type")
        name = message_data.get('name', '알 수 없음')
        text = ""

        # ... (기존 포맷팅 로직 유지: 생략된 부분은 위와 동일하다고 가정하고, 핵심만 교체) ...
        # (⚠ NOTE: 위쪽 로직이 너무 길어서 diff block 안에서 그대로 재사용해야 함. 
        #  replace_file_content는 전체 교체가 아니므로 주의. 
        #  하지만 여기서는 구조가 많이 바뀌어서 전체를 덮어쓰거나 MultiReplace를 써야 안전함.
        #  기존 send_message_to_user 내부 로직은 살려야 함.)
        
        # (전략: 기존 포맷팅 로직 복사)
        # --------------------------------------------------------------------------
        # 1. 텍스트 생성 (VIP vs Free)
        # --------------------------------------------------------------------------
        text_vip = ""
        text_free = ""
        
        upgrade_link = "\n👉 **[AI 분석 정보 받기]**\nhttps://t.me/Stock_Now_Bot?start=subscribe"

        if msg_type in ["CONDITION", "CONDITION_US"]:
            price = message_data.get('price', '0')
            rate = message_data.get('rate', '0')
            emoji = "🚀" if float(rate) > 0 else "💧"
            header = f"🇺🇸 [미국 포착]" if msg_type == "CONDITION_US" else f"🔥 [국내 포착]"
            
            # VIP: Full Text
            text_vip = f"{header} {name}\n{emoji} 등락률: {rate}%\n💰 현재가: {price}\n#속보"
            # Free: Same for simple alerts (or add teaser if analysis exists? Condition usually has no analysis)
            text_free = text_vip # Condition alerts are simple enough to share? Or hide price? User didn't specify for Condition.
            # User example was for "AI Analysis". Condition alerts might be separate.
            # But let's keep them same for now unless specified.
            
        elif msg_type == "NEWS_SUMMARY":
            summary = message_data.get('summary', '')
            sentiment = message_data.get('sentiment', 'Neutral')
            link = message_data.get('link', '')

            if "브리핑" in name:
                text_vip = f"{name}\n------------------------------\n{summary}\n------------------------------\n🔗 [전체 현황판 보기]({link})\n"
                text_free = text_vip # ✅ 브리핑은 Free 채널에도 전체 공개 (User Request) 
            else:
                sent_emoji = "😐"
                if "Positive" in sentiment or "호재" in sentiment: sent_emoji = "😍 (호재)"
                elif "Negative" in sentiment or "악재" in sentiment: sent_emoji = "😱 (악재)"
                
                price = message_data.get('price')
                rate = message_data.get('rate')
                market_info = ""
                if price and rate:
                    rate_emoji = "🚀" if float(rate) > 0 else "💧"
                    market_info = f"{rate_emoji} 등락률: {rate}% | 💰 현재가: {price}\n"
                
                judgment_line = f"📊 판단: {sent_emoji}\n" if sentiment != "Neutral" else ""
                link_label = "관련 뉴스"
                if "pdf" in link.lower() or "📑" in name: link_label = "Original Report"

                if sentiment == "Unknown" or not summary:
                    text_vip = f"🚨 [수급 포착] {name}\n------------------------------\n{market_info}------------------------------\n⚠️ 특이사항 없음\n🔗 [직접 검색 확인]({link})\n"
                    text_free = text_vip 
                else:
                    # VIP: Full Analysis
                    text_vip = f"💡 [AI 심층분석] {name}\n------------------------------\n{market_info}------------------------------\n{summary}\n------------------------------\n{judgment_line}🔗 [{link_label}]({link})\n"
                    
                    # Free Channel Logic
                    if "pdf" in link.lower() or "리포트" in name or "Report" in name:
                        # 📑 리포트 Teaser: 첫 번째 문단만 추출
                        # summary의 첫 줄(제목 등) + 첫 문단 정도?
                        # 안전하게 줄바꿈 2번 기준으로 자름
                        teaser_text = summary.split('\n\n')[0] 
                        if len(teaser_text) < 50: # 너무 짧으면 하나 더
                            parts = summary.split('\n\n')
                            if len(parts) > 1: teaser_text += "\n\n" + parts[1]
                        
                        upgrade_btn = "👉 [유망 종목 정보 받기]" if "Kiwoom" in name else "👉 [유망 종목 정보 받기]" # User requested specific button text? "유망 종목 정보 받기"

                        text_free = f"💡 [AI 심층분석] {name}\n------------------------------\n{teaser_text}\n...\n------------------------------\n🔗 [{link_label}]({link})\n\n{upgrade_btn}\nhttps://t.me/Stock_Now_Bot?start=upgrade"
                    else:
                        # 일반 종목 분석 Teaser: 내용 숨김
                        text_free = f"💡 [AI 심층분석] {name}\n------------------------------\n{market_info}{upgrade_link}\n"

        elif msg_type == "SNS_SUMMARY":
            summary = message_data.get('summary', '')
            link = message_data.get('link', '')
            
            # VIP: Full
            text_vip = f"{name}\n------------------------------\n{summary}\n------------------------------\n🔗 [원문 보기]({link})\n"
            
            # Free: Teaser (Hide Summary)
            text_free = f"{name}\n------------------------------\n🔒 (AI 분석 내용은 Premium 전용)\n------------------------------\n🔗 [원문 보기]({link})\n{upgrade_link}"

        # --------------------------------------------------------------------------
        # 2. 전송 로직 (Dual Channel)
        # --------------------------------------------------------------------------
        
        # 1) VIP Channel
        if text_vip:
            try:
                msg = await bot.send_message(
                    chat_id=settings.TELEGRAM_VIP_CHANNEL_ID, 
                    text=text_vip, 
                    disable_web_page_preview=True
                )
                if message_data.get('should_pin', False):
                    try: await bot.pin_chat_message(settings.TELEGRAM_VIP_CHANNEL_ID, msg.message_id) 
                    except: pass
                logger.info(f"🚀 [Broadcast] VIP 전송 완료: {name}")
            except Exception as e:
                logger.error(f"❌ VIP 전송 실패: {e}")

        # 2) Free Channel
        if text_free:
            try:
                await bot.send_message(
                    chat_id=settings.TELEGRAM_FREE_CHANNEL_ID, 
                    text=text_free, 
                    disable_web_page_preview=True
                )
                logger.info(f"🚀 [Broadcast] Free 전송 완료: {name}")
            except Exception as e:
                logger.error(f"❌ Free 전송 실패: {e}")

    except Exception as e:
        logger.error(f"❌ [Bot] 포맷팅 에러: {e}")

async def run_expiry_checker(bot):

    """(Scheduler) 매일 유료 기간 만료자를 확인하고 강퇴"""
    while True:
        logger.info("📅 [Scheduler] Daily Expiry Check Started...")
        try:
            # 1. Fetch All Users from Backend
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{BACKEND_URL}/subscribers/detail") as resp:
                    if resp.status == 200:
                        users = await resp.json()
                        for u in users:
                            # Check PRO/VIP & Expiry
                            if u.get('tier') in ['PRO', 'VIP'] and u.get('expiry_date'):
                                expiry_str = u['expiry_date'] 
                                # Backend returns ISO format (e.g. 2026-01-25T...)
                                expiry_dt = datetime.fromisoformat(expiry_str)
                                
                                if expiry_dt < datetime.now():
                                    chat_id = u['chat_id']
                                    name = u.get('name', 'User')
                                    logger.info(f"⏳ [Expiry] 체험 만료 감지: {name} ({chat_id})")
                                    
                                    # Action 1: Kick (Ban & Unban)
                                    try:
                                        # VIP 채널에서 추방 (Ban)
                                        await bot.ban_chat_member(chat_id=settings.TELEGRAM_VIP_CHANNEL_ID, user_id=chat_id)
                                        # 다시 들어올 수 있게 즉시 Unban
                                        await bot.unban_chat_member(chat_id=settings.TELEGRAM_VIP_CHANNEL_ID, user_id=chat_id)
                                        logger.info(f"👢 [Kick] 만료된 사용자 추방 완료: {name}")
                                    except Exception as e:
                                        logger.error(f"⚠️ [Kick Failed] 추방 실패 ({name}): {e}")

                                    # Action 2: Notification Message
                                    try:
                                        # Google Form Link Generation (Auto-fill Name)
                                        import urllib.parse
                                        # 텔레그램 이름이 없으면 '사용자'로 대체
                                        safe_name = sub.name if sub.name else "사용자"
                                        encoded_name = urllib.parse.quote(safe_name)
                                        
                                        # 구글 폼 링크 (이름 자동 입력)
                                        voc_link = f"https://docs.google.com/forms/d/e/1FAIpQLSe4ICn7DbfNeeYLU9_NuMrFH7VBLjrOp62MVPiEubvE7Jslkw/viewform?usp=pp_url&entry.485428648={encoded_name}"
                                        postype_url = "https://www.postype.com/@stock-now/post/21361212"

                                        msg = (
                                            f"😭 **{safe_name}님, 구독 기간이 만료되었습니다.**\n"
                                            f"({expiry_str.split('T')[0]} 만료)\n\n"
                                            f"더 이상 VIP 채널의 실시간 정보를 받아보실 수 없습니다.\n"
                                            f"계속해서 최고의 투자 정보를 받아보시려면 멤버십을 연장해주세요!\n\n"
                                            f"👉 **[멤버십 연장하러 가기]**\n"
                                            f"{postype_url}\n\n"
                                            f"📢 **[서비스 의견/불편 신고]**\n"
                                            f"혹시 오류이거나 건의사항이 있으신가요?\n"
                                            f"아래 링크를 통해 의견을 남겨주세요! (이름 자동입력)\n"
                                            f"{voc_link}"
                                        )
                                        await bot.send_message(chat_id=chat_id, text=msg)
                                        logger.info(f"📉 [Expiry] 만료 알림 & VoC 링크 발송: {safe_name}")
                                        
                                        # Admin Notification (만료/강퇴)
                                        try:
                                            if settings.TELEGRAM_CHAT_ID:
                                                admin_msg = f"📉 **[만료 알림]**\n{safe_name} ({chat_id}) 님의 구독이 만료되었습니다.\n(강퇴 및 알림 발송 완료)"
                                                await bot.send_message(chat_id=settings.TELEGRAM_CHAT_ID, text=admin_msg)
                                        except: pass
                                    except: pass

                                    # Action 3: Mark Tier as 'FREE' & Inactive (Loop Kick 방지)
                                    try:
                                        # backend_update_subscriber 함수 재사용
                                        payload = {"tier": "FREE", "is_active": False}
                                        await backend_update_subscriber(chat_id, payload)
                                        logger.info(f"🔄 [Update] 사용자 등급 변경 완료 (PRO -> FREE): {name}")
                                    except Exception as e:
                                        logger.error(f"⚠️ [Update Failed] 등급 변경 실패: {e}")
                                        
        except Exception as e:
            logger.error(f"⚠️ [Scheduler] 에러 발생: {e}")
        
        # 24시간 대기
        await asyncio.sleep(3600 * 24)

# ==============================================================================
# 🔄 [Self-Healing] 정기 재기동 스케줄러 (오전 7시 / 오후 7시)
# ==============================================================================
# ==============================================================================
# 🔄 [Self-Healing] 정기 재기동 스케줄러 (오전 7시 / 오후 7시)
# ==============================================================================
async def run_scheduled_restarter():
    """
    매일 07:00, 19:00에 프로세스를 종료합니다.
    """
    import random
    import signal
    
    logger.info("📅 [Restarter] 정기 재기동 스케줄러 가동 (Target: 07:00, 19:00 KST)")
    
    while True:
        now = datetime.now()
        hour = now.hour
        minute = now.minute
        
        # 07:00 ~ 07:05 or 19:00 ~ 19:05
        if (hour == 7 or hour == 19) and minute < 5:
            wait_sec = random.randint(1, 60)
            logger.warning(f"🛑 [Self-Destruct] 정기 점검 시간입니다. {wait_sec}초 후 프로세스를 종료합니다...")
            await asyncio.sleep(wait_sec)
            
            logger.warning("💣 [Goodbye] 시스템 종료 신호 발송 (SIGTERM)...")
            # ✅ self-termination via SIGTERM to trigger graceful shutdown
            os.kill(os.getpid(), signal.SIGTERM)
            return
            
        await asyncio.sleep(60)

# ==============================================================================
# 🚀 메인 실행기 (Application 방식)
# ==============================================================================
async def main():
    import signal
    
    logger.info("🚀 [Worker System] 통합 가동 시작...")
    
    # 🎯 Shutdown Event for Graceful Exit
    shutdown_event = asyncio.Event()

    def signal_handler():
        logger.info("🛑 [Signal] 종료 신호 수신! 정리 작업을 시작합니다...")
        shutdown_event.set()

    # Register Signal Handlers (SIGINT, SIGTERM)
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, signal_handler)

    # 1. Telegram App 초기화
    app = (
        ApplicationBuilder()
        .token(settings.TELEGRAM_BOT_TOKEN)
        .read_timeout(60)
        .write_timeout(60)
        .connect_timeout(60)
        .pool_timeout(60)
        .get_updates_read_timeout(60)
        .connection_pool_size(16)
        .build()
    )
    app.add_handler(CommandHandler("start", start_command))
    
    await app.initialize()
    await app.start()
    
    await app.updater.start_polling(
        allowed_updates=Update.ALL_TYPES,
        poll_interval=2.0,
        bootstrap_retries=-1
    )
    
    logger.info("🤖 [Bot] Polling Started...")

    # 2. Redis 리스너 & 뉴스 워커 병렬 실행
    worker = NewsWorker()
    asyncio.create_task(run_telegram_bot(app, shutdown_event))
    asyncio.create_task(worker.run(shutdown_event))
    asyncio.create_task(run_expiry_checker(app.bot))
    asyncio.create_task(run_scheduled_restarter())

    # 3. Wait for Shutdown Signal
    logger.info("🛡️ [System] 메인 루프 대기 중 (Press Ctrl+C to stop)...")
    await shutdown_event.wait()
    
    # ==========================================================================
    # 🛑 GRACEFUL SHUTDOWN LOGIC
    # ==========================================================================
    logger.info("🛑 [Shutdown] Cleaning up tasks...")
    
    # 1. Cancel all running tasks FIRST
    tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
    [task.cancel() for task in tasks]
    
    logger.info(f"🛑 [Shutdown] Cancelling {len(tasks)} pending tasks...")
    await asyncio.gather(*tasks, return_exceptions=True)
    
    # 2. Stop Telegram Updater
    try:
        if app.updater.running:
            await app.updater.stop()
        await app.shutdown()
    except Exception as e:
        logger.error(f"⚠️ [Shutdown Error] Bot shutdown: {e}")
        
    logger.info("👋 [Shutdown] All tasks cleanup done. Bye!")

if __name__ == "__main__":
    try:
        if sys.platform.startswith("win"):
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("🛑 시스템 종료")
    except Exception as e:
        logger.error(f"⚠️ [Main Error] {e}")