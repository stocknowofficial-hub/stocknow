"""
wallstreet_watcher.py
미국 종목: yfinance로 월가 컨센서스 수집
한국 종목: 네이버 증권 크롤링으로 증권사 컨센서스(투자의견 + 목표주가) 수집
하루 1회 실행
"""

import asyncio
import json
import re
import aiohttp
import requests as req_sync
import yfinance as yf
from bs4 import BeautifulSoup
from common.config import settings
from common.logger import setup_logger

logger = setup_logger("WallStreetWatcher", "logs/watcher", "watcher.log")

BASE_URL = getattr(settings, "CLOUDFLARE_URL", "https://stock-now.pages.dev")
SECRET   = getattr(settings, "WHALE_SECRET", "") or ""

RECOMMENDATION_MAP = {
    "strong_buy": "Strong Buy",
    "buy": "Buy",
    "hold": "Hold",
    "sell": "Sell",
    "strong_sell": "Strong Sell",
}

# 네이버 증권 투자의견 점수 → 텍스트 매핑 (5점 만점)
KR_OPINION_MAP = [
    (4.5, "Strong Buy"),
    (3.5, "Buy"),
    (2.5, "Hold"),
    (1.5, "Sell"),
    (0.0, "Strong Sell"),
]


def _fetch_naver_kr_consensus(code: str) -> dict | None:
    """
    네이버 증권 coinfo 페이지에서 한국 종목의 증권사 컨센서스(투자의견 + 목표주가) 스크래핑.
    ETF 등 컨센서스가 없는 종목은 None 반환.
    """
    url = f"https://finance.naver.com/item/coinfo.naver?code={code}&target=analyst"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    try:
        resp = req_sync.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(resp.content.decode("euc-kr", "replace"), "html.parser")

        # ── 투자의견 점수 + 목표주가 (table.rwidth > td 첫번째 셀) ──
        opinion_score: float | None = None
        target_price: float | None = None
        recommendation = None

        table = soup.find("table", class_="rwidth")
        if table:
            td = table.find("td")
            if td:
                text = td.get_text()
                score_m = re.search(r"(\d+\.\d+)", text)
                price_m = re.search(r"(\d{1,3}(?:,\d{3})+)", text)  # 1,335,200 / 252,720 등
                if score_m:
                    try:
                        opinion_score = float(score_m.group(1))
                        for threshold, label in KR_OPINION_MAP:
                            if opinion_score >= threshold:
                                recommendation = label
                                break
                    except ValueError:
                        pass
                if price_m:
                    target_price = float(price_m.group(1).replace(",", ""))

        if not recommendation:
            return None  # 컨센서스 없는 종목 (ETF 등)

        # ── 현재가 (Naver mobile API) ──
        current_price: float | None = None
        try:
            r2 = req_sync.get(
                f"https://m.stock.naver.com/api/stock/{code}/basic",
                headers={"User-Agent": "Mozilla/5.0"}, timeout=5
            )
            close = r2.json().get("closePrice", "")
            if close:
                current_price = float(close.replace(",", ""))
        except Exception:
            pass

        # ── 상승여력 계산 ──
        upside_pct: float | None = None
        if target_price and current_price and current_price > 0:
            upside_pct = round((target_price - current_price) / current_price * 100, 1)

        return {
            "ticker": code,
            "recommendation": recommendation,
            "target_price": target_price,
            "current_price": current_price,
            "upside_pct": upside_pct,
            "analyst_count": 0,  # coinfo 페이지에서 애널리스트 수 미제공
        }

    except Exception as e:
        logger.warning(f"[WallStreet] 네이버 크롤링 {code} 실패: {e}")
        return None


def _fetch_yfinance(ticker: str) -> dict | None:
    """yfinance로 월가 컨센서스 데이터 조회"""
    try:
        info = yf.Ticker(ticker).info
        rec_key = info.get("recommendationKey")
        if not rec_key:
            return None

        target_price = info.get("targetMeanPrice")
        current_price = info.get("currentPrice") or info.get("regularMarketPrice")
        analyst_count = info.get("numberOfAnalystOpinions", 0)

        upside_pct = None
        if target_price and current_price and current_price > 0:
            upside_pct = round((target_price - current_price) / current_price * 100, 1)

        return {
            "ticker": ticker,
            "recommendation": RECOMMENDATION_MAP.get(rec_key, rec_key),
            "target_price": round(target_price, 2) if target_price else None,
            "current_price": round(current_price, 2) if current_price else None,
            "analyst_count": analyst_count or 0,
            "upside_pct": upside_pct,
        }
    except Exception as e:
        logger.warning(f"[WallStreet] yfinance {ticker} 조회 실패: {e}")
        return None


async def _fetch_tickers_from_predictions(session: aiohttp.ClientSession) -> tuple[list[dict], list[dict]]:
    """
    최근 예측에서 미국 티커(alpha 1~5자)와 한국 종목코드(6자리 숫자) 분리 추출
    returns: (us_tickers, kr_codes) — 각각 {ticker/code, name} dict 리스트
    """
    try:
        async with session.get(
            f"{BASE_URL}/api/predictions?limit=50",
            headers={"X-Secret-Key": SECRET},
            timeout=aiohttp.ClientTimeout(total=10),
        ) as r:
            data = await r.json()

        us: dict[str, str] = {}   # ticker → name
        kr: dict[str, str] = {}   # code → name

        for pred in data.get("predictions", []):
            # target_code 직접 추출
            tc = (pred.get("target_code") or "").strip()
            tn = pred.get("target", "")
            if tc:
                if tc.isascii() and tc.isalpha() and 1 <= len(tc) <= 5:
                    us[tc.upper()] = tn
                elif tc.isdigit() and len(tc) == 6:
                    kr[tc] = tn

            # related_stocks도 추출
            try:
                for s in json.loads(pred.get("related_stocks") or "[]"):
                    code = (s.get("code") or "").strip()
                    name = s.get("name", code)
                    if code.isascii() and code.isalpha() and 1 <= len(code) <= 5:
                        us[code.upper()] = name
                    elif code.isdigit() and len(code) == 6:
                        kr[code] = name
            except Exception:
                pass

        return (
            [{"ticker": t, "name": n} for t, n in us.items()],
            [{"code": c, "name": n} for c, n in kr.items()],
        )
    except Exception as e:
        logger.error(f"[WallStreet] predictions 조회 실패: {e}")
        return [], []


async def _post_results(session: aiohttp.ClientSession, items: list[dict]) -> None:
    """결과를 API에 저장"""
    try:
        async with session.post(
            f"{BASE_URL}/api/wallstreet",
            json=items,
            headers={"X-Secret-Key": SECRET, "Content-Type": "application/json"},
            timeout=aiohttp.ClientTimeout(total=10),
        ) as r:
            result = await r.json()
            logger.info(f"[WallStreet] 저장 완료: {result}")
    except Exception as e:
        logger.error(f"[WallStreet] 저장 실패: {e}")


async def _collect():
    logger.info("[WallStreet] 컨센서스 수집 시작 (미국 yfinance + 한국 네이버)")
    loop = asyncio.get_running_loop()

    async with aiohttp.ClientSession() as session:
        # 1. 예측에서 미국/한국 종목 분리 추출
        us_tickers, kr_codes = await _fetch_tickers_from_predictions(session)
        logger.info(f"[WallStreet] US티커: {[t['ticker'] for t in us_tickers]}, KR코드: {[c['code'] for c in kr_codes]}")

        results = []

        # 2. 미국 종목 → yfinance
        for item in us_tickers:
            data = await loop.run_in_executor(None, _fetch_yfinance, item["ticker"])
            if data:
                data["name"] = item["name"]
                results.append(data)
                logger.info(
                    f"[WallStreet][US] {item['ticker']} → {data['recommendation']} "
                    f"| 목표 ${data['target_price']} ({data['upside_pct']:+.1f}%) "
                    f"| {data['analyst_count']}명"
                )

        # 3. 한국 종목 → 네이버 크롤링
        for item in kr_codes:
            data = await loop.run_in_executor(None, _fetch_naver_kr_consensus, item["code"])
            if data:
                data["name"] = item["name"]
                results.append(data)
                pct = f"{data['upside_pct']:+.1f}%" if data['upside_pct'] is not None else "N/A"
                target = f"{int(data['target_price']):,}원" if data['target_price'] else "N/A"
                logger.info(
                    f"[WallStreet][KR] {item['code']} ({item['name']}) → {data['recommendation']} "
                    f"| 목표 {target} ({pct}) | {data['analyst_count']}명"
                )
            else:
                logger.info(f"[WallStreet][KR] {item['code']} → 컨센서스 없음 (ETF 또는 미지원)")

        if not results:
            logger.info("[WallStreet] 수집 결과 없음")
            return

        # 4. 저장
        await _post_results(session, results)
        logger.info(f"[WallStreet] 완료: {len(results)}개 저장")


async def run_wallstreet_watcher() -> None:
    logger.info("📈 [WallStreet] 월가 컨센서스 수집기 시작 (24시간 주기)")
    while True:
        try:
            await _collect()
        except Exception as e:
            logger.error(f"❌ [WallStreet] 루프 오류: {e}")
        await asyncio.sleep(86400)  # 24시간
