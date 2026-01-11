"use client";

import { useEffect, useState, useMemo } from 'react';

const API_base = "http://localhost:8000"; // localhost로 변경

interface Subscriber {
    chat_id: string;
    username: string | null;
    name: string | null;
    tier: string;
    expiry_date: string | null;
    is_active: boolean;
    created_at: string;
}

type SortKey = keyof Subscriber;
type SortDirection = 'asc' | 'desc';

export default function AdminPage() {
    const [subscribers, setSubscribers] = useState<Subscriber[]>([]);
    const [searchTerm, setSearchTerm] = useState("");
    const [sortConfig, setSortConfig] = useState<{ key: SortKey; direction: SortDirection } | null>({ key: 'created_at', direction: 'desc' });
    const [filterTier, setFilterTier] = useState<string>("ALL");

    useEffect(() => {
        fetchSubscribers();
    }, []);

    const fetchSubscribers = async () => {
        try {
            const res = await fetch(`${API_base}/subscribers/detail`);
            if (res.ok) {
                setSubscribers(await res.json());
            }
        } catch (e) {
            console.error(e);
            alert("백엔드 연결 실패 (localhost:8000 확인 필요)");
        }
    };

    const toggleStatus = async (chat_id: string, currentStatus: boolean) => {
        try {
            const res = await fetch(`${API_base}/subscribers/${chat_id}`, {
                method: "PUT",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ is_active: !currentStatus }),
            });
            if (res.ok) {
                setSubscribers(prev => prev.map(sub =>
                    sub.chat_id === chat_id ? { ...sub, is_active: !currentStatus } : sub
                ));
            } else {
                alert("업데이트 실패");
            }
        } catch (e) {
            alert("통신 오류");
        }
    };

    const updateTier = async (chat_id: string, newTier: string) => {
        try {
            const res = await fetch(`${API_base}/subscribers/${chat_id}`, {
                method: "PUT",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ tier: newTier }),
            });
            if (res.ok) {
                setSubscribers(prev => prev.map(sub =>
                    sub.chat_id === chat_id ? { ...sub, tier: newTier } : sub
                ));
            } else {
                alert("등급 변경 실패");
            }
        } catch (e) {
            alert("통신 오류");
        }
    };

    const deleteSubscriber = async (chat_id: string, name: string) => {
        if (!confirm(`🚨 정말로 [${name || "Unknown"}] 님을 삭제하시겠습니까?\n삭제 후엔 복구할 수 없습니다.`)) return;

        try {
            const res = await fetch(`${API_base}/subscribers/${chat_id}`, {
                method: "DELETE",
            });
            if (res.ok) {
                setSubscribers(prev => prev.filter(sub => sub.chat_id !== chat_id));
            } else {
                alert("삭제 실패");
            }
        } catch (e) {
            alert("통신 오류");
        }
    };

    const handleSort = (key: SortKey) => {
        let direction: SortDirection = 'asc';
        if (sortConfig && sortConfig.key === key && sortConfig.direction === 'asc') {
            direction = 'desc';
        }
        setSortConfig({ key, direction });
    };

    // 🔍 필터링 & 정렬 로직
    const processedSubscribers = useMemo(() => {
        let items = [...subscribers];

        // 1. 검색 (Search)
        if (searchTerm) {
            const lowerTerm = searchTerm.toLowerCase();
            items = items.filter(s =>
                (s.username && s.username.toLowerCase().includes(lowerTerm)) ||
                (s.name && s.name.toLowerCase().includes(lowerTerm)) ||
                s.chat_id.includes(lowerTerm) ||
                s.tier.toLowerCase().includes(lowerTerm)
            );
        }

        // 2. 등급 필터 (Tier Filter)
        if (filterTier !== "ALL") {
            items = items.filter(s => s.tier === filterTier);
        }

        // 3. 정렬 (Sort)
        if (sortConfig) {
            items.sort((a, b) => {
                const aValue = a[sortConfig.key] ?? "";
                const bValue = b[sortConfig.key] ?? "";

                if (aValue < bValue) return sortConfig.direction === 'asc' ? -1 : 1;
                if (aValue > bValue) return sortConfig.direction === 'asc' ? 1 : -1;
                return 0;
            });
        }

        return items;
    }, [subscribers, searchTerm, sortConfig, filterTier]);

    // 🎨 UI Helpers
    const getExpiryDisplay = (dateStr: string | null) => {
        if (!dateStr) return <span className="text-green-600 font-semibold text-xs">무제한</span>;
        const date = new Date(dateStr);
        const now = new Date();
        const isExpired = date < now;
        return (
            <span className={`text-xs ${isExpired ? "text-red-500 font-bold" : "text-gray-600"}`}>
                {date.toLocaleDateString()} {isExpired && "(만료)"}
            </span>
        );
    };

    return (
        <div className="min-h-screen bg-gray-100 flex flex-col items-center py-10">
            <h1 className="text-4xl font-extrabold mb-8 text-indigo-800 tracking-tight">🛡️ Reason Hunter Admin</h1>

            <div className="bg-white shadow-xl rounded-xl p-8 w-full max-w-7xl transition-all hover:shadow-2xl">
                {/* 🛠️ 컨트롤 패널 */}
                <div className="flex flex-col md:flex-row justify-between items-center mb-6 gap-4">
                    <div className="flex items-center gap-2">
                        <h2 className="text-2xl font-bold text-gray-800">구독자 관리</h2>
                        <span className="bg-indigo-100 text-indigo-800 text-xs font-medium px-2.5 py-0.5 rounded border border-indigo-400">
                            Total: {subscribers.length}
                        </span>
                    </div>

                    <div className="flex gap-3 w-full md:w-auto">
                        <div className="relative">
                            <input
                                type="text"
                                placeholder="검색 (ID, 이름, 등급)"
                                className="pl-3 p-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 w-full md:w-64"
                                value={searchTerm}
                                onChange={e => setSearchTerm(e.target.value)}
                            />
                        </div>

                        <select
                            className="p-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 bg-white cursor-pointer"
                            value={filterTier}
                            onChange={e => setFilterTier(e.target.value)}
                        >
                            <option value="ALL">전체 등급</option>
                            <option value="FREE">FREE</option>
                            <option value="BASIC">BASIC</option>
                            <option value="PRO">PRO</option>
                        </select>

                        <button onClick={fetchSubscribers} className="bg-gray-200 hover:bg-gray-300 px-4 py-2 rounded-lg font-medium transition text-gray-700">
                            🔄 새로고침
                        </button>
                    </div>
                </div>

                <div className="bg-blue-50 p-4 mb-6 rounded-lg text-sm text-blue-800 border-l-4 border-blue-400 flex items-center shadow-sm">
                    📢 <b>Tip</b>: 등급(Tier)을 변경하면 <b>즉시 저장</b>됩니다. 삭제 버튼은 신중히 눌러주세요.
                </div>

                {/* 📊 테이블 */}
                <div className="overflow-x-auto rounded-lg border border-gray-200 shadow-sm">
                    <table className="min-w-full text-sm text-left text-gray-700">
                        <thead className="text-xs text-gray-600 uppercase bg-gray-50 border-b">
                            <tr>
                                <th className="px-4 py-4 w-16 text-center">Delete</th>
                                <th onClick={() => handleSort('is_active')} className="px-4 py-4 cursor-pointer hover:bg-gray-100">Status ↕</th>
                                <th onClick={() => handleSort('tier')} className="px-4 py-4 cursor-pointer hover:bg-gray-100">Tier (Edit) ↕</th>
                                <th onClick={() => handleSort('username')} className="px-4 py-4 cursor-pointer hover:bg-gray-100">Username ↕</th>
                                <th onClick={() => handleSort('expiry_date')} className="px-4 py-4 cursor-pointer hover:bg-gray-100">Expiry ↕</th>
                                <th onClick={() => handleSort('name')} className="px-4 py-4 cursor-pointer hover:bg-gray-100">Name ↕</th>
                                <th className="px-4 py-4">Chat ID</th>
                                <th onClick={() => handleSort('created_at')} className="px-4 py-4 cursor-pointer hover:bg-gray-100">Joined ↕</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-100">
                            {processedSubscribers.length > 0 ? (
                                processedSubscribers.map((sub) => (
                                    <tr key={sub.chat_id} className={`hover:bg-indigo-50 transition group ${!sub.is_active ? 'bg-gray-50 opacity-60' : 'bg-white'}`}>
                                        <td className="px-4 py-4 text-center">
                                            <button
                                                onClick={() => deleteSubscriber(sub.chat_id, sub.name || "")}
                                                className="text-gray-400 hover:text-red-600 transition p-2 rounded-full hover:bg-red-50 text-base"
                                                title="영구 삭제"
                                            >
                                                🗑️
                                            </button>
                                        </td>
                                        <td className="px-4 py-4">
                                            <label className="inline-flex items-center cursor-pointer">
                                                <input
                                                    type="checkbox"
                                                    className="w-4 h-4 text-indigo-600 rounded focus:ring-indigo-500 border-gray-300 transition"
                                                    checked={sub.is_active}
                                                    onChange={() => toggleStatus(sub.chat_id, sub.is_active)}
                                                />
                                                <span className={`ml-2 font-medium ${sub.is_active ? "text-green-600" : "text-gray-400"}`}>
                                                    {sub.is_active ? "On" : "Off"}
                                                </span>
                                            </label>
                                        </td>
                                        <td className="px-4 py-4">
                                            <select
                                                value={sub.tier}
                                                onChange={(e) => updateTier(sub.chat_id, e.target.value)}
                                                className={`text-xs font-bold px-3 py-1.5 rounded-full border-0 cursor-pointer focus:ring-2 focus:ring-indigo-500 shadow-sm transition appearance-none text-center ${sub.tier === 'PRO' ? 'bg-purple-100 text-purple-700 hover:bg-purple-200' :
                                                        sub.tier === 'BASIC' ? 'bg-blue-100 text-blue-700 hover:bg-blue-200' :
                                                            'bg-gray-100 text-gray-600 hover:bg-gray-200'
                                                    }`}
                                            >
                                                <option value="FREE">FREE</option>
                                                <option value="BASIC">BASIC</option>
                                                <option value="PRO">PRO</option>
                                            </select>
                                        </td>
                                        <td className="px-4 py-4 font-semibold text-indigo-900">
                                            {sub.username || "-"}
                                        </td>
                                        <td className="px-4 py-4 text-gray-600">
                                            {getExpiryDisplay(sub.expiry_date)}
                                        </td>
                                        <td className="px-4 py-4 text-gray-800">{sub.name || "Unknown"}</td>
                                        <td className="px-4 py-4 font-mono text-xs text-gray-500">{sub.chat_id}</td>
                                        <td className="px-4 py-4 text-gray-500 text-xs">{new Date(sub.created_at).toLocaleDateString()}</td>
                                    </tr>
                                ))
                            ) : (
                                <tr>
                                    <td colSpan={8} className="text-center py-10 text-gray-500">
                                        검색 결과가 없습니다.
                                    </td>
                                </tr>
                            )}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    );
}
