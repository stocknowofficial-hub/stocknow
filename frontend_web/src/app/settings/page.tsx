import { redirect } from "next/navigation";
import { getServerSession } from "next-auth/next";
import { authOptions } from "@/lib/auth";
import { DashboardSidebar } from "@/components/DashboardSidebar";
import { TelegramLinkButton } from "@/components/TelegramLinkButton";
import { MobileNav } from "@/components/MobileNav";
import { SignOutButton } from "@/components/SignOutButton";
import { ReferralCodeInput } from "@/components/ReferralCodeInput";

interface UserRow {
  telegram_id: string | null;
  id_type: string | null;
  created_at: string | null;
  referred_by: string | null;
}

const providerLabel: Record<string, string> = {
  google: "Google",
  kakao: "카카오",
  naver: "네이버",
};

function ProviderBadge({ provider, size = 16 }: { provider: string; size?: number }) {
  if (provider === 'naver') {
    return (
      <span style={{ width: size, height: size, fontSize: size * 0.75 }}
        className="inline-flex items-center justify-center rounded-sm bg-[#03C75A] text-white font-bold leading-none">
        N
      </span>
    );
  }
  if (provider === 'kakao') {
    return (
      <span style={{ width: size, height: size, fontSize: size * 0.75 }}
        className="inline-flex items-center justify-center rounded-sm bg-[#FEE500] text-[#3C1E1E] font-bold leading-none">
        K
      </span>
    );
  }
  return null;
}

export default async function SettingsPage() {
  const session = await getServerSession(authOptions);
  if (!session?.user) redirect("/auth/signin");

  const userId = session.user.id as string;
  let telegramLinked = false;
  let provider = "google";
  let createdAt: string | null = null;
  let referredBy: string | null = null;

  try {
    const { getCloudflareContext } = require("@opennextjs/cloudflare");
    const ctx = getCloudflareContext();
    const db = ctx?.env?.DB as import("@cloudflare/workers-types").D1Database | undefined;
    if (db) {
      const row = await db
        .prepare("SELECT telegram_id, id_type, created_at, referred_by FROM users WHERE id = ?")
        .bind(userId)
        .first<UserRow>();

      telegramLinked = !!row?.telegram_id;
      provider = row?.id_type ?? userId.split("_")[0];
      createdAt = row?.created_at ?? null;
      referredBy = row?.referred_by ?? null;
    }
  } catch (e) {
    console.error("[Settings] D1 fetch failed:", e);
  }

  const joinedDisplay = createdAt
    ? new Date(createdAt).toLocaleDateString("ko-KR", {
        year: "numeric",
        month: "long",
        day: "numeric",
      })
    : "-";

  return (
    <div className="min-h-screen bg-[#0a0a0c] text-white">
      <div className="flex">
        <DashboardSidebar user={session.user} provider={provider} />

        <main className="flex-1">
          <div className="px-4 pt-6 pb-28 lg:px-12 lg:pt-10 lg:pb-12 max-w-2xl mx-auto">
            <header className="mb-6">
              <h2 className="text-2xl lg:text-3xl font-bold mb-1">설정</h2>
              <p className="text-gray-500 text-sm">계정 정보 및 연동 설정을 관리합니다.</p>
            </header>

            <div className="space-y-4">
              {/* 프로필 카드 */}
              <div className="p-6 lg:p-8 rounded-2xl lg:rounded-3xl bg-white/[0.03] border border-white/10">
                <h3 className="text-base font-bold mb-4">프로필</h3>
                <div className="flex items-center gap-4 mb-5">
                  {session.user.image ? (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img
                      src={session.user.image}
                      alt="profile"
                      className="w-14 h-14 rounded-full border-2 border-white/10 object-cover shrink-0"
                    />
                  ) : (
                    <div className="w-14 h-14 rounded-full bg-gradient-to-tr from-gray-700 to-gray-500 border-2 border-white/10 shrink-0" />
                  )}
                  <div>
                    <div className="text-lg font-semibold">{session.user.name || "사용자"}</div>
                    {provider === 'naver' || provider === 'kakao' ? (
                      <div className="mt-0.5">
                        <ProviderBadge provider={provider} size={16} />
                      </div>
                    ) : (
                      <div className="text-sm text-gray-400 mt-0.5">{session.user.email || ""}</div>
                    )}
                  </div>
                </div>
                <div className="space-y-0">
                  <div className="flex items-center justify-between py-3 border-t border-white/5">
                    <span className="text-sm text-gray-400">로그인 방식</span>
                    <span className="text-sm font-medium px-3 py-1 bg-white/5 rounded-full">
                      {providerLabel[provider] ?? provider} 로그인
                    </span>
                  </div>
                  <div className="flex items-center justify-between py-3 border-t border-white/5">
                    <span className="text-sm text-gray-400">가입일</span>
                    <span className="text-sm font-medium">{joinedDisplay}</span>
                  </div>
                </div>
              </div>

              {/* 텔레그램 연동 카드 */}
              <div className="p-6 lg:p-8 rounded-2xl lg:rounded-3xl bg-white/[0.03] border border-white/10">
                <h3 className="text-base font-bold mb-2">텔레그램 연동</h3>
                <p className="text-sm text-gray-400 mb-4 leading-relaxed">
                  텔레그램 계정을 연동하면 실시간 주식 알림을 받을 수 있습니다.
                  연동 버튼을 누르면 봇 채팅이 열리며, 봇에서 시작 버튼을 누르면 자동으로 연동됩니다.
                </p>
                <div className="flex flex-wrap items-center gap-3">
                  <TelegramLinkButton isLinked={telegramLinked} />
                  {telegramLinked && (
                    <span className="text-xs text-gray-500">연동 해제는 고객센터로 문의해주세요.</span>
                  )}
                </div>
              </div>

              {/* 초대 코드 입력 카드 */}
              <div className="p-6 lg:p-8 rounded-2xl lg:rounded-3xl bg-white/[0.03] border border-white/10">
                <h3 className="text-base font-bold mb-2">추천인 코드 입력</h3>
                <p className="text-sm text-gray-400 mb-4 leading-relaxed">
                  친구에게 받은 초대 코드를 입력하면 추천인에게 <span className="text-white font-semibold">7일 보상</span>이 주어집니다.
                  코드는 한 번만 입력 가능합니다.
                </p>
                <ReferralCodeInput alreadyApplied={!!referredBy} />
              </div>

              {/* 계정 관리 카드 */}
              <div className="p-6 lg:p-8 rounded-2xl lg:rounded-3xl bg-white/[0.03] border border-white/10">
                <h3 className="text-base font-bold mb-4">계정 관리</h3>
                <SignOutButton />
              </div>
            </div>
          </div>
        </main>
      </div>
      <MobileNav />
    </div>
  );
}
