'use client';

import { useState } from 'react';

export function TelegramLinkButton() {
  const [loading, setLoading] = useState(false);

  const handleLink = async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/auth/telegram', { method: 'POST' });
      const data = await res.json();
      
      if (data.link) {
        // Open Telegram link in a new tab
        window.open(data.link, '_blank');
      } else {
        alert('연동 링크 생성에 실패했습니다.');
      }
    } catch (error) {
      console.error('Failed to link telegram:', error);
      alert('오류가 발생했습니다.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <button
      onClick={handleLink}
      disabled={loading}
      className="w-full sm:w-auto px-6 py-3 bg-gradient-to-r from-blue-500 to-blue-600 text-white font-bold rounded-2xl hover:scale-105 transition-transform disabled:opacity-50 disabled:hover:scale-100 flex items-center justify-center gap-2 shadow-lg shadow-blue-500/20"
    >
      {loading ? (
        <span className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
      ) : (
        <span>📱 텔레그램 알림 연동하기</span>
      )}
    </button>
  );
}
