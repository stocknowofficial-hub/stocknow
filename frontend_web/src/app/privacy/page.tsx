import Link from "next/link";

export const metadata = { title: "개인정보처리방침 | StockNow" };

export default function PrivacyPage() {
  return (
    <main className="min-h-screen bg-[#0a0a0c] text-white">
      <div className="max-w-3xl mx-auto px-6 py-16">
        <Link href="/" className="text-sm text-gray-500 hover:text-gray-300 transition-colors mb-8 inline-block">
          ← 홈으로
        </Link>

        <h1 className="text-3xl font-bold mb-2">개인정보처리방침</h1>
        <p className="text-gray-500 text-sm mb-12">최종 수정일: 2026년 3월 29일</p>

        <div className="space-y-10 text-gray-300 leading-relaxed">

          <section>
            <h2 className="text-lg font-bold text-white mb-3">제1조 (개인정보의 처리 목적)</h2>
            <p>클라우드 브릿지(이하 "회사")가 운영하는 StockNow 서비스(이하 "서비스")는 다음의 목적을 위하여 개인정보를 처리합니다. 처리하는 개인정보는 다음의 목적 이외의 용도로는 이용되지 않으며, 이용 목적이 변경될 경우에는 개인정보보호법 제18조에 따라 별도의 동의를 받는 등 필요한 조치를 이행할 예정입니다.</p>
            <ul className="list-disc list-inside mt-3 space-y-1 text-gray-400">
              <li>회원 가입 및 서비스 이용을 위한 본인 식별·인증</li>
              <li>유료 서비스 결제 및 환불 처리</li>
              <li>텔레그램 알림 서비스 제공</li>
              <li>서비스 개선 및 신규 기능 안내</li>
              <li>불법·부정 이용 방지</li>
            </ul>
          </section>

          <section>
            <h2 className="text-lg font-bold text-white mb-3">제2조 (수집하는 개인정보 항목)</h2>
            <div className="space-y-3">
              <div>
                <p className="font-semibold text-white/80">소셜 로그인 (Google, Naver, Kakao)</p>
                <p className="text-gray-400 text-sm mt-1">이름, 이메일 주소, 프로필 사진 (각 플랫폼에서 제공하는 범위 내)</p>
              </div>
              <div>
                <p className="font-semibold text-white/80">서비스 이용</p>
                <p className="text-gray-400 text-sm mt-1">텔레그램 Chat ID (알림 서비스 신청 시), 접속 로그, 서비스 이용 기록</p>
              </div>
              <div>
                <p className="font-semibold text-white/80">결제</p>
                <p className="text-gray-400 text-sm mt-1">결제 수단 정보는 PG사(PayApp)에서 직접 처리하며, 회사는 결제 완료 여부 및 거래 번호만 보관합니다.</p>
              </div>
            </div>
          </section>

          <section>
            <h2 className="text-lg font-bold text-white mb-3">제3조 (개인정보의 보유 및 이용 기간)</h2>
            <p>회사는 법령에 따른 개인정보 보유·이용 기간 또는 정보주체로부터 개인정보를 수집 시에 동의받은 개인정보 보유·이용 기간 내에서 개인정보를 처리·보유합니다.</p>
            <ul className="list-disc list-inside mt-3 space-y-1 text-gray-400">
              <li>회원 정보: 탈퇴 후 30일 이내 삭제 (단, 관련 법령에 따라 일정 기간 보관)</li>
              <li>결제 기록: 전자상거래법에 따라 5년 보관</li>
              <li>접속 로그: 통신비밀보호법에 따라 3개월 보관</li>
            </ul>
          </section>

          <section>
            <h2 className="text-lg font-bold text-white mb-3">제4조 (개인정보의 제3자 제공)</h2>
            <p>회사는 원칙적으로 이용자의 개인정보를 제3자에게 제공하지 않습니다. 다만, 아래의 경우에는 예외로 합니다.</p>
            <ul className="list-disc list-inside mt-3 space-y-1 text-gray-400">
              <li>이용자가 사전에 동의한 경우</li>
              <li>법령의 규정에 의하거나 수사 기관의 요구가 있는 경우</li>
            </ul>
            <p className="mt-3 text-sm text-gray-500">※ 소셜 로그인 시 Google, Naver, Kakao의 개인정보처리방침이 별도 적용됩니다.</p>
          </section>

          <section>
            <h2 className="text-lg font-bold text-white mb-3">제5조 (개인정보 처리 위탁)</h2>
            <div className="overflow-x-auto">
              <table className="w-full text-sm border border-white/10 rounded-xl overflow-hidden">
                <thead className="bg-white/5 text-white/70">
                  <tr>
                    <th className="px-4 py-3 text-left">수탁업체</th>
                    <th className="px-4 py-3 text-left">위탁 업무</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/5 text-gray-400">
                  <tr><td className="px-4 py-3">PayApp (주식회사 와이디온라인)</td><td className="px-4 py-3">결제 처리 및 대금 정산</td></tr>
                  <tr><td className="px-4 py-3">Cloudflare, Inc.</td><td className="px-4 py-3">서비스 인프라 및 데이터 저장</td></tr>
                  <tr><td className="px-4 py-3">Telegram Messenger</td><td className="px-4 py-3">알림 메시지 전송</td></tr>
                </tbody>
              </table>
            </div>
          </section>

          <section>
            <h2 className="text-lg font-bold text-white mb-3">제6조 (정보주체의 권리·의무)</h2>
            <p>이용자는 개인정보주체로서 다음과 같은 권리를 행사할 수 있습니다.</p>
            <ul className="list-disc list-inside mt-3 space-y-1 text-gray-400">
              <li>개인정보 열람 요구</li>
              <li>오류 등이 있을 경우 정정 요구</li>
              <li>삭제 요구</li>
              <li>처리 정지 요구</li>
            </ul>
            <p className="mt-3 text-sm text-gray-400">위 권리 행사는 아래 개인정보 보호책임자에게 이메일로 요청하실 수 있습니다.</p>
          </section>

          <section>
            <h2 className="text-lg font-bold text-white mb-3">제7조 (개인정보 보호책임자)</h2>
            <div className="bg-white/[0.03] border border-white/10 rounded-2xl p-5 space-y-2 text-sm">
              <div className="flex gap-3"><span className="text-gray-500 w-28 shrink-0">회사명</span><span>클라우드 브릿지</span></div>
              <div className="flex gap-3"><span className="text-gray-500 w-28 shrink-0">대표자</span><span>조현호</span></div>
              <div className="flex gap-3"><span className="text-gray-500 w-28 shrink-0">사업자등록번호</span><span>224-29-01931</span></div>
              <div className="flex gap-3"><span className="text-gray-500 w-28 shrink-0">소재지</span><span>경기도 안양시 평촌동</span></div>
              <div className="flex gap-3"><span className="text-gray-500 w-28 shrink-0">이메일</span><span>stocknow.official@gmail.com</span></div>
              <div className="flex gap-3"><span className="text-gray-500 w-28 shrink-0">전화</span><span>070-8144-2193</span></div>
            </div>
          </section>

          <section>
            <h2 className="text-lg font-bold text-white mb-3">제8조 (개인정보처리방침 변경)</h2>
            <p>이 개인정보처리방침은 시행일로부터 적용되며, 법령 및 방침에 따른 변경 내용의 추가, 삭제 및 정정이 있는 경우에는 변경사항의 시행 7일 전부터 공지사항을 통하여 고지할 것입니다.</p>
          </section>

        </div>
      </div>
    </main>
  );
}
