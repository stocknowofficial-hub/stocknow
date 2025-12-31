import asyncio
import ujson
import requests
import os
from common.config import settings
from common.redis_client import redis_client
from watcher.kis_auth import get_access_token

# =========================================================
# 👇 [설정] 폴링 간격 (60초 권장)
POLLING_INTERVAL = 60 
# 👇 [설정] 감시할 조건식 인덱스 (0번이 확실함)
TARGET_SEQ = "0"
# =========================================================

PREV_STOCKS = set()

def fetch_condition_stocks(token, user_id):
    """
    REST API로 조건검색 결과를 1회 조회
    """
    url = "https://openapi.koreainvestment.com:9443/uapi/domestic-stock/v1/quotations/psearch-result"
    
    headers = {
        "content-type": "application/json; utf-8",
        "authorization": f"Bearer {token}",  # 넘겨받은 토큰 사용
        "appkey": settings.KIS_APP_KEY,
        "appsecret": settings.KIS_APP_SECRET,
        "tr_id": "HHKST03900300",  # [수정] 목록조회(300) 아니고 결과조회(400)이 맞는지 확인 필요하지만
                                   # 아까 성공했던 코드의 ID를 쓰세요. (아마 HHKST03900400 일겁니다)
                                   # 사장님이 성공했다고 한 코드의 ID: HHKST03900400
        "tr_id": "HHKST03900400",  
        "custtype": "P",
        "tr_cont": "N",
        "ctx_area_fk": "",
        "ctx_area_nk": ""
    }
    
    params = {
        "user_id": user_id,
        "seq": TARGET_SEQ
    }
    
    try:
        res = requests.get(url, headers=headers, params=params, timeout=5)
        data = res.json()
        
        # 성공 시 리스트 반환
        if res.status_code == 200 and 'output2' in data:
            return data['output2']
        else:
            # 실패 로그
            msg = data.get('msg1', '알 수 없는 오류')
            # 토큰 만료 에러 코드 체크 (보통 EGW00133은 발급제한이고, 만료는 다름)
            if "접근토큰" in msg or "Failure" in msg:
                print(f"⚠️ [API 경고] {msg}")
                return "AUTH_ERROR" # 별도 신호 반환
            
            return []
    except Exception as e:
        print(f"❌ [API 에러] {e}")
        return []

async def run_condition_watcher(approval_key, access_token=None):
    """
    [국내 조건팀] 폴링 방식 (토큰 중복 발급 방지 Ver)
    """
    global PREV_STOCKS
    
    # 👇 [핵심] main.py에서 준 토큰을 우선 사용합니다.
    current_token = access_token
    
    print(f"🕵️ [국내 조건팀] 'ReasonHunter(seq={TARGET_SEQ})' 감시 시작! (방식: {POLLING_INTERVAL}초 폴링)")

    MY_HTS_ID = settings.KIS_HTS_ID 
    if not MY_HTS_ID:
        # 혹시 설정에 없으면 하드코딩 된거라도 쓰게 방어
        MY_HTS_ID = "chh6518"

    while True:
        try:
            # 1. API 조회 (Blocking 방지)
            loop = asyncio.get_event_loop()
            stock_list = await loop.run_in_executor(None, fetch_condition_stocks, current_token, MY_HTS_ID)
            
            # 2. 토큰 만료 처리 (비상 상황)
            if stock_list == "AUTH_ERROR":
                print("🔄 [시스템] 토큰이 만료된 것 같습니다. 65초 대기 후 재발급...")
                await asyncio.sleep(65) # 1분 제한 피하기 위해 넉넉히 대기
                new_token = get_access_token()
                if new_token:
                    current_token = new_token
                    print("✅ [시스템] 토큰 갱신 완료!")
                continue

            # 3. 데이터 분석
            if isinstance(stock_list, list):
                current_set = set()
                
                # 첫 실행이라 PREV_STOCKS가 비어있으면 -> 알림 안 보내고 목록만 채움 (소음 방지)
                # 만약 처음부터 알림 받고 싶으면 아래 is_first_run 로직 제거하세요.
                is_first_run = (len(PREV_STOCKS) == 0)

                for item in stock_list:
                    code = item['code']
                    name = item['name']
                    price = item['price']
                    rate = item['chgrate']
                    
                    current_set.add(code)
                    
                    # [신규 포착]
                    if not is_first_run and code not in PREV_STOCKS:
                        print(f"🔥 [조건포착] {name} ({code}) {rate}%")
                        
                        payload = {
                            "type": "CONDITION",
                            "code": code,
                            "name": name,
                            "price": price,
                            "rate": rate,
                            "market": "KR"
                        }
                        await redis_client.publish(settings.REDIS_CHANNEL_STOCK, ujson.dumps(payload))
                
                # 첫 실행 로그
                if is_first_run and len(stock_list) > 0:
                     print(f"📋 [초기화] 현재 {len(stock_list)}개 종목이 검색됩니다. (변동 시 알림)")
                     # 초기 리스트도 Redis로 쏘고 싶으면 여기서 loop 돌리셔도 됩니다.

                # 목록 업데이트
                PREV_STOCKS = current_set
            
            # 4. 대기
            await asyncio.sleep(POLLING_INTERVAL)

        except Exception as e:
            print(f"❌ [폴링 에러] {e}")
            await asyncio.sleep(10)