import Link from "next/link";
import { MobileNav } from "@/components/MobileNav";
import { DashboardSidebar } from "@/components/DashboardSidebar";
import { getServerSession } from "next-auth/next";
import { authOptions } from "@/lib/auth";
import { redirect } from "next/navigation";

const CURRENT_VERSION = "v1.1.0";

const changelog = [
  {
    version: "v1.1.0",
    date: "2026.04.12",
    label: "공개 베타",
    items: [
      "서비스 공개 베타 런칭",
      "한국장·미국장 고래 수급 실시간 알림 (텔레그램 연동)",
      "트럼프 Truth Social 긴급 분석 2-step 파이프라인",
      "주간 컨센서스 Fear & Greed / VIX 매크로 시그널",
      "예측 성과 히스토리 페이지",
      "구독 연장 기능 (만료일 기준 자동 연장)",
      "친구 초대 혜택 (+7일 보상)",
    ],
  },
];

export default async function ChangelogPage() {
  const session = await getServerSession(authOptions);
  if (!session?.user) redirect("/auth/signin");

  const provider = (session.user.id as string).split("_")[0];

  return (
    <div className="min-h-screen bg-[#0a0a0c] text-white">
      <div className="flex">
        <DashboardSidebar user={session.user} provider={provider} />

        <main className="flex-1 px-4 pt-6 pb-28 lg:px-12 lg:pt-10 lg:pb-12 max-w-2xl mx-auto w-full">
          <div className="mb-8">
            <div className="flex items-center gap-3 mb-1">
              <Link href="/dashboard" className="text-gray-500 hover:text-gray-300 transition-colors text-sm">
                ← 대시보드
              </Link>
            </div>
            <h1 className="text-2xl lg:text-3xl font-bold">업데이트 내역</h1>
            <p className="text-gray-500 text-sm mt-1">Stock Now의 변경 이력을 확인하세요.</p>
          </div>

          <div className="space-y-8">
            {changelog.map((entry) => (
              <div key={entry.version} className="relative pl-6 border-l border-white/10">
                {/* 타임라인 점 */}
                <div className="absolute -left-[5px] top-1.5 w-2.5 h-2.5 rounded-full bg-purple-500" />

                <div className="flex items-center gap-2 mb-3">
                  <span className="font-black text-lg tracking-tight">{entry.version}</span>
                  {entry.version === CURRENT_VERSION && (
                    <span className="text-[10px] px-2 py-0.5 bg-purple-500/20 text-purple-400 rounded-full font-bold">
                      최신
                    </span>
                  )}
                  {entry.label && (
                    <span className="text-[10px] px-2 py-0.5 bg-white/5 text-gray-400 rounded-full">
                      {entry.label}
                    </span>
                  )}
                  <span className="text-xs text-gray-600 ml-auto">{entry.date}</span>
                </div>

                <ul className="space-y-2">
                  {entry.items.map((item, i) => (
                    <li key={i} className="flex items-start gap-2 text-sm text-gray-300">
                      <span className="text-purple-500 mt-0.5 shrink-0">•</span>
                      {item}
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </main>
      </div>
      <MobileNav />
    </div>
  );
}
