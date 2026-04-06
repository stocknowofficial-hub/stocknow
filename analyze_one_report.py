"""
analyze_one_report.py
PDF 리포트 1개를 수동으로 분석해서 D1에 저장합니다.
텍스트 PDF, 이미지 스캔본 모두 지원 (Gemini File API 사용).

사용법:
  python analyze_one_report.py <pdf_path_or_url> [source] [source_desc]

예시 (로컬 파일):
  python analyze_one_report.py data/reports/ds투자_20260329.pdf "ds투자증권" "DS Weekly TalkTalk Vol.252"

예시 (URL):
  python analyze_one_report.py https://stock.pstatic.net/stock-research/market/18/20260327_market_973455000.pdf "키움증권" "Kiwoom Weekly 03/27"
"""

import asyncio
import sys
import os
import tempfile
import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from worker.modules.prediction_generator import generate_prediction_from_report


def download_pdf(url: str) -> str:
    """URL에서 PDF 다운로드 → 임시 파일 경로 반환"""
    print(f"📥 PDF 다운로드 중: {url}")
    resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
    resp.raise_for_status()

    suffix = ".pdf"
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    tmp.write(resp.content)
    tmp.close()
    size_kb = len(resp.content) / 1024
    print(f"💾 다운로드 완료: {size_kb:.0f} KB → {tmp.name}")
    return tmp.name


async def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    target   = sys.argv[1]
    source   = sys.argv[2] if len(sys.argv) > 2 else "증권사"
    source_desc = sys.argv[3] if len(sys.argv) > 3 else os.path.basename(target)

    # URL이면 다운로드
    is_url = target.startswith("http://") or target.startswith("https://")
    tmp_path = None
    if is_url:
        tmp_path = download_pdf(target)
        pdf_path = tmp_path
        source_url = target
    else:
        pdf_path = target
        source_url = f"manual://{os.path.basename(target)}"

    if not os.path.exists(pdf_path):
        print(f"❌ 파일 없음: {pdf_path}")
        sys.exit(1)

    file_size = os.path.getsize(pdf_path) / 1024
    print(f"\n{'='*60}")
    print(f"📄 분석 대상: {pdf_path} ({file_size:.0f} KB)")
    print(f"📌 출처: {source} / {source_desc}")
    print(f"{'='*60}\n")

    try:
        await generate_prediction_from_report(
            source=source,
            source_desc=source_desc,
            source_url=source_url,
            file_path=pdf_path,
        )
        print(f"\n✅ 완료! https://stock-now.pages.dev/consensus 에서 확인하세요.")
    finally:
        # URL 다운로드한 임시 파일 정리
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)


if __name__ == "__main__":
    asyncio.run(main())
