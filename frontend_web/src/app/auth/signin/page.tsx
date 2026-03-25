'use client';

import { signIn } from "next-auth/react";
import Link from "next/link";

export default function SignInPage() {
  return (
    <main className="min-h-screen bg-[#0a0a0c] text-white flex flex-col items-center justify-center p-6 relative overflow-hidden">
      {/* Background Glow */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[500px] h-[500px] bg-purple-600/10 blur-[120px] rounded-full pointer-events-none" />
      
      <div className="relative z-10 w-full max-w-md">
        {/* Logo & Header */}
        <div className="text-center mb-12">
          <Link href="/" className="inline-flex items-center gap-3 mb-8 hover:opacity-80 transition-opacity">
            <div className="w-12 h-12 bg-gradient-to-br from-purple-500 to-blue-600 rounded-2xl flex items-center justify-center font-bold text-2xl shadow-xl shadow-purple-500/20">
              S
            </div>
            <span className="text-2xl font-bold tracking-tight">StockNow</span>
          </Link>
          <h1 className="text-3xl font-bold mb-3">반갑습니다! 👋</h1>
          <p className="text-gray-500">소셜 계정으로 간편하게 시작하세요.</p>
        </div>

        {/* Login Buttons */}
        <div className="space-y-4">
          {/* Kakao Login */}
          <button
            onClick={() => signIn("kakao", { callbackUrl: "/dashboard" })}
            className="w-full flex items-center justify-center gap-3 px-6 py-4 bg-[#FEE500] text-[#191919] font-bold rounded-2xl hover:bg-[#FEE500]/90 transition-all shadow-lg active:scale-[0.98]"
          >
            <span className="text-xl">💬</span>
            카카오로 시작하기
          </button>

          {/* Naver Login */}
          <button
            onClick={() => signIn("naver", { callbackUrl: "/dashboard" })}
            className="w-full flex items-center justify-center gap-3 px-6 py-4 bg-[#03C75A] text-white font-bold rounded-2xl hover:bg-[#03C75A]/90 transition-all shadow-lg active:scale-[0.98]"
          >
            <span className="text-lg font-black">N</span>
            네이버로 시작하기
          </button>

          {/* Google Login */}
          <button
            onClick={() => signIn("google", { callbackUrl: "/dashboard" }, { prompt: "select_account" })}
            className="w-full flex items-center justify-center gap-3 px-6 py-4 bg-white text-[#191919] font-bold rounded-2xl hover:bg-gray-100 transition-all shadow-lg active:scale-[0.98]"
          >
            <img src="https://www.gstatic.com/firebasejs/ui/2.0.0/images/auth/google.svg" alt="Google" className="w-5 h-5" />
            Google로 시작하기
          </button>
        </div>

        {/* Footer Info */}
        <p className="mt-12 text-center text-sm text-gray-500 leading-relaxed">
          로그인 시 StockNow의 <br />
          <span className="underline cursor-pointer">이용약관</span> 및 <span className="underline cursor-pointer">개인정보처리방침</span>에 동의하게 됩니다.
        </p>

        <div className="mt-8 text-center">
          <Link href="/" className="text-sm text-gray-400 hover:text-white transition-colors">
            ← 메인 화면으로 돌아가기
          </Link>
        </div>
      </div>
    </main>
  );
}
