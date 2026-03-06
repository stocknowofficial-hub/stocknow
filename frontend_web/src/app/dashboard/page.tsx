"use client";

import { useSession, signOut } from "next-auth/react";
import Image from "next/image";
import { LogOut, Send, Zap, TrendingUp, AlertCircle, CheckCircle2, ArrowRight } from "lucide-react";
import { useEffect } from "react";
import { useRouter } from "next/navigation";

interface ExtendedUser {
    id?: string;
    name?: string | null;
    email?: string | null;
    image?: string | null;
}

export default function Dashboard() {
    const { data: session, status } = useSession();
    const router = useRouter();

    // Redirect to login if unauthenticated
    // Redirect to login if unauthenticated
    useEffect(() => {
        if (status === "unauthenticated") {
            // router.push("/"); // TEMP: Uncomment when OAuth keys are ready
        }
    }, [status, router]);

    // If loading or unauthenticated, show nothing or a loader
    if (status === "loading") {
        return (
            <div className="min-h-screen bg-[#0f1115] flex items-center justify-center">
                <div className="w-10 h-10 border-4 border-[#00ffd5] border-t-transparent rounded-full animate-spin"></div>
            </div>
        );
    }

    // Mock data for UI
    const mockUser = {
        name: session?.user?.name || "사용자",
        email: session?.user?.email || "user@example.com",
        image: session?.user?.image || "https://api.dicebear.com/7.x/initials/svg?seed=" + (session?.user?.name || "U"),
        telegramLinked: false, // For testing, set to false
        uuid: (session?.user as ExtendedUser)?.id || "mock-uuid-1234",
        krTier: "FREE",
        krExpiry: "2026-03-31",
        usTier: "PRO",
        usExpiry: "2026-12-31",
    };

    const BOT_USERNAME = "Stock_Now_Bot"; // Change to your actual bot id

    return (
        <div className="min-h-screen bg-[#0f1115] text-white selection:bg-[#00ffd5]/30 selection:text-[#00ffd5] pb-20">

            {/* Navbar */}
            <nav className="border-b border-white/5 bg-[#1a1d24]/80 backdrop-blur-xl sticky top-0 z-50">
                <div className="max-w-6xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between">
                    <div className="flex items-center space-x-3">
                        <div className="relative w-8 h-8">
                            <Image src="/logo.png" alt="Logo" fill className="object-contain" />
                        </div>
                        <span className="font-bold text-lg tracking-wider">STOCK <span className="text-[#00ffd5]">NOW</span></span>
                    </div>

                    <div className="flex items-center space-x-4">
                        <div className="hidden sm:block text-right">
                            <p className="text-sm font-medium leading-tight">{mockUser.name}</p>
                            <p className="text-xs text-gray-400">{mockUser.email}</p>
                        </div>
                        {mockUser.image ? (
                            <Image src={mockUser.image} alt="Avatar" width={36} height={36} className="rounded-full ring-2 ring-white/10" />
                        ) : (
                            <div className="w-9 h-9 rounded-full ring-2 ring-white/10 bg-white/10 flex items-center justify-center text-sm font-bold">
                                {mockUser.name?.[0] || "U"}
                            </div>
                        )}
                        <button
                            onClick={() => signOut({ callbackUrl: "/" })}
                            className="p-2 text-gray-400 hover:text-white hover:bg-white/5 rounded-lg transition"
                        >
                            <LogOut className="w-5 h-5" />
                        </button>
                    </div>
                </div>
            </nav>

            {/* Main Content */}
            <main className="max-w-6xl mx-auto px-4 sm:px-6 pt-8 space-y-8">

                {/* Header Section */}
                <div>
                    <h1 className="text-3xl sm:text-4xl font-bold mb-2">
                        환영합니다, <span className="text-transparent bg-clip-text bg-gradient-to-r from-[#00ffd5] to-[#ff3b3b]">{mockUser.name}</span>님 👋
                    </h1>
                    <p className="text-gray-400">당신의 AI 퀀트 포트폴리오와 알림 상태를 확인하세요.</p>
                </div>

                {/* Telegram Linkage Banner (Crucial Call to Action) */}
                {!mockUser.telegramLinked && (
                    <div className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-[#2AABEE]/20 to-[#2AABEE]/5 border border-[#2AABEE]/30 p-6 flex flex-col sm:flex-row items-center justify-between gap-6 shadow-[0_0_30px_rgba(42,171,238,0.1)]">
                        <div className="absolute -right-10 -top-10 text-[#2AABEE]/10 w-40 h-40 origin-center rotate-12 pointer-events-none">
                            <Send className="w-full h-full" />
                        </div>
                        <div className="z-10 relative">
                            <h3 className="text-xl font-bold text-white flex items-center mb-2">
                                <AlertCircle className="w-5 h-5 mr-2 text-[#2AABEE]" />
                                텔레그램 알림 시스템 활성화가 필요합니다!
                            </h3>
                            <p className="text-blue-100/70 text-sm max-w-xl">
                                웹에서의 구독 정보와 봇을 연동해야 실시간 종목 감지 모델(Whale Watcher)의 긴급 알림을 놓치지 않고 받을 수 있습니다.
                            </p>
                        </div>
                        <a
                            href={`https://t.me/${BOT_USERNAME}?start=link_${mockUser.uuid}`}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="z-10 whitespace-nowrap bg-[#2AABEE] hover:bg-[#2299d6] text-white px-6 py-3 rounded-xl font-semibold flex items-center transition shadow-lg hover:scale-105 active:scale-95"
                        >
                            <Send className="w-4 h-4 mr-2" />
                            텔레그램 연결하기
                        </a>
                    </div>
                )}

                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">

                    {/* US Market Subscription Card */}
                    <div className="bg-[#1a1d24] border border-white/5 rounded-2xl p-6 relative overflow-hidden group">
                        <div className="absolute top-0 right-0 w-32 h-32 bg-[#ff3b3b] rounded-full blur-[100px] opacity-[0.15] group-hover:opacity-30 transition-opacity"></div>
                        <div className="flex justify-between items-start mb-6">
                            <div>
                                <p className="text-sm text-gray-400 font-medium mb-1">🇺🇸 미국 주식 (US Market)</p>
                                <h3 className="text-2xl font-bold flex items-center">
                                    PRO Plan
                                    <span className="ml-3 px-2 py-0.5 rounded text-[10px] uppercase font-bold tracking-wider bg-[#ff3b3b]/20 text-[#ff3b3b] border border-[#ff3b3b]/30">Active</span>
                                </h3>
                            </div>
                        </div>
                        <div className="space-y-3 mb-6">
                            <div className="flex justify-between text-sm">
                                <span className="text-gray-400">만료일</span>
                                <span className="font-medium">{mockUser.usExpiry}</span>
                            </div>
                            <div className="w-full bg-white/5 rounded-full h-2">
                                <div className="bg-gradient-to-r from-[#ff3b3b]/50 to-[#ff3b3b] h-2 rounded-full w-[70%]"></div>
                            </div>
                            <p className="text-xs text-gray-500 text-right">약 9개월 남음</p>
                        </div>
                        <button className="w-full py-3 bg-white/5 hover:bg-white/10 border border-white/10 rounded-xl text-sm font-semibold transition text-white">
                            기간 연장하기 (Payapp)
                        </button>
                    </div>

                    {/* KR Market Subscription Card */}
                    <div className="bg-[#1a1d24] border border-white/5 rounded-2xl p-6 relative overflow-hidden group">
                        <div className="absolute top-0 right-0 w-32 h-32 bg-[#00ffd5] rounded-full blur-[100px] opacity-[0.1] group-hover:opacity-20 transition-opacity"></div>
                        <div className="flex justify-between items-start mb-6">
                            <div>
                                <p className="text-sm text-gray-400 font-medium mb-1">🇰🇷 한국 주식 (KR Market)</p>
                                <h3 className="text-2xl font-bold flex items-center text-gray-400">
                                    FREE Plan
                                </h3>
                            </div>
                        </div>
                        <div className="space-y-3 mb-6 flex-1">
                            <div className="flex justify-between text-sm">
                                <span className="text-gray-400">만료일</span>
                                <span className="font-medium">-</span>
                            </div>
                            <p className="text-sm text-gray-500 mt-2">
                                현재 기본 시황 요약 정보만 제공됩니다. 급등주 실시간 포착을 위해 PRO로 업그레이드하세요.
                            </p>
                        </div>
                        <button className="w-full mt-auto py-3 bg-gradient-to-r from-[#00ffd5]/80 to-[#00b395] hover:from-[#00ffd5] hover:to-[#00ceab] text-black rounded-xl text-sm font-extrabold transition shadow-[0_0_15px_rgba(0,255,213,0.3)]">
                            PRO 업그레이드
                        </button>
                    </div>

                    {/* Recent AI Activity (Premium Feel UI) */}
                    <div className="bg-[#1a1d24] border border-white/5 rounded-2xl p-6 flex flex-col lg:col-span-1 md:col-span-2">
                        <h3 className="text-lg font-bold mb-4 flex items-center">
                            <Zap className="w-5 h-5 text-yellow-400 mr-2" />
                            최근 감지 알고리즘 대시보드
                        </h3>

                        <div className="flex-1 space-y-4">
                            <div className="flex p-3 rounded-lg bg-white/5 border border-white/5 hover:bg-white/10 transition">
                                <div className="bg-red-500/20 text-red-400 p-2 rounded-lg h-fit mr-3">
                                    <TrendingUp className="w-4 h-4" />
                                </div>
                                <div>
                                    <div className="flex items-center gap-2 mb-1">
                                        <span className="font-bold">NVDA</span>
                                        <span className="text-xs bg-red-500/20 text-red-400 px-1.5 py-0.5 rounded">+4.2% 폭등 감지</span>
                                    </div>
                                    <p className="text-xs text-gray-400 line-clamp-2">미국장 장전 거래에서 기관 대량 매수세 포착. 주요 지지선 돌파 후 랠리 지속 전망 (Gemini Macro-Context 적용)</p>
                                </div>
                            </div>

                            <div className="flex p-3 rounded-lg bg-white/5 border border-white/5 hover:bg-white/10 transition">
                                <div className="bg-blue-500/20 text-blue-400 p-2 rounded-lg h-fit mr-3">
                                    <CheckCircle2 className="w-4 h-4" />
                                </div>
                                <div>
                                    <div className="flex items-center gap-2 mb-1">
                                        <span className="font-bold">삼성전자</span>
                                        <span className="text-xs text-gray-500">2시간 전</span>
                                    </div>
                                    <p className="text-xs text-gray-400 line-clamp-2">외인 순매수 전환 확인. HBM 품질 테스트 통과 관련 비공식 소스 루머 반영됨.</p>
                                </div>
                            </div>
                        </div>

                        <button className="w-full mt-4 text-xs font-medium text-gray-400 hover:text-white transition group flex items-center justify-center">
                            모든 기록 보기
                            <ArrowRight className="w-3 h-3 ml-1 opacity-0 group-hover:opacity-100 -translate-x-2 group-hover:translate-x-0 transition-all" />
                        </button>
                    </div>
                </div>

            </main>
        </div>
    );
}
