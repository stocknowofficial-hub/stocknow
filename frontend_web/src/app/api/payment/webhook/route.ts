import { NextResponse } from "next/server";

export async function POST(request: Request) {
  try {
    const formData = await request.formData();
    const data = Object.fromEntries(formData.entries());

    // Payapp parameters
    const userid = data.userid;
    const linkkey = data.linkkey;
    const state = data.state; // 1: 결제완료
    const userId = data.var1 as string; // We passed this in request
    const planId = data.var2 as string;
    
    // 1. Validation
    if (userid !== process.env.PAYAPP_USER_ID || linkkey !== process.env.PAYAPP_LINK_KEY) {
      console.error("Invalid Webhook Source:", data);
      return new Response("Invalid credentials", { status: 403 });
    }

    if (state !== "1") {
      console.log("Payment not completed or failed:", data);
      return new Response("OK"); // Still return OK to Payapp
    }

    const db = process.env.DB as unknown as import("@cloudflare/workers-types").D1Database;

    // 2. Calculate Expiry Extension
    let monthsToAdd = 1;
    if (planId === "premium_3m") monthsToAdd = 3;
    // Add more plans here

    // 3. Update Subscription
    // Check if subscription exists, if not create, if exists extend
    const existingSub = await db
      .prepare("SELECT * FROM subscriptions WHERE user_id = ?")
      .bind(userId)
      .first();

    let newExpiry: Date;
    if (existingSub && existingSub.expires_at) {
      const currentExpiry = new Date(existingSub.expires_at as string);
      // If already expired, start from now
      const baseDate = currentExpiry > new Date() ? currentExpiry : new Date();
      newExpiry = new Date(baseDate);
      newExpiry.setMonth(newExpiry.getMonth() + monthsToAdd);
    } else {
      newExpiry = new Date();
      newExpiry.setMonth(newExpiry.getMonth() + monthsToAdd);
    }

    await db
      .prepare(`
        INSERT INTO subscriptions (user_id, plan, expires_at, status, updated_at)
        VALUES (?, ?, ?, 'active', CURRENT_TIMESTAMP)
        ON CONFLICT(user_id) DO UPDATE SET
          plan = ?,
          expires_at = ?,
          status = 'active',
          updated_at = CURRENT_TIMESTAMP
      `)
      .bind(userId, 'premium', newExpiry.toISOString(), 'premium', newExpiry.toISOString())
      .run();

    // 4. (Optional) Mark Payapp transaction in a payments table
    // (We should have a payments table as per schema.sql)

    return new Response("OK");

  } catch (error) {
    console.error("Webhook processing failed:", error);
    return new Response("Internal Server Error", { status: 500 });
  }
}
