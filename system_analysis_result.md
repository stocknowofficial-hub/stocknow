# 📊 stock_now 시스템 종합 분석 보고서

> 분석 일자: 2026-04-02
> 분석 범위: 전체 프로젝트 구조 / 아키텍처 / 보안 / 코드 품질 / 개선 방향

---

## 1. 📁 폴더 구조 개요

```
stock_now/
├── backend/           FastAPI (구독자 관리, 분석 로그 DB)
├── common/            공통 설정 (config, redis_client, logger)
├── watcher/           데이터 수집 엔진 (12개 태스크)
│   ├── tasks/         각 수집 워커 (condition, rank, whale, trump, macro...)
│   └── utils/         공통 유틸 (definitions.py 889줄)
├── worker/            Redis 메시지 처리 + 텔레그램 봇
│   └── modules/       AI 분석 (Gemini), 예측카드 생성
│       └── ai/        gemini_search.py / gemini_search_pro.py / prompts.py
├── frontend/          관리자 대시보드 (Docker 컨테이너, Next.js dev서버)
├── frontend_web/      사용자 서비스 (Cloudflare Pages, 프리미엄 구독)
├── data/
│   └── reports/       PDF 리포트 저장소
├── logs/              서비스별 로그 (backend/watcher/worker)
├── docker-compose.yml
├── .env               민감 정보 (KIS, Gemini, Telegram 키)
│
├── [루트 유틸 스크립트 10개]  ← 아래 별도 설명
└── [개발 계획 문서 4개]       ← 관리 필요
```

### 듀얼 프론트엔드 구조

| 항목 | frontend/ | frontend_web/ |
|---|---|---|
| 용도 | 관리자 도구 | 사용자 서비스 |
| 배포 | Docker (포트 3000) | Cloudflare Pages |
| DB | backend SQLite | Cloudflare D1 |
| 접근 | 내부망 | 퍼블릭 |
| 실행 모드 | `npm run dev` | Pages 빌드 배포 |

---

## 2. 🐳 Docker 구성 분석

### 컨테이너 구성 (5개)

| 컨테이너 | 역할 | 포트 |
|---|---|---|
| reason_redis | 메시지 브로커 (pub/sub) | 6379 |
| reason_backend | FastAPI (구독자/로그 DB) | 8000 |
| reason_worker | 텔레그램 봇 + AI 처리 | - |
| reason_watcher | 데이터 수집 (12태스크) | - |
| reason_frontend | 관리자 Next.js 앱 | 3000 |

### ✅ 잘 된 점
- `restart: always` — 컨테이너 자동 재시작
- Redis 데이터 볼륨 영속화 (`redis_data`)
- Self-Healing Restarter (매일 07:00, 19:00 재기동)
- watcher에 외부 DNS(8.8.8.8) 명시

### ⚠️ 개선 필요

**[중요도: 높음]**
- **`frontend`가 `npm run dev`로 운영 중**: 개발 서버이므로 소스맵 노출, 속도 저하, 보안 취약. `npm run build && npm start`로 전환해야 함
- **모든 컨테이너가 전체 코드를 마운트**: `volumes: - .:/app` — backend, worker, watcher 모두 동일한 볼륨 공유. 코드 분리가 없어 한 컨테이너 침해 시 전체 코드 접근 가능

**[중요도: 중간]**
- **헬스체크 없음**: `depends_on`이 컨테이너 '시작'만 확인하고 '준비'는 확인 안 함. Redis나 Backend가 준비되기 전에 Worker/Watcher가 연결 시도할 수 있음
- **내부 네트워크 미정의**: 기본 bridge 네트워크 사용. `networks:` 블록으로 명시적 격리 권장
- **리소스 제한 없음**: `mem_limit`, `cpus` 미설정. 하나의 태스크가 메모리 폭주하면 전체 컨테이너 영향

---

## 3. 🔄 서비스 간 통신 구조

```
[watcher]
  ├── KIS API (HTTP) → 조건검색, 랭킹, 수급
  ├── Truth Social API → 트럼프 SNS
  ├── Gemini API → AI 분석
  ├── CNN / Yahoo Finance → 매크로 지표
  ├── Cloudflare D1 (HTTPS POST) → 매크로, 고래수급, 컨센서스 저장
  └── Redis PUBLISH → stock_alert, news_alert

[worker]
  ├── Redis SUBSCRIBE → stock_alert
  ├── Gemini API → AI 뉴스 요약 / 예측카드
  ├── Backend HTTP → /subscribers (구독자 조회)
  ├── Backend HTTP → /analysis/stock (분석 저장)
  └── Telegram Bot API → 알림 발송

[backend]
  ├── SQLite → 구독자/분석 로그
  └── Redis PUBLISH → (분석 요청 수신)

[frontend_web]
  └── Cloudflare D1 → API Routes (CRUD)
```

### Redis 채널 현황

| 채널명 | 발행자 | 구독자 | 용도 |
|---|---|---|---|
| `stock_alert` | watcher (대부분) | worker | 메인 분석 채널 |
| `news_alert` | condition_watcher | worker | 브리핑 알림 채널 |

> ⚠️ 채널이 2개로 분리되어 있는데, `news_alert`는 condition_watcher만 사용함. 명확하긴 하나 문서화가 별도로 필요함.

---

## 4. 🔒 보안 분석

### ❌ 취약점 (즉시 조치 권장)

**1. CORS 전체 허용 (`backend/main.py`)**
```python
allow_origins=["*"]  # 현재 설정
```
- Backend(포트 8000)가 외부에서 접근 가능하면 모든 출처에서 API 호출 가능
- → 실제 사용 주소로 한정 필요: `["http://localhost:3000", "https://stock-now.pages.dev"]`

**2. Backend API 인증 없음**
- `/subscribers`, `/analysis/*`, `/analyze` 등 모든 엔드포인트에 인증 없음
- 포트 8000이 외부에 열려있으면 누구든 구독자 조회/삭제 가능
- → `X-Secret-Key` 헤더 검증 미들웨어 추가 필요

**3. `PAYMENT_SECRETS`가 코드에 하드코딩 (`common/config.py`)**
```python
PAYMENT_SECRETS: dict = {
    "req_1m": "SECRET_1M_2026",  # ← 코드에 고정값
    "req_6m": "SECRET_6M_2026",
    "req_1y": "SECRET_1Y_2026",
}
```
- 코드 저장소에 시크릿 노출
- → `.env`로 분리 필요 (또는 최소한 `.gitignore`에 `.env` 포함 확인)

**4. 루트에 민감 파일 존재**
- `access_token.txt` — KIS API 토큰 (평문 저장)
- `backup_subscribers.json` — 구독자 데이터 (개인정보)
- → `.gitignore`에 반드시 포함 확인

### ⚠️ 주의 (개선 권장)

**5. `.env` 파일 관리**
- 23개 환경변수가 `.env` 하나에 집중
- `.env.example` 파일이 없어 신규 세팅 시 참고 불가
- → `.env.example` 생성 권장 (값 없이 키만)

**6. Cloudflare Pages API Route 인증**
- `WHALE_SECRET`/`CRON_SECRET`으로 보호된 엔드포인트 존재 → 양호
- 단, 시크릿 값이 config.py 기본값으로 설정되면 빈 문자열 허용 위험

---

## 5. 💻 코드 품질 분석

### ✅ 잘 된 점
- 공통 logger 모듈 분리 (`common/logger.py`)
- watcher 태스크별 파일 분리 (12개)
- Redis pub/sub로 느슨한 결합
- Self-Healing Restarter로 안정성 확보
- Gemini 45초 타임아웃 설정

### ⚠️ 개선 필요

**1. `definitions.py` 비대화 (889줄)**
- 하나의 파일에 KIS API 호출, Telegraph, 조건검색, 각종 상수 혼재
- → `kis_api.py`, `telegraph.py`, `stock_definitions.py` 등으로 분리 권장

**2. 동기 HTTP를 `run_in_executor`로 래핑하는 패턴 혼재**
```python
# macro_watcher.py — requests를 executor로
resp = await loop.run_in_executor(None, lambda: requests.get(...))

# 일부 파일 — aiohttp 사용
async with aiohttp.ClientSession() as session: ...
```
- 전체적으로 `aiohttp`로 통일하는 게 asyncio 친화적

**3. `asyncio.get_event_loop()` 사용 (deprecated)**
- Python 3.10+에서 `get_event_loop()` 대신 `get_running_loop()` 권장
- `condition_watcher.py` 등에서 사용 중

**4. Gemini 클라이언트 인스턴스 중복 생성**
- `gemini_search.py`, `consensus_summary_watcher.py` 등에서 매 호출마다 `genai.Client()` 생성
- → 싱글톤 패턴으로 재사용 권장

**5. 예측 생성기 파일 크기 (541줄)**
- `prediction_generator.py` 단일 파일에 프롬프트, API 호출, 파싱, 저장 혼재
- → 관심사 분리 고려

---

## 6. 🚀 Watcher 태스크 현황

| 태스크 | 주기 | 설명 |
|---|---|---|
| condition_watcher | 60초 | 🇰🇷 국내 조건검색 (시총 100위 ±3%) |
| condition_watcher_us | - | 🇺🇸 미국 조건검색 |
| rank_poller | - | 🇰🇷 국내 랭킹 시황 |
| rank_poller_2 | - | 🇺🇸 미국 랭킹 시황 |
| trump_watcher | - | 트럼프 SNS 감시 |
| report_watcher | - | BlackRock/Kiwoom PDF 리포트 |
| whale_watcher_us | - | 🇺🇸 미국 대량 수급 |
| whale_watcher_kr | - | 🇰🇷 국내 수급 (프로그램+외국인) |
| prediction_price_updater | 2시간 | 예측 가격 업데이트 (OHLC) |
| macro_watcher | 30분 | Fear&Greed, VIX 수집 |
| consensus_summary_watcher | 6시간 | AI 주간 종합 분석 생성 |
| wallstreet_watcher | 24시간 | 증권사 컨센서스 수집 |

**모든 태스크가 단일 프로세스(`watcher/main.py`)에서 `asyncio.gather`로 병렬 실행됨**

> ✅ 장점: 배포 단순
> ⚠️ 단점: 하나의 태스크가 블로킹되면 전체 영향 가능. 현재는 Self-Healing Restarter로 보완 중.

---

## 7. 🗂️ 루트 디렉토리 정리 필요 파일

현재 루트에 개발 유틸 스크립트 10개 + 문서 5개가 산재해 있음.

### 루트 스크립트 현황

| 파일 | 용도 | 정리 방향 |
|---|---|---|
| `analyze_one_report.py` | PDF 수동 분석 | `scripts/` 폴더로 이동 |
| `backup_restore.py` | 구독자 DB 백업/복원 | `scripts/` 폴더로 이동 |
| `check_current_status.py` | 시스템 상태 확인 | `scripts/` 폴더로 이동 |
| `clear_market_logs.py` | 마켓 로그 초기화 | `scripts/` 폴더로 이동 |
| `get_condition_list.py` | KIS 조건 목록 조회 | `scripts/` 폴더로 이동 |
| `migrate_db.py` | DB 마이그레이션 | `scripts/` 폴더로 이동 |
| `reset_logs.py` | 로그 초기화 | `scripts/` 폴더로 이동 |
| `send_promo_broadcast.py` | 홍보 메시지 일괄 발송 | `scripts/` 폴더로 이동 |
| `test_prediction.py` | 예측 테스트 | `scripts/` 폴더로 이동 |
| `verify_k_whale_status.py` | 고래 상태 확인 | `scripts/` 폴더로 이동 |
| `access_token.txt` | KIS 토큰 캐시 | `.gitignore` 확인 필수 |
| `backup_subscribers.json` | 구독자 백업 | `.gitignore` 확인 필수 |
| `telegraph_config_*.json` | 텔레그래프 설정 | `config/` 폴더로 이동 권장 |

### 문서 현황

| 파일 | 상태 |
|---|---|
| `system_manual.md` | ✅ 최신 (2026-04 재작성) |
| `ARCHITECTURE.md` | ⚠️ 갱신 필요 여부 확인 |
| `development_plan.md` | 🗑️ 구버전 — 아카이브 권장 |
| `development_plan_2.md` | 🗑️ 구버전 — 아카이브 권장 |
| `development_plan_3.md` | 🗑️ 구버전 — 아카이브 권장 |
| `migration_guide.md` | ⚠️ 확인 필요 |
| `task_status.md` | ⚠️ 확인 필요 |
| `system_analysis_result.md` | ✅ 이 파일 |

---

## 8. 📈 효율성 분석

### Cloudflare D1 선택 — ✅ 적절
- 프리미엄 사용자 서비스가 Cloudflare Pages + D1으로 운영 → 글로벌 엣지 캐싱, 무료 플랜 내 운영 가능
- KV나 별도 DB 없이 SQL 쿼리 가능

### 듀얼 프론트엔드 — ✅ 합리적 분리
- 관리자 도구(`frontend/`)와 사용자 서비스(`frontend_web/`)를 분리한 설계는 올바름
- 다만 `frontend/`는 dev 서버로 운영 중인 것이 개선 필요

### Redis pub/sub — ✅ 적합
- 느슨한 결합으로 watcher → worker 분리. 확장성 양호.
- 다만 메시지 유실 시 재처리 메커니즘 없음 (Redis Stream 대신 pub/sub 한계)

### 예측 hit/miss 판정 (OHLC 기반) — ✅ 스마트
- 일중 가격 폴링 없이 일봉 고가/저가로 판정 → API 호출 최소화

---

## 9. 🔧 개선 우선순위 요약

### 🔴 즉시 조치 (보안)
1. `PAYMENT_SECRETS` → `.env`로 이전
2. `access_token.txt`, `backup_subscribers.json` → `.gitignore` 확인
3. Backend CORS `allow_origins=["*"]` → 특정 주소로 한정
4. `frontend/` → `npm run dev` → `npm start` (프로덕션 빌드) 전환

### 🟡 단기 개선 (코드 품질)
5. 루트 스크립트 10개 → `scripts/` 폴더로 이동
6. `definitions.py` (889줄) → 역할별 파일 분리
7. `requests` + `run_in_executor` → `aiohttp`로 통일
8. `asyncio.get_event_loop()` → `asyncio.get_running_loop()`로 교체
9. `.env.example` 파일 생성

### 🟢 장기 개선 (아키텍처)
10. Docker Compose 헬스체크 추가
11. 컨테이너 리소스 제한 설정
12. 내부 네트워크 명시적 정의
13. Redis pub/sub → Redis Stream 마이그레이션 검토 (메시지 유실 방지)
14. 구버전 development_plan 문서 아카이브

---

## 10. 💪 전체 평가

| 항목 | 점수 | 코멘트 |
|---|---|---|
| 아키텍처 설계 | ⭐⭐⭐⭐ | watcher/worker/backend 분리 명확, 이중 프론트 합리적 |
| 보안 | ⭐⭐ | CORS 전체허용, 인증 미비, 코드 내 시크릿 존재 |
| 코드 품질 | ⭐⭐⭐ | 파일 분리 양호, 일부 대형 파일/패턴 불일치 |
| 운영 안정성 | ⭐⭐⭐⭐ | Self-Healing, restart always, 타임아웃 처리 |
| 확장성 | ⭐⭐⭐ | Redis 기반 확장 가능, 태스크 단일 프로세스 한계 |
| 문서화 | ⭐⭐⭐ | system_manual.md 최신화됨, 구버전 문서 정리 필요 |

**총평**: 개인 프로젝트 수준을 넘어 실제 서비스로 잘 성장한 구조. AI 분석 파이프라인과 실시간 데이터 수집이 유기적으로 연결된 점이 강점. 보안 부분을 보완하면 완성도가 크게 올라갈 것.
