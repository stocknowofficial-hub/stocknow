"use client";

import { useState } from "react";
import Link from "next/link";

const API_BASE = "http://localhost:8000";

export default function AnalyzePage() {
  const [pdfUrl, setPdfUrl] = useState("");
  const [source, setSource] = useState("");
  const [title, setTitle] = useState("");
  const [reportDate, setReportDate] = useState(
    new Date().toISOString().split("T")[0]
  );
  const [status, setStatus] = useState<{
    type: "idle" | "loading" | "success" | "error";
    message?: string;
  }>({ type: "idle" });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!pdfUrl.trim() || !source.trim()) {
      setStatus({ type: "error", message: "PDF URL과 증권사명은 필수입니다." });
      return;
    }

    setStatus({ type: "loading" });

    try {
      const res = await fetch(`${API_BASE}/analyze`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          pdf_url: pdfUrl.trim(),
          source: source.trim(),
          title: title.trim() || undefined,
          report_date: reportDate || undefined,
        }),
      });

      const data = await res.json();

      if (res.ok) {
        setStatus({
          type: "success",
          message: `✅ 전송 완료: "${data.title}"`,
        });
        setPdfUrl("");
        setTitle("");
      } else {
        setStatus({
          type: "error",
          message: `❌ 오류: ${data.detail || "알 수 없는 오류"}`,
        });
      }
    } catch (e) {
      setStatus({
        type: "error",
        message: "❌ 백엔드 연결 실패 (localhost:8000 확인 필요)",
      });
    }
  };

  return (
    <div className="min-h-screen bg-gray-100 flex flex-col items-center py-10 px-4">
      <div className="w-full max-w-xl">
        <div className="mb-6">
          <Link
            href="/admin"
            className="text-sm text-indigo-600 hover:underline"
          >
            ← 관리자 홈
          </Link>
          <h1 className="text-3xl font-extrabold mt-2 text-indigo-800">
            📄 리포트 수동 분석
          </h1>
          <p className="text-sm text-gray-500 mt-1">
            PDF 리포트 URL을 입력하면 Watcher가 자동으로 분석하여 예측 카드를
            생성합니다.
          </p>
        </div>

        <form
          onSubmit={handleSubmit}
          className="bg-white shadow-xl rounded-xl p-8 space-y-5"
        >
          {/* PDF URL */}
          <div>
            <label className="block text-sm font-semibold text-gray-700 mb-1">
              PDF URL <span className="text-red-500">*</span>
            </label>
            <input
              type="url"
              placeholder="https://example.com/report.pdf"
              value={pdfUrl}
              onChange={(e) => setPdfUrl(e.target.value)}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-indigo-500 outline-none"
              required
            />
            <p className="text-xs text-gray-400 mt-1">
              네이버 증권 리포트 또는 직접 링크 가능한 PDF URL
            </p>
          </div>

          {/* 증권사명 */}
          <div>
            <label className="block text-sm font-semibold text-gray-700 mb-1">
              증권사명 <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              placeholder="예: 키움증권, 삼성증권, BlackRock"
              value={source}
              onChange={(e) => setSource(e.target.value)}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-indigo-500 outline-none"
              required
            />
          </div>

          {/* 리포트 제목 (선택) */}
          <div>
            <label className="block text-sm font-semibold text-gray-700 mb-1">
              리포트 제목{" "}
              <span className="text-gray-400 font-normal">(선택)</span>
            </label>
            <input
              type="text"
              placeholder="생략 시 '증권사명 리포트 (날짜)' 자동 생성"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-indigo-500 outline-none"
            />
          </div>

          {/* 리포트 날짜 (선택) */}
          <div>
            <label className="block text-sm font-semibold text-gray-700 mb-1">
              리포트 날짜{" "}
              <span className="text-gray-400 font-normal">(선택)</span>
            </label>
            <input
              type="date"
              value={reportDate}
              onChange={(e) => setReportDate(e.target.value)}
              className="border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-indigo-500 outline-none"
            />
          </div>

          {/* 상태 메시지 */}
          {status.type !== "idle" && (
            <div
              className={`rounded-lg px-4 py-3 text-sm font-medium ${
                status.type === "success"
                  ? "bg-green-50 text-green-700 border border-green-200"
                  : status.type === "error"
                  ? "bg-red-50 text-red-700 border border-red-200"
                  : "bg-blue-50 text-blue-700 border border-blue-200"
              }`}
            >
              {status.type === "loading" ? "⏳ 분석 요청 중..." : status.message}
            </div>
          )}

          <button
            type="submit"
            disabled={status.type === "loading"}
            className="w-full bg-indigo-600 hover:bg-indigo-700 disabled:bg-indigo-300 text-white font-semibold py-2.5 rounded-lg transition text-sm"
          >
            {status.type === "loading" ? "처리 중..." : "🚀 분석 요청 전송"}
          </button>
        </form>

        <div className="mt-4 bg-yellow-50 border border-yellow-200 rounded-lg p-4 text-xs text-yellow-800">
          <b>📌 참고사항</b>
          <ul className="mt-1 space-y-1 list-disc list-inside">
            <li>PDF가 백엔드 서버에 다운로드된 후 Watcher가 분석을 시작합니다.</li>
            <li>분석 결과는 수 분 내 텔레그램 알림 및 히스토리 페이지에 반영됩니다.</li>
            <li>동일 URL을 중복 제출해도 분석은 1회만 진행됩니다.</li>
          </ul>
        </div>
      </div>
    </div>
  );
}
