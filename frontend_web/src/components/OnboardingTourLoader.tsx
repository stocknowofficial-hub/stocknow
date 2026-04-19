"use client";

import dynamic from "next/dynamic";

const OnboardingTour = dynamic(() => import("./OnboardingTour"), { ssr: false });

export default function OnboardingTourLoader({ usFirst, onboardingDone }: { usFirst?: boolean; onboardingDone?: boolean }) {
  return <OnboardingTour usFirst={usFirst} onboardingDone={onboardingDone} />;
}
