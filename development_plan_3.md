# 개발 계획서 v3 — 예측 트래킹 시스템 (Prediction Tracker)

> 작성일: 2026-03-25
> 목표: 기존 데이터 소스(증권사 리포트, 트럼프 게시글, 시황 브리핑)를 바탕으로
> AI가 예측 카드를 자동 생성하고, 실제 결과와 비교해 적중률을 공개하는 시스템

---

## 1. 전체 플로우

```
[기존 소스]                   [예측 생성]               [저장]            [결과 추적]         [프론트]
report_watcher.py  →  Redis  →  worker/main.py       →  D1               →  cron (daily)  →  /predictions
trump_watcher.py   →  Redis  →  (REPORT_ANALYSIS /      predictions         결과 체크          예측 피드
                               SNS_ANALYSIS 이벤트)      테이블              hit/miss 판정      적중률 표시
                               ↓
                           Gemini API 호출
                           (PDF 텍스트 or 트럼프 글 분석)
                           예측 카드 JSON 생성
                           ↓
                       POST /api/predictions (D1 저장)
```

---

## 2. D1 테이블 설계 (`schema.sql`)

```sql
CREATE TABLE IF NOT EXISTS predictions (
  id           TEXT PRIMARY KEY,   -- 'pred_20260325_blackrock_001'
  created_at   TEXT DEFAULT (datetime('now')),
  source       TEXT NOT NULL,      -- 'blackrock' | 'kiwoom' | 'trump' | 'briefing'
  source_desc  TEXT,               -- 'BlackRock Weekly 2026-03-23'
  source_url   TEXT,               -- 원본 링크 (있는 경우)
  prediction   TEXT NOT NULL,      -- "방산 섹터 단기 강세 예상"
  direction    TEXT NOT NULL,      -- 'up' | 'down' | 'sideways'
  target       TEXT NOT NULL,      -- "방산 섹터" | "삼성전자" | "WTI 원유"
  target_code  TEXT,               -- KIS 종목코드 or ETF코드 (없으면 NULL)
  basis        TEXT,               -- AI가 생성한 근거 한 줄
  timeframe    INTEGER NOT NULL,   -- 며칠 후 체크 (7 | 14 | 30)
  expires_at   TEXT NOT NULL,      -- created_at + timeframe (결과 체크 기준일)
  confidence   TEXT NOT NULL,      -- 'high' | 'medium' | 'low'
  result       TEXT,               -- NULL(진행중) | 'hit' | 'miss' | 'partial'
  result_val   TEXT,               -- 실제 결과값 "+8.3%" (결과 확정 시 입력)
  result_at    TEXT                -- 결과 확정 시각
);
```

### 적용 방법
- `frontend_web/schema.sql`에 위 테이블 추가
- Cloudflare D1 콘솔에서 직접 실행:
  ```
  wrangler d1 execute stock-now-database --file=./schema.sql
  ```

---

## 3. Step 1 — D1 테이블 추가

**파일**: `frontend_web/schema.sql`
**작업**: 위 `predictions` 테이블 정의 추가
**완료 기준**: D1에 테이블 생성 확인

---

## 4. Step 2 — API 엔드포인트 (`/api/predictions`)

**파일**: `frontend_web/src/app/api/predictions/route.ts` (신규)

### GET /api/predictions
- D1에서 예측 목록 조회
- 쿼리 파라미터: `status=pending|completed`, `limit=20`
- 정렬: created_at DESC

### POST /api/predictions
- worker에서 예측 카드 저장
- 인증: `X-Secret-Key: WHALE_SECRET` (기존 방식 재사용)
- Body:
  ```json
  {
    "source": "blackrock",
    "source_desc": "BlackRock Weekly 2026-03-23",
    "source_url": "https://...",
    "prediction": "방산 섹터 단기 강세 예상",
    "direction": "up",
    "target": "방산 섹터",
    "target_code": null,
    "basis": "지정학적 리스크 확대 + 미국 국방예산 증가 언급",
    "timeframe": 7,
    "confidence": "high"
  }
  ```

### PATCH /api/predictions/[id]/result (결과 업데이트)
- cron에서 결과 체크 후 호출
- Body: `{ "result": "hit", "result_val": "+8.3%" }`

---

## 5. Step 3 — worker: 예측 생성 (Gemini API)

**파일**: `worker/modules/prediction_generator.py` (신규)

### 5-1. PDF 텍스트 추출 + Gemini 분석

```python
# 기존 report_watcher → Redis → worker에서 REPORT_ANALYSIS 이벤트 수신 시 호출

async def generate_prediction_from_report(source, source_desc, source_url, file_path):
    """
    PDF 파일 → 텍스트 추출 → Gemini 분석 → 예측 카드 생성 → D1 저장
    """
    # 1. PDF 텍스트 추출 (pymupdf or pdfplumber)
    text = extract_pdf_text(file_path)

    # 2. Gemini 호출
    prompt = REPORT_PREDICTION_PROMPT.format(
        source=source,
        text=text[:3000]  # 토큰 절약: 앞부분 3000자
    )
    client = genai.Client(api_key=settings.GOOGLE_API_KEY)
    response = client.models.generate_content(
        model='gemini-2.0-flash',
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0.1
        )
    )

    # 3. JSON 파싱
    card = json.loads(response.text)

    # 4. D1 저장
    await post_prediction(card, source, source_desc, source_url)
```

### 5-2. 트럼프 게시글 분석

```python
async def generate_prediction_from_trump(post_text, post_url, post_time):
    """
    트럼프 게시글 → Gemini 분석 → 시장 영향 예측 카드 생성
    """
    # 관세/금리/달러 관련 여부 먼저 필터링
    # 관련 없으면 스킵 (음식 얘기 같은 거)
    prompt = TRUMP_PREDICTION_PROMPT.format(text=post_text)
    ...
```

### 5-3. 프롬프트 설계

```
[REPORT_PREDICTION_PROMPT]
다음 증권사 리포트를 분석해서 시장 예측 카드를 JSON으로 만들어줘.

리포트: {source}
내용: {text}

규칙:
- 구체적이고 검증 가능한 예측 1개만 (예: "X 섹터 상승" or "Y 자산 하락")
- 너무 광범위한 예측 금지 (예: "시장 불확실성" 같은 거)
- target_code는 KIS 종목코드 or ETF 코드. 모르면 null

출력 (JSON만, 설명 없이):
{
  "prediction": "한 문장",
  "direction": "up|down|sideways",
  "target": "예측 대상",
  "target_code": "종목코드 or null",
  "basis": "근거 한 줄",
  "timeframe": 7 또는 14 또는 30,
  "confidence": "high|medium|low"
}

[TRUMP_PREDICTION_PROMPT]
트럼프 Truth Social 게시글을 분석해서 한국/미국 주식시장 영향을 예측해줘.

게시글: {text}

규칙:
- 주식/경제 관련 내용이 아니면 {"skip": true} 반환
- 관세 언급 → 수혜/피해 업종 분석
- 금리/달러 언급 → 영향 자산 분석
- 한국 시장 관련성 우선 고려

출력 (JSON만):
{
  "prediction": "한 문장",
  "direction": "up|down|sideways",
  "target": "예측 대상 (한국 섹터 or 자산명)",
  "target_code": "ETF코드 or null",
  "basis": "근거 한 줄",
  "timeframe": 7 또는 14,
  "confidence": "high|medium|low"
}
```

### 5-4. worker/main.py 연동

기존 이벤트 핸들러에 추가:
```python
# REPORT_ANALYSIS 이벤트 수신 시
if msg_type == "REPORT_ANALYSIS":
    ...기존 처리...
    # 예측 생성 추가
    asyncio.create_task(
        generate_prediction_from_report(
            source=data['source'],
            source_desc=data['title'],
            source_url=data['url'],
            file_path=data['file_path']
        )
    )

# SNS_ANALYSIS 이벤트 수신 시
elif msg_type == "SNS_ANALYSIS":
    ...기존 처리...
    # 트럼프 예측 생성 추가
    asyncio.create_task(
        generate_prediction_from_trump(
            post_text=data['text'],
            post_url=data['url'],
            post_time=data['time']
        )
    )
```

---

## 6. Step 4 — 결과 자동 체크 (Cron)

**방법**: Cloudflare Cron Trigger (매일 09:00 KST)
**파일**: `frontend_web/src/app/api/cron/check-predictions/route.ts` (신규)

### 로직
```typescript
// 1. 오늘 만료된 예측 조회
const expired = await db.prepare(
  "SELECT * FROM predictions WHERE expires_at <= date('now') AND result IS NULL"
).all()

// 2. 각 예측에 대해 결과 체크
for (const pred of expired.results) {
  let result = 'miss'
  let resultVal = ''

  if (pred.target_code) {
    // KIS API or 다른 소스로 가격 변화 조회 (추후 구현)
    // 일단은 수동 입력 방식으로 시작
  }

  // target_code 없는 경우: 수동 검토 필요 → result = null 유지
  // target_code 있는 경우: 자동 판정
}
```

> **참고**: 자동 결과 체크는 KIS API를 활용해 예측 생성 시점 대비 현재가 변화율을 계산.
> 초기에는 수동 입력 방식으로 시작하고, 자동화는 2단계에서 구현.

---

## 7. Step 5 — 프론트엔드 `/predictions` 페이지

**파일**: `frontend_web/src/app/predictions/page.tsx` (신규)

### UI 구성

```
┌─────────────────────────────────────────────────────┐
│  📊 StockNow 예측 트래커                              │
│  AI가 리포트와 뉴스를 분석해 생성한 예측과 실제 결과    │
│                                                      │
│  누적 적중률  ████████░░  73%   (22건 / 30건)         │
└─────────────────────────────────────────────────────┘

[진행중]  [완료]  탭

┌─────────────────────────┐  ┌─────────────────────────┐
│ 📈 방산 섹터 단기 강세    │  │ ✅ WTI 원유 하락 적중     │
│ BlackRock Weekly 기반    │  │ 3/18 예측 → 3/25 결과    │
│ 신뢰도: ●●● HIGH         │  │ 실제: -6.2% ✓            │
│ 근거: 지정학 리스크 확대  │  │ 근거: 공급 과잉 우려       │
│ D-3 (4/1 체크 예정)      │  │ BlackRock 리포트 기반     │
└─────────────────────────┘  └─────────────────────────┘
```

### 컴포넌트 구조
- `PredictionCard.tsx` — 개별 예측 카드 (진행중/완료 상태별 스타일)
- `HitRateBadge.tsx` — 적중률 배지 (홈화면 등에도 재사용)
- `/predictions/page.tsx` — 메인 페이지 (탭: 진행중 / 완료)

### 접근 권한
- **프리뷰 (무료)**: 최근 3개 예측 카드만 표시
- **프리미엄**: 전체 히스토리 + 적중률 통계

---

## 8. 개발 순서 및 체크리스트

```
[ ] 1. schema.sql — predictions 테이블 추가 + D1 적용
[ ] 2. /api/predictions/route.ts — GET / POST 구현
[ ] 3. worker/modules/prediction_generator.py — Gemini 예측 생성
[ ] 4. worker/main.py — REPORT_ANALYSIS / SNS_ANALYSIS 핸들러에 연동
[ ] 5. /api/cron/check-predictions/route.ts — 결과 체크 cron
[ ] 6. frontend: PredictionCard.tsx 컴포넌트
[ ] 7. frontend: /predictions/page.tsx 메인 페이지
[ ] 8. 사이드바 메뉴에 "예측 트래커" 링크 추가
[ ] 9. 홈 대시보드에 최근 예측 3개 미리보기 추가 (선택)
```

---

## 9. 의존성 추가

**Python (requirements.txt)**
```
pymupdf  # PDF 텍스트 추출 (fitz)
# or
pdfplumber  # 대안 (표 추출에 강함)
```
> `pdfplumber`는 이미 설치되어 있을 수 있음 — `requirements.txt` 확인 필요

---

## 10. 주의사항

1. **트럼프 예측 필터링 중요**: 음식, 스포츠 등 비경제 글은 Gemini가 `{"skip": true}` 반환하도록 프롬프트 설계
2. **예측 중복 방지**: 같은 리포트에서 중복 생성 방지 — `source_url` 기준으로 중복 체크
3. **자동 결과 체크 1단계**: target_code 없는 예측(섹터/거시 예측)은 초기에 수동 입력
   target_code 있는 예측만 KIS API로 자동 판정
4. **법적 주의**: 예측 카드에 "투자 조언이 아닙니다" 문구 필수
