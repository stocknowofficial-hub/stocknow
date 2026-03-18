-- Users Table (Auth + Profile)
CREATE TABLE IF NOT EXISTS users (
  id TEXT PRIMARY KEY,
  id_type TEXT, -- 'google', 'kakao', 'naver', 'telegram'
  id_social TEXT, -- social provider unique id
  email TEXT UNIQUE,
  emailVerified DATETIME, -- Added for NextAuth compatibility
  name TEXT,
  image TEXT,
  role TEXT DEFAULT 'user',
  telegram_id TEXT,
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
