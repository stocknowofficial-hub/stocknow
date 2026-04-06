import Link from "next/link";

export const metadata = { title: "이용약관 | StockNow" };

export default function TermsPage() {
  return (
    <main className="min-h-screen bg-[#0a0a0c] text-white">
      <div className="max-w-3xl mx-auto px-6 py-16">
        <Link href="/" className="text-sm text-gray-500 hover:text-gray-300 transition-colors mb-8 inline-block">
          ← 홈으로
        </Link>

        <h1 className="text-3xl font-bold mb-2">이용약관</h1>
        <p className="text-gray-500 text-sm mb-12">최종 수정일: 2026년 3월 29일</p>

        <div className="space-y-10 text-gray-300 leading-relaxed">

          <section>
            <h2 className="text-lg font-bold text-white mb-3">제1조 (목적)</h2>
            <p>본 약관은 클라우드 브릿지(이하 "회사")가 운영하는 StockNow 서비스(이하 "서비스")의 이용에 관한 조건 및 절차, 회사와 이용자의 권리·의무 및 책임사항을 규정함을 목적으로 합니다.</p>
          </section>

          <section>
            <h2 className="text-lg font-bold text-white mb-3">제2조 (서비스의 정의)</h2>
            <p>서비스는 AI 기반 시장 수급 분석 정보, 고래 거래 감지 알림, 주간 컨센서스 리포트, 텔레그램 알림 등 투자 참고 정보를 제공하는 플랫폼입니다.</p>
            <div className="mt-3 p-4 bg-amber-500/10 border border-amber-500/20 rounded-xl text-amber-300/80 text-sm">
              ⚠️ 본 서비스는 투자 참고 정보만을 제공하며, 특정 종목의 매수·매도를 권유하지 않습니다. 투자 판단 및 그에 따른 손익은 전적으로 이용자 본인의 책임입니다.
            </div>
          </section>

          <section>
            <h2 className="text-lg font-bold text-white mb-3">제3조 (약관의 효력 및 변경)</h2>
            <p>본 약관은 서비스 화면에 게시하거나 기타의 방법으로 회원에게 공지함으로써 효력이 발생합니다. 회사는 합리적인 사유가 있는 경우 약관을 변경할 수 있으며, 변경된 약관은 적용일 7일 전에 공지합니다.</p>
          </section>

          <section>
            <h2 className="text-lg font-bold text-white mb-3">제4조 (회원 가입 및 자격)</h2>
            <ul className="list-disc list-inside space-y-2 text-gray-400">
              <li>소셜 로그인(Google, Naver, Kakao)을 통해 회원 가입이 완료됩니다.</li>
              <li>만 14세 미만은 서비스를 이용할 수 없습니다.</li>
              <li>타인의 정보를 도용하거나 허위 정보를 제공한 경우 서비스 이용이 제한될 수 있습니다.</li>
            </ul>
          </section>

          <section>
            <h2 className="text-lg font-bold text-white mb-3">제5조 (유료 서비스 및 결제)</h2>
            <ul className="list-disc list-inside space-y-2 text-gray-400">
              <li>프리미엄 서비스 이용 요금은 월 5,900원이며, 사전 공지 후 변경될 수 있습니다.</li>
              <li>결제는 PayApp을 통해 처리됩니다.</li>
              <li>결제 완료 즉시 프리미엄 서비스 이용이 가능합니다.</li>
              <li>자동 갱신이 적용될 경우 갱신 3일 전 사전 안내됩니다.</li>
            </ul>
          </section>

          <section>
            <h2 className="text-lg font-bold text-white mb-3">제6조 (환불 및 청약철회)</h2>
            <p>환불 정책은 별도의 <Link href="/refund" className="text-purple-400 hover:underline">환불·취소 정책</Link>에 따릅니다.</p>
          </section>

          <section>
            <h2 className="text-lg font-bold text-white mb-3">제7조 (금지 행위)</h2>
            <ul className="list-disc list-inside space-y-2 text-gray-400">
              <li>서비스 내 정보를 무단으로 크롤링·스크래핑하는 행위</li>
              <li>서비스를 통해 제공받은 정보를 제3자에게 재판매하는 행위</li>
              <li>서비스의 정상적인 운영을 방해하는 행위</li>
              <li>타인의 계정을 무단으로 이용하는 행위</li>
              <li>관련 법령을 위반하는 일체의 행위</li>
            </ul>
          </section>

          <section>
            <h2 className="text-lg font-bold text-white mb-3">제8조 (서비스의 중단)</h2>
            <p>회사는 다음 각 호의 경우 서비스의 전부 또는 일부를 일시적으로 중단할 수 있습니다.</p>
            <ul className="list-disc list-inside mt-3 space-y-1 text-gray-400">
              <li>시스템 점검, 보수, 교체 작업</li>
              <li>천재지변 또는 불가항력적 사유</li>
              <li>외부 API 또는 데이터 제공업체의 장애</li>
            </ul>
            <p className="mt-3 text-sm text-gray-500">단, 예정된 점검은 사전에 공지합니다.</p>
          </section>

          <section>
            <h2 className="text-lg font-bold text-white mb-3">제9조 (면책 조항)</h2>
            <ul className="list-disc list-inside space-y-2 text-gray-400">
              <li>서비스에서 제공하는 모든 정보는 AI 및 외부 데이터 기반의 참고 정보로, 투자 결과에 대한 법적 책임을 지지 않습니다.</li>
              <li>이용자의 귀책사유로 인한 서비스 이용 장애에 대해서는 책임을 지지 않습니다.</li>
              <li>이용자 상호 간의 거래에서 발생한 분쟁에 대해서는 개입하지 않습니다.</li>
            </ul>
          </section>

          <section>
            <h2 className="text-lg font-bold text-white mb-3">제10조 (준거법 및 분쟁 해결)</h2>
            <p>본 약관은 대한민국 법률에 따라 해석되며, 서비스 이용으로 발생한 분쟁은 회사의 본점 소재지를 관할하는 법원을 제1심 관할 법원으로 합니다.</p>
          </section>

          <section className="border-t border-white/10 pt-8">
            <div className="bg-white/[0.03] border border-white/10 rounded-2xl p-5 space-y-2 text-sm">
              <div className="flex gap-3"><span className="text-gray-500 w-28 shrink-0">회사명</span><span>클라우드 브릿지</span></div>
              <div className="flex gap-3"><span className="text-gray-500 w-28 shrink-0">대표자</span><span>조현호</span></div>
              <div className="flex gap-3"><span className="text-gray-500 w-28 shrink-0">사업자등록번호</span><span>224-29-01931</span></div>
              <div className="flex gap-3"><span className="text-gray-500 w-28 shrink-0">소재지</span><span>경기도 안양시 평촌동</span></div>
              <div className="flex gap-3"><span className="text-gray-500 w-28 shrink-0">이메일</span><span>stocknow.official@gmail.com</span></div>
              <div className="flex gap-3"><span className="text-gray-500 w-28 shrink-0">전화</span><span>070-8144-2193</span></div>
            </div>
          </section>

        </div>
      </div>
    </main>
  );
}
