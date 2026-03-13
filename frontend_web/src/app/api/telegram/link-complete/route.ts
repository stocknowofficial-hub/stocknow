import { NextResponse } from "next/server";

export async function POST(request: Request) {
  try {
    const { token, chat_id, name } = await request.json();

    if (!token || !chat_id) {
      return NextResponse.json({ error: "Missing parameters" }, { status: 400 });
    }

    const db = process.env.DB as unknown as import("@cloudflare/workers-types").D1Database;
    
    const linkEntry = await db
      .prepare("SELECT user_id FROM telegram_link_tokens WHERE token = ?")
      .bind(token)
      .first();

    if (!linkEntry) {
      return NextResponse.json({ error: "Invalid or expired token" }, { status: 404 });
    }

    const userId = linkEntry.user_id;

    // 2. Update the user with telegram_id
    await db
      .prepare("UPDATE users SET telegram_id = ?, name = COALESCE(name, ?), image = COALESCE(image, ?) WHERE id = ?")
      .bind(chat_id, name, "", userId) // image placeholder as empty string
      .run();

    // 3. Delete the token after use
    await db
      .prepare("DELETE FROM telegram_link_tokens WHERE token = ?")
      .bind(token)
      .run();

    // 4. (Optional) Initialize subscription if new to telegram but already exists in web
    // This part can be expanded based on business logic

    return NextResponse.json({ success: true, userId });
  } catch (error) {
    console.error("Failed to complete telegram link:", error);
    return NextResponse.json({ error: "Internal Server Error" }, { status: 500 });
  }
}
