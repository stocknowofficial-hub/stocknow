import requests
import ujson
import pytz  # ✅ pytz 필수 임포트
from datetime import datetime
from common.config import settings

# =========================================================
# 🛠️ [Helper] 휴장일 체크
# =========================================================
def check_is_holiday(token):
    """
    오늘이 휴장일인지 확인
    Returns: True(휴장), False(개장), "AUTH_ERROR"(토큰만료)
    """
    today_dt = datetime.now()
    if today_dt.weekday() >= 5: # 5=토, 6=일
        print(f"😴 [KR-Condition] 오늘은 주말입니다 ({today_dt.strftime('%A')}).")
        return True

    today_str = today_dt.strftime("%Y%m%d")
    url = "https://openapi.koreainvestment.com:9443/uapi/domestic-stock/v1/quotations/chk-holiday"
    
    headers = {
        "content-type": "application/json; utf-8",
        "authorization": f"Bearer {token}",
        "appkey": settings.KIS_APP_KEY,
        "appsecret": settings.KIS_APP_SECRET,
        "tr_id": "CTCA0903R",
        "custtype": "P"
    }
    params = {"BASS_DT": today_str, "CTX_AREA_NK": "", "CTX_AREA_FK": ""}
    
    try:
        res = requests.get(url, headers=headers, params=params, timeout=5)
        data = res.json()
        
        if res.status_code != 200 or "Failure" in data.get('msg1', ''):
            return "AUTH_ERROR"

        if res.status_code == 200 and 'output' in data:
            for day_info in data['output']:
                if day_info['bass_dt'] == today_str:
                    if day_info['opnd_yn'] == 'N':
                        print(f"😴 [KR-Condition] 오늘은 휴장일입니다 ({today_str}).")
                        return True
                    else:
                        print(f"✅ [KR-Condition] 오늘은 개장일입니다 ({today_str}).")
                        return False
            
            print(f"⚠️ [KR-Condition] API 데이터에 오늘 날짜({today_str}) 없음 -> 개장일로 가정합니다.")
            return False
        return "AUTH_ERROR"
    except Exception as e:
        print(f"❌ [API 에러] 휴장일 체크 중 오류: {e}")
        return "AUTH_ERROR"

# =========================================================
# 🛠️ [Helper] Telegra.ph 관리
# =========================================================
def setup_telegraph_account(telegraph_info):
    """Telegraph 계정 생성 (telegraph_info 딕셔너리 갱신)"""
    try:
        url = "https://api.telegra.ph/createAccount"
        params = {"short_name": "ReasonHunter", "author_name": "AI Analyst"}
        res = requests.get(url, params=params).json()
        if res.get("ok"):
            telegraph_info["access_token"] = res["result"]["access_token"]
            return True
    except: pass
    return False

# watcher/utils/definitions.py 의 update_telegraph_board 함수 수정

def update_telegraph_board(telegraph_info, title, stock_list):
    """
    현황판 업데이트
    :param telegraph_info: 메인 파일에서 관리하는 상태 딕셔너리
    """
    if not telegraph_info["access_token"]:
        if not setup_telegraph_account(telegraph_info): return None

    current_time_str = datetime.now().strftime("%H:%M:%S")
    formatted_date = datetime.now().strftime("%m월 %d일 %p %I:%M 등록").replace("PM", "오후").replace("AM", "오전")
    
    content_json = [
        {"tag": "p", "children": [f"• {formatted_date}"]},
        {"tag": "h3", "children": ["실시간 급등/급락 종목 현황 (±3% 이상)"]},
        {"tag": "p", "children": [f"🕒 최종 업데이트: {current_time_str}"]}
    ]
    
    # 상위 20개만 보여주거나 전체 보여주거나 (여기선 전체)
    for idx, item in enumerate(stock_list):
        # ✅ [Header Support] 섹션 구분용
        if item.get('is_header'):
            content_json.append({"tag": "h4", "children": [item['name']]})
            continue
            
        rank = idx + 1
        name = item['name']
        
        # ✅ [수정된 부분] 🇰🇷KR은 'chgrate', 🇺🇸US는 'rate'를 씁니다. 둘 다 체크!
        raw_rate = item.get('chgrate') or item.get('rate')
        # 4.995 -> 4.99 (버림)
        rate = int(float(raw_rate) * 100) / 100
        
        emoji = "🔥" if rate > 0 else "💧"
        if rate == 0: emoji = "➖"
        
        # 미국장은 가격 정보도 있으면 보여줌 (선택사항)
        price_info = ""
        if 'price' in item and item['price']:
            try:
                p_val = float(item['price'])
                
                # 🇰🇷 한국장 (chgrate 키가 있으면 한국장으로 간주)
                if 'chgrate' in item:
                    # 정수만 남기고 $ 제거 (예: 138,100)
                    price_info = f" ({int(p_val):,})"
                else:
                    # 🇺🇸 미국장 ($ 붙이고 소수점 2자리)
                    price_info = f" (${p_val:,.2f})"
            except:
                price_info = f" ({item['price']})"
        
        # ✅ [수정] 티커(Code) 포함: "애플(AAPL) : -0.12% 💧 ($248.04)"
        code_str = item.get('code', '')
        if code_str:
            line_text = f"{name}({code_str}) : {rate}% {emoji}{price_info}"
        else:
            line_text = f"{name} : {rate}% {emoji}{price_info}"
        
        # 순위 표시 (Header가 아닌 일반 항목만)
        if not item.get('no_rank'):
             line_text = f"{rank}위. " + line_text
             
        content_json.append({"tag": "p", "children": [line_text]})

    content_str = ujson.dumps(content_json)
    
    try:
        # path가 없으면 생성, 있으면 수정
        if not telegraph_info["path"]:
            url = "https://api.telegra.ph/createPage"
            data = {"access_token": telegraph_info["access_token"], "title": title, "content": content_str, "return_content": False}
            res = requests.post(url, json=data).json()
            if res.get("ok"):
                telegraph_info["path"] = res["result"]["path"]
                telegraph_info["url"] = res["result"]["url"]
                return telegraph_info["url"]
        else:
            url = "https://api.telegra.ph/editPage"
            data = {"access_token": telegraph_info["access_token"], "path": telegraph_info["path"], "title": title, "content": content_str, "return_content": False}
            requests.post(url, json=data)
            return telegraph_info["url"]
    except: return None

# =========================================================
# 🛠️ [Helper] KIS 조건검색
# =========================================================
def fetch_condition_stocks(token, user_id, target_seq):
    """KIS 조건검색 결과 조회"""
    url = "https://openapi.koreainvestment.com:9443/uapi/domestic-stock/v1/quotations/psearch-result"
    headers = {
        "content-type": "application/json; utf-8",
        "authorization": f"Bearer {token}",
        "appkey": settings.KIS_APP_KEY,
        "appsecret": settings.KIS_APP_SECRET,
        "tr_id": "HHKST03900400", 
        "custtype": "P",
    }
    params = {"user_id": user_id, "seq": target_seq}
    try:
        res = requests.get(url, headers=headers, params=params, timeout=5)
        data = res.json()
        if res.status_code == 200 and 'output2' in data:
            return data['output2']
        else:
            msg = data.get('msg1', '')
            if "접근토큰" in msg or "Failure" in msg: return "AUTH_ERROR"
            return []
    except: return []

# ... (기존 check_is_holiday 등은 그대로 유지) ...

# =========================================================
# 🛠️ [Helper] 미국장 개장 여부 (시간 & 날짜 교차 검증)
# =========================================================
def check_us_market_open(token):
    """
    미국장 개장 여부 확인 (3중 검증)
    1. 주말 체크 (토/일) -> 즉시 False
    2. API 데이터 날짜(xymd) == 오늘 뉴욕 날짜 확인
    3. 거래량(tvol) > 0 확인
    """
    try:
        # 1️⃣ [1차 방어] 파이썬 레벨에서 요일 체크
        ny_tz = pytz.timezone('America/New_York')
        now_ny = datetime.now(ny_tz)
        
        # 주말 (토=5, 일=6)이면 무조건 휴장
        if now_ny.weekday() >= 5:
            print(f"💤 [US Market] 오늘은 주말입니다 ({now_ny.strftime('%A')}).")
            return False

        # ---------------------------------------------------------
        
        check_symbols = ["SPY", "QQQ", "NVDA"]
        url = "https://openapi.koreainvestment.com:9443/uapi/overseas-price/v1/quotations/price-detail"
        
        headers = {
            "content-type": "application/json; utf-8",
            "authorization": f"Bearer {token}",
            "appkey": settings.KIS_APP_KEY,
            "appsecret": settings.KIS_APP_SECRET,
            "tr_id": "HHDFS76200200"
        }

        today_ymd = now_ny.strftime("%Y%m%d") # 예: 20260104

        for sym in check_symbols:
            excd = "AMS" if sym == "SPY" else "NAS"
            params = {"AUTH": "", "EXCD": excd, "SYMB": sym}
            
            res = requests.get(url, headers=headers, params=params, timeout=3)
            data = res.json()
            
            if res.status_code != 200 or "Failure" in data.get('msg1', ''):
                return "AUTH_ERROR"

            if res.status_code == 200 and 'output' in data:
                output = data['output']
                
                # 2️⃣ [2차 방어] 데이터 날짜(xymd) 확인
                # API가 주는 날짜가 오늘 날짜와 다르면 => "과거 데이터" (휴장)
                # ⚠️ 주의: 프리마켓 등에서는 xymd가 None이나 빈 값일 수 있음. 이 경우 거래량으로 판단.
                data_date = output.get('xymd') # 년월일
                
                if data_date and data_date != today_ymd:
                    # 날짜가 "있는데" 오늘이 아니면 -> 확실한 과거 데이터
                    continue 
                
                # 날짜가 None이면 통과 -> 거래량 체크로 넘어감 

                # 3️⃣ [3차 방어] 거래량 확인
                try:
                    tvol = int(output['tvol'])
                    if tvol > 0:
                        # 30분에 한 번만 로그 출력 (콘솔 도배 방지)
                        if now_ny.minute % 30 == 0:
                            print(f"✅ [US Market] 개장 확인 ({sym} | Date: {data_date} | Vol: {tvol})")
                        return True
                except: pass
        
        print(f"💤 [US Market] 거래량 없음/날짜 불일치 (Current: {today_ymd})")
        return False

    except Exception as e:
        print(f"⚠️ [Check Error] {e}")
        return "AUTH_ERROR"

def fetch_us_stocks_by_condition(token, exchange_code, min_market_cap):
    """미국 시총 상위 조회"""
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
        "AUTH": "", "EXCD": exchange_code, "CO_YN_VALX": "1",
        "CO_ST_VALX": min_market_cap, "CO_EN_VALX": "999999999999", "KEYB": ""
    }
    try:
        res = requests.get(url, headers=headers, params=params, timeout=5)
        data = res.json()
        if res.status_code == 200 and 'output2' in data:
            return data['output2']
        return []
    except: return []

# =========================================================
# 🛠️ [New] 미국 주식 지정 종목 가격 조회 (Batch)
# =========================================================
def fetch_prices_by_codes(token, codes_list):
    """
    여러 종목의 현재가를 조회 (단건 조회 API 반복 호출)
    Round-Robin으로 거래소 시도 (AMS -> NYS -> NAS)
    """
    results = []
    url = "https://openapi.koreainvestment.com:9443/uapi/overseas-price/v1/quotations/price-detail"
    
    headers = {
        "content-type": "application/json; utf-8",
        "authorization": f"Bearer {token}",
        "appkey": settings.KIS_APP_KEY,
        "appsecret": settings.KIS_APP_SECRET,
        "tr_id": "HHDFS76200200"
    }

    for code in codes_list:
        found = False
        # ✅ [Retry Logic] 거래소 순회 (ETF는 AMS/NYS, 개별주는 NAS 등 다양)
        # 우선순위: AMS(ETF) -> NAS(Tech) -> NYS(General)
        exchange_candidates = ["AMS", "NAS", "NYS"]
        
        for excd in exchange_candidates:
            if found: break
            try:
                params = {"AUTH": "", "EXCD": excd, "SYMB": code}
                res = requests.get(url, headers=headers, params=params, timeout=3.0)
                data = res.json()
                
                if res.status_code == 200 and 'output' in data:
                    item = data['output']
                    # 데이터 유효성 체크
                    if not item.get('last'): 
                        print(f"⚠️ [FetchSkip] {code} in {excd}: No Price (last is empty)")
                        continue 
                    
                    # 1. 등락률 계산 (rate가 없으면 base로 계산)
                    current_price = float(item['last'])
                    rate = 0.0
                    try:
                        raw_rate = item.get('rate') or item.get('diff')
                        if raw_rate:
                            rate = float(raw_rate)
                        else:
                            # base(전일종가) 이용 계산
                            base_price = float(item.get('base') or item.get('p_close') or current_price)
                            if base_price > 0:
                                rate = ((current_price - base_price) / base_price) * 100
                    except: pass
                    
                    # 2. 이름 정제 (DAMSGLD -> GLD or ename)
                    raw_name = item.get('rsym') or code
                    
                    # 영어 이름(ename)이 있으면 우선 사용
                    if item.get('ename'):
                        final_name = item['ename']
                    else:
                        # 접두어 제거 (DAMS, DNAS, DNYS, DASI 등 4글자)
                        # 보통 D+거래소(3) 조합. 
                        # 그냥 code가 있으면 code와 비교해서 정제?
                        # DAMSGLD -> GLD.
                        if raw_name.startswith("DAMS") or raw_name.startswith("DNAS") or raw_name.startswith("DNYS"):
                            final_name = raw_name[4:]
                        else:
                            final_name = raw_name

                    results.append({
                        "code": code,
                        "name": final_name, 
                        "price": item['last'],
                        "rate": rate,
                        "market_cap": 0,
                        "is_sector": True
                    })
                    found = True
                else:
                    # 실패 이유 출력
                    pass # print(f"⚠️ [FetchRetry] {code} in {excd}: Status {res.status_code}, Msg: {data.get('msg1')}")

            except Exception as e:
                print(f"⚠️ [FetchEx] {code} in {excd}: {e}")
                pass
        
        if not found:
             print(f"❌ [FetchFail] {code} not found in any exchange. (Check Token/Limit?)")
             pass
        
    return results

# =========================================================
# 🛠️ [NEW] 통합 휴장일/상태 체크 (Domestic Only)
# =========================================================
def check_today_actionable(token):
    """
    오늘 국내장이 '돌아가는 날'인지 판단 (주말 X, 공휴일 X)
    Returns: 
        - "OPEN": 개장일
        - "WEEKEND": 주말 (토/일)
        - "HOLIDAY": 공휴일 (평일인데 쉼)
        - "AUTH_ERROR": 토큰 오류
    """
    today_dt = datetime.now()
    
    # 1. [Python Level] 주말 컷
    if today_dt.weekday() >= 5: # 5=토, 6=일
        print(f"😴 [System] 오늘은 주말({today_dt.strftime('%A')})입니다. (Skip)")
        return "WEEKEND"

    # 2. [API Level] 공휴일 체크
    # 기존 check_is_holiday가 내부적으로 API 호출 및 True/False 리턴
    # 단, check_is_holiday가 이미 '주말 체크'를 포함하고 있어서 중복될 수 있으나 
    # 명확한 상태 분리를 위해 래핑함
    holiday_check = check_is_holiday(token)
    
    if holiday_check == "AUTH_ERROR":
        return "AUTH_ERROR"
    
    if holiday_check is True:
        # check_is_holiday 안에서 이미 로그 찍음
        return "HOLIDAY"
        
    # 3. 개장일
    return "OPEN"