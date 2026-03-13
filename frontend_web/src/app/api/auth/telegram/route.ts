import { NextResponse } from "next/server";
import { getServerSession } from "next-auth/next";
import { authOptions } from "@/lib/auth";
import { v4 as uuidv4 } from "uuid";

export async function POST() {
  const session = await getServerSession(authOptions);

  if (!session || !session.user) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const token = uuidv4();
  const userId = session.user.id;

  try {
    // Save token to D1
    // Note: In Cloudflare Environment, process.env.DB is the binding
    const db = process.env.DB as unknown as import("@cloudflare/workers-types").D1Database;
    
    await db
      .prepare("INSERT INTO telegram_link_tokens (token, user_id) VALUES (?, ?)")
      .bind(token, userId)
      .run();

    const botUsername = "Stock_Now_Bot"; // Should be env var eventually
    const link = `https://t.me/${botUsername}?start=link_${token}`;

    return NextResponse.json({ link, token });
  } catch (error) {
    console.error("Failed to create link token:", error);
    return NextResponse.json({ error: "Internal Server Error" }, { status: 500 });
  }
}
