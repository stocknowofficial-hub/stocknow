# 🔐 Stock Now 관리자 매뉴얼

> 최종 업데이트: 2026-04-06

---

## 1. 관리자 접속 방법

관리자 페이지는 **로컬에서만** 접근 가능합니다. (외부 공개 안 됨)

```
http://localhost:3000/admin
```

> MacBook에서 Docker 실행 중일 때 접근 가능.
> 원격 접근이 필요하면 SSH 터널링 사용.

**로그인**: `/admin/login` 에서 관리자 계정으로 로그인

---

## 2. 구독자 관리 (`/admin`)

### 화면 구성

| 컬럼 | 설명 |
|------|------|
| 이름/ID | 사용자 이름 + 고유 ID |
| Tier | `free` / `premium` / `pro` |
| 만료일 | 빨간색 = 이미 만료됨 |
| 상태 | `active` / `expired` / `canceled` |
| 액션 버튼 | `[+1M]` `[+2M]` `[🔽]` |

### Tier & 만료일 변경

1. 해당 사용자 행의 **Tier 드롭다운** 변경
2. 만료일 직접 수정 (날짜 입력)
3. **💾 저장** 버튼 클릭 (저장 안 하면 변경 안 됨!)

### 빠른 버튼

| 버튼 | 동작 |
|------|------|
| `[+1M]` | 만료일 +33일 연장 + premium 승급 |
| `[+2M]` | 만료일 +66일 연장 + pro 승급 |
| `[🔽]` | free 등급 강등 + 만료일 제거 |

### 구독자 수동 등록

텔레그램 봇 `/start` 없이 수동 등록이 필요한 경우 Backend API 직접 호출:

```bash
curl -X POST http://localhost:8000/subscribers \
  -H "Content-Type: application/json" \
  -d '{"chat_id": "사용자ID", "tier": "premium", "expires_at": "2026-05-06T00:00:00"}'
```

---

## 3. 리포트 수동 분석 (`/admin/analyze`)

증권사 리포트 PDF를 AI가 자동 수집하지 못했을 때 수동으로 분석 트리거합니다.

### 사용법

1. `http://localhost:3000/admin/analyze` 접속
2. **PDF URL** 입력 (네이버 증권 리포트 링크 또는 직접 PDF 링크)
3. **증권사명** 입력 (예: `키움증권`, `하나증권`)
4. **리포트 제목** 입력 (선택)
5. **🚀 분석 요청 전송** 클릭

### 처리 흐름

```
PDF URL 입력
    ↓
Backend /analyze API 호출
    ↓
PDF 다운로드 → Redis 발행
    ↓
Worker 수신 → Gemini 분석
    ↓
D1 predictions 테이블 저장
    ↓
텔레그램 알림 발송 + 컨센서스 페이지 반영 (수 분 내)
```

### 주의사항
- PDF 링크가 직접 다운로드 가능한 URL이어야 함
- 네이버 증권 리포트: `https://ssl.pstatic.net/imgstock/upload/research/...pdf` 형태

---

## 4. Cloudflare D1 직접 조회/수정

### 조회 (읽기)

```bash
cd frontend_web

# 최근 예측 10개 확인
npx wrangler d1 execute stock-now-database --remote --command="SELECT id, source, target, direction, confidence, result, created_at FROM predictions ORDER BY created_at DESC LIMIT 10"

# 구독자 현황
npx wrangler d1 execute stock-now-database --remote --command="SELECT * FROM subscriptions ORDER BY created_at DESC"

# 이번 주 예측 통계
npx wrangler d1 execute stock-now-database --remote --command="SELECT direction, confidence, COUNT(*) as cnt FROM predictions WHERE created_at >= date('now', '-7 days') GROUP BY direction, confidence"
```

### 수정 (주의!)

```bash
# 예측 결과 수동 수정 (잘못된 hit/miss 정정 시)
npx wrangler d1 execute stock-now-database --remote --command="UPDATE predictions SET result='hit' WHERE id='예측ID'"

# 만료된 예측 정리
npx wrangler d1 execute stock-now-database --remote --command="UPDATE predictions SET result='miss' WHERE result IS NULL AND expires_at < datetime('now')"
```

### DB 백업

```bash
cd frontend_web
npx wrangler d1 export stock-now-database --remote --output=backup_$(date +%Y%m%d).sql
```

---

## 5. Docker 서버 관리 (MacBook)

### 상태 확인

```bash
# 전체 컨테이너 상태
docker compose ps

# 실시간 로그 (전체)
docker compose logs -f

# 서비스별 로그
docker compose logs -f worker     # 텔레그램 봇 + 예측 생성
docker compose logs -f watcher    # 시장 감시 태스크
docker compose logs -f backend    # FastAPI
```

### 재시작

```bash
# 특정 서비스만
docker compose restart worker
docker compose restart watcher
docker compose restart backend

# 전체 재시작
docker compose down && docker compose up -d

# 코드 업데이트 후 재빌드
git pull && docker compose up -d --build
```

### 자동 재기동 스케줄
Watcher는 매일 **07:00, 19:00 KST** 자동 재기동됩니다. (정상 동작)

---

## 6. 구독 링크 발급

### 결제 후 수동 발급

```
# 1개월권
t.me/Stock_Now_Bot?start=req_1m_SECRET_1M_2026

# 6개월권
t.me/Stock_Now_Bot?start=req_6m_SECRET_6M_2026

# 1년권
t.me/Stock_Now_Bot?start=req_1y_SECRET_1Y_2026
```

> 링크를 사용자에게 전달 → 사용자가 봇에서 클릭 → 자동 구독 처리

---

## 7. 정기 점검 체크리스트

### 매일
- [ ] `docker compose ps` — 컨테이너 전부 `Up` 상태인지 확인
- [ ] 텔레그램 채널에 시황 브리핑 정상 수신됐는지 확인

### 매주
- [ ] `/consensus` 페이지 주간 예측 정상 업데이트 확인
- [ ] `/history` 적중률 통계 정상 표시 확인
- [ ] D1 DB 백업 (`npx wrangler d1 export ...`)
- [ ] 만료 구독자 정리 (필요 시 강등 처리)

### 매달
- [ ] dev DB → prod DB 동기화 확인
- [ ] Docker 이미지 업데이트 (`docker compose pull && docker compose up -d --build`)
- [ ] GitHub 레포 Private 상태 확인

---

## 8. 긴급 대응

### 텔레그램 알림이 갑자기 안 올 때
```bash
docker compose logs worker --tail=50
docker compose restart worker
```

### 웹 페이지가 안 보일 때
```bash
# Cloudflare 대시보드에서 롤백
# dash.cloudflare.com → stock-now → Deployments → 이전 배포 → Rollback
```

### 예측이 생성 안 될 때
```bash
docker compose logs worker | grep PredGen
# GOOGLE_API_KEY 확인, worker 재시작
```

### watcher가 멈췄을 때
```bash
docker compose logs watcher --tail=50
docker compose restart watcher
```
