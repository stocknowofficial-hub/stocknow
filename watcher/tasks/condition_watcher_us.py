import asyncio
import ujson
import requests
import os
from datetime import datetime
import pytz 
from common.config import settings
from common.redis_client import redis_client
from watcher.kis_auth import get_access_token

POLLING_INTERVAL = 60 #폴링간격

MIN_MARKET_CAP = "350000000" #3,500억 달러
MAX_MARKET_CAP = "999999999999" 

TARGET_EXCHANGES = ["NAS", "NYS", "AMS"] #거래소
PREV_US_STOCKS = set()

def is_us_market_open():
    """
    미국 주식 운영 시간 체크 (Pre + Regular + After)
    - 뉴욕 시간 기준: 04:00 ~ 20:00
    - 주말(토, 일) 제외
    """
    try:
        ny_tz = pytz.timezone('America/New_York') # 뉴욕시간
        now_ny = datetime.now(ny_tz)
        
        if now_ny.weekday() >= 5: # 5,6일 주말
            return False, "주말 휴장"

        current_time_int = now_ny.hour * 100 + now_ny.minute # int(HHMM) 형태로 변환하여 비교
        
        start_time = 400   # 04:00 AM (프리장 시작)
        end_time = 2000    # 08:00 PM (애프터마켓 종료)

        if start_time <= current_time_int < end_time:
            return True, "개장 중"
        else:
            return False, f"장 마감 (현재 뉴욕 {now_ny.strftime('%H:%M')})"
            
    except Exception as e:
        print(f"⚠️ [시간 체크 오류] {e}")
        return True, "시간 체크 실패(Pass)" 

def fetch_us_stocks_by_condition(token, exchange_code):
    # [REST API] 해외주식 조건검색 요청 (시총 조건만 사용)
    url = "https://openapi.koreainvestment.com:9443/uapi/overseas-price/v1/quotations/inquire-search"
    
    headers = {
        "content-type": "application/json; utf-8",
        "authorization": f"Bearer {token}",
        "appkey": settings.KIS_APP_KEY,
        "appsecret": settings.KIS_APP_SECRET,
        "tr_id": "HHDFS76410000",
        "custtype": "P"
    }
    
    params = {
        "AUTH": "",
        "EXCD": exchange_code,
        "CO_YN_VALX": "1",          # 시가총액 조건 사용
        "CO_ST_VALX": MIN_MARKET_CAP,
        "CO_EN_VALX": MAX_MARKET_CAP,
        "KEYB": ""
    }
    
    try:
        res = requests.get(url, headers=headers, params=params, timeout=5)
        data = res.json()
        
        if res.status_code == 200 and 'output2' in data:
            return data['output2']
        return []
            
    except Exception as e:
        print(f"❌ [US API 에러] {e}")
        return []

async def run_condition_watcher_us(approval_key, access_token=None):
    """
    [해외 조건팀] 'Volatile Giants' (시총 500조↑ & 등락률 ±2%↑)
    """
    global PREV_US_STOCKS
    current_token = access_token
    
    # 디버그용 (처음 한 번만 출력)
    if current_token:
        print(f"🇺🇸 [해외 조건팀] 토큰 확인 완료 ({current_token[:5]}...)")
    
    print(f"🇺🇸 [해외 조건팀] 'Volatile Giants' 대기 중... (운영시간: 뉴욕 04:00~20:00)")

    while True:
        try:
            # 1. 운영 시간 체크
            is_open, msg = is_us_market_open()
            
            if not is_open:
                # 장 마감 시간이면 API 호출 안 하고 대기
                # 여기서는 5분(300초)마다 체크하도록 설정
                await asyncio.sleep(300) 
                continue

            current_cycle_stocks = set()
            found_list = []

            for excd in TARGET_EXCHANGES:
                loop = asyncio.get_event_loop()
                stock_list = await loop.run_in_executor(None, fetch_us_stocks_by_condition, current_token, excd)
                
                # 토큰 만료 처리
                if stock_list == [] and current_token is None:
                     current_token = get_access_token()
                     continue

                if isinstance(stock_list, list):
                    for item in stock_list:
                        code = item.get('rsym') or item.get('code')
                        name = item.get('ename') or item.get('name')
                        price = item.get('last') or item.get('price')
                        rate = item.get('rate') or item.get('diff')

                        if code and rate:
                            # 🚨 [핵심 필터] 등락률 절대값이 2.0 이상인 경우만 통과
                            try:
                                rate_val = float(rate)
                                if abs(rate_val) < 1.0:
                                    continue 
                            except:
                                continue

                            unique_key = f"{excd}:{code}"
                            current_cycle_stocks.add(unique_key)
                            
                            stock_info = {
                                "excd": excd,
                                "code": code,
                                "name": name,
                                "price": price,
                                "rate": rate,
                                "key": unique_key
                            }
                            found_list.append(stock_info)

            # 결과 처리
            is_first_run = (len(PREV_US_STOCKS) == 0)

            # 1. 초기 리스트 출력
            if is_first_run:
                if len(found_list) > 0:
                    print(f"\n🌊 [초기 포착] 현재 춤추는 대장주 {len(found_list)}개 발견:")
                    print("="* 60)
                    for s in found_list:
                        emoji = "🚀" if float(s['rate']) > 0 else "💧"
                        print(f"   {emoji} {s['name']:<20} ({s['code']})  ${s['price']} ({s['rate']}%)")
                    print("="* 60)
                else:
                    # 장 중인데 조건 만족하는 게 없을 때
                    pass

            # 2. 신규 진입 알림
            elif not is_first_run:
                for s in found_list:
                    if s['key'] not in PREV_US_STOCKS:
                        emoji = "🚀" if float(s['rate']) > 0 else "💧"
                        print(f"🇺🇸 [변동 포착] {s['name']} ({s['code']}) 급변동! {s['rate']}%")
                        
                        payload = {
                            "type": "CONDITION_US",
                            "code": s['code'],
                            "name": s['name'],
                            "price": s['price'],
                            "rate": s['rate'],
                            "market": "US",
                            "exchange": s['excd']
                        }
                        await redis_client.publish(settings.REDIS_CHANNEL_STOCK, ujson.dumps(payload))

            # 목록 업데이트
            PREV_US_STOCKS = current_cycle_stocks
            
            await asyncio.sleep(POLLING_INTERVAL)

        except Exception as e:
            print(f"❌ [US 폴링 에러] {e}")
            await asyncio.sleep(10)