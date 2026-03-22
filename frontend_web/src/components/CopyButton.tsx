'use client';

import { useState } from 'react';

interface CopyButtonProps {
  text: string;
  label?: string;
}

export function CopyButton({ text, label = '복사' }: CopyButtonProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <button
      onClick={handleCopy}
      className="shrink-0 text-xs px-3 py-1.5 bg-white/5 rounded-lg hover:bg-white/10 text-white transition-colors"
    >
      {copied ? '✓ 복사됨' : label}
    </button>
  );
}
