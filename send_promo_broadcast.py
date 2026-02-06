import asyncio
import os
import aiohttp
from telegram.ext import ApplicationBuilder
from common.config import settings
from common.logger import setup_logger

# Logger setup
logger = setup_logger("Broadcast", "logs/worker", "broadcast.log")

# Backend URL (Internal Docker Network)
BACKEND_URL = settings.BACKEND_URL or "http://backend:8000"

async def fetch_subscribers():
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{BACKEND_URL}/subscribers") as resp:
            if resp.status == 200:
                return await resp.json()
    return []

async def send_broadcast():
    print("🚀 Starting Broadcast...")
    
    # 1. Initialize Bot
    app = ApplicationBuilder().token(settings.TELEGRAM_BOT_TOKEN).build()
    await app.initialize()
    
    # Get Bot Username dynamically
    bot_info = await app.bot.get_me()
    bot_username = bot_info.username
    print(f"🤖 Bot: @{bot_username}")

    # 2. Get Users
    users = await fetch_subscribers()
    print(f"👥 Target Users: {len(users)}명")
    
    # 3. Send Message
    success_count = 0
    fail_count = 0
    
    for chat_id in users:
        try:
            ref_link = f"https://t.me/{bot_username}?start=ref_{chat_id}"
            
            msg = (
                f"🎁 [친구 추천 이벤트] 무료 체험 연장 혜택\n\n"
                f"지인에게 아래 링크를 공유하고 추천하면, 2주가 추가 연장되어 최대 2달(8주)까지 무료 체험 기간을 늘릴 수 있습니다!\n"
                f"(친구가 가입 완료 시 즉시 적용됩니다)\n\n"
                f"👇 나의 추천 링크 (복사해서 공유하세요)\n"
                f"{ref_link}"
            )
            
            await app.bot.send_message(chat_id=chat_id, text=msg)
            print(f"✅ Sent to {chat_id}")
            success_count += 1
            await asyncio.sleep(0.5) # Rate Limit
            
        except Exception as e:
            print(f"❌ Failed to {chat_id}: {e}")
            fail_count += 1
            
    print(f"\n📊 Result: Success {success_count}, Fail {fail_count}")

if __name__ == "__main__":
    asyncio.run(send_broadcast())
