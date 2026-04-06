'use client';

import { useState, useTransition } from 'react';
import { ReportAccordion } from './ReportAccordion';

interface ReportRow {
  id: string;
  source: string;
  source_desc: string | null;
  source_url: string | null;
  prediction: string;
  direction: string;
  target: string;
  target_code: string | null;
  confidence: string;
  created_at: string;
  key_points: string | null;
  related_stocks: string | null;
  action: string | null;
  trade_setup: string | null;
  price_change_pct: number | null;
  expires_at: string | null;
}

interface WallStreetData {
  recommendation: string;
  target_price: number | null;
  current_price: number | null;
  analyst_count: number;
  upside_pct: number | null;
}

const PAGE_SIZE = 5;

export function ShowMoreReports({
  reports: initial,
  total,
  wsMap = {},
}: {
  reports: ReportRow[];
  total: number;        // 이번 주 전체 리포트 수 (DB에서 count)
  wsMap?: Record<string, WallStreetData>;
}) {
  const [reports, setReports] = useState(initial);
  const [isPending, startTransition] = useTransition();

  const hasMore = reports.length < total;

  const loadMore = () => {
    startTransition(async () => {
      const res = await fetch(`/api/reports?offset=${reports.length}&limit=${PAGE_SIZE}`);
      if (!res.ok) return;
      const data = await res.json() as { reports: ReportRow[] };
      setReports(prev => [...prev, ...data.reports]);
    });
  };

  return (
    <>
      <ReportAccordion reports={reports} wsMap={wsMap} />
      {hasMore && (
        <button
          onClick={loadMore}
          disabled={isPending}
          className="w-full mt-3 py-2.5 text-[12px] font-semibold text-gray-400 hover:text-gray-200 disabled:opacity-40 border border-white/[0.06] hover:border-white/[0.12] rounded-xl transition-colors"
        >
          {isPending ? '로딩 중...' : `더보기 (${total - reports.length}건 남음) ▼`}
        </button>
      )}
    </>
  );
}
