"use client";

import { useEffect, useState, useMemo } from 'react';
import Link from 'next/link';

const API_base = "http://localhost:8000"; // localhost (or use env var in real deploy)

interface Subscriber {
    chat_id: string;
    username: string | null;
    name: string | null;
    tier: string;
    expiry_date: string | null;
    is_active: boolean;
    created_at: string;
    referrer_id: string | null; // ✅ 추가
}

type SortKey = keyof Subscriber;
type SortDirection = 'asc' | 'desc';

export default function AdminPage() {
    const [subscribers, setSubscribers] = useState<Subscriber[]>([]);
    const [searchTerm, setSearchTerm] = useState("");
    const [sortConfig, setSortConfig] = useState<{ key: SortKey; direction: SortDirection } | null>({ key: 'created_at', direction: 'desc' });
    const [filterTier, setFilterTier] = useState<string>("ALL");

    // ✅ [Local State] 변경사항 추적 (chat_id -> 변경된 필드들)
    const [modifiedRows, setModifiedRows] = useState<Record<string, Partial<Subscriber>>>({});

    useEffect(() => {
        fetchSubscribers();
    }, []);

    const fetchSubscribers = async () => {
        try {
            const res = await fetch(`${API_base}/subscribers/detail`);
            if (res.ok) {
                setSubscribers(await res.json());
                setModifiedRows({}); // 초기화
            }
        } catch (e) {
            console.error(e);
            alert("백엔드 연결 실패 (localhost:8000 확인 필요)");
        }
    };

    // --- ✨ Local Edit Handlers (No API Call) ---

    const handleLocalChange = (chat_id: string, field: keyof Subscriber, value: any) => {
        setModifiedRows(prev => ({
            ...prev,
            [chat_id]: {
                ...prev[chat_id],
                [field]: value
            }
        }));
    };

    const cancelChanges = (chat_id: string) => {
        setModifiedRows(prev => {
            const next = { ...prev };
            delete next[chat_id];
            return next;
        });
    };

    // --- 🚀 Save Action (API Call) ---

    const saveRow = async (chat_id: string) => {
        const changes = modifiedRows[chat_id];
        if (!changes) return;

        // Date 처리: YYYY-MM-DD -> ISO string (Optional)
        // Backend handles YYYY-MM-DD for datetime fields usually implies 00:00:00

        try {
            const res = await fetch(`${API_base}/subscribers/${chat_id}`, {
                method: "PUT",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(changes),
            });

            if (res.ok) {
                // Update Local State with saved changes
                setSubscribers(prev => prev.map(sub =>
                    sub.chat_id === chat_id ? { ...sub, ...changes } : sub
                ));
                // Remove from modified list
                cancelChanges(chat_id);
            } else {
                alert("저장 실패");
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

    // ⏩ [New] Extend Expiry Helper
    const extendExpiry = async (chat_id: string, currentExpiryStr: string | null, months: number) => {
        if (!confirm(`${months}개월 연장하시겠습니까?`)) return;

        let baseDate = new Date();
        if (currentExpiryStr) {
            const currentExp = new Date(currentExpiryStr);
            // 만약 아직 만료 안 됐으면 거기서부터 연장
            if (currentExp > new Date()) baseDate = currentExp;
        }

        baseDate.setDate(baseDate.getDate() + (months * 30)); // 30일/월 계산

        try {
            const res = await fetch(`${API_base}/subscribers/${chat_id}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    expiry_date: baseDate.toISOString(),
                    is_active: true,
                    tier: 'PRO' // 연장 시 PRO 등급 부여
                })
            });
            if (res.ok) {
                alert(`✅ 만료일이 ${baseDate.toISOString().split('T')[0]}로 연장되었습니다.`);
                fetchSubscribers();
            } else alert("오류 발생");
        } catch (e) { console.error(e); }
    };

    // 👢 [New] Kick / Demote Helper
    const demoteToFree = async (chat_id: string) => {
        if (!confirm("이 사용자를 강등(FREE) 처리하시겠습니까? 만료일도 삭제됩니다.")) return;
        try {
            const res = await fetch(`${API_base}/subscribers/${chat_id}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    expiry_date: null, // 만료일 삭제
                    tier: 'FREE',
                    is_active: true
                })
            });
            if (res.ok) {
                alert("✅ FREE 등급으로 변경되었습니다.");
                fetchSubscribers();
            }
        } catch (e) { console.error(e); }
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
                (s.referrer_id && s.referrer_id.includes(lowerTerm)) || // ✅ Search Referrer
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
                const aVal = modifiedRows[a.chat_id]?.[sortConfig.key] ?? a[sortConfig.key] ?? "";
                const bVal = modifiedRows[b.chat_id]?.[sortConfig.key] ?? b[sortConfig.key] ?? "";

                if (aVal < bVal) return sortConfig.direction === 'asc' ? -1 : 1;
                if (aVal > bVal) return sortConfig.direction === 'asc' ? 1 : -1;
                return 0;
            });
        }

        return items;
    }, [subscribers, searchTerm, sortConfig, filterTier, modifiedRows]); // modifiedRows change triggers re-sort/render

    // 🗓️ Date Convert Helper
    const toDateInputValue = (isoStr: string | null) => {
        if (!isoStr) return "";
        return isoStr.split("T")[0]; // YYYY-MM-DD
    };

    return (
        <div className="min-h-screen bg-gray-100 flex flex-col items-center py-10">
            <h1 className="text-4xl font-extrabold mb-4 text-indigo-800 tracking-tight">🛡️ Reason Hunter Admin (Manual Save)</h1>
            <div className="flex gap-3 mb-6">
                <Link href="/admin/analyze" className="bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-semibold px-4 py-2 rounded-lg transition">
                    📄 리포트 수동 분석
                </Link>
            </div>

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

                <div className="bg-yellow-50 p-4 mb-6 rounded-lg text-sm text-yellow-800 border-l-4 border-yellow-400 flex items-center shadow-sm">
                    ⚠️ <b>Update:</b> 변경 후 반드시 좌측 <b>[💾 저장]</b> 버튼을 눌러야 반영됩니다. 날짜를 클릭하여 기간을 연장하세요.
                </div>

                {/* 📊 테이블 */}
                <div className="overflow-x-auto rounded-lg border border-gray-200 shadow-sm" style={{ minHeight: '400px' }}>
                    <table className="min-w-full text-sm text-left text-gray-700">
                        <thead className="text-xs text-gray-600 uppercase bg-gray-50 border-b">
                            <tr>
                                <th className="px-4 py-4 w-24 text-center">Action</th>
                                <th onClick={() => handleSort('is_active')} className="px-4 py-4 cursor-pointer hover:bg-gray-100">Status ↕</th>
                                <th onClick={() => handleSort('tier')} className="px-4 py-4 cursor-pointer hover:bg-gray-100">Tier ↕</th>
                                <th onClick={() => handleSort('referrer_id')} className="px-4 py-4 cursor-pointer hover:bg-gray-100 text-indigo-600">Referrer ↕</th>{/* ✅ New */}
                                <th onClick={() => handleSort('username')} className="px-4 py-4 cursor-pointer hover:bg-gray-100">Username ↕</th>
                                <th onClick={() => handleSort('expiry_date')} className="px-4 py-4 cursor-pointer hover:bg-gray-100">Expiry (Date) ↕</th>
                                <th onClick={() => handleSort('name')} className="px-4 py-4 cursor-pointer hover:bg-gray-100">Name ↕</th>
                                <th className="px-4 py-4">Chat ID</th>
                                <th onClick={() => handleSort('created_at')} className="px-4 py-4 cursor-pointer hover:bg-gray-100">Joined ↕</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-100">
                            {processedSubscribers.length > 0 ? (
                                processedSubscribers.map((sub) => {
                                    // 🟢 Local State vs Original State
                                    const changes = modifiedRows[sub.chat_id];
                                    const isModified = !!changes;

                                    const currentActive = changes?.is_active ?? sub.is_active;
                                    const currentTier = changes?.tier ?? sub.tier;
                                    // Date Input needs YYYY-MM-DD
                                    const currentExpiry = changes?.expiry_date !== undefined ? changes.expiry_date : toDateInputValue(sub.expiry_date);

                                    return (
                                        <tr key={sub.chat_id} className={`hover:bg-indigo-50 transition group ${isModified ? "bg-yellow-50" : (!currentActive ? 'bg-gray-50 opacity-60' : 'bg-white')}`}>

                                            {/* Action Column */}
                                            <td className="px-4 py-4 text-center flex justify-center gap-2">
                                                {isModified ? (
                                                    <>
                                                        <button
                                                            onClick={() => saveRow(sub.chat_id)}
                                                            className="text-white bg-green-500 hover:bg-green-600 transition p-1.5 rounded shadow-sm"
                                                            title="저장"
                                                        >
                                                            💾
                                                        </button>
                                                        <button
                                                            onClick={() => cancelChanges(sub.chat_id)}
                                                            className="text-white bg-gray-400 hover:bg-gray-500 transition p-1.5 rounded shadow-sm"
                                                            title="취소"
                                                        >
                                                            ❌
                                                        </button>
                                                    </>
                                                ) : (
                                                    <div className="flex gap-1 items-center">
                                                        <button
                                                            onClick={() => deleteSubscriber(sub.chat_id, sub.name || "")}
                                                            className="text-gray-400 hover:text-red-600 transition p-1.5 rounded-full hover:bg-red-50 text-xs"
                                                            title="영구 삭제"
                                                        >
                                                            🗑️
                                                        </button>
                                                        <button onClick={() => extendExpiry(sub.chat_id, sub.expiry_date, 1)} className="text-xs bg-indigo-50 text-indigo-700 px-1.5 py-0.5 rounded border border-indigo-200 hover:bg-indigo-100 transition whitespace-nowrap" title="1개월 연장">+1M</button>
                                                        <button onClick={() => extendExpiry(sub.chat_id, sub.expiry_date, 2)} className="text-xs bg-indigo-50 text-indigo-700 px-1.5 py-0.5 rounded border border-indigo-200 hover:bg-indigo-100 transition whitespace-nowrap" title="2개월 연장">+2M</button>
                                                        <button onClick={() => demoteToFree(sub.chat_id)} className="text-xs bg-red-50 text-red-700 px-1.5 py-0.5 rounded border border-red-200 hover:bg-red-100 transition" title="멤버십 해지 (강등)">🔽</button>
                                                    </div>
                                                )}
                                            </td>

                                            <td className="px-4 py-4">
                                                <label className="inline-flex items-center cursor-pointer">
                                                    <input
                                                        type="checkbox"
                                                        className="w-4 h-4 text-indigo-600 rounded focus:ring-indigo-500 border-gray-300 transition"
                                                        checked={currentActive}
                                                        onChange={(e) => handleLocalChange(sub.chat_id, 'is_active', e.target.checked)}
                                                    />
                                                    <span className={`ml-2 font-medium ${currentActive ? "text-green-600" : "text-gray-400"}`}>
                                                        {currentActive ? "On" : "Off"}
                                                    </span>
                                                </label>
                                            </td>

                                            <td className="px-4 py-4">
                                                <select
                                                    value={currentTier}
                                                    onChange={(e) => handleLocalChange(sub.chat_id, 'tier', e.target.value)}
                                                    className={`text-xs font-bold px-3 py-1.5 rounded-full border-0 cursor-pointer focus:ring-2 focus:ring-indigo-500 shadow-sm transition appearance-none text-center ${currentTier === 'PRO' ? 'bg-purple-100 text-purple-700' :
                                                        currentTier === 'BASIC' ? 'bg-blue-100 text-blue-700' :
                                                            'bg-gray-100 text-gray-600'
                                                        }`}
                                                >
                                                    <option value="FREE">FREE</option>
                                                    <option value="BASIC">BASIC</option>
                                                    <option value="PRO">PRO</option>
                                                </select>
                                            </td>

                                            <td className="px-4 py-4 font-mono text-xs text-indigo-500">
                                                {sub.referrer_id ? `🔗 ${sub.referrer_id}` : "-"}
                                            </td>

                                            <td className="px-4 py-4 font-semibold text-indigo-900">
                                                {sub.username || "-"}
                                            </td>

                                            {/* 🗓️ Editable Date Picker */}
                                            <td className="px-4 py-4">
                                                <input
                                                    type="date"
                                                    className={`border rounded px-2 py-1 text-xs outline-none transition ${(currentExpiry && currentExpiry < new Date().toISOString().split('T')[0])
                                                        ? 'border-red-500 text-red-600 bg-red-50 font-bold focus:ring-2 focus:ring-red-500'
                                                        : 'border-gray-300 text-gray-700 focus:ring-2 focus:ring-blue-500'
                                                        }`}
                                                    value={currentExpiry || ""}
                                                    onChange={(e) => handleLocalChange(sub.chat_id, 'expiry_date', e.target.value)} // Stores YYYY-MM-DD
                                                />
                                            </td>

                                            <td className="px-4 py-4 text-gray-800">{sub.name || "Unknown"}</td>
                                            <td className="px-4 py-4 font-mono text-xs text-gray-500">{sub.chat_id}</td>
                                            <td className="px-4 py-4 text-gray-500 text-xs">{new Date(sub.created_at).toLocaleDateString()}</td>
                                        </tr>
                                    );
                                })
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
