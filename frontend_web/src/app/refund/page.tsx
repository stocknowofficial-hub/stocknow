import Link from "next/link";

export const metadata = { title: "환불·취소 정책 | StockNow" };

export default function RefundPage() {
  return (
    <main className="min-h-screen bg-[#0a0a0c] text-white">
      <div className="max-w-3xl mx-auto px-6 py-16">
        <Link href="/" className="text-sm text-gray-500 hover:text-gray-300 transition-colors mb-8 inline-block">
          ← 홈으로
        </Link>

        <h1 className="text-3xl font-bold mb-2">환불·취소 정책</h1>
        <p className="text-gray-500 text-sm mb-12">최종 수정일: 2026년 3월 29일</p>

        <div className="space-y-10 text-gray-300 leading-relaxed">

          <section>
            <h2 className="text-lg font-bold text-white mb-3">환불 원칙</h2>
            <p>StockNow 프리미엄 서비스는 전자상거래 등에서의 소비자보호에 관한 법률에 따라 아래의 환불 정책을 적용합니다.</p>
          </section>

          <section>
            <div className="grid gap-4">
              <div className="p-5 bg-emerald-500/10 border border-emerald-500/20 rounded-2xl">
                <div className="flex items-center gap-2 mb-2">
                  <span className="text-emerald-400 font-bold">환불 가능</span>
                </div>
                <p className="text-sm text-gray-300">결제일로부터 <span className="text-white font-semibold">7일 이내</span>이며, 프리미엄 웹 서비스(컨센서스, 트럼프 임팩트 페이지 등)에 <span className="text-white font-semibold">1회 이상 접속한 이력이 없는 경우</span> 전액 환불됩니다.</p>
              </div>
              <div className="p-5 bg-red-500/10 border border-red-500/20 rounded-2xl">
                <div className="flex items-center gap-2 mb-2">
                  <span className="text-red-400 font-bold">환불 불가</span>
                </div>
                <ul className="text-sm text-gray-300 space-y-1 list-disc list-inside">
                  <li>결제일로부터 7일이 경과한 경우</li>
                  <li>프리미엄 웹 서비스(컨센서스, 트럼프 임팩트 페이지 등)에 1회 이상 접속한 경우</li>
                  <li>이용 기간 중 서비스 이용 약관을 위반한 경우</li>
                </ul>
              </div>
            </div>
          </section>

          <section>
            <h2 className="text-lg font-bold text-white mb-3">환불 신청 방법</h2>
            <ol className="list-decimal list-inside space-y-3 text-gray-400">
              <li>아래 이메일 또는 전화로 환불 요청</li>
              <li>결제자 이름, 결제일, 결제 금액, 환불 사유 안내</li>
              <li>확인 후 <span className="text-white">영업일 기준 3~5일 이내</span> 결제 수단으로 환불 처리</li>
            </ol>
            <div className="mt-5 bg-white/[0.03] border border-white/10 rounded-2xl p-5 space-y-2 text-sm">
              <div className="flex gap-3"><span className="text-gray-500 w-16 shrink-0">이메일</span><span>stocknow.official@gmail.com</span></div>
              <div className="flex gap-3"><span className="text-gray-500 w-16 shrink-0">전화</span><span>070-8144-2193</span></div>
              <div className="flex gap-3"><span className="text-gray-500 w-16 shrink-0">운영시간</span><span>평일 10:00 – 18:00 (공휴일 제외)</span></div>
            </div>
          </section>

          <section>
            <h2 className="text-lg font-bold text-white mb-3">디지털 콘텐츠 특성 안내</h2>
            <p className="text-sm text-gray-400">
              본 서비스는 전자상거래법 제17조 제2항에 따라, 이용자가 서비스를 사용하기 시작한 경우 청약철회가 제한될 수 있습니다. 이 사실은 결제 전 화면에서 명확히 고지됩니다.
            </p>
          </section>

          <section>
            <h2 className="text-lg font-bold text-white mb-3">소비자 분쟁 해결</h2>
            <p className="text-sm text-gray-400">
              환불 관련 분쟁이 해결되지 않을 경우 한국소비자원(국번 없이 1372) 또는 전자거래분쟁조정위원회에 조정을 신청하실 수 있습니다.
            </p>
          </section>

        </div>
      </div>
    </main>
  );
}
