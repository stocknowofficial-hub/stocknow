import asyncio
import requests
import ujson
from datetime import datetime
from common.config import settings
from common.redis_client import redis_client

async def run_rank_poller(access_token):
    """
    [대장주 감시] 30분마다 주요 종목(시총 상위+주도주) 시세 리포트 전송
    """
    # 감시할 종목 (삼성전자, 하이닉스, 엔솔, 현대차, 에코프로)
    TARGET_CODES = ["005930", "000660", "373220", "005380", "086520"]

    # 주식현재가 시세 URL
    url = f"{settings.KIS_BASE_URL}/uapi/domestic-stock/v1/quotations/inquire-price"
    
    headers = {
        "content-type": "application/json; utf-8",
        "authorization": f"Bearer {access_token}",
        "appkey": settings.KIS_APP_KEY,
        "appsecret": settings.KIS_APP_SECRET,
        "tr_id": "FHKST01010100"
    }

    print(f"📊 [폴링팀] 1분마다 시계 확인 중... (매시 0분, 30분에 발송)")
    
    # 중복 발송 방지용
    last_sent_minute = -1 

    while True:
        try:
            now = datetime.now()
            current_minute = now.minute
            current_time_str = now.strftime("%H:%M")

            # ==========================================================
            # [조건] 1. 지금이 0분 or 30분인가?
            #        2. 이번 분(minute)에 아직 안 보냈는가?
            # ==========================================================
            if (current_minute % 30 == 0) and (current_minute != last_sent_minute):
                
                print(f"⏰ [폴링팀] {current_time_str} 리포트 생성 시작!")
                report_data = []

                for code in TARGET_CODES:
                    params = {"FID_COND_MRKT_DIV_CODE": "J", "FID_INPUT_ISCD": code}
                    res = requests.get(url, headers=headers, params=params)
                    
                    if res.status_code == 200:
                        output = res.json().get('output')
                        if output:
                            # 종목명 매핑
                            name_map = {
                                "005930": "삼성전자", "000660": "SK하이닉스", 
                                "373220": "LG엔솔", "005380": "현대차", 
                                "086520": "에코프로"
                            }
                            name = name_map.get(code, code)
                            price = int(output.get('stck_prpr', '0'))
                            rate = float(output.get('prdy_ctrt', '0.0'))
                            
                            emoji = "📈" if rate > 0 else "📉"
                            if rate == 0: emoji = "➖"

                            # 가격 천단위 콤마
                            report_data.append(f"{emoji} {name} {price:,}원 ({rate}%)")
                    
                    await asyncio.sleep(0.2) # API 매너 호출

                if report_data:
                    payload = {
                        "type": "RANKING",
                        "time": current_time_str,
                        "data": report_data
                    }
                    await redis_client.publish(settings.REDIS_CHANNEL_STOCK, ujson.dumps(payload))
                    print(f"🚀 [전송완료] {current_time_str} 리포트 발송 완료!")
                    
                    # [중요] '이번 분'에는 보냈다고 기록 (중복 방지)
                    last_sent_minute = current_minute

        except Exception as e:
            print(f"❌ [폴링팀] 에러: {e}")
        
        # [중요] 30분을 자면 안 됩니다! 1분만 자고 일어나서 시계를 봐야 합니다.
        await asyncio.sleep(60)