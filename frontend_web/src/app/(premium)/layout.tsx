import { redirect } from "next/navigation";
import { getServerSession } from "next-auth/next";
import { authOptions } from "@/lib/auth";
import { MobileNav } from "@/components/MobileNav";

export default async function PremiumLayout({ children }: { children: React.ReactNode }) {
  const session = await getServerSession(authOptions);

  // 비로그인 → 로그인 페이지
  if (!session?.user) {
    redirect("/auth/signin");
  }

  // D1에서 구독 조회
  try {
    const { getCloudflareContext } = require("@opennextjs/cloudflare");
    const ctx = getCloudflareContext();
    const db = ctx?.env?.DB;

    if (db) {
      const sub = await db
        .prepare("SELECT plan, status, expires_at FROM subscriptions WHERE user_id = ?")
        .bind(session.user.id)
        .first() as { plan: string; status: string; expires_at: string | null } | null;

      const plan = sub?.plan ?? "free";
      const isPaid = plan !== "free"; // trial 포함 접근 허용

      // 만료 여부 체크 (expires_at이 있는 경우)
      const isExpired = sub?.expires_at
        ? new Date(sub.expires_at) < new Date()
        : false;

      if (!isPaid || isExpired) {
        redirect("/dashboard?upgrade=1");
      }
    }
  } catch {
    // DB 조회 실패 시 대시보드로 (안전한 방향)
    redirect("/dashboard?upgrade=1");
  }

  return <>{children}<MobileNav /></>;
}
