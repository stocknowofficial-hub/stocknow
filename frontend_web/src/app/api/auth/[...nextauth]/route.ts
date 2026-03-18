import NextAuth from "next-auth";
import { authOptions } from "@/lib/auth";
import { NextRequest } from "next/server";

// NextAuth 원본 핸들러
const handler = NextAuth(authOptions);

// Cloudflare 실시간 디버깅 래퍼 및 DB 바인딩 주입기
async function handleRequest(req: NextRequest, ctx: any) {
  try {
    // OpenNext 1.17.1 기준 getCloudflareContext 사용
    const { getCloudflareContext } = require("@opennextjs/cloudflare");
    
    if (typeof getCloudflareContext === 'function') {
      const bcontext = getCloudflareContext();
      if (bcontext && bcontext.env && bcontext.env.DB) {
        console.log("[NextAuth Route] SUCCESS! Found DB via getCloudflareContext");
        (globalThis as any).__CF_ENV_DB = bcontext.env.DB;
      } else {
        console.warn("[NextAuth Route] DB not found in getCloudflareContext.env");
      }
    } else {
      console.error("[NextAuth Route] getCloudflareContext is not a function!");
    }
  } catch (e: any) {
    console.warn("[NextAuth Route] getCloudflareContext failed:", e.message);
  }
  
  // 만약 아직도 없다면 process.env에서 DB 키를 가진 객체 필사적 탐색
  if (!(globalThis as any).__CF_ENV_DB) {
    const env = process.env as any;
    for (const key in env) {
      if ((key === "DB" || key.includes("D1")) && env[key] && typeof env[key].prepare === 'function') {
        console.log(`[NextAuth Route] Found DB in process.env[${key}]`);
        (globalThis as any).__CF_ENV_DB = env[key];
        break;
      }
    }
  }
  
  try {
    return await handler(req, ctx);
  } catch (error) {
    console.error("[NextAuth FATAL ERROR]", error);
    throw error;
  }
}

export async function GET(req: NextRequest, ctx: any) {
  return handleRequest(req, ctx);
}

export async function POST(req: NextRequest, ctx: any) {
  return handleRequest(req, ctx);
}
