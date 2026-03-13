# Stock Now 리뉴얼 Task 현황

## Phase 1: 개발 환경 및 프론트엔드 기초 (Next.js 15)
- [x] 신규 Next.js 프론트엔드(`frontend_web`) 프로젝트 세팅 (로고 적용, UI 잡기)
- [x] 소셜 로그인 기반의 Cloudflare D1 스키마 설계 (`users`, `subscriptions`, `referrals`)
- [x] D1 DB 로컬 초기설정 및 테이블 생성 완료
- [x] NextAuth (Google/Kakao/Naver) 및 D1 어댑터 연동 기초 작업
- [x] 프리미엄 다크 모드 랜딩 페이지 및 대시보드 UI 구현

## Phase 2: 텔레그램 연동 및 추천인 시스템 상세 구현 (현재 진행 중)
- [x] 텔레그램 봇(`/start`) 처리 로직 고도화
    - [x] `/start` 진입 시 자동 1개월 무료 체험 기간 부여
    - [x] 추천인 링크(`/start ref_{chat_id}`) 처리: 추천인에게 1개월 보상 지급
- [x] 웹 대시보드 - 텔레그램 계정 연동 로직 구현
    - [x] 대시보드에서 텔레그램 연동용 일회성 토큰(UUID) 생성
    - [x] 텔레그램 봇으로 토큰 전송 시 웹 계정(`email`)과 텔레그램(`chat_id`) 매핑
- [ ] 무료 기간 만료 알림 및 웹 결제 유도 메시지 발송 로직 [/]

## Phase 3: Payapp 결제 연동 및 구독 자동화 (완료)
- [x] Payapp 결제창 호출 및 Webhook 수신 API 개발
- [x] 대시보드 내 결제 버튼 연동 완료

## Phase 4: 테스트 및 실서버 이관 (진행 중)
- [x] Cloudflare Pages 및 Workers 실서버 배포 완료
- [ ] **[다음]** 실서버 환경 변수 및 D1 바인딩 설정 [/]
- [ ] 소셜 로그인 리다이렉트 URI 업데이트 (Google, Kakao, Naver)
- [ ] 정식 오픈 준비

## Phase 4: 테스트 및 실서버 이관
- [ ] 가입 -> 연동 -> 추천 -> 결제 -> 초대 전 과정 통합 테스트
- [ ] Cloudflare Pages 및 Workers 실서버 배포
- [ ] 정식 오픈 준비
