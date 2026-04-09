# Stock Now — Claude 작업 지침

## 🚫 반드시 지켜야 할 규칙

### Git
- **`git add` / `git commit` / `git push` 는 절대 임의로 하지 않는다.**
  - 사용자가 직접 staged 관리 및 commit/push를 처리함
  - 명시적으로 "commit해줘" / "push해줘" 라고 요청할 때만 실행
- `git push --force` 는 절대 금지

### 배포
- **`npm run pages:deploy` (운영 배포)는 임의로 하지 않는다.**
  - 개발 배포(`pages:deploy:dev`)는 자유롭게 가능
  - 운영 배포 전 반드시 확인 요청할 것

---

## 🏗️ 프로젝트 구조 요약

- **MacBook** = 운영 서버 (Docker 24/7)
- **Windows** = 개발 PC (코드 수정 + 테스트)
- **Cloudflare Pages 운영**: `stock-now` → `stock-now.pages.dev`
- **Cloudflare Pages 개발**: `stock-now-dev` → `stock-now-dev.pages.dev`
- **D1 운영 DB**: `stock-now-database`
- **D1 개발 DB**: `stock-now-dev-database`

## 배포 명령
```bash
npm run pages:deploy:dev   # 개발 환경 (자유롭게 가능)
npm run pages:deploy       # 운영 환경 (반드시 확인 후)
```

---

## 💬 커뮤니케이션 스타일
- 한국어로 대화
- 간결하게 핵심만 전달
- 코드 변경 전 영향 범위가 클 경우 먼저 설명하고 확인 받기
