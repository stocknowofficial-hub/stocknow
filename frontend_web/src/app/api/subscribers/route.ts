import { NextResponse } from "next/server";

function getDB(): import("@cloudflare/workers-types").D1Database | null {
  try {
    const { getCloudflareContext } = require("@opennextjs/cloudflare");
    const ctx = getCloudflareContext();
    if (ctx?.env?.DB) return ctx.env.DB;
  } catch {}
  const g = globalThis as any;
  return g.__CF_ENV_DB ?? (process.env as any).DB ?? null;
}

export async function POST(request: Request) {
  try {
    const { chat_id, name, referrer_id } = await request.json();

    if (!chat_id) {
      return NextResponse.json({ error: "Missing chat_id" }, { status: 400 });
    }

    const db = getDB();
    if (!db) return NextResponse.json({ error: "DB not available" }, { status: 500 });

    // 1. Check if user already exists (as telegram user or linked user)
    const existingUser = await db
      .prepare("SELECT * FROM users WHERE telegram_id = ? OR id = ?")
      .bind(chat_id, `tg_${chat_id}`)
      .first();

    if (existingUser) {
      return NextResponse.json({ success: true, message: "Already exists", userId: existingUser.id });
    }

    // 2. Create new Telegram-First User
    const userId = `tg_${chat_id}`;
    await db
      .prepare("INSERT INTO users (id, id_type, id_social, name, telegram_id, trial_started_at) VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)")
      .bind(userId, 'telegram', chat_id, name, chat_id)
      .run();

    // 3. Create Subscription (1 Month Free)
    const expiresAt = new Date();
    expiresAt.setMonth(expiresAt.getMonth() + 1);
    
    await db
      .prepare("INSERT INTO subscriptions (user_id, plan, expires_at) VALUES (?, ?, ?)")
      .bind(userId, 'free', expiresAt.toISOString())
      .run();

    // 4. Handle Referral Reward
    let rewardedReferrerId = null;
    if (referrer_id && referrer_id !== chat_id) {
      // Find referrer by their telegram_id or userId
      const referrer = await db
        .prepare("SELECT * FROM users WHERE telegram_id = ? OR id = ?")
        .bind(referrer_id, referrer_id)
        .first();

      if (referrer) {
        // Reward: Extend 1 month
        await db
          .prepare(`
            UPDATE subscriptions 
            SET expires_at = datetime(expires_at, '+1 month') 
            WHERE user_id = ?
          `)
          .bind(referrer.id)
          .run();

        // Record referral
        await db
          .prepare("INSERT INTO referrals (referrer_id, referee_id, rewarded) VALUES (?, ?, ?)")
          .bind(referrer.id, userId, 1)
          .run();

        rewardedReferrerId = referrer.telegram_id || referrer.id;
      }
    }

    return NextResponse.json({ 
      success: true, 
      userId,
      rewarded_referrer_id: rewardedReferrerId
    });

  } catch (error) {
    console.error("Failed to register subscriber:", error);
    return NextResponse.json({ error: "Internal Server Error" }, { status: 500 });
  }
}
