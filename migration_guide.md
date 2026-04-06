# 🚀 Stock Now — 개발/운영 환경 분리 & 맥북 이관 가이드

> **작성 기준**: 2026년 4월 / Windows 개발 + MacBook 운영 + Cloudflare Pages + D1

---

## 전체 구조 한눈에 보기

```
┌─────────────────────────────┐      ┌──────────────────────────────────┐
│   Windows (개발 PC)          │      │   MacBook (운영 서버, 24/7)       │
│                             │      │                                  │
│  코드 수정 & 로컬 테스트      │─git──▶│  git pull → docker compose up    │
│  npm run pages:deploy:dev   │      │  npm run pages:deploy            │
│         ↓                   │      │         ↓                        │
│  [Cloudflare stock-now-dev] │      │  [Cloudflare stock-now (운영)]   │
│  [D1: stock-now-dev-db]     │      │  [D1: stock-now-database (운영)] │
└─────────────────────────────┘      └──────────────────────────────────┘
```

| 구분 | Windows (개발) | MacBook (운영) |
|------|--------------|--------------|
| Cloudflare Pages 프로젝트 | `stock-now-dev` | `stock-now` |
| D1 데이터베이스 | `stock-now-dev-database` | `stock-now-database` |
| Docker 백엔드/워커/왓처 | 로컬 테스트용 | 24/7 상시 운영 |
| 도메인 연결 | ❌ 없음 | ✅ stock-now.pages.dev |
| 배포 명령 | `npm run pages:deploy:dev` | `npm run pages:deploy` |

---

## PART 1 — Cloudflare 개발 환경 셋업 (Windows에서 최초 1회)

### Step 1. dev용 D1 데이터베이스 생성

```bash
cd frontend_web

# 1. dev DB 생성
npx wrangler d1 create stock-now-dev-database
# → 출력된 database_id를 복사해두기!
# 예시 출력:
# database_id = "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
```

### Step 2. wrangler.toml에 dev 환경 추가

`frontend_web/wrangler.toml`을 아래처럼 수정:

```toml
name = "stock-now"
compatibility_date = "2025-03-13"
compatibility_flags = ["nodejs_compat"]
pages_build_output_dir = ".open-next/assets"

# ── 운영 DB ──────────────────────────────────────
[[d1_databases]]
binding = "DB"
database_name = "stock-now-database"
database_id = "9b2b4c73-4743-4740-aaca-8a79f5f7f2b0"
migrations_dir = "migrations"

# ── 개발 DB (로컬 wrangler pages dev 용) ──────────
# [env.dev] 는 Pages에서 지원 안 됨 → 대신 Cloudflare 대시보드 바인딩 사용
# (아래 Step 4 참고)
```

> ⚠️ Cloudflare Pages는 wrangler.toml의 `[env.dev]` 를 지원하지 않습니다.
> D1 바인딩은 **Cloudflare 대시보드**에서 프로젝트별로 설정합니다.

### Step 3. dev용 Pages 프로젝트 생성

```bash
# Cloudflare Pages 프로젝트 생성 (최초 1회)
npx wrangler pages project create stock-now-dev
# → 프로덕션 브랜치: main
```

### Step 4. 대시보드에서 dev D1 바인딩

1. [dash.cloudflare.com](https://dash.cloudflare.com) 접속
2. **Workers & Pages** → `stock-now-dev` 선택
3. **Settings** → **Functions** → **D1 Database Bindings**
4. **Add binding** 클릭:
   - Variable name: `DB`
   - D1 database: `stock-now-dev-database`
5. **Save** 클릭

(운영용 `stock-now` 프로젝트에는 이미 `stock-now-database`가 바인딩되어 있음)

### Step 5. 운영 DB → dev DB로 데이터 복사

```bash
# 운영 DB 전체 export
npx wrangler d1 export stock-now-database --output=prod_backup.sql

# dev DB에 import
npx wrangler d1 execute stock-now-dev-database --file=prod_backup.sql
```

> 이후에는 필요할 때 위 명령으로 dev DB를 운영 DB와 동기화할 수 있음

### Step 6. package.json 배포 스크립트 추가

`frontend_web/package.json`의 `scripts` 섹션에 추가:

```json
"pages:deploy": "npm run pages:build && node scripts/cf-deploy.mjs",
"pages:deploy:dev": "npm run pages:build && node scripts/cf-deploy.mjs --dev"
```

### Step 7. cf-deploy.mjs에 --dev 옵션 추가

`frontend_web/scripts/cf-deploy.mjs` 수정:

```js
import { cpSync, copyFileSync } from "fs";
import { execSync } from "child_process";

const isDev = process.argv.includes('--dev');
const projectName = isDev ? 'stock-now-dev' : 'stock-now';

const commitHash = (() => {
  try { return execSync("git rev-parse --short HEAD").toString().trim(); } catch { return "unknown"; }
})();

const src = ".open-next";
const dest = ".open-next/assets";

copyFileSync(`${src}/worker.js`, `${dest}/_worker.js`);
console.log("✓ Copied worker.js → assets/_worker.js");

try {
  copyFileSync("_routes.json", `${dest}/_routes.json`);
  console.log("✓ Copied _routes.json → assets/_routes.json");
} catch {
  console.log("⚠ _routes.json not found, skipping");
}

for (const dir of ["cloudflare", "middleware", "server-functions", ".build"]) {
  try {
    cpSync(`${src}/${dir}`, `${dest}/${dir}`, { recursive: true });
    console.log(`✓ Copied ${dir}/ → assets/${dir}/`);
  } catch {}
}

console.log(`\n🚀 Deploying to [${projectName}]...\n`);
execSync(
  `npx wrangler pages deploy .open-next/assets --project-name=${projectName} --commit-dirty=true --commit-message="${commitHash}"`,
  { stdio: "inherit" }
);
```

---

## PART 2 — MacBook 운영 서버 초기 셋업 (최초 1회)

### Step 1. 기존 Docker 완전 정리

```bash
# MacBook 터미널
docker compose down --volumes --rmi all
docker system prune -af

# 기존 폴더 삭제
rm -rf ~/stock_now   # 기존 경로에 맞게 조정
```

### Step 2. 최신 코드 클론

```bash
cd ~
git clone https://github.com/[깃허브계정]/[레포이름].git stock_now
cd stock_now
```

### Step 3. 환경변수 파일 생성

```bash
# 프로젝트 루트에 .env 생성
cat > .env << 'EOF'
# ── 텔레그램 ──────────────────────────────────────
TELEGRAM_BOT_TOKEN=운영용_봇_토큰
TELEGRAM_VIP_CHANNEL_ID=-100운영채널ID
TELEGRAM_FREE_CHANNEL_ID=-100무료채널ID

# ── KIS (한국투자증권) ────────────────────────────
KIS_APP_KEY=...
KIS_APP_SECRET=...
KIS_ACCOUNT_NO=...

# ── Redis ─────────────────────────────────────────
REDIS_HOST=redis
REDIS_PORT=6379

# ── Gemini ────────────────────────────────────────
GEMINI_API_KEY=...
EOF
```

> Windows 개발용 `.env`에는 테스트 봇 토큰을 넣어서 운영 채널에 메시지가 가지 않도록 분리

### Step 4. Docker 빌드 & 실행

```bash
cd ~/stock_now
docker compose up -d --build
```

### Step 5. 정상 작동 확인

```bash
# 전체 컨테이너 상태 확인
docker compose ps

# 각 서비스 로그 확인
docker compose logs -f worker     # AI 예측 워커
docker compose logs -f watcher    # 조건검색/트럼프 왓처
docker compose logs -f backend    # 백엔드 API
```

---

## PART 3 — 일상 개발 워크플로우

### 개발 흐름 (Windows)

```
1. 코드 수정 (Windows)
       ↓
2. npm run pages:deploy:dev   ← dev 환경(stock-now-dev)에 배포
       ↓
3. https://stock-now-dev.pages.dev 에서 테스트
       ↓
4. 문제 없으면 git push origin main
```

### 운영 반영 (MacBook)

```bash
# MacBook 터미널에서

# 1. 최신 코드 받기
cd ~/stock_now
git pull

# 2. Docker 서비스 재시작 (변경된 Python 코드 반영)
docker compose up -d --build

# 3. Cloudflare 웹 프론트 배포 (Next.js 변경 시만)
cd frontend_web
npm run pages:deploy
```

> 💡 **Docker는 맥북**에서 직접 배포, **Cloudflare Pages는 Windows에서도 가능**
> (wrangler 인증은 `npx wrangler login`으로 양쪽 모두 로그인되어 있어야 함)

---

## PART 4 — DB 스키마 변경이 있을 때 (마이그레이션)

D1은 SQLite 기반이라 테이블 변경 시 직접 migration SQL을 실행해야 합니다.

```bash
# 1. dev DB에 먼저 적용 & 테스트
npx wrangler d1 execute stock-now-dev-database --command="ALTER TABLE predictions ADD COLUMN new_col TEXT"

# 2. 문제 없으면 운영 DB에 적용
npx wrangler d1 execute stock-now-database --command="ALTER TABLE predictions ADD COLUMN new_col TEXT"
```

> migrations/ 폴더에 SQL 파일로 버전 관리하는 것 권장:
> `migrations/0002_add_new_col.sql`

---

## PART 5 — 문제 발생 시 대응

### 운영 롤백 (Cloudflare Pages)

Cloudflare 대시보드 → `stock-now` → **Deployments** → 이전 배포 옆 `···` → **Rollback to this deployment**

### Docker 재시작 (MacBook)

```bash
# 특정 컨테이너만 재시작
docker compose restart worker
docker compose restart watcher

# 전체 재시작
docker compose down && docker compose up -d
```

### 로그 확인

```bash
docker compose logs -f            # 전체
docker compose logs -f worker     # 워커만
docker compose logs --tail=100 watcher  # 최근 100줄
```

### dev DB 초기화 (운영 DB로 덮어쓰기)

```bash
# 운영 → dev DB 재동기화
npx wrangler d1 export stock-now-database --output=prod_backup.sql
npx wrangler d1 execute stock-now-dev-database --file=prod_backup.sql
```

---

## PART 6 — 체크리스트

### Cloudflare 최초 셋업 체크리스트 (Windows, 1회)
- [ ] `npx wrangler d1 create stock-now-dev-database` 실행 후 ID 기록
- [ ] `npx wrangler pages project create stock-now-dev` 실행
- [ ] 대시보드에서 `stock-now-dev` 프로젝트에 D1 바인딩 (`DB` → `stock-now-dev-database`)
- [ ] 운영 DB export → dev DB import 완료
- [ ] `package.json`에 `pages:deploy:dev` 스크립트 추가
- [ ] `cf-deploy.mjs` 수정 완료
- [ ] `npm run pages:deploy:dev` 테스트 배포 성공 확인

### MacBook 이관 체크리스트 (1회)
- [ ] 기존 Docker/폴더 완전 삭제
- [ ] `git clone` 완료
- [ ] `.env` 파일 생성 (운영용 토큰)
- [ ] `docker compose up -d --build` 성공
- [ ] 각 컨테이너 정상 작동 확인 (`docker compose ps`)
- [ ] `npm run pages:deploy` 로 운영 Cloudflare 배포 확인

### 주간 운영 체크리스트
- [ ] MacBook Docker 컨테이너 전부 `Up` 상태인지 확인
- [ ] watcher.log에 오류 없는지 확인
- [ ] /consensus 페이지 정상 업데이트 확인

---

## 참고: 환경별 설정 요약

| 항목 | Windows (개발) | MacBook (운영) |
|------|--------------|--------------|
| `.env` | 테스트 봇 토큰 | 운영 봇 토큰 |
| Cloudflare 프로젝트 | `stock-now-dev` | `stock-now` |
| D1 DB | `stock-now-dev-database` | `stock-now-database` |
| 배포 명령 | `npm run pages:deploy:dev` | `npm run pages:deploy` |
| 도메인 | `stock-now-dev.pages.dev` | `stock-now.pages.dev` + 커스텀 도메인 |
| 용도 | 기능 개발 & 테스트 | 실 사용자 서비스 |
