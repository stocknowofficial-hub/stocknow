import asyncio
import json
import aiohttp
import requests as req_sync
from datetime import datetime
from google import genai
from google.genai import types
from common.config import settings

# ─────────────────────────────────────────
# 프롬프트 정의
# ─────────────────────────────────────────

REPORT_PREDICTION_PROMPT = """
다음 증권사 리포트를 분석해서 시장 예측 카드를 JSON으로 만들어줘.

리포트 출처: {source}
리포트 내용:
{text}

규칙:
- 구체적이고 검증 가능한 예측 1개만 생성
- "시장 불확실성", "변동성 확대" 같이 모호한 예측은 금지
- target_code: 아래 ETF/종목 코드 목록에서 가장 적합한 것 선택. 없으면 null.
- timeframe: 7일 / 14일 / 30일 중 리포트 내용에 가장 적합한 것 선택
- confidence: 리포트에서 강하게 주장할수록 high, 가능성 언급이면 low

[자주 쓰는 ETF/종목 코드 참고]
- 코스피 지수: 069500 (KODEX 200)
- 코스닥 지수: 229200 (KODEX 코스닥150)
- 미국 S&P500: 379800 (KODEX 미국S&P500TR)
- 미국 나스닥: 133690 (TIGER 미국나스닥100)
- WTI 원유: 261220 (KODEX WTI원유선물(H))
- 금(Gold): 132030 (KODEX 골드선물(H))
- 방산: 490090 (KODEX K-방산)
- 반도체: 091160 (KODEX 반도체)
- 2차전지: 305720 (KODEX 2차전지산업)
- 바이오: 244580 (KODEX 바이오)
- 은행: 091170 (KODEX 은행)
- 자동차: 091180 (KODEX 자동차)
- 조선: 139220 (TIGER 조선TOP10)
- 삼성전자: 005930
- SK하이닉스: 000660
- 현대차: 005380

JSON만 출력 (설명 없이, 코드블록 없이):
{{
  "prediction": "[출처] 예측 대상 방향 전망 (예: '[키움증권] WTI 원유 단기 상승 전망')",
  "direction": "up 또는 down 또는 sideways",
  "target": "예측 대상 (예: 'WTI 원유', '반도체 섹터', '삼성전자')",
  "target_code": "6자리 코드 또는 null",
  "basis": "핵심 근거 한 줄 요약",
  "key_points": [
    "근거 1: 구체적 수치나 사실 포함 (예: '연준 점도표 상향 → 금리 인하 기대 후퇴')",
    "근거 2: 구체적 수치나 사실 포함",
    "근거 3: 구체적 수치나 사실 포함"
  ],
  "timeframe": 7,
  "confidence": "high 또는 medium 또는 low"
}}
"""

TRUMP_PREDICTION_PROMPT = """
트럼프의 Truth Social 게시글을 분석해서 한국/미국 주식시장 영향을 예측해줘.

게시글 내용:
{text}

규칙:
- 주식/경제/정책과 무관한 게시글(음식, 스포츠, 개인 일상 등)이면: {{"skip": true}} 만 반환
- 관세 언급 → 피해 업종(수출주: 자동차/반도체) 또는 수혜 업종 분석
- 금리/달러/국채 언급 → 영향 자산 분석
- 지정학/전쟁/외교 언급 → 방산/원유 섹터 분석
- target_code: 아래 ETF 코드 목록에서 가장 적합한 것 선택. 없으면 null.
- timeframe: 주로 7일 또는 14일

[ETF 코드 참고]
- 코스피 지수: 069500 (KODEX 200)
- 미국 S&P500: 379800 (KODEX 미국S&P500TR)
- 미국 나스닥: 133690 (TIGER 미국나스닥100)
- WTI 원유: 261220 (KODEX WTI원유선물(H))
- 금(Gold): 132030 (KODEX 골드선물(H))
- 방산: 490090 (KODEX K-방산)
- 반도체: 091160 (KODEX 반도체)
- 2차전지: 305720 (KODEX 2차전지산업)
- 자동차: 091180 (KODEX 자동차)
- 조선: 139220 (TIGER 조선TOP10)
- 삼성전자: 005930 / SK하이닉스: 000660 / 현대차: 005380

JSON만 출력 (설명 없이, 코드블록 없이):
{{
  "prediction": "[트럼프] 예측 대상 방향 전망 (예: '[트럼프] 자동차 관세 → 현대차 단기 하락 전망')",
  "direction": "up 또는 down 또는 sideways",
  "target": "예측 대상 (섹터명 or 자산명)",
  "target_code": "6자리 코드 또는 null",
  "basis": "핵심 근거 한 줄 (트럼프 발언 요약 포함)",
  "key_points": [
    "트럼프 발언 핵심 요약",
    "영향받는 업종/자산 분석",
    "단기 시장 반응 예상"
  ],
  "timeframe": 7,
  "confidence": "high 또는 medium 또는 low"
}}
"""

# ─────────────────────────────────────────
# 현재가 조회 (네이버 금융 공개 API)
# ─────────────────────────────────────────

def fetch_current_price(code: str) -> float | None:
    """
    종목코드로 현재가 조회 (네이버 모바일 JSON API)
    한국 종목/ETF: 6자리 코드 (005930, 261220 등)
    """
    try:
        url = f"https://m.stock.naver.com/api/stock/{code}/basic"
        headers = {'User-Agent': 'Mozilla/5.0'}
        resp = req_sync.get(url, headers=headers, timeout=5)
        if resp.status_code != 200:
            return None
        data = resp.json()
        price_str = data.get('closePrice', '')
        if price_str:
            return float(str(price_str).replace(',', ''))
        return None
    except Exception as e:
        print(f"⚠️ [PredGen] 현재가 조회 실패 ({code}): {e}")
        return None


# ─────────────────────────────────────────
# PDF 텍스트 추출
# ─────────────────────────────────────────

def extract_pdf_text(file_path: str, max_chars: int = 4000) -> str:
    """PDF에서 텍스트 추출 (pymupdf 사용)"""
    try:
        import fitz  # pymupdf
        doc = fitz.open(file_path)
        text = ""
        for page in doc:
            text += page.get_text()
            if len(text) >= max_chars:
                break
        doc.close()
        return text[:max_chars].strip()
    except Exception as e:
        print(f"⚠️ [PredGen] PDF 추출 실패: {e}")
        return ""

# ─────────────────────────────────────────
# Gemini 호출
# ─────────────────────────────────────────

def _call_gemini_sync(client, prompt: str) -> dict | None:
    """Gemini API 동기 호출 → JSON 파싱"""
    response = client.models.generate_content(
        model='gemini-2.0-flash',
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0.1,
        )
    )
    if not response or not response.text:
        return None
    text = response.text.strip()
    # 코드블록 제거 (혹시 포함된 경우)
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    return json.loads(text.strip())

# ─────────────────────────────────────────
# D1 저장
# ─────────────────────────────────────────

async def _post_prediction(card: dict, source: str, source_desc: str, source_url: str):
    """예측 카드를 /api/predictions에 저장 (entry_price 포함)"""
    secret = getattr(settings, 'WHALE_SECRET', '') or ''
    if not secret:
        print("⚠️ [PredGen] WHALE_SECRET 없음. 저장 스킵.")
        return

    # target_code 있으면 entry_price 즉시 조회
    entry_price = None
    target_code = card.get('target_code')
    if target_code:
        loop = asyncio.get_event_loop()
        entry_price = await loop.run_in_executor(None, fetch_current_price, target_code)
        if entry_price:
            print(f"💰 [PredGen] entry_price 조회 완료: {target_code} = {entry_price:,.0f}원")
        else:
            print(f"⚠️ [PredGen] entry_price 조회 실패: {target_code}")

    url = f"{settings.CLOUDFLARE_URL}/api/predictions"
    payload = {
        "source": source,
        "source_desc": source_desc,
        "source_url": source_url,
        "entry_price": entry_price,
        **card,
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                json=payload,
                headers={"X-Secret-Key": secret},
                timeout=aiohttp.ClientTimeout(total=15)
            ) as resp:
                result = await resp.json()
                if result.get("skipped"):
                    print(f"💨 [PredGen] 중복 스킵: {source_desc}")
                elif result.get("ok"):
                    print(f"✅ [PredGen] 예측 저장 완료: {card.get('prediction')} (id: {result.get('id')})")
                else:
                    print(f"⚠️ [PredGen] 저장 실패: {result}")
    except Exception as e:
        print(f"⚠️ [PredGen] D1 저장 오류: {e}")

# ─────────────────────────────────────────
# 공개 함수
# ─────────────────────────────────────────

async def generate_prediction_from_report(source: str, source_desc: str, source_url: str, file_path: str):
    """
    증권사 리포트 PDF → Gemini 분석 → 예측 카드 생성 → D1 저장
    source: 'blackrock' | 'kiwoom' 등
    """
    if not settings.GOOGLE_API_KEY:
        print("⚠️ [PredGen] GOOGLE_API_KEY 없음.")
        return

    print(f"🔮 [PredGen] 리포트 분석 시작: {source_desc}")

    # 1. PDF 텍스트 추출
    text = extract_pdf_text(file_path)
    if not text:
        print(f"⚠️ [PredGen] PDF 텍스트 추출 실패: {file_path}")
        return

    # 2. Gemini 호출
    prompt = REPORT_PREDICTION_PROMPT.format(source=source, text=text)
    try:
        client = genai.Client(api_key=settings.GOOGLE_API_KEY)
        loop = asyncio.get_running_loop()
        card = await asyncio.wait_for(
            loop.run_in_executor(None, _call_gemini_sync, client, prompt),
            timeout=30.0
        )
    except asyncio.TimeoutError:
        print(f"⚠️ [PredGen] Gemini 타임아웃: {source_desc}")
        return
    except Exception as e:
        print(f"⚠️ [PredGen] Gemini 오류: {e}")
        return

    if not card or card.get("skip"):
        print(f"💨 [PredGen] 예측 생성 스킵: {source_desc}")
        return

    print(f"📋 [PredGen] 예측 생성됨: {card.get('prediction')} (신뢰도: {card.get('confidence')})")

    # 3. D1 저장
    await _post_prediction(card, source, source_desc, source_url)


async def generate_prediction_from_trump(post_text: str, post_url: str, post_time: str):
    """
    트럼프 Truth Social 게시글 → Gemini 분석 → 예측 카드 생성 → D1 저장
    """
    if not settings.GOOGLE_API_KEY:
        return

    print(f"🔮 [PredGen] 트럼프 게시글 분석 시작...")

    prompt = TRUMP_PREDICTION_PROMPT.format(text=post_text)
    try:
        client = genai.Client(api_key=settings.GOOGLE_API_KEY)
        loop = asyncio.get_running_loop()
        card = await asyncio.wait_for(
            loop.run_in_executor(None, _call_gemini_sync, client, prompt),
            timeout=30.0
        )
    except asyncio.TimeoutError:
        print(f"⚠️ [PredGen] Gemini 타임아웃 (트럼프)")
        return
    except Exception as e:
        print(f"⚠️ [PredGen] Gemini 오류 (트럼프): {e}")
        return

    if not card or card.get("skip"):
        print(f"💨 [PredGen] 트럼프 게시글 — 경제 무관 스킵")
        return

    print(f"📋 [PredGen] 트럼프 예측 생성됨: {card.get('prediction')}")

    source_desc = f"Trump Truth Social ({post_time[:10] if post_time else ''})"
    await _post_prediction(card, "trump", source_desc, post_url)
