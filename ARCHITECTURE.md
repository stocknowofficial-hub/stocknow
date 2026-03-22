# Stock Now — 시스템 아키텍처

> 마지막 업데이트: 2026-03-19

---

## 전체 구조 개요

```
[한국투자증권 API / 트럼프 SNS / 리포트]
             │
             ▼
        ┌─────────┐      Redis        ┌──────────┐
        │ Watcher │ ─── pub/sub ────▶ │  Worker  │
        └─────────┘   (stock_alert)   └──────────┘
                                           │
                          ┌────────────────┼────────────────┐
                          ▼                ▼                ▼
                     [Telegram         [Backend         [Cloudflare
                      채널 발송]        FastAPI]          Pages]
                                           │                │
                                      [SQLite DB]      [D1 Database]
```

로컬 머신(Docker Compose)에서 `watcher`, `worker`, `backend`, `redis` 4개 서비스가 돌아가고,
프론트엔드(웹)만 Cloudflare Pages에 배포되어 운영됩니다.

---

## 서비스별 상세 역할

### 1. Watcher (`watcher/`)

**역할**: 시장 데이터를 감시하고 이벤트를 감지하여 Redis로 발행(publish)

**실행 환경**: 로컬 Docker 컨테이너 (`reason_watcher`)

**감시 태스크 목록** (모두 `asyncio.gather`로 동시 실행):

| 태스크 | 파일 | 설명 |
|--------|------|------|
| `run_condition_watcher` | `tasks/condition_watcher.py` | 국내(KR) 주식 조건검색 — 급등 포착 |
| `run_rank_poller` | `tasks/rank_poller.py` | 국내 시황 랭킹 브리핑 |
| `run_us_rank_poller` | `tasks/rank_poller_2.py` | 미국(US) 시황 랭킹 브리핑 |
| `run_condition_watcher_us` | `tasks/condition_watcher_us.py` | 미국 주식 조건검색 — 급등 포착 |
| `run_trump_watcher` | `tasks/trump_watcher.py` | 트럼프 SNS(Truth Social 등) 게시글 감시 |
| `run_report_watcher` | `tasks/report_watcher.py` | 기관 리포트(BlackRock, 키움 등) 분석 |
| `run_whale_watcher_us` | `tasks/whale_watcher_us.py` | 미국 대량 수급(고래) 감지 |
| `run_whale_watcher_kr` | `tasks/whale_watcher_kr.py` | 국내 수급 — 프로그램 매매 / 외국인 |
| `run_scheduled_restarter` | `main.py` | 매일 07:00, 19:00 Self-Destruct (Docker restart: always로 재기동) |

**인증 방식**: 한국투자증권(KIS) API — `approval_key` (웹소켓 승인키) + `access_token` (REST 인증)

**데이터 흐름**:
```
KIS WebSocket / REST API
       │
       ▼
  이벤트 감지 (급등 / 고래 수급 / 트럼프 SNS 등)
       │
       ▼
  Redis PUBLISH → channel: "stock_alert"
```

---

### 2. Worker (`worker/`)

**역할**: Redis 이벤트를 수신하여 Gemini AI 분석 후 텔레그램 채널 발송 + 봇 운영

**실행 환경**: 로컬 Docker 컨테이너 (`reason_worker`)

**주요 URL 참조**:
- `BACKEND_URL`: `http://backend:8000` (Docker 내부 FastAPI)
- `CLOUDFLARE_URL`: `https://stock-now.pages.dev` (프론트엔드 API 호출용)

**기능 1 — 알림 발송 파이프라인**:
```
Redis SUBSCRIBE "stock_alert"
       │
       ▼
  Gemini AI 분석 (뉴스/수급 요약, 감성 분류)
       │
       ▼
  Backend API POST /analysis/stock|market (분석 로그 저장)
       │
       ▼
  텔레그램 채널 발송:
    - 프리미엄 채널 (TELEGRAM_VIP_CHANNEL_ID)
    - 무료 채널 (TELEGRAM_FREE_CHANNEL_ID)
```

**기능 2 — 텔레그램 봇 운영** (`@Stock_Now_Bot` / 개발: `@Stock_Now_Dev_Bot`):

| 명령 / 이벤트 | 처리 |
|--------------|------|
| `/start` (일반) | Backend에 구독자 등록 (2주 무료 체험 자동 적용) |
| `/start link_<TOKEN>` | 웹 유저와 텔레그램 계정 연동 — `CLOUDFLARE_URL/api/telegram/link-complete` 호출 |
| `/start ref_<TG_ID>` | 추천인 처리 (referrer_id 전달) |
| 구독 만료 체크 | 만료 D-3, D-0 알림 발송 |
| 관리자 BCC | 봇이 유저에게 보낸 메시지를 관리자 채팅(TELEGRAM_CHAT_ID)에도 복사 |

**텔레그램 연동 전체 플로우**:
```
웹(대시보드) → POST /api/auth/telegram
    → D1 telegram_link_tokens에 토큰 저장
    → 반환: t.me/Stock_Now_Bot?start=link_<TOKEN>

유저가 링크 클릭 → 봇에서 /start link_<TOKEN> 수신
    → Worker → POST CLOUDFLARE_URL/api/telegram/link-complete
    → 토큰 검증 → D1 users.telegram_id 업데이트 → 토큰 삭제
    → 봇이 "연동 완료" 메시지 발송
```

---

### 3. Backend (`backend/`)

**역할**: 구독자(텔레그램 chat_id 기반) CRUD + 분석 로그 저장

**실행 환경**: 로컬 Docker 컨테이너 (`reason_backend`, port 8000)

**프레임워크**: FastAPI + SQLAlchemy (SQLite, `data/` 폴더에 파일 저장)

**API 엔드포인트**:

| Method | Path | 설명 |
|--------|------|------|
| `POST` | `/subscribers` | 구독자 생성 또는 재활성화 (신규 가입 시 14일 PRO 체험 자동 적용, 추천인 보상 처리) |
| `GET` | `/subscribers` | 활성 구독자 chat_id 목록 반환 |
| `GET` | `/subscribers/detail` | 전체 구독자 상세 정보 (어드민용) |
| `PUT` | `/subscribers/{chat_id}` | 구독자 정보 수정 (tier, is_active, expiry_date 등) |
| `DELETE` | `/subscribers/{chat_id}` | 구독자 삭제 |
| `POST` | `/analysis/stock` | 개별 종목 AI 분석 로그 저장 |
| `POST` | `/analysis/market` | 시장 브리핑/트럼프 분석 로그 저장 |
| `GET` | `/analysis/market/recent` | 최근 N일 시장 분석 조회 (Worker AI context 주입용) |

**추천인 보상 로직** (Backend SQLite 기준):
- 신규 가입 시 `referrer_id` 있으면 추천인 만료일 +14일 연장
- 최대 연장 한도: 현재로부터 60일 (Cap)

> **주의**: Backend SQLite는 텔레그램 봇 구독자 관리용이며, 웹 로그인 유저 정보는 Cloudflare D1에 별도 저장됩니다.

---

### 4. Frontend (`frontend_web/`)

**역할**: 웹 대시보드 — 소셜 로그인, 구독 정보 조회, 텔레그램 연동, 초대 혜택

**실행 환경**: Cloudflare Pages (배포), 로컬 `npm run dev` (개발)

**프레임워크**: Next.js 15 (App Router) + OpenNext (`@opennextjs/cloudflare`)

**소셜 로그인** (NextAuth.js v4, JWT 전략):
- Google, 카카오, 네이버 지원
- Cloudflare Workers 엣지 런타임 호환을 위해 커스텀 Fetch 기반 Provider 구현
- 로그인 시 D1에 `users` + `subscriptions` 레코드 자동 upsert

**페이지 구성**:

| 경로 | 파일 | 설명 |
|------|------|------|
| `/auth/signin` | `app/auth/signin/page.tsx` | 소셜 로그인 페이지 |
| `/dashboard` | `app/dashboard/page.tsx` | 메인 대시보드 — 구독 정보, 초대 코드, 실시간 피드(목업) |
| `/referrals` | `app/referrals/page.tsx` | 초대 혜택 — 초대 코드, 봇 초대 링크, 초대 목록, 보상 현황 |
| `/settings` | `app/settings/page.tsx` | 계정 설정 — 프로필, 텔레그램 연동, 로그아웃 |

**API 라우트**:

| 경로 | 파일 | 설명 |
|------|------|------|
| `/api/auth/[...nextauth]` | NextAuth 핸들러 | OAuth 콜백 처리 |
| `/api/auth/telegram` | `api/auth/telegram/route.ts` | 텔레그램 연동 토큰 생성 |
| `/api/telegram/link-complete` | `api/telegram/link-complete/route.ts` | 봇에서 호출 — 토큰 검증 후 telegram_id 업데이트 |
| `/api/subscribers` | `api/subscribers/route.ts` | 프론트에서 구독자 조회 |

**D1 접근 방식**: `getCloudflareContext().env.DB` (Cloudflare Workers 바인딩)

**공통 컴포넌트**:
- `DashboardSidebar`: 사이드바, `usePathname()`으로 활성 탭 자동 하이라이트
- `TelegramLinkButton`: 연동/연동됨 상태 토글, 딥링크 생성
- `CopyButton`: 클립보드 복사, 2초간 "✓ 복사됨" 피드백
- `SignOutButton`: NextAuth signOut 호출
- `PremiumUpgradeButton`: 프리미엄 업그레이드 CTA

---

### 5. Cloudflare (인프라)

**역할**: 프론트엔드 호스팅 + 엣지 데이터베이스

**서비스 구성**:

| 서비스 | 용도 |
|--------|------|
| **Cloudflare Pages** | Next.js 앱 호스팅 (OpenNext로 Cloudflare Workers 위에서 동작) |
| **Cloudflare D1** (`stock-now-database`) | SQLite 호환 엣지 DB — 웹 유저 전용 |
| **Cloudflare Workers** | Pages 서버리스 함수 실행 환경 |

**D1 데이터베이스 스키마** (`stock-now-database`, ID: `9b2b4c73-...`):

```sql
users                   -- 소셜 로그인 유저, telegram_id, referred_by
subscriptions           -- plan(free/premium/pro), status, expires_at
referrals               -- referrer_id, referee_id, rewarded
telegram_link_tokens    -- 웹-텔레그램 연동 임시 토큰
accounts                -- NextAuth OAuth 계정 정보
sessions                -- NextAuth 세션 (JWT 전략이므로 현재 미사용)
verification_tokens     -- NextAuth 이메일 인증 토큰
```

**배포 방식**:
```bash
# OpenNext 빌드
npx opennextjs-cloudflare build

# Cloudflare Pages 배포
npx wrangler pages deploy .open-next/assets --project-name=stock-now
```

**환경 변수** (Cloudflare Pages Settings에 설정):
- `NEXTAUTH_SECRET`, `NEXTAUTH_URL`
- `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`
- `KAKAO_CLIENT_ID`, `KAKAO_CLIENT_SECRET`
- `NAVER_CLIENT_ID`, `NAVER_CLIENT_SECRET`

---

## 데이터 흐름 요약

### 웹 유저 로그인
```
유저 → /auth/signin → OAuth 제공자 (Google/Kakao/Naver)
    → NextAuth 콜백 → D1 users UPSERT + subscriptions UPSERT
    → JWT 세션 발급 → 대시보드 진입
```

### 텔레그램 연동
```
설정 페이지 → "텔레그램 연동" 클릭
    → POST /api/auth/telegram → D1 telegram_link_tokens에 토큰 저장
    → 딥링크: t.me/Stock_Now_Bot?start=link_<TOKEN>
    → 봇 /start 수신 → POST /api/telegram/link-complete
    → D1 users.telegram_id 업데이트 → 토큰 삭제
    → 봇 "연동 완료" 메시지 발송
```

### 주식 알림 발송
```
KIS WebSocket → Watcher 이벤트 감지
    → Redis PUBLISH "stock_alert"
    → Worker Redis SUBSCRIBE → Gemini AI 분석
    → Backend POST /analysis/* (로그 저장)
    → 텔레그램 채널 메시지 발송 (VIP / 무료)
```

---

## 로컬 개발 실행

```bash
# Docker 서비스 전체 기동
docker compose up -d

# 개별 로그 확인
docker compose logs -f worker
docker compose logs -f watcher
docker compose logs -f backend

# 프론트엔드 로컬 개발
cd frontend_web
npm run dev
```

**주요 포트**:
- `6379`: Redis
- `8000`: Backend (FastAPI)
- `3000`: Frontend (Next.js dev, 현재 Cloudflare Pages로 이전)

---

## 현재 한계 및 향후 과제 (Phase 2+)

| 항목 | 현황 | 향후 계획 |
|------|------|----------|
| 실시간 피드 | 목업 데이터 (하드코딩) | Worker → D1/KV → 웹 실시간 연동 |
| 프리미엄 결제 | 수동 처리 (시크릿 링크) | PG 연동 (토스페이먼츠 등) |
| Backend DB | 로컬 SQLite (Docker 볼륨) | D1 통합 또는 Cloudflare 호환 DB 마이그레이션 |
| 카카오/네이버 로그인 | 구현 완료, 미검증 | 실제 테스트 및 앱 심사 등록 |
| 추천인 보상 | Backend SQLite만 처리 | D1 referrals 테이블과 통합 |
| 어드민 페이지 | 없음 | 구독자 관리 어드민 UI |
