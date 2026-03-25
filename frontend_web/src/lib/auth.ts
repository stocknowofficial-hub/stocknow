import { NextAuthOptions } from "next-auth";
import type { OAuthConfig } from "next-auth/providers/oauth";

// Cloudflare Workers 환경에서 `node:https`, `openid-client` 내부 에러 우회를 위한 Fetch 기반 Provider 생성 유틸

interface GoogleProfile extends Record<string, unknown> {
  sub: string;
  name: string;
  email: string;
  picture: string;
}

function CloudflareGoogleProvider(): OAuthConfig<GoogleProfile> {
  return {
    id: "google",
    name: "Google",
    type: "oauth",
    authorization: {
      url: "https://accounts.google.com/o/oauth2/v2/auth",
      params: { scope: "openid email profile", response_type: "code", prompt: "select_account" },
    },
    token: {
      url: "https://oauth2.googleapis.com/token",
      async request({ params, provider }) {
        const redirect_uri = provider.callbackUrl.replace("http://", "https://");
        const body = new URLSearchParams({
          code: params.code as string,
          client_id: provider.clientId as string,
          client_secret: provider.clientSecret as string,
          redirect_uri,
          grant_type: "authorization_code",
        });
        const res = await fetch("https://oauth2.googleapis.com/token", {
          method: "POST",
          headers: { "Content-Type": "application/x-www-form-urlencoded" },
          body: body.toString(),
        });
        const text = await res.text();
        try {
          const tokens = JSON.parse(text);
          if (tokens.error) console.error("Google Token Error:", tokens);
          return { tokens };
        } catch (e) {
          console.error("Google Token Parse Error! Raw response:", text);
          throw e;
        }
      },
    },
    userinfo: {
      url: "https://openidconnect.googleapis.com/v1/userinfo",
      async request({ tokens }) {
        const res = await fetch("https://openidconnect.googleapis.com/v1/userinfo", {
          headers: { Authorization: `Bearer ${tokens.access_token}` },
        });
        const text = await res.text();
        try {
          return JSON.parse(text);
        } catch (e) {
          console.error("Google UserInfo Parse Error! Raw response:", text);
          throw e;
        }
      },
    },
    profile(profile) {
      return {
        id: profile.sub,
        name: profile.name,
        email: profile.email,
        image: profile.picture,
      };
    },
    clientId: process.env.GOOGLE_CLIENT_ID || "",
    clientSecret: process.env.GOOGLE_CLIENT_SECRET || "",
  };
}

interface KakaoProfile extends Record<string, unknown> {
  id: number;
  kakao_account?: {
    email?: string;
    profile?: {
      nickname?: string;
      thumbnail_image_url?: string;
    };
  };
  properties?: {
    nickname?: string;
    thumbnail_image?: string;
  };
}

function CloudflareKakaoProvider(): OAuthConfig<KakaoProfile> {
  return {
    id: "kakao",
    name: "Kakao",
    type: "oauth",
    authorization: "https://kauth.kakao.com/oauth/authorize",
    token: {
      url: "https://kauth.kakao.com/oauth/token",
      async request({ params, provider }) {
        const redirect_uri = provider.callbackUrl.replace("http://", "https://");
        const body = new URLSearchParams({
          grant_type: "authorization_code",
          client_id: provider.clientId as string,
          client_secret: provider.clientSecret as string,
          redirect_uri,
          code: params.code as string,
        });
        const res = await fetch("https://kauth.kakao.com/oauth/token", {
          method: "POST",
          headers: { "Content-Type": "application/x-www-form-urlencoded" },
          body: body.toString(),
        });
        const text = await res.text();
        try {
          const tokens = JSON.parse(text);
          if (tokens.error) console.error("Kakao Token Error:", tokens);
          return { tokens };
        } catch (e) {
          console.error("Kakao Token Parse Error! Raw response:", text);
          throw e;
        }
      },
    },
    userinfo: {
      url: "https://kapi.kakao.com/v2/user/me",
      async request({ tokens }) {
        const res = await fetch("https://kapi.kakao.com/v2/user/me", {
          headers: {
            Authorization: `Bearer ${tokens.access_token}`,
            "Content-Type": "application/x-www-form-urlencoded;charset=utf-8",
          },
        });
        const text = await res.text();
        try {
          return JSON.parse(text);
        } catch (e) {
          console.error("Kakao UserInfo Parse Error! Raw response:", text);
          throw e;
        }
      },
    },
    profile(profile) {
      return {
        id: profile.id.toString(),
        name: profile.kakao_account?.profile?.nickname || profile.properties?.nickname || "카카오 사용자",
        email: profile.kakao_account?.email || `${profile.id}@kakao.user`,
        image: profile.kakao_account?.profile?.thumbnail_image_url || profile.properties?.thumbnail_image || null,
      };
    },
    clientId: process.env.KAKAO_CLIENT_ID || "",
    clientSecret: process.env.KAKAO_CLIENT_SECRET || "",
  };
}

interface NaverProfile extends Record<string, unknown> {
  response: {
    id: string;
    name?: string;
    nickname?: string;
    email?: string;
    profile_image?: string;
    mobile?: string;
  };
}

function CloudflareNaverProvider(): OAuthConfig<NaverProfile> {
  return {
    id: "naver",
    name: "Naver",
    type: "oauth",
    authorization: "https://nid.naver.com/oauth2.0/authorize",
    token: {
      url: "https://nid.naver.com/oauth2.0/token",
      async request({ params, provider }) {
        const body = new URLSearchParams({
          grant_type: "authorization_code",
          client_id: provider.clientId as string,
          client_secret: provider.clientSecret as string,
          code: params.code as string,
          state: params.state as string,
        });
        const res = await fetch(`https://nid.naver.com/oauth2.0/token?${body.toString()}`, {
          method: "GET",
        });
        const text = await res.text();
        try {
          const tokens = JSON.parse(text);
          if (tokens.error) console.error("Naver Token Error:", tokens);
          return { tokens };
        } catch (e) {
          console.error("Naver Token Parse Error! Raw response:", text);
          throw e;
        }
      },
    },
    userinfo: {
      url: "https://openapi.naver.com/v1/nid/me",
      async request({ tokens }) {
        const res = await fetch("https://openapi.naver.com/v1/nid/me", {
          headers: { Authorization: `Bearer ${tokens.access_token}` },
        });
        const text = await res.text();
        try {
          return JSON.parse(text);
        } catch (e) {
          console.error("Naver UserInfo Parse Error! Raw response:", text);
          throw e;
        }
      },
    },
    profile(profile) {
      return {
        id: profile.response.id,
        name: profile.response.nickname || profile.response.name || "네이버 사용자",
        email: profile.response.email || `${profile.response.id}@naver.user`,
        image: profile.response.profile_image || null,
        mobile: profile.response.mobile || null,
      };
    },
    clientId: process.env.NAVER_CLIENT_ID || "",
    clientSecret: process.env.NAVER_CLIENT_SECRET || "",
  };
}

export const authOptions: NextAuthOptions = {
  // Cloudflare Pages D1 호환성을 위해 JWT 전략 사용
  providers: [
    CloudflareGoogleProvider(),
    CloudflareKakaoProvider(),
    CloudflareNaverProvider()
  ],
  session: {
    strategy: "jwt",
  },
  callbacks: {
    async jwt({ token, user, account }) {
      if (user && account) {
        const customId = `${account.provider}_${account.providerAccountId}`;
        token.id = customId;
        token.provider = account.provider;

        try {
          // Cloudflare Workers 환경에서 안전하게 D1 바인딩 접근
          const env = process.env as Record<string, unknown>;
          const global = globalThis as Record<string, unknown>;
          const envDb = global.__CF_ENV_DB || env.DB || global.DB || env.__NEXT_RUNTIME_D1_DB;
          
          console.log("[Auth Callback] DB Object Check:", envDb ? "Found (Type: D1Database)" : "NOT FOUND");

          if (envDb) {
            const db = envDb as import("@cloudflare/workers-types").D1Database;
            console.log("[Auth Callback] Starting UPSERT for ID:", customId);
            
            const mobile = (user as any).mobile ?? null;
            const userResult = await db.prepare(
                `INSERT INTO users (id, id_type, id_social, email, name, image, mobile)
                 VALUES (?, ?, ?, ?, ?, ?, ?)
                 ON CONFLICT(id) DO UPDATE SET
                   name  = EXCLUDED.name,
                   image = EXCLUDED.image,
                   mobile = COALESCE(EXCLUDED.mobile, users.mobile),
                   updated_at = CURRENT_TIMESTAMP`
              ).bind(
                customId,
                account.provider,
                account.providerAccountId,
                user.email ?? null,
                user.name ?? null,
                user.image ?? null,
                mobile
              ).run();
            
            console.log("[Auth Callback] User UPSERT Success!", userResult.success);

            // 신규 가입 시 7일 무료 체험 자동 부여 (기존 유저는 IGNORE로 건드리지 않음)
            const subResult = await db.prepare(
                `INSERT OR IGNORE INTO subscriptions (user_id, plan, status, expires_at)
                 VALUES (?, 'trial', 'active', datetime('now', '+7 days'))`
              ).bind(customId).run();
              
            console.log("[Auth Callback] Subscription UPSERT Success!", subResult.success);
          }
        } catch (e: any) {
          console.error("[Auth Callback] D1 operation failed!");
          console.error("Error Name:", e.name);
          console.error("Error Message:", e.message);
          if (e.cause) console.error("Error Cause:", e.cause);
        }
      }
      return token;
    },
    async session({ session, token }) {
      if (session.user && token) {
        session.user.id = token.id as string;
      }
      return session;
    },
    async redirect({ url, baseUrl }) {
      if (url.startsWith("/")) return `${baseUrl}${url}`;
      if (url.startsWith(baseUrl)) return url;
      return baseUrl;
    },
  },
  secret: process.env.NEXTAUTH_SECRET,
  pages: {
    signIn: "/auth/signin",
    // 오류가 발생하면 로그인 페이지에 에러 쿼리 파라미터를 추가하여 표시
    error: "/auth/signin", 
  },
  // Cloudflare Pages 특성상 TLS/SSL이 기본 제공되므로 쿠키 보안 강제 설정
  useSecureCookies: true,
  // 문제 발생 시 원인을 파악하기 위해 로깅 활성화
  debug: true,
  // Cloudflare Pages 환경에서 Cross-Site 리다이렉트 후 쿠키 손실/불일치 방지를 위한 명시적 쿠키 설정
  cookies: {
    sessionToken: {
      name: `__Secure-next-auth.session-token`,
      options: { httpOnly: true, sameSite: 'lax', path: '/', secure: true }
    },
    callbackUrl: {
      name: `__Secure-next-auth.callback-url`,
      options: { sameSite: 'lax', path: '/', secure: true }
    },
    csrfToken: {
      name: `__Host-next-auth.csrf-token`,
      options: { httpOnly: true, sameSite: 'lax', path: '/', secure: true }
    },
    pkceCodeVerifier: {
      name: `__Secure-next-auth.pkce.code_verifier`,
      options: { httpOnly: true, sameSite: 'lax', path: '/', secure: true, maxAge: 900 }
    },
    state: {
      name: `__Secure-next-auth.state`,
      options: { httpOnly: true, sameSite: 'lax', path: '/', secure: true, maxAge: 900 }
    },
    nonce: {
      name: `__Secure-next-auth.nonce`,
      options: { httpOnly: true, sameSite: 'lax', path: '/', secure: true }
    }
  },
  logger: {
    error(code, metadata) {
      console.error("NextAuth Error:", code, metadata);
    },
    warn(code) {
      console.warn("NextAuth Warning:", code);
    },
    debug(code, metadata) {
      console.log("NextAuth Debug:", code, metadata);
    }
  },
};
