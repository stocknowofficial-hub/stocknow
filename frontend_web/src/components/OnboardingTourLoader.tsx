"use client";

import dynamic from "next/dynamic";

const OnboardingTour = dynamic(() => import("./OnboardingTour"), { ssr: false });

export default function OnboardingTourLoader({ usFirst }: { usFirst?: boolean }) {
  return <OnboardingTour usFirst={usFirst} />;
}
