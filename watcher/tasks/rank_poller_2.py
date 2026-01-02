import asyncio
import requests
import ujson
from datetime import datetime
from common.config import settings
from common.redis_client import redis_client

# 안전한 변환 함수 (그대로 유지)
def safe_float(value):
    if not value:
        return 0.0
    try:
        return float(value)
    except ValueError:
        return 0.0

async def run_us_rank_poller(access_token):
    """
    [해외주식팀] 미국 나스닥 대장주 시세 감시 (주기 변경 가능)
    """
    
    # ====================================================
    # [설정] 몆 분마다 알림을 보낼까요? (숫자만 바꾸세요!)
    # 예: 10 -> 10분, 20분, 30분... 에 발송
    # 예: 60 -> 매시 정각(0분)에만 발송
    SEND_INTERVAL_MINUTES = 60 
    # ====================================================

    # 감시할 종목
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

    url = f"{settings.KIS_BASE_URL}/uapi/overseas-price/v1/quotations/price"
    
    headers = {
        "content-type": "application/json; utf-8",
        "authorization": f"Bearer {access_token}",
        "appkey": settings.KIS_APP_KEY,
        "appsecret": settings.KIS_APP_SECRET,
        "tr_id": "HHDFS00000300"
    }

    print(f"🇺🇸 [해외팀] 모니터링 시작! ({SEND_INTERVAL_MINUTES}분 간격)(17:00 ~ 10:00 가동)")
    
    # 중복 발송 방지용 기록
    last_sent_minute = -1

    while True:
        try:
            now = datetime.now()
            current_hour = now.hour
            current_minute = now.minute
            current_time_str = now.strftime("%H:%M")

            is_us_market_open = (current_hour >= 17) or (current_hour < 10)
            if is_us_market_open:
            # [핵심 로직]
            # 1. 1분마다 깨어나지만, '설정된 간격'에 딱 맞을 때만 실행합니다.
            # 2. 이번 분(minute)에 이미 보냈으면 스킵합니다.
                is_time_to_send = (current_minute % SEND_INTERVAL_MINUTES == 0)
                
                if is_time_to_send and (current_minute != last_sent_minute):
                    
                    print(f"🗽 [해외팀] {current_time_str} 정기 조회 시작...")
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
                                price = safe_float(output.get('last'))
                                rate = safe_float(output.get('rate'))
                                
                                emoji = "🚀" if rate > 0 else "💧"
                                if rate == 0: emoji = "➖"

                                report_data.append(f"{emoji} {name}({symbol}) ${price} ({rate}%)")
                        
                        # API 호출 너무 빠르지 않게
                        await asyncio.sleep(0.2)

                    if report_data:
                        payload = {
                            "type": "RANKING",
                            "time": f"🇺🇸 {current_time_str}",
                            "data": report_data
                        }
                        await redis_client.publish(settings.REDIS_CHANNEL_STOCK, ujson.dumps(payload))
                        print(f"🛫 [전송완료] {current_time_str} 데이터 발송 끝!")
                        
                        # '이번 분'에는 보냈다고 도장 쾅!
                        last_sent_minute = current_minute
            else:
                # 미국장 닫힌 낮 시간에는 그냥 쉽니다.
                pass

        except Exception as e:
            print(f"❌ [해외팀] 에러: {e}")
        
        # [절대 수정 금지] 30분씩 자면 안 됩니다.
        # 무조건 1분(60초)만 자고 일어나서 시계를 봐야 프로그램이 안 죽습니다.
        await asyncio.sleep(60)