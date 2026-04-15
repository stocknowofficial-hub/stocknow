"""
prediction_price_updater.py
장 마감 후 일별 고가/저가(OHLC)로 예측 peak를 추적하고 hit/miss를 판정합니다.

실행 시점 (하루 2회):
  - 한국장 마감 후: KST 15:40
  - 미국장 마감 후: KST 06:10 (= ET 17:10 전날)

핵심 개선:
  - 2시간 폴링 → 일별 고가/저가 사용 (장중 peak 누락 없음)
  - up 예측: 당일 고가(High) 기준 → 진입가 대비 변화율
  - down 예측: 당일 저가(Low) 기준 → 진입가 대비 변화율
  - hit 이후에도 만료일까지 peak 계속 갱신 (result 변경 없음)
"""

import asyncio
from datetime import datetime, timezone

import aiohttp
import requests as req
import yfinance as yf
import pytz

from common.config import settings
from common.logger import setup_logger

logger = setup_logger("PredictionPriceUpdater", "logs/watcher", "watcher.log")

BASE_URL = getattr(settings, 'CLOUDFLARE_URL', 'https://stock-now.pages.dev')
SECRET   = getattr(settings, 'WHALE_SECRET', '') or ''

HIT_THRESHOLD = 1.0  # 1% 이상 방향 일치 시 hit


# ──────────────────────────────────────────────
# OHLC 조회
# ──────────────────────────────────────────────

def fetch_us_ohlc(ticker: str) -> dict | None:
    """yfinance — 당일 고가/저가/종가"""
    try:
        hist = yf.Ticker(ticker).history(period="5d")
        if hist.empty:
            return None
        row = hist.iloc[-1]
        return {
            "high":  float(row["High"]),
            "low":   float(row["Low"]),
            "close": float(row["Close"]),
        }
    except Exception as e:
        logger.warning(f"[PriceUpdater] yfinance {ticker} 실패: {e}")
        return None


def fetch_kr_ohlc(code: str) -> dict | None:
    """네이버 모바일 API — 당일 고가/저가/종가"""
    try:
        resp = req.get(
            f"https://m.stock.naver.com/api/stock/{code}/basic",
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=10,
        )
        if resp.status_code != 200:
            return None
        data = resp.json()

        def parse(val: str) -> float | None:
            if not val:
                return None
            try:
                return float(str(val).replace(",", ""))
            except ValueError:
                return None

        close = parse(data.get("closePrice"))
        if not close:
            return None
        high  = parse(data.get("highPrice"))  or close
        low   = parse(data.get("lowPrice"))   or close
        return {"high": high, "low": low, "close": close}
    except Exception as e:
        logger.warning(f"[PriceUpdater] Naver {code} 실패: {e}")
        return None


def fetch_ohlc(code: str) -> dict | None:
    if code.isascii() and code.isalpha() and len(code) <= 5:
        return fetch_us_ohlc(code.upper())
    return fetch_kr_ohlc(code)


# ──────────────────────────────────────────────
# 예측 조회 헬퍼
# ──────────────────────────────────────────────

async def fetch_predictions(status: str) -> list:
    """status: 'pending' | 'completed'"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{BASE_URL}/api/predictions?status={status}&limit=50",
                headers={"X-Secret-Key": SECRET},
                timeout=aiohttp.ClientTimeout(total=30),
            ) as resp:
                if resp.status != 200:
                    logger.warning(f"⚠️ [PriceUpdater] 예측 조회 실패 ({status}): HTTP {resp.status}")
                    return []
                data = await resp.json()
                return data.get("predictions", [])
    except Exception as e:
        logger.error(f"❌ [PriceUpdater] 예측 조회 오류: {e}")
        return []


# ──────────────────────────────────────────────
# 마감 후 일별 업데이트
# ──────────────────────────────────────────────

async def run_daily_update(market: str):
    """
    KR (15:40 KST) 또는 US (06:10 KST) 마감 후 호출.
    - pending 예측: hit/miss 판정 + peak 갱신 + 현재가 업데이트
    - hit 예측 (만료 전): peak만 계속 갱신 (이미 맞췄지만 얼마나 올랐는지 추적)
    """
    logger.info(f"💹 [PriceUpdater] {market} 일별 OHLC 업데이트 시작")

    # ① pending 예측 + 만료 전 hit 예측 모두 수집
    pending_preds = await fetch_predictions("pending")
    hit_preds     = await fetch_predictions("completed")

    now_utc = datetime.now(timezone.utc)

    # hit 중 만료 전인 것 (peak 갱신 대상) + 만료된 것 (current_price만 갱신)
    hit_active = []   # 만료 전: peak + current_price 갱신
    hit_expired = []  # 만료 후: current_price만 갱신
    for p in hit_preds:
        if p.get("result") != "hit":
            continue
        raw_exp = p.get("expires_at")
        if not raw_exp:
            continue
        expires = datetime.fromisoformat(raw_exp.replace(" ", "T"))
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        if expires > now_utc:
            hit_active.append(p)
        else:
            hit_expired.append(p)

    def market_filter(p: dict) -> bool:
        code = p.get("target_code", "")
        if market == "KR":
            return bool(code) and code.isdigit()
        else:  # US
            return bool(code) and code.isascii() and code.isalpha() and len(code) <= 5

    active_pending  = [p for p in pending_preds if market_filter(p) and p.get("direction") in ("up", "down") and p.get("source") != "trump"]
    active_hit      = [p for p in hit_active    if market_filter(p) and p.get("direction") in ("up", "down") and p.get("source") != "trump"]
    expired_hit     = [p for p in hit_expired   if market_filter(p) and p.get("direction") in ("up", "down") and p.get("source") != "trump"]

    logger.info(f"💹 [PriceUpdater] {market} 대상: pending {len(active_pending)}건, hit(만료전) {len(active_hit)}건, hit(만료후) {len(expired_hit)}건")

    if not active_pending and not active_hit:
        return

    loop = asyncio.get_running_loop()
    now_str = now_utc.strftime("%Y-%m-%d %H:%M:%S")
    updated = 0

    # ② pending 예측 처리 (hit/miss 판정 + peak 갱신)
    for pred in active_pending:
        code      = pred["target_code"]
        direction = pred["direction"]

        ohlc = await loop.run_in_executor(None, fetch_ohlc, code)
        if not ohlc:
            logger.warning(f"⚠️ [PriceUpdater] {code} OHLC 조회 실패")
            continue

        entry_price = pred.get("entry_price") or ohlc["close"]

        # 방향별 유리한 가격: up → 고가, down → 저가
        best_price   = ohlc["high"] if direction == "up" else ohlc["low"]
        best_pct     = round(((best_price - entry_price) / entry_price) * 100, 2)
        close_pct    = round(((ohlc["close"] - entry_price) / entry_price) * 100, 2)

        # 만료 여부
        is_expired = False
        raw_exp = pred.get("expires_at")
        if raw_exp:
            expires = datetime.fromisoformat(raw_exp.replace(" ", "T"))
            if expires.tzinfo is None:
                expires = expires.replace(tzinfo=timezone.utc)
            is_expired = expires < now_utc

        # peak 갱신
        prev_peak  = pred.get("peak_change_pct")
        is_new_peak = (
            (direction == "up"   and (prev_peak is None or best_pct > prev_peak)) or
            (direction == "down" and (prev_peak is None or best_pct < prev_peak))
        )

        # hit/miss 판정
        result = None
        is_hit = (
            (direction == "up"   and best_pct >=  HIT_THRESHOLD) or
            (direction == "down" and best_pct <= -HIT_THRESHOLD)
        )
        if is_hit:
            result = "hit"
        elif is_expired:
            result = "miss"

        patch_body: dict = {
            "current_price":    ohlc["close"],
            "entry_price":      entry_price,
            "price_change_pct": close_pct,   # 종가 기준 표시
        }
        if is_new_peak:
            patch_body["peak_change_pct"] = best_pct
            patch_body["peak_at"]         = now_str
        if result:
            patch_body["result"]         = result
            patch_body["hit_change_pct"] = best_pct  # 최초 hit 시점 스냅샷
            patch_body["hit_at"]         = now_str

        async with aiohttp.ClientSession() as session:
            async with session.patch(
                f"{BASE_URL}/api/predictions/{pred['id']}",
                json=patch_body,
                headers={"X-Secret-Key": SECRET},
                timeout=aiohttp.ClientTimeout(total=15),
            ) as resp:
                if resp.status == 200:
                    updated += 1
                    if result:
                        sign = "+" if best_pct >= 0 else ""
                        logger.info(
                            f"💹 [AutoJudge] {pred['id']} ({code}) → {result} "
                            f"({sign}{best_pct}%, dir={direction}, 고가/저가 기준)"
                        )
                else:
                    logger.warning(f"⚠️ [PriceUpdater] PATCH 실패: {pred['id']} HTTP {resp.status}")

    # ③ 이미 hit된 예측 — peak만 계속 갱신 (만료일까지)
    for pred in active_hit:
        code      = pred["target_code"]
        direction = pred["direction"]

        ohlc = await loop.run_in_executor(None, fetch_ohlc, code)
        if not ohlc:
            continue

        entry_price = pred.get("entry_price") or ohlc["close"]
        best_price  = ohlc["high"] if direction == "up" else ohlc["low"]
        best_pct    = round(((best_price - entry_price) / entry_price) * 100, 2)
        close_pct   = round(((ohlc["close"] - entry_price) / entry_price) * 100, 2)

        prev_peak   = pred.get("peak_change_pct")
        is_new_peak = (
            (direction == "up"   and (prev_peak is None or best_pct > prev_peak)) or
            (direction == "down" and (prev_peak is None or best_pct < prev_peak))
        )

        # 현재가는 항상 업데이트, peak는 신고점일 때만 갱신
        patch_body = {
            "current_price":    ohlc["close"],
            "price_change_pct": close_pct,
        }
        if is_new_peak:
            patch_body["peak_change_pct"] = best_pct
            patch_body["peak_at"]         = now_str
        async with aiohttp.ClientSession() as session:
            async with session.patch(
                f"{BASE_URL}/api/predictions/{pred['id']}",
                json=patch_body,
                headers={"X-Secret-Key": SECRET},
                timeout=aiohttp.ClientTimeout(total=15),
            ) as resp:
                if resp.status == 200:
                    updated += 1
                    sign = "+" if best_pct >= 0 else ""
                    logger.info(
                        f"🏔 [PeakUpdate] {pred['id']} ({code}) peak 갱신: {sign}{best_pct}%"
                    )

    # ④ 만료된 hit 예측 — current_price만 갱신 (peak는 건드리지 않음)
    for pred in expired_hit:
        code      = pred["target_code"]
        direction = pred["direction"]

        ohlc = await loop.run_in_executor(None, fetch_ohlc, code)
        if not ohlc:
            continue

        entry_price = pred.get("entry_price") or ohlc["close"]
        close_pct   = round(((ohlc["close"] - entry_price) / entry_price) * 100, 2)

        patch_body = {
            "current_price":    ohlc["close"],
            "price_change_pct": close_pct,
        }
        async with aiohttp.ClientSession() as session:
            async with session.patch(
                f"{BASE_URL}/api/predictions/{pred['id']}",
                json=patch_body,
                headers={"X-Secret-Key": SECRET},
                timeout=aiohttp.ClientTimeout(total=15),
            ) as resp:
                if resp.status == 200:
                    updated += 1

    logger.info(f"💹 [PriceUpdater] {market} 완료: {updated}건 업데이트")


# ──────────────────────────────────────────────
# 메인 루프 — 10분마다 시간 체크, 하루 2회 실행
# ──────────────────────────────────────────────

async def run_prediction_price_updater():
    logger.info("💹 [PriceUpdater] 일별 OHLC 기반 가격 업데이트 태스크 시작")
    logger.info("   실행 시점: KST 15:40 (한국장 마감), KST 06:10 (미국장 마감)")

    last_run_kr: str = ""   # "YYYY-MM-DD" 형식으로 중복 실행 방지
    last_run_us: str = ""

    while True:
        try:
            now_kst = datetime.now(pytz.timezone('Asia/Seoul'))
            weekday = now_kst.weekday()  # 0=월 … 4=금, 5=토, 6=일
            today   = now_kst.strftime("%Y-%m-%d")

            if weekday < 5:  # 평일만
                h, m = now_kst.hour, now_kst.minute

                # 한국장 마감 후: 15:40 ~ 16:30
                if h == 15 and m >= 40 and last_run_kr != today:
                    last_run_kr = today
                    await run_daily_update("KR")

                # 미국장 마감 후: 06:10 ~ 07:00 KST
                # (미국 금요일 마감 = KST 토요일 06:10이므로 주말 체크 예외 처리)
                if h == 6 and m >= 10 and last_run_us != today:
                    last_run_us = today
                    await run_daily_update("US")

            # 토요일 06:10: 미국 금요일 마감 처리
            elif weekday == 5 and now_kst.hour == 6 and now_kst.minute >= 10 and last_run_us != today:
                last_run_us = today
                await run_daily_update("US")

        except Exception as e:
            logger.error(f"❌ [PriceUpdater] 루프 오류: {e}", exc_info=True)

        await asyncio.sleep(600)  # 10분마다 시간 체크
