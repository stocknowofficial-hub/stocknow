import { NextRequest, NextResponse } from "next/server";
import { getToken } from "next-auth/jwt";

// 로그인한 사용자만 접근 가능한 API 경로
const PROTECTED_API = [
  "/api/history",
  "/api/consensus-data",
  "/api/consensus-summary",
  "/api/whale-feed",
  "/api/reports",
  "/api/wallstreet",
  "/api/macro",
  "/api/predictions",
];

export async function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // 보호된 API 경로: 세션 없으면 401
  // /api/predictions/[id] 는 watcher가 X-Secret-Key로 호출하므로 제외
  const isProtected =
    PROTECTED_API.some((p) => pathname.startsWith(p)) &&
    !(pathname.startsWith("/api/predictions/") && pathname.split("/").length === 4);

  if (isProtected) {
    const token = await getToken({ req: request, secret: process.env.NEXTAUTH_SECRET });
    if (!token) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }
  }

  // 모든 응답에 보안 헤더 추가
  const response = NextResponse.next();
  response.headers.set("X-Content-Type-Options", "nosniff");
  response.headers.set("X-Frame-Options", "SAMEORIGIN");
  response.headers.set("X-XSS-Protection", "1; mode=block");
  response.headers.set("Referrer-Policy", "strict-origin-when-cross-origin");
  response.headers.set("Permissions-Policy", "camera=(), microphone=(), geolocation=()");
  return response;
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};
