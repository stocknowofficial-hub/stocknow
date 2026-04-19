"use client";

import { useEffect, useRef, useState } from "react";
// eslint-disable-next-line @typescript-eslint/no-explicit-any
const { Joyride } = require("react-joyride") as any;

const STEP_TELEGRAM    = { target: "#tour-telegram-btn",   title: "텔레그램 계정 연동",  content: "Stock Now의 핵심인 '실시간 알림'을 받기 위한 필수 단계입니다. 구독 후 VIP 채널 입장 링크가 텔레그램으로 전송됩니다.", placement: "bottom", skipBeacon: true };
const STEP_UPGRADE     = { target: "#tour-upgrade-btn",    title: "프리미엄 업그레이드", content: "AI 심층 분석부터 트럼프 SNS 긴급 포착까지. 남들보다 한발 빠른 투자 인사이트를 끊김 없이 누려보세요.", placement: "bottom", skipBeacon: true };
const STEP_REFERRAL_CARD = { target: "#tour-referral-card", title: "🎁 친구 초대 혜택", content: "친구 1명 초대 시 구독 기간이 +7일씩 늘어납니다 (최대 20명). '초대 링크 복사' 버튼을 눌러 친구에게 링크를 전달하면, 친구가 가입 후 채널 입장 시 자동으로 적립돼요!", placement: "top", skipBeacon: true };
const STEP_KR          = { target: "#tour-kr-market",      title: "국내 수급 현황",      content: "외국인, 기관, 프로그램의 자금 흐름을 5분 단위로 추적합니다. 지금 시장을 주도하는 진짜 수급을 확인해 보세요.", placement: "top", skipBeacon: true };
const STEP_US          = { target: "#tour-us-market",      title: "미국 시장 현황",      content: "글로벌 시장의 돈이 어디로 몰리는지 직관적으로 파악해 보세요. 내일 장 대응을 위한 확실한 힌트가 여기에 있습니다.", placement: "top", skipBeacon: true };
const STEP_CONSENSUS   = { target: "#tour-nav-consensus",  title: "🧭 컨센서스",         content: "증권사들의 목표주가·투자의견을 한곳에 모아 보여줍니다. 시장 전문가들이 어떤 종목에 주목하는지 바로 확인하세요.", placement: "top", skipBeacon: true };
const STEP_HISTORY     = { target: "#tour-nav-history",    title: "🎯 성과",             content: "AI가 분석한 종목들의 예측 정확도를 추적합니다. 실제 등락 결과와 비교해 AI 신호의 신뢰도를 직접 검증해 보세요.", placement: "top", skipBeacon: true };
const STEP_TRUMP       = { target: "#tour-nav-trump",      title: "🏛️ 트럼프",           content: "트럼프의 SNS·발언을 실시간으로 포착해 시장 영향을 분석합니다. 정치 리스크에 누구보다 빠르게 대응할 수 있습니다.", placement: "top", skipBeacon: true };
const STEP_REFERRALS   = { target: "#tour-nav-referrals",  title: "🎁 초대 현황",        content: "내가 초대한 친구 수와 적립된 추가 기간을 여기서 확인할 수 있어요.", placement: "top", skipBeacon: true };

export default function OnboardingTour({ usFirst = false, onboardingDone = false }: { usFirst?: boolean; onboardingDone?: boolean }) {
  const [run, setRun] = useState(false);
  const saved = useRef(false);

  useEffect(() => {
    if (onboardingDone) return;
    const t = setTimeout(() => setRun(true), 800);
    return () => clearTimeout(t);
  }, [onboardingDone]);

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const handleEvent = (data: any) => {
    const { status } = data ?? {};
    if ((status === "finished" || status === "skipped") && !saved.current) {
      saved.current = true;
      setRun(false);
      fetch("/api/user/onboarding", { method: "PATCH" })
        .then(r => { if (!r.ok) console.error("[Tour] onboarding PATCH failed", r.status); })
        .catch(e => console.error("[Tour] onboarding PATCH error", e));
    }
  };

  if (!run) return null;

  const steps = usFirst
    ? [STEP_TELEGRAM, STEP_UPGRADE, STEP_REFERRAL_CARD, STEP_US, STEP_KR, STEP_CONSENSUS, STEP_HISTORY, STEP_TRUMP, STEP_REFERRALS]
    : [STEP_TELEGRAM, STEP_UPGRADE, STEP_REFERRAL_CARD, STEP_KR, STEP_US, STEP_CONSENSUS, STEP_HISTORY, STEP_TRUMP, STEP_REFERRALS];

  return (
    <Joyride
      steps={steps}
      run={run}
      continuous
      showSkipButton
      showProgress
      scrollToFirstStep
      spotlightClicks
      spotlightPadding={8}
      onEvent={handleEvent}
      locale={{ back: "이전", close: "닫기", last: "완료", next: "다음", skip: "건너뛰기" }}
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      styles={{
        tooltip: { borderRadius: 16, padding: "20px 24px", backgroundColor: "#1a1a2e", color: "#e5e7eb" },
        tooltipTitle: { fontSize: 15, fontWeight: 700 },
        tooltipContent: { fontSize: 13, lineHeight: 1.6 },
        buttonNext: { backgroundColor: "#a855f7", borderRadius: 8 },
        buttonBack: { color: "#9ca3af" },
        buttonSkip: { color: "#6b7280", fontSize: 12 },
        overlay: { backgroundColor: "rgba(0,0,0,0.75)" },
      } as any}
    />
  );
}
