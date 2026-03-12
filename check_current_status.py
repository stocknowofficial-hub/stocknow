
import asyncio
import pprint
from common.config import settings
from watcher.utils.definitions import fetch_kr_volume_rank, fetch_kr_program_trend
from watcher.kis_auth import get_access_token

async def check_status():
    print("🔑 Access Token 발급 중...")
    token = get_access_token()
    if not token:
        print("❌ 토큰 발급 실패")
        return

    print("\n📊 [현재 거래량 상위 종목 조회 시도]...")
    candidates = fetch_kr_volume_rank(token)
    
    data_source = "API (거래량 랭킹)"
    if not candidates:
        data_source = "Fallback (시총 상위 20개)"
        FALLBACK_CODES = [
            # 삼성전자, LG엔솔, SK하이닉스, 삼바, 삼성전자우, 현대차, 기아, 포스코홀딩스, KB금융, NAVER
            "005930", "373220", "000660", "207940", "005935", 
            "005380", "000270", "005490", "105560", "035420"
        ]
        candidates = []
        for code in FALLBACK_CODES:
            # Fallback은 이름/정보를 따로 가져와야 함. 
            # 프로그램 동향 API에서 정보(이름 불가, 거래량 가능)를 얻을 수 있음.
            # 여기서는 편의상 코드로 진행
            candidates.append({"mksc_shrn_iscd": code, "hts_kor_isnm": f"Code {code}"})

    print(f"👉 사용 중인 리스트 소스: {data_source}")
    print(f"👉 후보 개수: {len(candidates)}개\n")

    print(f"🔎 후보군 상세 분석 (Top 5 확인):")
    print(f"{'종목명':<10} | {'현재가':<10} | {'프로그램 순매수(백만)':<15} | {'누적거래량':<15}")
    print("-" * 60)

    # 상위 5개만 샘플링
    for stock in candidates[:10]:
        code = stock.get('mksc_shrn_iscd')
        name = stock.get('hts_kor_isnm', code)
        
        # 프로그램 동향 확인
        p_data = fetch_kr_program_trend(token, code)
        
        prog_net_buy_mill = 0
        acml_vol = 0
        current_price = 0
        
        if p_data:
            latest = p_data[0]
            # whol_smtn_ntby_tr_pbmn: 전체 순매수 거래대금 (원)
            raw_buy = int(latest.get('whol_smtn_ntby_tr_pbmn', 0))
            prog_net_buy_mill = round(raw_buy / 1000000) # 백만 단위로 변환
            
            acml_vol = int(latest.get('acml_vol', 0))
            current_price = int(latest.get('stck_prpr', 0))
        
        print(f"{name:<10} | {current_price:<10,} | {prog_net_buy_mill:<15,} | {acml_vol:<15,}")

if __name__ == "__main__":
    asyncio.run(check_status())
