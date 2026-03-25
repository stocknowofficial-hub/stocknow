'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';

interface UserRow {
  id: string;
  name: string | null;
  email: string | null;
  id_type: string | null;
  telegram_id: string | null;
  telegram_name: string | null;
  mobile: string | null;
  created_at: string | null;
  plan: string | null;
  status: string | null;
  expires_at: string | null;
}

const PLAN_OPTIONS = ['free', 'trial', 'standard', 'standard_kr', 'standard_us', 'premium'];
const STATUS_OPTIONS = ['active', 'expired', 'canceled'];

const planBadge: Record<string, string> = {
  free: 'bg-gray-500/20 text-gray-400',
  trial: 'bg-cyan-500/20 text-cyan-400',
  standard: 'bg-purple-500/20 text-purple-400',
  standard_kr: 'bg-blue-500/20 text-blue-400',
  standard_us: 'bg-blue-500/20 text-blue-400',
  premium: 'bg-yellow-500/20 text-yellow-400',
};

export function AdminDashboard({ initialUsers }: { initialUsers: UserRow[] }) {
  const router = useRouter();
  const [users, setUsers] = useState(initialUsers);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editData, setEditData] = useState<{ plan: string; status: string; expires_at: string }>({
    plan: 'free', status: 'active', expires_at: '',
  });
  const [saving, setSaving] = useState(false);
  const [search, setSearch] = useState('');
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const startEdit = (user: UserRow) => {
    setEditingId(user.id);
    setEditData({
      plan: user.plan || 'free',
      status: user.status || 'active',
      expires_at: user.expires_at ? user.expires_at.slice(0, 10) : '',
    });
  };

  const saveEdit = async (userId: string) => {
    setSaving(true);
    try {
      const res = await fetch(`/api/admin/users/${encodeURIComponent(userId)}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          plan: editData.plan,
          status: editData.status,
          expires_at: editData.expires_at || null,
        }),
      });

      if (res.ok) {
        setUsers((prev) =>
          prev.map((u) =>
            u.id === userId
              ? { ...u, plan: editData.plan, status: editData.status, expires_at: editData.expires_at || null }
              : u
          )
        );
        setEditingId(null);
      } else if (res.status === 401) {
        router.replace('/admin/login');
      } else {
        alert('저장 실패');
      }
    } finally {
      setSaving(false);
    }
  };

  const deleteUser = async (userId: string, userName: string | null) => {
    if (!confirm(`"${userName || userId}" 계정을 삭제하시겠습니까?\n이 작업은 되돌릴 수 없습니다.`)) return;
    setDeletingId(userId);
    try {
      const res = await fetch(`/api/admin/users/${encodeURIComponent(userId)}`, { method: 'DELETE' });
      if (res.ok) {
        setUsers((prev) => prev.filter((u) => u.id !== userId));
      } else if (res.status === 401) {
        router.replace('/admin/login');
      } else {
        alert('삭제 실패');
      }
    } finally {
      setDeletingId(null);
    }
  };

  const handleLogout = async () => {
    await fetch('/api/admin/logout', { method: 'POST' });
    router.replace('/admin/login');
  };

  const filtered = users.filter((u) => {
    const q = search.toLowerCase();
    return (
      !q ||
      u.name?.toLowerCase().includes(q) ||
      u.email?.toLowerCase().includes(q) ||
      u.id.toLowerCase().includes(q)
    );
  });

  return (
    <div className="min-h-screen bg-[#0a0a0c] text-white">
      {/* 헤더 */}
      <header className="border-b border-white/10 px-8 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <span className="text-xl">🛡️</span>
          <span className="font-bold text-lg">Stock Now 관리자</span>
          <span className="text-xs text-gray-500 bg-white/5 px-2 py-0.5 rounded-full">
            {users.length}명
          </span>
        </div>
        <button
          onClick={handleLogout}
          className="text-sm text-gray-400 hover:text-white px-4 py-2 rounded-xl hover:bg-white/5 transition-colors"
        >
          로그아웃
        </button>
      </header>

      <main className="p-8">
        {/* 검색 */}
        <div className="mb-6 max-w-sm">
          <input
            type="text"
            placeholder="이름, 이메일, ID 검색"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full px-4 py-2.5 rounded-xl bg-white/5 border border-white/10 text-sm text-white placeholder-gray-500 outline-none focus:border-purple-500 transition-colors"
          />
        </div>

        {/* 테이블 */}
        <div className="rounded-2xl border border-white/10 overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-white/10 bg-white/[0.02]">
                <th className="text-left px-5 py-3 text-gray-500 font-medium">이름 / 이메일</th>
                <th className="text-left px-5 py-3 text-gray-500 font-medium">가입</th>
                <th className="text-left px-5 py-3 text-gray-500 font-medium">텔레그램</th>
                <th className="text-left px-5 py-3 text-gray-500 font-medium">휴대폰</th>
                <th className="text-left px-5 py-3 text-gray-500 font-medium">플랜</th>
                <th className="text-left px-5 py-3 text-gray-500 font-medium">만료일</th>
                <th className="text-left px-5 py-3 text-gray-500 font-medium">가입일</th>
                <th className="text-left px-5 py-3 text-gray-500 font-medium">관리</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((user) => (
                <tr key={user.id} className="border-b border-white/5 hover:bg-white/[0.02] transition-colors">
                  <td className="px-5 py-4">
                    <div className="font-medium">{user.name || '—'}</div>
                    <div className="text-xs text-gray-500 mt-0.5">{user.email || user.id}</div>
                  </td>
                  <td className="px-5 py-4">
                    <span className="text-xs px-2 py-0.5 rounded-full bg-white/5 text-gray-400">
                      {user.id_type || '—'}
                    </span>
                  </td>
                  <td className="px-5 py-4 text-xs">
                    {user.telegram_id ? (
                      <div>
                        <div className="text-emerald-400 font-medium">{user.telegram_name || '연동됨'}</div>
                        <div className="text-gray-600 mt-0.5 font-mono">{user.telegram_id}</div>
                      </div>
                    ) : (
                      <span className="text-gray-600">미연동</span>
                    )}
                  </td>

                  <td className="px-5 py-4 text-xs text-gray-400 font-mono">
                    {user.mobile || <span className="text-gray-600">—</span>}
                  </td>

                  {editingId === user.id ? (
                    <>
                      {/* 편집 모드 */}
                      <td className="px-5 py-4">
                        <select
                          value={editData.plan}
                          onChange={(e) => setEditData((p) => ({ ...p, plan: e.target.value }))}
                          className="bg-black/60 border border-white/20 text-white text-xs rounded-lg px-2 py-1.5 outline-none"
                        >
                          {PLAN_OPTIONS.map((p) => (
                            <option key={p} value={p}>{p}</option>
                          ))}
                        </select>
                        <select
                          value={editData.status}
                          onChange={(e) => setEditData((p) => ({ ...p, status: e.target.value }))}
                          className="mt-1 bg-black/60 border border-white/20 text-white text-xs rounded-lg px-2 py-1.5 outline-none"
                        >
                          {STATUS_OPTIONS.map((s) => (
                            <option key={s} value={s}>{s}</option>
                          ))}
                        </select>
                      </td>
                      <td className="px-5 py-4">
                        <input
                          type="date"
                          value={editData.expires_at}
                          onChange={(e) => setEditData((p) => ({ ...p, expires_at: e.target.value }))}
                          className="bg-black/60 border border-white/20 text-white text-xs rounded-lg px-2 py-1.5 outline-none"
                        />
                        <button
                          onClick={() => setEditData((p) => ({ ...p, expires_at: '' }))}
                          className="ml-1 text-[10px] text-gray-500 hover:text-red-400"
                          title="무제한"
                        >
                          무제한
                        </button>
                      </td>
                      <td className="px-5 py-4 text-xs text-gray-600">
                        {user.created_at
                          ? new Date(user.created_at).toLocaleDateString('ko-KR')
                          : '—'}
                      </td>
                      <td className="px-5 py-4">
                        <div className="flex gap-2">
                          <button
                            onClick={() => saveEdit(user.id)}
                            disabled={saving}
                            className="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-medium rounded-lg disabled:opacity-50"
                          >
                            {saving ? '저장 중...' : '저장'}
                          </button>
                          <button
                            onClick={() => setEditingId(null)}
                            className="px-3 py-1.5 bg-white/10 hover:bg-white/20 text-xs rounded-lg"
                          >
                            취소
                          </button>
                        </div>
                      </td>
                    </>
                  ) : (
                    <>
                      {/* 보기 모드 */}
                      <td className="px-5 py-4">
                        <span
                          className={`text-xs px-2 py-0.5 rounded-full font-medium ${planBadge[user.plan || 'free'] || 'bg-gray-500/20 text-gray-400'}`}
                        >
                          {user.plan || 'free'}
                        </span>
                        {user.status === 'expired' && (
                          <span className="ml-1 text-xs text-red-400">만료</span>
                        )}
                      </td>
                      <td className="px-5 py-4 text-xs text-gray-400">
                        {user.expires_at
                          ? new Date(user.expires_at).toLocaleDateString('ko-KR')
                          : <span className="text-gray-600">무제한</span>}
                      </td>
                      <td className="px-5 py-4 text-xs text-gray-600">
                        {user.created_at
                          ? new Date(user.created_at).toLocaleDateString('ko-KR')
                          : '—'}
                      </td>
                      <td className="px-5 py-4">
                        <div className="flex gap-2">
                          <button
                            onClick={() => startEdit(user)}
                            className="px-3 py-1.5 bg-white/10 hover:bg-purple-600 text-xs font-medium rounded-lg transition-colors"
                          >
                            수정
                          </button>
                          <button
                            onClick={() => deleteUser(user.id, user.name)}
                            disabled={deletingId === user.id}
                            className="px-3 py-1.5 bg-white/5 hover:bg-red-600/70 text-gray-500 hover:text-white text-xs font-medium rounded-lg transition-colors disabled:opacity-50"
                          >
                            {deletingId === user.id ? '삭제 중...' : '삭제'}
                          </button>
                        </div>
                      </td>
                    </>
                  )}
                </tr>
              ))}

              {filtered.length === 0 && (
                <tr>
                  <td colSpan={7} className="px-5 py-12 text-center text-gray-600 text-sm">
                    검색 결과가 없습니다.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </main>
    </div>
  );
}
