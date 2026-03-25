'use client';

import { useState } from 'react';

interface Props {
  alreadyApplied: boolean;
}

export function ReferralCodeInput({ alreadyApplied }: Props) {
  const [code, setCode] = useState('');
  const [status, setStatus] = useState<'idle' | 'loading' | 'success' | 'error'>('idle');
  const [message, setMessage] = useState('');

  if (alreadyApplied) {
    return (
      <div className="flex items-center gap-2 text-sm text-emerald-400">
        <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 shrink-0" />
        추천인 코드가 이미 등록되어 있습니다.
      </div>
    );
  }

  const handleApply = async () => {
    const trimmed = code.trim();
    if (!trimmed) return;
    setStatus('loading');
    setMessage('');

    try {
      const res = await fetch('/api/referral/apply', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ code: trimmed }),
      });
      const data = await res.json();

      if (res.ok) {
        setStatus('success');
        setMessage('초대 코드가 적용되었습니다! 구독 기간이 1개월 연장됐습니다. 🎉');
      } else {
        setStatus('error');
        setMessage(data.error ?? '오류가 발생했습니다.');
      }
    } catch {
      setStatus('error');
      setMessage('네트워크 오류가 발생했습니다.');
    }
  };

  return (
    <div className="space-y-3">
      <div className="flex gap-2">
        <input
          type="text"
          value={code}
          onChange={(e) => {
            setCode(e.target.value.toUpperCase());
            if (status !== 'idle') { setStatus('idle'); setMessage(''); }
          }}
          placeholder="SN-XXXX-XXXX"
          maxLength={12}
          disabled={status === 'loading' || status === 'success'}
          className="flex-1 bg-black/40 border border-white/10 rounded-xl px-4 py-2.5 text-sm font-mono text-white placeholder:text-gray-600 focus:outline-none focus:border-purple-500/50 disabled:opacity-50"
        />
        <button
          onClick={handleApply}
          disabled={!code.trim() || status === 'loading' || status === 'success'}
          className="px-4 py-2.5 bg-purple-600 hover:bg-purple-500 disabled:opacity-40 disabled:cursor-not-allowed text-white text-sm font-semibold rounded-xl transition-colors shrink-0"
        >
          {status === 'loading' ? '적용 중...' : '적용'}
        </button>
      </div>

      {message && (
        <p className={`text-xs ${status === 'success' ? 'text-emerald-400' : 'text-red-400'}`}>
          {message}
        </p>
      )}
    </div>
  );
}
