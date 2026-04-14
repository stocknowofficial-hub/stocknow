"""
market_data.py
브리핑용 실시간 시장 데이터 조회 모듈

- fetch_us_market_data(): KR_OPENING용 — 전날 미국 마감 지수 (yfinance)
- fetch_kr_realtime_data(): KR_MID용 — 장중 코스피/코스닥 현재 지수 (네이버 API)
"""

import requests
import yfinance as yf

def fetch_us_market_data() -> dict:
    """
    KR_OPENING 브리핑용.
    전날 미국 마감 기준: S&P500, NASDAQ, 필라델피아반도체, WTI, 원/달러환율
    월요일 개장이나 휴장 다음날도 history(period='5d').iloc[-1]로 자동 처리.
    """
    result = {}

    tickers = {
        "S&P500":       "^GSPC",
        "NASDAQ":       "^IXIC",
        "필라델피아반도체":  "^SOX",
        "WTI유가":       "CL=F",
        "원달러환율":     "KRW=X",
    }

    for name, symbol in tickers.items():
        try:
            hist = yf.Ticker(symbol).history(period="5d")
            if hist.empty:
                continue
            if len(hist) >= 2:
                prev = hist.iloc[-2]["Close"]
                last = hist.iloc[-1]["Close"]
                change_pct = round(((last - prev) / prev) * 100, 2)
                sign = "+" if change_pct >= 0 else ""
                if name == "원달러환율":
                    result[name] = f"{last:,.2f}원"
                elif name == "WTI유가":
                    result[name] = f"{last:.2f}달러 ({sign}{change_pct}%)"
                else:
                    result[name] = f"{last:,.2f} ({sign}{change_pct}%)"
            else:
                # 데이터 1개뿐일 때 등락률 없이 현재값만
                last = hist.iloc[-1]["Close"]
                if name == "원달러환율":
                    result[name] = f"{last:,.2f}원"
                elif name == "WTI유가":
                    result[name] = f"{last:.2f}달러"
                else:
                    result[name] = f"{last:,.2f}"
        except Exception as e:
            print(f"⚠️ [MarketData] {symbol} 조회 실패: {e}")

    return result


def fetch_kr_realtime_data() -> dict:
    """
    KR_MID 브리핑용.
    장중 코스피/코스닥 현재 지수 + 원/달러 환율
    """
    result = {}

    # 코스피(0001), 코스닥(1001) — 네이버 지수 API
    indices = {
        "코스피": "0001",
        "코스닥": "1001",
    }

    for name, code in indices.items():
        try:
            resp = requests.get(
                f"https://m.stock.naver.com/api/index/{code}/basic",
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=10,
            )
            if resp.status_code != 200:
                continue
            data = resp.json()
            close = data.get("closePrice") or data.get("currentPrice") or ""
            ratio = data.get("fluctuationsRatio", "")
            change = data.get("compareToPreviousClosePrice", "")
            sign = "+" if str(ratio).startswith("-") is False and ratio else ""
            if close and ratio:
                result[name] = f"{close} ({sign}{ratio}%)"
            elif close:
                result[name] = str(close)
        except Exception as e:
            print(f"⚠️ [MarketData] {name} 조회 실패: {e}")

    # 원/달러 환율 (yfinance KRW=X)
    try:
        hist = yf.Ticker("KRW=X").history(period="2d")
        if not hist.empty:
            rate = hist.iloc[-1]["Close"]
            result["원달러환율"] = f"{rate:,.2f}원"
    except Exception as e:
        print(f"⚠️ [MarketData] KRW=X 조회 실패: {e}")

    return result


def format_market_data_for_prompt(data: dict, label: str = "") -> str:
    """
    조회한 market_data dict를 프롬프트 삽입용 텍스트로 변환
    """
    if not data:
        return ""

    lines = []
    if label:
        lines.append(label)
    for key, val in data.items():
        lines.append(f"- {key}: {val}")
    return "\n".join(lines)
