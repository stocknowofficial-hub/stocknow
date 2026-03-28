import asyncio
import aiohttp
from common.config import settings
from common.logger import setup_logger

logger = setup_logger("PredictionPriceUpdater", "logs/watcher", "watcher.log")

async def run_prediction_price_updater():
    """2시간마다 predictions 현재가 업데이트"""
    logger.info("💹 [PriceUpdater] 예측 가격 업데이트 태스크 시작 (2시간 주기)")

    while True:
        try:
            secret = getattr(settings, 'WHALE_SECRET', '') or ''
            url = f"{getattr(settings, 'FRONTEND_URL', 'https://stock-now.pages.dev')}/api/cron/update-prediction-prices"

            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers={"X-Secret-Key": secret}, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        logger.info(f"💹 [PriceUpdater] 완료: {data}")
                    else:
                        logger.warning(f"⚠️ [PriceUpdater] 실패: HTTP {resp.status}")
        except Exception as e:
            logger.error(f"❌ [PriceUpdater] 오류: {e}")

        await asyncio.sleep(7200)  # 2시간
