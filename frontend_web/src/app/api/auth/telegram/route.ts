import { NextResponse } from "next/server";
import { getServerSession } from "next-auth/next";
import { authOptions } from "@/lib/auth";
import { v4 as uuidv4 } from "uuid";

function getDB(): import("@cloudflare/workers-types").D1Database | null {
  try {
    const { getCloudflareContext } = require("@opennextjs/cloudflare");
    const ctx = getCloudflareContext();
    if (ctx?.env?.DB) return ctx.env.DB;
  } catch {}
  const g = globalThis as any;
  return g.__CF_ENV_DB ?? (process.env as any).DB ?? null;
}

export async function POST() {
  const session = await getServerSession(authOptions);

  if (!session || !session.user) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const token = uuidv4();
  const userId = session.user.id;

  try {
    const db = getDB();
    console.log("[TelegramLink] DB found:", !!db, "| userId:", userId, "| token:", token);
    if (!db) return NextResponse.json({ error: "DB not available" }, { status: 500 });

    const result = await db
      .prepare("INSERT INTO telegram_link_tokens (token, user_id) VALUES (?, ?)")
      .bind(token, userId)
      .run();

    console.log("[TelegramLink] INSERT result:", JSON.stringify(result));

    // 바로 SELECT해서 저장됐는지 확인
    const check = await db
      .prepare("SELECT token FROM telegram_link_tokens WHERE token = ?")
      .bind(token)
      .first();
    console.log("[TelegramLink] SELECT check:", check ? "FOUND" : "NOT FOUND");

    const botUsername = "Stock_Now_Dev_Bot"; // TODO: move to env var
    const link = `https://t.me/${botUsername}?start=link_${token}`;

    return NextResponse.json({ link, token });
  } catch (error) {
    console.error("[TelegramLink] Failed:", error);
    return NextResponse.json({ error: "Internal Server Error" }, { status: 500 });
  }
}
