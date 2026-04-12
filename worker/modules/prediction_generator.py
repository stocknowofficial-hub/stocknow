import asyncio
import json
import os
import aiohttp
import requests as req_sync
from datetime import datetime, timezone, timedelta
from google import genai
from google.genai import types
from common.config import settings

# ─────────────────────────────────────────
# 프롬프트 정의
# ─────────────────────────────────────────

REPORT_PREDICTION_PROMPT = """
다음 증권사 리포트를 분석해서, 핵심 근거마다 영향받는 종목별 예측 카드 배열을 만들어줘.
ETF 수준뿐 아니라 실제로 사고팔 수 있는 개별 종목까지 가장 적합한 대상을 자유롭고 정확하게 뽑아줘.

리포트 출처: {source}
리포트 내용:
{text}

[분석 및 타겟 선정 규칙]
1. 리포트의 핵심 근거(key insight)마다 영향받는 대표 종목/ETF 각각 1장씩 카드 생성 (최대 5개).
2. 같은 근거로 여러 종목이 영향받더라도 가장 대장격인 종목 1개만 메인 target으로 선정 (중복 근거 카드 금지).
3. 방향이 up 또는 down으로 명확한 것만 포함. sideways(횡보/영향 미미/불확실)나 모호한 예측("변동성 확대" 등)은 절대 제외할 것.
4. 종목/ETF 자율 선정 및 코드 매칭 (매우 중요):
   - 리포트에서 특정 섹터/테마만 언급했다면, 해당 섹터를 대표하는 가장 유동성이 풍부한 실제 상장 ETF(예: KODEX, TIGER 등)나 시가총액 1위 대장주를 알아서 추론하여 타겟으로 잡을 것.
   - 한국 주식/ETF의 경우 target_code에 '정확한 6자리 한국거래소(KRX) 종목코드'(예: 005930, 261220)를 입력할 것.
   - 미국 주식/ETF의 경우 target_code에 '정확한 공식 티커'(예: XOM, SPY, TLT)를 입력할 것.
   - 존재하지 않는 가상의 ETF나 코드를 지어내지 말 것.
5. timeframe은 7 / 14 / 30 (일) 중 근거의 성격(단기 이슈 vs 구조적 변화)에 맞게 선택.
6. confidence는 리포트의 어조를 반영(강한 확신/단정적 표현 → high, 가능성/전망 수준 → medium, 간접적 수혜/영향 → low).
7. key_points는 리포트에 등장하는 '구체적 수치, 가격, 데이터, 팩트'를 반드시 포함하여 작성. 추상적 표현 금지.
8. related_stocks는 메인 타겟과 연관된 종목을 최소 2개 이상 포함하며, 메인이 ETF면 개별 대장주를, 메인이 개별주면 경쟁사나 헷지용 ETF를 추천할 것. role이 "매도"인 경우 reason에 메인 타겟과의 관계(예: 자금 이동, 대체재 등)를 명시할 것.

JSON 배열만 출력 (설명 없이, 코드블록 없이):
[
  {{
    "prediction": "[{source}] 구체적 예측 (예: '[BlackRock] 중동 확전 → 엑손모빌 단기 급등 전망')",
    "direction": "up 또는 down",
    "target": "정확한 종목명 또는 ETF명",
    "target_code": "미국 티커(예: XOM) 또는 한국 6자리 코드(예: 261220)",
    "basis": "이 종목이 영향받는 핵심 근거 한 줄 (리포트 내용과 직접 연결)",
    "key_points": [
      "리포트 핵심 주장: 구체적 수치나 사실 포함",
      "이 종목이 수혜/피해받는 메커니즘",
      "단기 시장 반응 예상"
    ],
    "related_stocks": [
      {{"name": "같은 테마 유사 종목", "code": "티커 또는 6자리 코드", "role": "매수 또는 매도 또는 헤지", "reason": "이유 한 줄"}},
      {{"name": "헤지 또는 반대 포지션 종목", "code": "티커 또는 6자리 코드", "role": "매수 또는 매도 또는 헤지", "reason": "이유 한 줄"}}
    ],
    "action": "매수 고려 / 비중 확대 / 관망 / 비중 축소 / 매도 고려 중 하나",
    "action_reason": "이유 한 줄",
    "trade_setup": {{
      "entry": "진입 조건 (예: '이번 주 내 분할 매수', '현재가 근처 즉시')",
      "stop_loss": "손절 기준 (예: '-5% 이탈 시', '전저점 하회 시')",
      "target": "목표 (예: '+10~15%', '52주 고점 재도전')"
    }},
    "timeframe": 7,
    "confidence": "high 또는 medium 또는 low"
  }}
]
"""

TRUMP_PREDICTION_PROMPT = """
트럼프 Truth Social 게시글에 대한 시장 전략 분석 결과를 바탕으로, 가장 직접적으로 영향받을 구체적인 상장 종목(개별주 또는 ETF) 1~2개에 대한 예측 카드 배열을 만들어줘.

트럼프 발언 분석 텍스트:
{text}

[분석 및 타겟 선정 규칙]
1. 필터링: 주식/경제/정책과 무관한 게시글(음식, 스포츠, 개인 일상, 단순 정치 비난 등)이면 [{{"skip": true}}] 만 반환할 것.
2. 타겟 구체화 (매우 중요): '비료 관련주', '방산 기업', '친환경 섹터' 같은 두리뭉실한 범주형 단어는 절대 target으로 사용 금지. 반드시 해당 이슈로 가장 직접적인 영향을 받을 실제 상장된 대장주 기업명(예: CF Industries, 록히드마틴 등)이나 대표 ETF를 스스로 추론하여 구체적으로 명시할 것.
3. 코드 매칭: target_code에는 실제 미국 주식 티커(예: CF, MOS, LMT) 또는 한국 6자리 코드(예: 069500)를 정확히 입력할 것. 가상의 코드를 지어내지 말 것.
4. 방향이 up 또는 down으로 명확한 것만 포함. 불확실하면 제외.
5. 트럼프 발언의 특성상 단기 테마성 움직임이 크므로 timeframe은 가급적 짧게(7일 등) 잡고, confidence는 발언의 강도에 따라 조절할 것.

JSON 배열만 출력 (설명 없이, 코드블록 없이):
[
  {{
    "prediction": "[트럼프] 발언 핵심 → 특정 종목명 단기 전망 (1줄)",
    "direction": "up 또는 down",
    "target": "정확한 상장 종목명 또는 ETF명 (예: CF Industries)",
    "target_code": "미국 티커(예: CF) 또는 한국 6자리 코드",
    "basis": "이 특정 종목이 영향받는 핵심 근거 한 줄",
    "key_points": [
      "트럼프 발언 핵심: (원문 뉘앙스 반영)",
      "이 특정 기업이 수혜/피해받는 구체적 비즈니스적 이유",
      "예상 시장/투심 반응"
    ],
    "related_stocks": [
      {{"name": "같은 섹터 내 경쟁사 또는 유사 수혜주", "code": "티커/코드", "role": "매수 또는 매도 또는 헤지", "reason": "이유 한 줄"}}
    ],
    "action": "매수 고려 / 비중 확대 / 관망 / 비중 축소 / 매도 고려 중 하나",
    "action_reason": "이유 한 줄",
    "trade_setup": {{
      "entry": "단기 진입 조건 (예: '개장 직후 변동성 활용')",
      "stop_loss": "손절 기준",
      "target": "단기 목표"
    }},
    "timeframe": 7,
    "confidence": "high 또는 medium 또는 low"
  }}
]
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
# Gemini File API — PDF 직접 분석
# ─────────────────────────────────────────

def _call_gemini_sync(client, prompt: str) -> dict | None:
    """
    텍스트 프롬프트만으로 Gemini 호출 (트럼프 게시글, 브리핑 등).
    """
    try:
        response = client.models.generate_content(
            model='gemini-3-flash-preview',
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.4,
            )
        )
        if not response or not response.text:
            return None
        text = response.text.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        return json.loads(text.strip())
    except Exception as e:
        print(f"⚠️ [PredGen] _call_gemini_sync 실패: {e}")
        return None


def _call_gemini_with_pdf(client, file_path: str, prompt: str) -> dict | None:
    """
    PDF 파일을 Gemini File API로 업로드한 뒤 직접 분석.
    텍스트 PDF, 이미지 스캔본 모두 동작.
    """
    uploaded = None
    try:
        print(f"📤 [PredGen] Gemini에 PDF 업로드 중: {os.path.basename(file_path)}")
        with open(file_path, 'rb') as f:
            uploaded = client.files.upload(
                file=f,
                config=types.UploadFileConfig(
                    mime_type='application/pdf',
                    display_name=os.path.basename(file_path),
                )
            )
        print(f"✅ [PredGen] 업로드 완료: {uploaded.name}")

        response = client.models.generate_content(
            model='gemini-3-flash-preview',
            contents=[
                types.Content(parts=[
                    types.Part(file_data=types.FileData(
                        file_uri=uploaded.uri,
                        mime_type='application/pdf',
                    )),
                    types.Part(text=prompt),
                ])
            ],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.4,
            )
        )

        if not response or not response.text:
            return None

        text = response.text.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        return json.loads(text.strip())

    finally:
        # 업로드한 파일 Gemini 서버에서 정리
        if uploaded:
            try:
                client.files.delete(name=uploaded.name)
                print(f"🗑️ [PredGen] Gemini 파일 삭제: {uploaded.name}")
            except Exception:
                pass

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

    # Gemini File API — PDF 직접 업로드 후 분석 (텍스트/이미지 스캔본 모두 지원)
    prompt = REPORT_PREDICTION_PROMPT.format(source=source, text="(PDF 파일 첨부 — 전체 내용을 직접 읽고 분석)")
    try:
        client = genai.Client(api_key=settings.GOOGLE_API_KEY)
        loop = asyncio.get_running_loop()
        card = await asyncio.wait_for(
            loop.run_in_executor(None, _call_gemini_with_pdf, client, file_path, prompt),
            timeout=180.0  # PDF 업로드 포함이므로 타임아웃 여유 있게
        )
    except asyncio.TimeoutError:
        print(f"⚠️ [PredGen] Gemini 타임아웃: {source_desc}")
        return
    except Exception as e:
        print(f"⚠️ [PredGen] Gemini 오류: {e}")
        return

    if not card or (isinstance(card, dict) and card.get("skip")):
        print(f"💨 [PredGen] 예측 생성 스킵: {source_desc}")
        return

    # 단일 dict면 배열로 감싸기 (하위 호환)
    cards = card if isinstance(card, list) else [card]

    # 2. sideways 제외
    cards = [c for c in cards if c.get("direction", "").lower() in ("up", "down")]

    # 3. 같은 (target_code, direction) 카드 합치기
    # — 같은 종목에 대한 여러 근거를 1개 카드로 통합
    CONF_RANK = {"high": 3, "medium": 2, "low": 1}

    merged: dict[tuple, dict] = {}
    for c in cards:
        key = (c.get("target_code") or c.get("target", ""), c.get("direction", "").lower())
        if key not in merged:
            merged[key] = dict(c)
            continue
        base = merged[key]
        # key_points 병합 (중복 제거, 최대 6개)
        existing_kp = base.get("key_points") or []
        new_kp = c.get("key_points") or []
        combined_kp = existing_kp + [p for p in new_kp if p not in existing_kp]
        base["key_points"] = combined_kp[:6]
        # basis: 더 높은 신뢰도 카드의 basis 사용, 또는 합치기
        base_conf = CONF_RANK.get(str(base.get("confidence", "")).lower(), 0)
        new_conf  = CONF_RANK.get(str(c.get("confidence", "")).lower(), 0)
        if new_conf > base_conf:
            base["prediction"]  = c["prediction"]
            base["basis"]       = c.get("basis", base.get("basis"))
            base["confidence"]  = c["confidence"]
            base["trade_setup"] = c.get("trade_setup", base.get("trade_setup"))
            base["timeframe"]   = max(base.get("timeframe", 7), c.get("timeframe", 7))
        # related_stocks 병합 (코드 기준 중복 제거, 최대 4개)
        existing_rs = {r.get("code"): r for r in (base.get("related_stocks") or [])}
        for r in (c.get("related_stocks") or []):
            if r.get("code") not in existing_rs:
                existing_rs[r["code"]] = r
        base["related_stocks"] = list(existing_rs.values())[:4]

    merged_cards = list(merged.values())

    # 4. prediction 텍스트 기준 추가 중복 제거
    # — 같은 예측 문장인데 target_code만 다른 카드는 신뢰도 높은 것 1개만 유지
    seen_predictions: dict[str, dict] = {}
    for c in merged_cards:
        pred_key = c.get("prediction", "").strip()
        if pred_key not in seen_predictions:
            seen_predictions[pred_key] = c
        else:
            existing_conf = CONF_RANK.get(str(seen_predictions[pred_key].get("confidence", "")).lower(), 0)
            new_conf = CONF_RANK.get(str(c.get("confidence", "")).lower(), 0)
            if new_conf > existing_conf:
                seen_predictions[pred_key] = c
    deduped_cards = list(seen_predictions.values())

    # 5. 최대 5개 제한 (신뢰도 높은 순)
    deduped_cards.sort(key=lambda c: CONF_RANK.get(str(c.get("confidence", "")).lower(), 0), reverse=True)
    deduped_cards = deduped_cards[:5]

    print(f"🔀 [PredGen] 카드 통합: {len(cards)}개 → {len(merged_cards)}개 (target_code별) → {len(deduped_cards)}개 (중복 제거·최대5)")
    merged_cards = deduped_cards

    # 6. D1 저장
    saved = 0
    for card_idx, c in enumerate(merged_cards):
        unique_url = f"{source_url}#card{card_idx}"
        print(f"📋 [PredGen] 예측 생성됨: {c.get('prediction')} (신뢰도: {c.get('confidence')})")
        await _post_prediction(c, source, source_desc, unique_url)
        saved += 1

    print(f"✅ [PredGen] 리포트 예측 저장 완료: {saved}개 (sideways 제외, 중복 통합)")


def _format_et(utc_iso: str | None) -> str:
    """UTC ISO 문자열 → 미국 동부시간(ET) 포맷. 예: 2026-03-27 EDT 19:20"""
    if not utc_iso:
        return ""
    try:
        dt = datetime.fromisoformat(utc_iso.replace("Z", "+00:00"))
        dt = dt.replace(tzinfo=timezone.utc)
        # DST 적용: 3월 두 번째 일요일 ~ 11월 첫 번째 일요일 = EDT(UTC-4), 나머지 = EST(UTC-5)
        year = dt.year
        # 3월 두 번째 일요일 계산
        mar1 = datetime(year, 3, 1, tzinfo=timezone.utc)
        dst_start = mar1 + timedelta(days=(6 - mar1.weekday()) % 7 + 7)
        dst_start = dst_start.replace(hour=7)  # 2:00 AM ET = 07:00 UTC
        # 11월 첫 번째 일요일 계산
        nov1 = datetime(year, 11, 1, tzinfo=timezone.utc)
        dst_end = nov1 + timedelta(days=(6 - nov1.weekday()) % 7)
        dst_end = dst_end.replace(hour=6)  # 2:00 AM ET = 06:00 UTC
        if dst_start <= dt < dst_end:
            et = dt + timedelta(hours=-4)
            label = "EDT"
        else:
            et = dt + timedelta(hours=-5)
            label = "EST"
        return f"{et.strftime('%Y-%m-%d')} {label} {et.strftime('%H:%M')}"
    except Exception:
        return utc_iso[:16]


BRIEFING_PREDICTION_PROMPT = """
다음 시장 브리핑을 분석해서 단기(1~2일) 예측 카드를 1개의 JSON 객체로 만들어줘.

시장: {market}
브리핑 종류: {subtype}
브리핑 내용:
{text}

[분석 및 타겟 선정 규칙]
1. 타겟 선정: 브리핑 내용 중 가장 구체적인 모멘텀(상승/하락률, 계약, 실적 등)이 명시된 가장 강력한 자산 딱 1개만 메인 target으로 선택.
   - 특정 대장주가 명확히 언급됐으면 그 종목 최우선 선택 (예: 삼성전자, 브로드컴, 엔비디아)
   - 개별주 언급 없이 거시경제/섹터만 언급됐으면 해당 섹터 대표 ETF 선택 (예: KODEX 반도체, KODEX WTI원유선물)
   - "반도체", "기술주" 같은 두리뭉실한 카테고리명 금지. 반드시 실제 거래 가능한 종목명/ETF 풀네임 사용.
2. 코드 매칭: target_code는 실제 존재하는 정확한 티커 또는 6자리 코드만 사용. 모르면 null. 가짜 코드 생성 절대 금지.
   - 참고: KODEX 200(069500), KODEX 반도체(091160), KODEX WTI원유선물(261220), 삼성전자(005930), SK하이닉스(000660)
3. key_points: 브리핑에 등장하는 구체적 수치(예: CPI 3.3%, 6.21% 급등, WTI 98달러 등)를 반드시 포함하여 작성.
4. 예외 처리: 방향이 불분명하거나 단순 요약만 있다면 {{"skip": true}} 반환.

JSON 객체만 1개 출력 (마크다운 코드블록 절대 금지, 설명 없이 순수 JSON 텍스트만 출력):
{{
  "prediction": "[{market} {subtype}] 핵심 이슈 → 종목명 단기 전망 (1줄)",
  "direction": "up 또는 down",
  "target": "정확한 상장 종목명 또는 ETF 풀네임",
  "target_code": "티커 또는 6자리 코드 또는 null",
  "basis": "이 종목이 영향받는 브리핑 내 핵심 근거 한 줄",
  "key_points": [
    "구체적 수치나 팩트 포함 근거 1",
    "이 종목에 미치는 영향 2",
    "단기 시장/투심 예상 3"
  ],
  "related_stocks": [
    {{"name": "수혜/피해 연관 종목명", "code": "티커 또는 코드", "role": "매수 / 매도 / 헤지 중 하나", "reason": "이유 한 줄"}}
  ],
  "action": "매수 고려 / 비중 확대 / 관망 / 비중 축소 / 매도 고려 중 하나",
  "action_reason": "이유 한 줄",
  "trade_setup": {{
    "entry": "진입 조건 (예: '시초가 변동성 활용', '조정 시 매수')",
    "stop_loss": "손절 기준",
    "target": "목표"
  }},
  "timeframe": 2,
  "confidence": "high 또는 medium 또는 low"
}}
"""


async def generate_prediction_from_briefing(market: str, subtype: str, briefing_text: str):
    """
    시장 브리핑 텍스트 → Gemini 분석 → 단기(2일) 예측 카드 생성 → D1 저장
    market: 'KR' | 'US'
    subtype: 'OPENING' | 'MID' | 'CLOSE'
    """
    if not settings.GOOGLE_API_KEY or not briefing_text:
        return

    subtype_label = {"OPENING": "개장", "MID": "장중", "CLOSE": "마감"}.get(subtype, subtype)
    market_label = "한국장" if market == "KR" else "미국장"
    source_desc = f"{market_label} {subtype_label} 브리핑 ({datetime.now().strftime('%Y-%m-%d')})"

    print(f"🔮 [PredGen] 브리핑 예측 분석 시작: {source_desc}")

    prompt = BRIEFING_PREDICTION_PROMPT.format(
        market=market_label, subtype=subtype_label, text=briefing_text[:3000]
    )
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
        print(f"💨 [PredGen] 브리핑 예측 스킵: {source_desc}")
        return

    print(f"📋 [PredGen] 브리핑 예측 생성됨: {card.get('prediction')}")
    source = f"briefing_{market.lower()}"
    await _post_prediction(card, source, source_desc, "")


async def generate_prediction_from_trump(analysis_text: str, post_url: str, post_time: str):
    """
    트럼프 발언 분석 텍스트(Step 1 결과) → Gemini 분석 → 섹터별 예측 카드 배열 생성 → D1 저장
    sideways(횡보) 예측은 저장하지 않음
    """
    if not settings.GOOGLE_API_KEY:
        return

    print(f"🔮 [PredGen] 트럼프 예측 카드 생성 시작...")

    prompt = TRUMP_PREDICTION_PROMPT.format(text=analysis_text)
    try:
        client = genai.Client(api_key=settings.GOOGLE_API_KEY)
        loop = asyncio.get_running_loop()
        result = await asyncio.wait_for(
            loop.run_in_executor(None, _call_gemini_sync, client, prompt),
            timeout=30.0
        )
    except asyncio.TimeoutError:
        print(f"⚠️ [PredGen] Gemini 타임아웃 (트럼프)")
        return
    except Exception as e:
        print(f"⚠️ [PredGen] Gemini 오류 (트럼프): {e}")
        return

    # skip 신호 처리 (dict 또는 배열 모두 처리)
    if not result:
        print(f"💨 [PredGen] 트럼프 게시글 — 결과 없음 스킵")
        return
    if isinstance(result, dict) and result.get("skip"):
        print(f"💨 [PredGen] 트럼프 게시글 — 경제 무관 스킵")
        return
    if isinstance(result, list) and len(result) > 0 and result[0].get("skip"):
        print(f"💨 [PredGen] 트럼프 게시글 — 경제 무관 스킵")
        return

    # 단일 dict면 배열로 감싸기 (하위 호환)
    cards = result if isinstance(result, list) else [result]

    source_desc = f"Trump Truth Social ({_format_et(post_time)})"
    saved = 0
    for card in cards:
        direction = card.get("direction", "").lower()
        # sideways / 방향 불명확 예측 저장 금지
        if direction not in ("up", "down"):
            print(f"💨 [PredGen] 트럼프 예측 스킵 (sideways): {card.get('target')}")
            continue
        print(f"📋 [PredGen] 트럼프 예측 생성됨: {card.get('prediction')}")
        await _post_prediction(card, "trump", source_desc, post_url)
        saved += 1

    print(f"✅ [PredGen] 트럼프 예측 저장 완료: {saved}개 (sideways 제외)")
