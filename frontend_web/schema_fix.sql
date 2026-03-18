-- missing columns to add to users table
-- We run these one by one or in a script. SQLite D1 handles semicolons.
-- If some already exist, the execution might fail, which is fine as long as we make sure the ones we need are added.

ALTER TABLE users ADD COLUMN image TEXT;
ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'user';
ALTER TABLE users ADD COLUMN telegram_id TEXT;
ALTER TABLE users ADD COLUMN trial_started_at DATETIME;
ALTER TABLE users ADD COLUMN referred_by TEXT;
ALTER TABLE users ADD COLUMN created_at DATETIME DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE users ADD COLUMN updated_at DATETIME DEFAULT CURRENT_TIMESTAMP;

-- subscriptions table columns check
-- (Assumed to be correct based on schema.sql, but adds if missing)
-- ALTER TABLE subscriptions ADD COLUMN plan TEXT DEFAULT 'free';
-- ALTER TABLE subscriptions ADD COLUMN status TEXT DEFAULT 'active';
