import asyncio
import json
import aiohttp
from google import genai
from google.genai import types
from common.config import settings
from common.logger import setup_logger

logger = setup_logger("ConsensusSummaryWatcher", "logs/watcher", "watcher.log")

BASE_URL = getattr(settings, "FRONTEND_URL", "https://stock-now.pages.dev")
SECRET = getattr(settings, "WHALE_SECRET", "") or ""
GOOGLE_API_KEY = getattr(settings, "GOOGLE_API_KEY", "") or ""

PROMPT_TEMPLATE = """당신은 한국 주식/ETF 시장 분석 전문가입니다.
아래 [수집 데이터]와 현재 글로벌 시장 상황을 Google 검색으로 파악하여 종합 분석하세요.

[수집 데이터]
▸ CNN Fear & Greed: {fg}
▸ CBOE VIX: {vix}
▸ 이번 주 국내 증권사 강세 전망: {bullish}
▸ 이번 주 국내 증권사 약세 전망: {bearish}
▸ 트럼프 최근 SNS: {trump}

[분석 지침]
1. Google 검색으로 현재 S&P500, 나스닥, KOSPI 최근 흐름 / 주요 매크로 이슈(관세, 연준, 환율 등)를 파악하세요.
2. 위 수집 데이터와 현재 시장 상황을 교차 분석하여 다이버전스(괴리)를 포착하세요.
3. 수치를 반드시 포함하세요 (F&G 수치, VIX 수치, 증권사 언급 건수).
4. 구체적인 ETF/종목명(KODEX 반도체, WTI원유 등)을 명시하세요.
5. 단순 나열이 아닌 "왜 지금 이게 중요한가"를 설명하세요.
6. 이 분석은 AI 자동 생성이며 투자 조언이 아님을 전제로, 판단은 독자 몫임을 인지하고 작성하세요.

다음 JSON 형식으로만 응답하세요 (다른 텍스트 없이):
{{
  "title": "이번 주 핵심 뷰 한 줄 (30자 이내, 핵심 종목/섹터와 시장 상황 포함, 강렬하게)",
  "situation": "🚨 현재 상황: 1~2문장. VIX 수치, F&G 수치, 현재 글로벌 시장 흐름(S&P500, 나스닥 등)을 구체적 수치와 함께 서술.",
  "analysis": "📊 증권사 리포트 시그널: 1~2문장. 수집된 증권사 컨센서스(종목명과 언급 건수 포함)와 현재 시장 상황 간의 괴리(다이버전스)를 구체적으로 서술.",
  "action": "💡 Action Point: 1~2문장. 위 분석을 바탕으로 어떤 관점으로 접근할지 명확히 서술. 구체적 ETF/종목명, 리스크 요인 포함. 투자 조언이 아닌 분석 관점임을 전제.",
  "signal": "bullish 또는 bearish 또는 neutral 또는 caution 중 하나"
}}"""


async def _fetch_macro(session: aiohttp.ClientSession) -> dict:
    try:
        async with session.get(f"{BASE_URL}/api/macro", timeout=aiohttp.ClientTimeout(total=10)) as resp:
            if resp.status == 200:
                return await resp.json()
    except Exception as e:
        logger.warning(f"⚠️ [ConsensusSummary] 매크로 데이터 조회 실패: {e}")
    return {}


async def _fetch_consensus_data(session: aiohttp.ClientSession) -> dict:
    try:
        async with session.get(f"{BASE_URL}/api/consensus-data", timeout=aiohttp.ClientTimeout(total=10)) as resp:
            if resp.status == 200:
                return await resp.json()
    except Exception as e:
        logger.warning(f"⚠️ [ConsensusSummary] 컨센서스 데이터 조회 실패: {e}")
    return {}


def _call_gemini(prompt: str) -> dict | None:
    if not GOOGLE_API_KEY:
        logger.error("❌ [ConsensusSummary] GOOGLE_API_KEY 없음")
        return None
    try:
        import re
        client = genai.Client(api_key=GOOGLE_API_KEY)
        resp = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.3,
                max_output_tokens=1024,
                tools=[types.Tool(google_search=types.GoogleSearch())],
            ),
        )
        raw = resp.text or ""
        match = re.search(r"\{[\s\S]*\}", raw)
        if not match:
            logger.error(f"❌ [ConsensusSummary] Gemini 응답에 JSON 없음: {raw[:300]}")
            return None
        return json.loads(match.group(0))
    except Exception as e:
        logger.error(f"❌ [ConsensusSummary] Gemini 호출 실패: {e}")
        return None


async def _push_summary(session: aiohttp.ClientSession, title: str, body: str, signal: str) -> bool:
    try:
        async with session.post(
            f"{BASE_URL}/api/consensus-summary",
            json={"title": title, "body": body, "signal": signal},
            headers={"X-Secret-Key": SECRET},
            timeout=aiohttp.ClientTimeout(total=15),
        ) as resp:
            if resp.status == 200:
                return True
            body_text = await resp.text()
            logger.warning(f"⚠️ [ConsensusSummary] 저장 실패 HTTP {resp.status} — {body_text[:200]}")
    except Exception as e:
        logger.error(f"❌ [ConsensusSummary] 저장 요청 실패: {e}")
    return False


async def _generate_summary() -> None:
    async with aiohttp.ClientSession() as session:
        macro, consensus = await asyncio.gather(
            _fetch_macro(session),
            _fetch_consensus_data(session),
        )

    fg_data = macro.get("fear_greed", {})
    vix_data = macro.get("vix", {})
    fg_str = f"{fg_data.get('value', '-')} ({fg_data.get('label', '-')})" if fg_data else "데이터 없음"
    vix_str = f"{vix_data.get('value', '-')} ({vix_data.get('label', '-')})" if vix_data else "데이터 없음"

    bullish = consensus.get("bullish", [])
    bearish = consensus.get("bearish", [])
    trump_snippets = consensus.get("trump_snippets", [])

    bullish_str = ", ".join(f"{t['name']}({t['count']}곳)" for t in bullish) or "없음"
    bearish_str = ", ".join(f"{t['name']}({t['count']}곳)" for t in bearish) or "없음"
    trump_str = " / ".join(s[:80] for s in trump_snippets) or "없음"

    prompt = PROMPT_TEMPLATE.format(
        fg=fg_str, vix=vix_str,
        bullish=bullish_str, bearish=bearish_str,
        trump=trump_str,
    )

    loop = asyncio.get_running_loop()
    parsed = await loop.run_in_executor(None, _call_gemini, prompt)
    if not parsed:
        return

    title = parsed.get("title", "")
    signal = parsed.get("signal", "neutral")
    # situation/analysis/action을 JSON 문자열로 body에 저장
    import json as _json
    body = _json.dumps({
        "situation": parsed.get("situation", ""),
        "analysis": parsed.get("analysis", ""),
        "action": parsed.get("action", ""),
    }, ensure_ascii=False)

    async with aiohttp.ClientSession() as session:
        ok = await _push_summary(session, title, body, signal)

    if ok:
        logger.info(f"✅ [ConsensusSummary] 주간 AI 요약 생성 완료 [{signal}] {title}")


async def run_consensus_summary_watcher() -> None:
    logger.info("🧠 [ConsensusSummary] 주간 AI 요약 생성기 시작 (6시간 주기)")
    while True:
        try:
            await _generate_summary()
        except Exception as e:
            logger.error(f"❌ [ConsensusSummary] 루프 오류: {e}")
        await asyncio.sleep(21600)  # 6시간
