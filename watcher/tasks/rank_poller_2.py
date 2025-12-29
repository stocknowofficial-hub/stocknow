import asyncio
import requests
import ujson
from datetime import datetime
from common.config import settings
from common.redis_client import redis_client

# [추가됨] 안전한 변환 함수
def safe_float(value):
    """빈 문자열('')이나 None이 오면 0.0으로 변환하여 에러 방지"""
    if not value: # None or ""
        return 0.0
    try:
        return float(value)
    except ValueError:
        return 0.0

async def run_us_rank_poller(access_token):
    """
    [해외주식팀] 미국 나스닥 대장주(Magnificent 7 + @) 실시간 시세 감시
    """
    
    # 감시할 종목 (티커: 거래소)
    TARGET_STOCKS = {
        "TSLA": {"name": "테슬라", "exch": "NAS"},
        "NVDA": {"name": "엔비디아", "exch": "NAS"},
        "AAPL": {"name": "애플", "exch": "NAS"},
        "MSFT": {"name": "마이크로소프트", "exch": "NAS"},
        "AMZN": {"name": "아마존", "exch": "NAS"},
        "GOOGL": {"name": "구글", "exch": "NAS"},
        "AMD": {"name": "AMD", "exch": "NAS"},
        "PLTR": {"name": "팔란티어", "exch": "NYS"},
    }

    # 해외주식 현재가 URL (실전)
    url = f"{settings.KIS_BASE_URL}/uapi/overseas-price/v1/quotations/price"
    
    headers = {
        "content-type": "application/json; utf-8",
        "authorization": f"Bearer {access_token}",
        "appkey": settings.KIS_APP_KEY,
        "appsecret": settings.KIS_APP_SECRET,
        "tr_id": "HHDFS00000300"
    }

    print(f"🇺🇸 [해외팀] 미국 주식 모니터링 시작! ({len(TARGET_STOCKS)}개 종목)")
    
    last_sent_minute = -1

    while True:
        try:
            now = datetime.now()
            current_minute = now.minute
            current_time_str = now.strftime("%H:%M")

            # 1분마다 무조건 실행
            if current_minute != last_sent_minute:
                
                print(f"🗽 [해외팀] {current_time_str} 시세 조회 중...")
                report_data = []

                for symbol, info in TARGET_STOCKS.items():
                    params = {
                        "AUTH": "",
                        "EXCD": info['exch'],
                        "SYMB": symbol
                    }
                    
                    res = requests.get(url, headers=headers, params=params)
                    
                    if res.status_code == 200:
                        output = res.json().get('output')
                        if output:
                            name = info['name']
                            
                            # [수정] safe_float 함수로 감싸서 에러 방지!
                            price = safe_float(output.get('last')) 
                            rate = safe_float(output.get('rate'))  
                            
                            emoji = "🚀" if rate > 0 else "💧"
                            if rate == 0: emoji = "➖"

                            report_data.append(f"{emoji} {name}({symbol}) ${price} ({rate}%)")
                    else:
                        print(f"⚠️ {symbol} 조회 실패: {res.status_code}")
                    
                    await asyncio.sleep(0.2)

                if report_data:
                    payload = {
                        "type": "RANKING",
                        "time": f"🇺🇸 {current_time_str}",
                        "data": report_data
                    }
                    await redis_client.publish(settings.REDIS_CHANNEL_STOCK, ujson.dumps(payload))
                    print(f"🛫 [전송완료] 미국 주식 데이터 발송 완료!")
                    
                    last_sent_minute = current_minute

        except Exception as e:
            print(f"❌ [해외팀] 에러: {e}")
        
        await asyncio.sleep(60)