# Stock Now — Development Plan 2
# 선행 인사이트 보드 (Forward-Looking Insight Board)

> **핵심 목표**: 후행적 실시간 알림의 한계를 극복하고, 기관 리포트 기반 주간 예측을 제공한 뒤
> 실제 시장이 그 예측과 일치할 때 자동으로 연결해주는 "예측 검증 피드백 루프" 구현

---

## 1. 문제 정의

### 현재 서비스의 한계
- 실시간 알림은 **후행적**: 주가가 이미 움직인 뒤에 알려줌
- 기관 리포트 분석 결과가 **텔레그램으로 전송하고 끝** → 어디에도 저장/누적되지 않음
- 예측과 실제 시장 흐름을 **연결하는 로직 없음**

### 목표
- 기관 리포트(BlackRock, Kiwoom 등 주요 증권사)에서 **이번 주 주목 섹터/테마** 추출
- 실제 시장에서 해당 테마가 실현될 때 **자동으로 "예측 일치" 노트** 추가
- 대시보드에 **주간 인사이트 보드** 페이지 제공 → 서비스 차별화 포인트

---

## 2. 최종 사용자 경험 (UX 목표)

```
[월요일 아침] 대시보드 /insights 페이지 오픈
  → "이번 주 기관 컨센서스: 반도체 ↑ 긍정 / 방산 ↓ 주의 / 2차전지 ⚠️ 중립"
  → 각 테마별 근거 리포트 요약 확인 가능

[수요일 장중] 반도체 종목 일괄 5%+ 급등
  → 텔레그램 알림:
     "💡 [예측 검증] 삼성전자 +6.2%
      이번 주 기관 리포트에서 예측한 '반도체 섹터 긍정' 시나리오와 일치합니다.
      (근거: BlackRock Weekly 2026-03-24, Kiwoom Weekly 2026-03-24)"

[대시보드 /insights] 해당 예측 카드가 ⏳ → ✅ 로 자동 업데이트
```

---

## 3. 시스템 아키텍처

```
┌─────────────────────────────────────────────────────────────────┐
│  STEP 1: 리포트 수집 확대 (report_watcher.py)                    │
│  BlackRock / Kiwoom / 삼성증권 / NH / 미래에셋 / KB / 한투        │
│  → PDF 다운로드 → Redis(REPORT_ANALYSIS) 발행                    │
└──────────────────────────┬──────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────────┐
│  STEP 2: AI 테마 추출 (worker/modules/ai/)                       │
│  Gemini: PDF 요약 → 구조화된 themes JSON 추출                    │
│  { sector: "반도체", sentiment: "positive", confidence: 0.85,   │
│    reason: "...", stocks: ["삼성전자", "SK하이닉스"] }            │
└──────────────────────────┬──────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────────┐
│  STEP 3: D1 저장 (POST /api/insights)                           │
│  insights 테이블: week_key / source / themes / status           │
│  weekly_consensus 뷰: 여러 기관 공통 테마 집계                    │
└──────────────┬───────────────────────┬──────────────────────────┘
               │                       │
┌──────────────▼──────────┐  ┌─────────▼───────────────────────────┐
│  STEP 4: /insights 페이지 │  │  STEP 5: 자동 확인 루프              │
│  (Next.js Dashboard)    │  │  condition_watcher → 섹터 급등락      │
│  - 이번 주 컨센서스      │  │  → D1 insights 조회 → 매칭 시         │
│  - 예측 카드 목록        │  │  "예측 일치" 노트 추가 + 텔레그램 발송 │
│  - ⏳/✅/❌ 상태 표시    │  └─────────────────────────────────────┘
└─────────────────────────┘
```

---

## 4. D1 Schema 추가

```sql
-- 기관 리포트 분석 결과 (주별 누적)
CREATE TABLE IF NOT EXISTS insights (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  week_key TEXT NOT NULL,              -- '2026-W13' 형식
  source TEXT NOT NULL,               -- 'BlackRock', 'Kiwoom', '삼성증권' 등
  report_title TEXT,
  report_url TEXT,
  summary TEXT,                        -- AI 요약 전문
  themes TEXT,                         -- JSON: [{ sector, sentiment, confidence, reason, stocks }]
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 예측 검증 이력 (실제 시장과 매칭된 기록)
CREATE TABLE IF NOT EXISTS insight_matches (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  insight_id INTEGER,                  -- insights.id 참조
  week_key TEXT NOT NULL,
  sector TEXT NOT NULL,
  predicted_sentiment TEXT,            -- 'positive' / 'negative' / 'neutral'
  actual_change REAL,                  -- 실제 등락률 (%)
  matched_stocks TEXT,                 -- JSON: 매칭된 종목들
  status TEXT DEFAULT 'pending',       -- 'pending' / 'confirmed' / 'failed'
  matched_at DATETIME,
  FOREIGN KEY (insight_id) REFERENCES insights(id)
);

CREATE INDEX IF NOT EXISTS idx_insights_week ON insights(week_key);
CREATE INDEX IF NOT EXISTS idx_insight_matches_week ON insight_matches(week_key);
```

---

## 5. 개발 단계 (Milestones)

### Phase 1: 리포트 소스 확대 + D1 저장 파이프라인
**목표**: 기존 2개(BlackRock, Kiwoom) → 6~8개로 확대, 분석 결과 D1에 저장

**추가 소스 (네이버 금융 크롤링)**
| 증권사 | 리포트명 | 주기 |
|--------|----------|------|
| 삼성증권 | 글로벌 주식 전략 / 주간 시황 | 주 1회 |
| NH투자증권 | 주간 투자전략 | 주 1회 |
| 미래에셋 | 주간 글로벌 마켓 | 주 1회 |
| KB증권 | 주간 투자전략 | 주 1회 |
| 한국투자증권 | 주간 전략 | 주 1회 |

**파일 수정:**
- `watcher/tasks/report_watcher.py` — 소스 추가 (네이버 금융 brokerCode별)
- `worker/main.py` — `REPORT_ANALYSIS` 처리 후 `/api/insights` POST 추가
- `frontend_web/src/app/api/insights/route.ts` — POST(저장) / GET(조회) 엔드포인트
- `frontend_web/schema.sql` — insights, insight_matches 테이블 추가

**AI 프롬프트 변경:**
```
기존: "이 리포트를 요약해줘"
변경: "이 리포트에서 다음 주 주목할 섹터/테마를 JSON으로 추출해줘.
       각 항목: sector(섹터명), sentiment(positive/negative/neutral),
       confidence(0~1), reason(근거 1문장), stocks(관련 종목 배열)"
```

---

### Phase 2: /insights 대시보드 페이지
**목표**: 주간 인사이트를 한눈에 볼 수 있는 페이지

**UI 구성:**
```
/insights
├── 헤더: "2026년 13주차 기관 컨센서스"
├── 컨센서스 섹터 카드 (여러 기관이 공통 언급한 섹터)
│   ├── 🟢 반도체 — 긍정 (BlackRock, Kiwoom, 삼성증권 3곳 동의)
│   ├── 🔴 방산 — 주의 (2곳 동의)
│   └── 🟡 2차전지 — 중립 (1곳)
├── 리포트별 상세 카드 (펼치기/닫기)
│   ├── BlackRock Weekly: 요약 + 근거
│   └── Kiwoom Weekly: 요약 + 근거
└── 예측 검증 히스토리 (지난 주 예측 vs 실제)
    ├── ✅ 반도체 긍정 → 삼성전자 +5.2% (일치)
    └── ❌ 2차전지 긍정 → POSCO홀딩스 -2.1% (빗나감)
```

**파일 신규 생성:**
- `frontend_web/src/app/insights/page.tsx`
- `frontend_web/src/components/InsightCard.tsx`
- `frontend_web/src/components/ConsensusBoard.tsx`

---

### Phase 3: 자동 예측 확인 루프
**목표**: 실시간 조건 감지 시 예측과 자동 매칭

**로직 (condition_watcher.py 또는 condition_watcher_us.py):**
```python
# 종목 급등락 감지 후 실행
async def check_insight_match(sector: str, change_rate: float, stocks: list):
    # D1에서 이번 주 해당 섹터 예측 조회
    resp = await fetch_insights_by_sector(sector)
    if not resp: return None

    # 매칭 기준: 예측 방향과 실제 방향 일치 여부
    for insight in resp:
        predicted = insight['sentiment']  # 'positive' / 'negative'
        actual = 'positive' if change_rate > 0 else 'negative'

        if predicted == actual and abs(change_rate) >= 3.0:  # 3% 이상일 때만
            # D1 insight_matches 저장
            await save_insight_match(insight, change_rate, stocks)
            # Stock Now Note 반환
            return f"(Stock Now Note: 이 흐름은 {insight['week_key']} 기관 리포트에서 " \
                   f"예측한 **'{sector} {predicted}'** 시나리오와 일치합니다. " \
                   f"근거: {insight['source']} — {insight['reason']})"
    return None
```

**파일 수정:**
- `watcher/tasks/condition_watcher.py` — `check_insight_match()` 호출 추가
- `watcher/tasks/condition_watcher_us.py` — 동일
- `frontend_web/src/app/api/insights/route.ts` — PATCH(상태 업데이트) 추가

---

### Phase 4: 텔레그램 인사이트 요약 발송
**목표**: 월요일 아침 자동으로 주간 인사이트 요약 텔레그램 발송

**발송 시점**: 월요일 08:00 KST (KR-Scheduler에 추가)

**메시지 형식:**
```
📊 [이번 주 기관 컨센서스]
━━━━━━━━━━━━━━━━━━━━

🟢 반도체 — 긍정 전망 (3개 기관)
"AI 수요 지속 + HBM 공급 타이트"

🔴 방산 — 주의 (2개 기관)
"중동 종전 기대감으로 단기 모멘텀 약화"

🟡 2차전지 — 중립 (1개 기관)
"미국 IRA 정책 불확실성 지속"

━━━━━━━━━━━━━━━━━━━━
📌 상세 분석: https://stock-now.pages.dev/insights
```

**파일 수정:**
- `watcher/tasks/report_watcher.py` 또는 `condition_watcher.py` — 월요일 08:00 트리거 추가

---

## 6. 기술 스택 및 의존성

| 구성 요소 | 기술 | 비고 |
|-----------|------|------|
| 리포트 수집 | Python `requests` + `BeautifulSoup` | 기존 코드 확장 |
| PDF 분석 | Gemini API (`gemini-2.5-pro-exp`) | 기존 AI 모듈 활용 |
| 테마 추출 | Gemini structured output (JSON mode) | 프롬프트 변경 필요 |
| 데이터 저장 | Cloudflare D1 (`insights`, `insight_matches`) | schema.sql 추가 |
| API 엔드포인트 | Next.js App Router Route Handler | `/api/insights` |
| 대시보드 UI | Next.js + Tailwind CSS | `/insights` 페이지 |
| 매칭 로직 | Python async (condition_watcher) | D1 API 호출 |

---

## 7. 우선순위 및 난이도

| Phase | 내용 | 난이도 | 우선순위 |
|-------|------|--------|----------|
| Phase 1 | D1 저장 파이프라인 + 소스 확대 | ★★☆ | 🔴 높음 (기반) |
| Phase 2 | /insights 대시보드 페이지 | ★★☆ | 🔴 높음 (사용자 가치) |
| Phase 3 | 자동 예측 확인 루프 | ★★★ | 🟡 중간 (차별화) |
| Phase 4 | 텔레그램 요약 발송 | ★☆☆ | 🟡 중간 (편의성) |

**Phase 1 → 2 순서로 진행 권장.**
Phase 1이 완료되어야 Phase 2~4가 의미 있음.

---

## 8. 예상 효과

- **서비스 차별화**: 단순 후행 알림 → 선행 예측 + 검증 피드백 루프
- **구독 유지율 향상**: 매주 월요일 인사이트 확인 습관 형성
- **신뢰도 향상**: "우리가 예측한 것이 실제로 맞았다"는 근거 누적
- **전환율 향상**: 무료 체험 유저가 예측 적중 경험 후 결제 전환 가능성 증가
