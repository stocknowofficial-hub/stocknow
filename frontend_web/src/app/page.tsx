"use client";

import Image from "next/image";
import { ArrowRight } from "lucide-react";
import { signIn } from "next-auth/react";

export default function Home() {
  return (
    <div className="min-h-screen bg-[#0f1115] flex flex-col items-center justify-center p-4 relative overflow-hidden">
      {/* Background glowing effects based on Brand colors (Mint & Red) */}
      <div className="absolute top-[0%] left-[-10%] w-[50%] h-[50%] bg-[#00ffd5] rounded-full blur-[200px] opacity-[0.15] animate-pulse" />
      <div className="absolute bottom-[0%] right-[-10%] w-[50%] h-[50%] bg-[#ff3b3b] rounded-full blur-[200px] opacity-[0.1] animate-pulse" style={{ animationDelay: '1s' }} />

      {/* Main Login Card */}
      <div className="bg-[#1a1d24]/60 backdrop-blur-2xl border border-white/10 rounded-3xl p-8 w-full max-w-md shadow-2xl z-10">

        {/* Logo Section */}
        <div className="flex flex-col items-center mb-10">
          <div className="relative w-36 h-36 mb-4 filter drop-shadow-[0_0_20px_rgba(255,59,59,0.3)] transition-transform hover:scale-105 duration-300">
            {/* User's Custom Logo */}
            <Image
              src="/logo.png"
              alt="Stock Now Logo"
              fill
              className="object-contain"
              priority
            />
          </div>
          <h1 className="text-4xl font-extrabold tracking-tight text-white mb-2 text-center drop-shadow-md">
            STOCK <span className="text-[#00ffd5]">NOW</span>
          </h1>
          <p className="text-gray-400 text-sm text-center font-medium">
            AI 기반 주식 퀀트 분석 및 텔레그램 실시간 알림
          </p>
        </div>

        {/* Login Buttons */}
        <div className="space-y-4">
          <button
            onClick={() => signIn("google", { callbackUrl: "/dashboard" })}
            className="w-full relative group overflow-hidden rounded-xl bg-[#ffffff] text-[#000000] font-semibold py-4 px-6 flex items-center justify-center transition-all hover:scale-[1.02] hover:shadow-[0_0_20px_rgba(255,255,255,0.2)]"
          >
            <svg className="w-5 h-5 mr-3" viewBox="0 0 24 24">
              <path fill="currentColor" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" />
              <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
              <path fill="#FBBC05" d="M5.84 14.1c-.22-.66-.35-1.36-.35-2.1s.13-1.44.35-2.1V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.62z" />
              <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z" />
            </svg>
            구글 계정으로 로그인
            <ArrowRight className="w-4 h-4 absolute right-4 opacity-0 group-hover:opacity-100 group-hover:translate-x-1 transition-all" />
          </button>

          <button
            onClick={() => signIn("kakao", { callbackUrl: "/dashboard" })}
            className="w-full relative group overflow-hidden rounded-xl bg-[#FEE500] text-[#000000] font-semibold py-4 px-6 flex items-center justify-center transition-all hover:scale-[1.02] hover:shadow-[0_0_20px_rgba(254,229,0,0.2)]"
          >
            <svg className="w-5 h-5 mr-3" viewBox="0 0 24 24" fill="currentColor">
              <path d="M12 3c-4.97 0-9 3.18-9 7.11 0 2.53 1.7 4.75 4.3 5.96L6.55 19c-.06.2.14.37.31.25l3.86-2.61c.42.04.85.07 1.28.07 4.97 0 9-3.18 9-7.11C21 6.18 16.97 3 12 3z" />
            </svg>
            카카오 계정으로 로그인
            <ArrowRight className="w-4 h-4 absolute right-4 opacity-0 group-hover:opacity-100 group-hover:translate-x-1 transition-all" />
          </button>

          <button
            onClick={() => signIn("naver", { callbackUrl: "/dashboard" })}
            className="w-full relative group overflow-hidden rounded-xl bg-[#03C75A] text-white font-semibold py-4 px-6 flex items-center justify-center transition-all hover:scale-[1.02] hover:shadow-[0_0_20px_rgba(3,199,90,0.2)]"
          >
            <svg className="w-6 h-6 mr-[10px] ml-[-2px]" viewBox="0 0 24 24" fill="currentColor">
              <path d="M16.27 10.64v6.62h-4.2V8.47l-4.14 8.79H4V4.54h4.2v6.2l4.14-8.73h3.93v8.63z" />
            </svg>
            네이버 계정으로 로그인
            <ArrowRight className="w-4 h-4 absolute right-4 opacity-0 group-hover:opacity-100 group-hover:translate-x-1 transition-all" />
          </button>
        </div>

        {/* Form Separator */}
        <div className="flex items-center my-6">
          <div className="flex-1 border-t border-white/10"></div>
          <span className="px-3 text-xs text-gray-500 uppercase tracking-widest">or continue as guest</span>
          <div className="flex-1 border-t border-white/10"></div>
        </div>

        <button className="w-full relative rounded-xl bg-transparent border border-white/20 text-gray-300 font-medium py-3.5 px-6 transition-all hover:bg-white/5 hover:text-white">
          서비스 둘러보기
        </button>

        {/* Footer info */}
        <div className="mt-8 text-center text-xs text-gray-500 space-y-1">
          <p>가입 시 Stock Now의 <a href="#" className="underline hover:text-white transition-colors">이용약관</a> 및 <a href="#" className="underline hover:text-white transition-colors">개인정보처리방침</a>에</p>
          <p>동의하는 것으로 간주합니다.</p>
        </div>
      </div>
    </div>
  );
}
