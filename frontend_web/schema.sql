-- Users Table (Auth + Profile)
CREATE TABLE IF NOT EXISTS users (
  id TEXT PRIMARY KEY,
  id_type TEXT, -- 'google', 'kakao', 'naver', 'telegram'
  id_social TEXT, -- social provider unique id
  email TEXT,
  emailVerified DATETIME, -- Added for NextAuth compatibility
  name TEXT,
  image TEXT,
  role TEXT DEFAULT 'user',
  telegram_id TEXT,
  telegram_name TEXT,
  mobile TEXT,
  trial_started_at DATETIME, -- Separate trial start tracking
  referred_by TEXT, -- ID of the user who referred this user
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Subscriptions Table
CREATE TABLE IF NOT EXISTS subscriptions (
  user_id TEXT PRIMARY KEY,
  plan TEXT DEFAULT 'free', -- 'free', 'premium', 'pro'
  status TEXT DEFAULT 'active', -- 'active', 'expired', 'canceled'
  expires_at DATETIME,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users (id)
);

-- Referral History Table
CREATE TABLE IF NOT EXISTS referrals (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  referrer_id TEXT NOT NULL, -- The user who invited
  referee_id TEXT NOT NULL,  -- The user who joined
  rewarded BOOLEAN DEFAULT FALSE, -- Whether the 1-month reward was given
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (referrer_id) REFERENCES users (id),
  FOREIGN KEY (referee_id) REFERENCES users (id)
);

-- Auth Sessions (for NextAuth D1 adapter)
CREATE TABLE IF NOT EXISTS accounts (
  id TEXT PRIMARY KEY,
  userId TEXT NOT NULL,
  type TEXT NOT NULL,
  provider TEXT NOT NULL,
  providerAccountId TEXT NOT NULL,
  refresh_token TEXT,
  access_token TEXT,
  expires_at INTEGER,
  token_type TEXT,
  scope TEXT,
  id_token TEXT,
  session_state TEXT,
  FOREIGN KEY (userId) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS sessions (
  id TEXT PRIMARY KEY,
  sessionToken TEXT UNIQUE NOT NULL,
  userId TEXT NOT NULL,
  expires DATETIME NOT NULL,
  FOREIGN KEY (userId) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS verification_tokens (
  identifier TEXT NOT NULL,
  token TEXT NOT NULL,
  expires DATETIME NOT NULL,
  PRIMARY KEY (identifier, token)
);

-- Telegram Link Tokens (for mapping web user to chat_id)
CREATE TABLE IF NOT EXISTS telegram_link_tokens (
  token TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Prediction Tracker (AI 예측 카드 + 결과 트래킹)
CREATE TABLE IF NOT EXISTS predictions (
  id           TEXT PRIMARY KEY,   -- 'pred_20260325_blackrock_001'
  created_at   TEXT DEFAULT (datetime('now')),
  source       TEXT NOT NULL,      -- 'blackrock' | 'kiwoom' | 'trump' | 'briefing'
  source_desc  TEXT,               -- 'BlackRock Weekly 2026-03-23'
  source_url   TEXT,               -- 원본 링크
  prediction   TEXT NOT NULL,      -- "방산 섹터 단기 강세 예상"
  direction    TEXT NOT NULL,      -- 'up' | 'down' | 'sideways'
  target       TEXT NOT NULL,      -- "방산 섹터" | "삼성전자" | "WTI 원유"
  target_code  TEXT,               -- KIS 종목코드 or ETF코드 (없으면 NULL)
  basis        TEXT,               -- AI 근거 한 줄
  timeframe    INTEGER NOT NULL,   -- 며칠 후 체크 (7 | 14 | 30)
  expires_at   TEXT NOT NULL,      -- 결과 체크 기준일
  confidence   TEXT NOT NULL,      -- 'high' | 'medium' | 'low'
  result       TEXT,               -- NULL(진행중) | 'hit' | 'miss' | 'partial'
  result_val   TEXT,               -- 실제 결과값 "+8.3%"
  result_at         TEXT,               -- 결과 확정 시각
  entry_price       REAL,               -- 예측 생성 당시 가격
  current_price     REAL,               -- 현재 가격 (2시간마다 갱신)
  price_change_pct  REAL,               -- 변화율 % (current/entry 기준)
  price_updated_at  TEXT,               -- 마지막 가격 업데이트 시각
  key_points        TEXT                -- JSON 배열 ["근거1", "근거2", "근거3"]
);

-- Whale Feed (수급 현황판 스냅샷 - watcher가 5분마다 업데이트)
CREATE TABLE IF NOT EXISTS whale_feed (
  market TEXT PRIMARY KEY,   -- 'KR', 'US'
  program_items TEXT,        -- JSON array (프로그램 순매수 Top10)
  foreign_items TEXT,        -- JSON array (외국인 순매수 Top10)
  volume_items TEXT,         -- JSON array (거래량 급증 Top20)
  updated_at TEXT DEFAULT (datetime('now'))
);

-- Payments Table (결제 이력 + 중복 방지)
-- plan_id: 'monthly' | 'annual' | 'monthly_kr' | 'monthly_us' | 'premium_monthly' | ...
-- plan:    'standard' | 'standard_kr' | 'standard_us' | 'premium' | ...
CREATE TABLE IF NOT EXISTS payments (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  pay_id TEXT UNIQUE NOT NULL,           -- Payapp 고유 결제 ID (중복 처리 방지)
  user_id TEXT NOT NULL,
  plan_id TEXT NOT NULL,                 -- 결제한 상품 ID (예: 'monthly', 'annual')
  plan TEXT NOT NULL,                    -- 반영될 플랜 (예: 'standard', 'premium')
  amount INTEGER NOT NULL,              -- 결제 금액 (원)
  months INTEGER NOT NULL,              -- 연장 개월 수
  status TEXT DEFAULT 'completed',      -- 'completed' | 'refunded'
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id)
);
