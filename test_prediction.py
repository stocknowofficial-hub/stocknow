"""
예측 생성 테스트 스크립트
기존 PDF 파일로 prediction_generator 동작 확인용
"""
import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from worker.modules.prediction_generator import generate_prediction_from_report

TEST_REPORTS = [
    {
        "source": "kiwoom",
        "source_desc": "Kiwoom Weekly 2026-03-23",
        "source_url": "https://stock.pstatic.net/stock-research/invest/39/20260323_invest_785443000.pdf",
        "file_path": "data/reports/kiwoom_20260323_0901.pdf",
    },
    {
        "source": "blackrock",
        "source_desc": "BlackRock Weekly Commentary 2026-03-24",
        "source_url": "https://www.blackrock.com/us/individual/literature/market-commentary/weekly-investment-commentary-en-us-20260323-dialing-down-risk-amid-supply-shock.pdf",
        "file_path": "data/reports/blackrock_20260324.pdf",
    },
]

async def main():
    for report in TEST_REPORTS:
        print(f"\n{'='*50}")
        print(f"📄 테스트: {report['source_desc']}")
        print(f"{'='*50}")
        await generate_prediction_from_report(**report)
        print()

if __name__ == "__main__":
    asyncio.run(main())
