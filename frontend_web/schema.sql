-- Stock Now Cloudflare D1 Schema
-- 이 파일을 D1 DB 생성 후 아래 명령어로 실행하세요:
-- wrangler d1 execute stock-now-db --file=./schema.sql

-- 사용자 테이블 (소셜 로그인 UUID 기반)
CREATE TABLE IF NOT EXISTS users (
    -- 기본 식별자 (소셜 로그인 기반)
    id         TEXT PRIMARY KEY,              -- NextAuth UUID (소셜 로그인 식별자)
    email      TEXT UNIQUE,                   -- 이메일
    name       TEXT,                          -- 웹 가입 이름
    image      TEXT,                          -- 프로필 이미지 URL
    provider   TEXT,                          -- 가입 경로 (google, kakao, naver)

    -- 텔레그램 연동 정보 (마이페이지에서 딥링크 통해 연동)
    telegram_chat_id   TEXT UNIQUE,           -- 텔레그램 Chat ID (봇 연동 후 채움)
    telegram_username  TEXT,                  -- 텔레그램 @handle

    -- 구독 정보 (마켓별 분리 관리)
    kr_tier          TEXT NOT NULL DEFAULT 'FREE',  -- 한국장 등급 (FREE, PRO)
    kr_expiry_date   DATETIME,                      -- 한국장 구독 만료일
    us_tier          TEXT NOT NULL DEFAULT 'FREE',  -- 미국장 등급 (FREE, PRO)
    us_expiry_date   DATETIME,                      -- 미국장 구독 만료일

    -- 부가 정보
    payment_cycle    TEXT,                    -- MONTHLY, YEARLY
    referrer_id      TEXT,                    -- 나를 초대한 사람의 UUID (users.id 참조)
    is_active        INTEGER NOT NULL DEFAULT 1,  -- 계정 활성 상태 (1=활성, 0=비활성)

    created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (referrer_id) REFERENCES users(id)
);

-- 결제 이력 테이블
CREATE TABLE IF NOT EXISTS payments (
    id                 TEXT PRIMARY KEY,      -- 결제 고유 ID (UUID)
    user_id            TEXT NOT NULL,         -- 결제한 유저 UUID (users.id 참조)
    payapp_receipt_id  TEXT UNIQUE,           -- Payapp 거래 ID (중복 결제 방지용)
    amount             INTEGER NOT NULL,      -- 결제 금액 (원)
    market_type        TEXT NOT NULL,         -- KR, US, BOTH
    duration_days      INTEGER NOT NULL DEFAULT 30,  -- 구독 기간 (일)
    status             TEXT NOT NULL DEFAULT 'COMPLETED', -- COMPLETED, REFUNDED, FAILED
    created_at         DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- Telegram 딥링크 연동 OTP 토큰 테이블
-- 마이페이지에서 "텔레그램 연결하기" 클릭 시 임시 토큰 생성 -> 봇이 수신 후 chat_id 매핑
CREATE TABLE IF NOT EXISTS telegram_link_tokens (
    token      TEXT PRIMARY KEY,             -- 랜덤 토큰 (링크에 포함)
    user_id    TEXT NOT NULL,                -- 연동할 유저 UUID
    expires_at DATETIME NOT NULL,            -- 토큰 만료 시각 (생성 후 10분)
    used       INTEGER NOT NULL DEFAULT 0,   -- 사용 여부 (0=미사용, 1=사용)
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- 인덱스 (빠른 조회를 위해)
CREATE INDEX IF NOT EXISTS idx_payments_user_id ON payments(user_id);
CREATE INDEX IF NOT EXISTS idx_users_telegram_chat_id ON users(telegram_chat_id);
CREATE INDEX IF NOT EXISTS idx_telegram_link_tokens_user_id ON telegram_link_tokens(user_id);
