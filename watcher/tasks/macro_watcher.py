import asyncio
import aiohttp
import requests
from common.config import settings
from common.logger import setup_logger

logger = setup_logger("MacroWatcher", "logs/watcher", "watcher.log")

FG_URL = "https://production.dataviz.cnn.io/index/fearandgreed/graphdata"
VIX_URL = "https://query1.finance.yahoo.com/v8/finance/chart/%5EVIX?interval=1d&range=5d"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json",
}


def _fg_label(score: float) -> str:
    if score < 25: return "Extreme Fear"
    if score < 45: return "Fear"
    if score < 55: return "Neutral"
    if score < 75: return "Greed"
    return "Extreme Greed"


def _vix_label(vix: float) -> str:
    if vix < 12: return "Low"
    if vix < 20: return "Normal"
    if vix < 30: return "Elevated"
    if vix < 40: return "High"
    return "Extreme"


async def _fetch_fear_greed() -> dict | None:
    try:
        loop = asyncio.get_running_loop()
        resp = await loop.run_in_executor(
            None, lambda: requests.get(FG_URL, headers=HEADERS, timeout=10)
        )
        data = resp.json()
        fg = data["fear_and_greed"]
        score = float(fg["score"])
        return {
            "key": "fear_greed",
            "value": round(score, 1),
            "label": _fg_label(score),
            "prev_close": round(float(fg.get("previous_close") or 0), 1),
            "week_ago": round(float(fg.get("previous_1_week") or 0), 1),
            "month_ago": round(float(fg.get("previous_1_month") or 0), 1),
        }
    except Exception as e:
        logger.error(f"❌ [MacroWatcher] Fear&Greed 수집 실패: {e}")
        return None


async def _fetch_vix() -> dict | None:
    try:
        loop = asyncio.get_running_loop()
        resp = await loop.run_in_executor(
            None, lambda: requests.get(VIX_URL, headers=HEADERS, timeout=10)
        )
        data = resp.json()
        result = data["chart"]["result"][0]
        meta = result["meta"]
        current = float(meta["regularMarketPrice"])
        prev_close = float(meta.get("chartPreviousClose") or meta.get("previousClose") or 0)
        closes = result["indicators"]["quote"][0].get("close") or []
        # closes는 최근 5일치: [5일전, ..., 전일] — 첫번째가 1주전에 가장 가깝다
        week_ago = float(closes[0]) if closes else None
        return {
            "key": "vix",
            "value": round(current, 2),
            "label": _vix_label(current),
            "prev_close": round(prev_close, 2),
            "week_ago": round(week_ago, 2) if week_ago else None,
            "month_ago": None,
        }
    except Exception as e:
        logger.error(f"❌ [MacroWatcher] VIX 수집 실패: {e}")
        return None


async def _push_macro(items: list[dict]):
    try:
        secret = getattr(settings, "WHALE_SECRET", "") or ""
        url = f"{getattr(settings, 'FRONTEND_URL', 'https://stock-now.pages.dev')}/api/macro"
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                json=items,
                headers={"X-Secret-Key": secret},
                timeout=aiohttp.ClientTimeout(total=15),
            ) as resp:
                if resp.status == 200:
                    fg = next((x for x in items if x["key"] == "fear_greed"), None)
                    vix = next((x for x in items if x["key"] == "vix"), None)
                    logger.info(
                        f"✅ [MacroWatcher] 저장 완료 "
                        f"F&G={fg['value'] if fg else '-'} ({fg['label'] if fg else '-'}) "
                        f"VIX={vix['value'] if vix else '-'} ({vix['label'] if vix else '-'})"
                    )
                else:
                    logger.warning(f"⚠️ [MacroWatcher] 저장 실패 HTTP {resp.status}")
    except Exception as e:
        logger.error(f"❌ [MacroWatcher] push 실패: {e}")


async def run_macro_watcher():
    logger.info("📊 [MacroWatcher] 매크로 지표 수집 시작 (30분 주기)")
    while True:
        try:
            fg_data, vix_data = await asyncio.gather(
                _fetch_fear_greed(),
                _fetch_vix(),
            )
            items = [x for x in [fg_data, vix_data] if x is not None]
            if items:
                await _push_macro(items)
        except Exception as e:
            logger.error(f"❌ [MacroWatcher] 루프 오류: {e}")

        await asyncio.sleep(1800)  # 30분
