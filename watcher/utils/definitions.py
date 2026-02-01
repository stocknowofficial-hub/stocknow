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
                        # print(f"✅ [KR-Condition] 오늘은 개장일입니다 ({today_str}).")
                        return False
            
            # print(f"⚠️ [KR-Condition] API 데이터에 오늘 날짜({today_str}) 없음 -> 개장일로 가정합니다.")
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
    rank = 1
    for item in stock_list:
        # ✅ [Header Support] 섹션 구분용
        if item.get('is_header'):
            content_json.append({"tag": "h4", "children": [item['name']]})
            rank = 1 # Reset Rank
            continue
            
        name = item['name']
        
        # ✅ [수정된 부분] 🇰🇷KR은 'chgrate', 🇺🇸US는 'rate'를 씁니다. 둘 다 체크!
        raw_rate = item.get('chgrate') or item.get('rate')
        # 4.995 -> 4.99 (버림)
        rate = int(float(raw_rate) * 100) / 100
        
        emoji = "🔥" if rate > 0 else "💧"
        if rate == 0: emoji = "➖"
        
        # Format Price
        price_str = ""
        if 'price' in item and item['price']:
            try:
                p_val = float(item['price'])
                if 'chgrate' in item: # KR
                     price_str = f"{int(p_val):,}원"
                else: # US
                     price_str = f"${p_val:,.2f}"
            except:
                price_str = str(item['price'])

        # Name Cleaning (Remove internal metadata from name if present)
        # Assuming name might have (🐳...) appended by caller, we might want to split?
        # The caller 'whale_watcher_us.py' appends info to name. 
        # Ideally, caller should pass raw data. 
        # But 'processed name' is passed. 
        # User saw: "브로드컴 (🐳2건/$4.0M)" 
        # I should change the CALLER format in whale_watcher_us.py instead of parsing here?
        # User Request: "2건은 뭐고... 숫자는 뭐고..."
        # So I will change how it is CONSTRUCTED in whale_watcher_us.py.
        # But here, I also need to fix Rank.
        
        # Let's assume standard format here:
        # If name has parens, it's already formatted.
        # I will just fix the Rank logic here first.
        
        line_text = f"{rank}. {name} : {rate}% {emoji}"
        if price_str:
             line_text += f" ({price_str})"
        
        # 순위 표시 (Header가 아닌 일반 항목만)
        if not item.get('no_rank'):
             content_json.append({"tag": "p", "children": [line_text]})
             rank += 1
        else:
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

def fetch_us_stocks_by_condition(token, exchange_code, min_market_cap, sort_key="VALX"):
    """
    미국 시총 상위 조회 (조건검색)
    :param sort_key: 정렬 기준 (VALX: 시총, VOL: 거래량(추정))
    """
    url = "https://openapi.koreainvestment.com:9443/uapi/overseas-price/v1/quotations/inquire-search"
    headers = {
        "content-type": "application/json; utf-8",
        "authorization": f"Bearer {token}",
        "appkey": settings.KIS_APP_KEY,
        "appsecret": settings.KIS_APP_SECRET,
        "tr_id": "HHDFS76410000",
        "custtype": "P"
    }
    # KEYB: NULL(시총순?), VOL(거래량?), RATE(등락률?)
    # 문서 확인 필요. 일단 KEYB="" 는 시총순(기본).
    # 여기서 KEYB에 값을 넣어 제어.
    key_val = "VOL" if sort_key == "VOL" else "" 
    
    params = {
        "AUTH": "", "EXCD": exchange_code, "CO_YN_VALX": "1",
        "CO_ST_VALX": min_market_cap, "CO_EN_VALX": "999999999999", "KEYB": key_val
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
                        "tvol": item.get('tvol', 0), # ✅ Add Volume
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

# =========================================================
# 🐳 [Whale Hunter] 미국 주식 전용 API
# =========================================================

def fetch_overseas_volume_rank(token, excd="NAS"):
    """
    미국 거래량 상위 (또는 급증) 종목 조회
    - 실시간 거래량 상위를 가져와서 1분 전 데이터와 비교하는 로직은 Watcher에서 수행
    - 여기서는 KIS의 '거래량 상위' API를 호출
    """
    # 해외주식 거래량 상위 (HHDFS76410000 이용 - 조건검색 응용)
    # CO_YN_VALX=1 (시가총액순)이 아닌 CO_YN_VOLX? 
    # 문서상 해외주식 조건검색에서 '전일대비율상위' 등은 있지만 '거래량상위' 정렬 옵션은 
    # '조건검색' inquire-search 에서 KEYB(정렬) 옵션으로 가능할 수 있음.
    # 혹은 '순위분석(거래량)' 전용 TR이 있는지 확인 필요.
    # (없으면 기존 조건검색에서 시총 필터 후 거래량 순 정렬 로직 사용)
    
    # 📌 해외주식 거래량 상위 (HHDFS76410000)
    # KEYB: 정렬기준 (VOL: 거래량)
    return fetch_us_stocks_by_condition(token, excd, min_market_cap="0", sort_key="VOL")

def fetch_overseas_time_sales(token, code, excd="NAS"):
    """
    해외주식 체결추이 (Time & Sales)
    - KIS TR: HHDFS76200300 (해외주식 체결추이)
    - URL: /uapi/overseas-price/v1/quotations/inquire-ccnl
    """
    url = "https://openapi.koreainvestment.com:9443/uapi/overseas-price/v1/quotations/inquire-ccnl"
    headers = {
        "content-type": "application/json; utf-8",
        "authorization": f"Bearer {token}",
        "appkey": settings.KIS_APP_KEY,
        "appsecret": settings.KIS_APP_SECRET,
        "tr_id": "HHDFS76200300"
    }
    
    # Params based on user documentation
    # EXCD: 거래소 (NYS, NAS, AMS)
    # TDAY: 0:전일, 1:당일 -> 실시간 감시니까 '1' (당일)
    # KEYB: Next Key (Paging) -> 공백
    params = {
        "AUTH": "", 
        "EXCD": excd, 
        "SYMB": code,
        "TDAY": "1",
        "KEYB": "" 
    }
    
    try:
        res = requests.get(url, headers=headers, params=params, timeout=3.0)
        
        # Debug
        if res.status_code != 200:
             print(f"⚠️ [Whale] Status: {res.status_code}, Body: {res.text}")
        
        data = res.json()
        if res.status_code == 200 and 'output1' in data:
            # output1 list items (Korean Time)
            # khms: 한국시간, last: 체결가, evol: 체결량, vpow: 체결강도
            return data['output1']
        return []
    except Exception as e:
        print(f"⚠️ [Whale] 체결추이 조회 실패 ({code}): {e}")
        return []

# =========================================================
# 🐳 [K-Whale] 국내 주식 수급 포착
# =========================================================

def fetch_kr_program_trend(token, code):
    """
    [REST] 종목별 프로그램 매매추이 (FHPPG04650101)
    - 당일 프로그램 순매수 추이 확인 (Trigger)
    """
    url = "https://openapi.koreainvestment.com:9443/uapi/domestic-stock/v1/quotations/program-trade-by-stock"
    headers = {
        "content-type": "application/json; utf-8",
        "authorization": f"Bearer {token}",
        "appkey": settings.KIS_APP_KEY,
        "appsecret": settings.KIS_APP_SECRET,
        "tr_id": "FHPPG04650101"
    }
    
    # FID_COND_MRKT_DIV_CODE: J(KRX)
    # FID_INPUT_ISCD: 종목코드
    params = {
        "FID_COND_MRKT_DIV_CODE": "J",
        "FID_INPUT_ISCD": code
    }
    
    try:
        res = requests.get(url, headers=headers, params=params, timeout=5.0)
        data = res.json()
        
        if res.status_code == 200 and 'output' in data:
            # output is list? Doc says 'output' is Object Array (history?). 
            # Usually [0] is latest.
            # Fields: whol_smtn_ntby_tr_pbmn (전체 합계 순매수 거래 대금 - 백만원 단위?)
            # Doc: whol_smtn_ntby_tr_pbmn (전체 합계 순매수 거래 대금)
            return data['output']
        return []
    except Exception as e:
        print(f"⚠️ [K-Whale] 프로그램 추이 조회 실패 ({code}): {e}")
        return []

def fetch_kr_investor_trend(token, code):
    """
    [REST] 국내기관_외국인 매매종목가집계 (FHPTJ04400000)
    - 외국인/기관 잠정 순매수 확인 (Confirmer)
    """
    url = "https://openapi.koreainvestment.com:9443/uapi/domestic-stock/v1/quotations/foreign-institution-total"
    headers = {
        "content-type": "application/json; utf-8",
        "authorization": f"Bearer {token}",
        "appkey": settings.KIS_APP_KEY,
        "appsecret": settings.KIS_APP_SECRET,
        "tr_id": "FHPTJ04400000"
    }
    
    # FID_COND_MRKT_DIV_CODE: V (Default)
    # FID_COND_SCR_DIV_CODE: 16449 (Default)
    # FID_INPUT_ISCD: 종목코드
    # FID_DIV_CLS_CODE: 1 (금액정렬) - 단건 조회시 무의미할 수 있음
    # FID_RANK_SORT_CLS_CODE: 0 (순매수상위)
    # FID_ETC_CLS_CODE: 0 (전체)
    params = {
        "FID_COND_MRKT_DIV_CODE": "V",
        "FID_COND_SCR_DIV_CODE": "16449",
        "FID_INPUT_ISCD": code,
        "FID_DIV_CLS_CODE": "1",
        "FID_RANK_SORT_CLS_CODE": "0",
        "FID_ETC_CLS_CODE": "0" 
    }
    
    try:
        res = requests.get(url, headers=headers, params=params, timeout=5.0)
        data = res.json()
        
        if res.status_code == 200 and 'output' in data:
            # output might be list or dict
            out = data['output']
            if isinstance(out, list):
                return out[0] if out else {}
            return out
        return {}
    except Exception as e:
        print(f"⚠️ [K-Whale] 투자자별 집계 실패 ({code}): {e}")
        return {}

def fetch_kr_broker_trend(token, code, member_code):
    """
    [REST] 주식현재가 회원사 종목매매동향 (FHPST04540000)
    - 특정 회원사(JP모건 등)가 오늘 이 종목을 얼마나 샀는지 확인 (Identifier)
    """
    url = "https://openapi.koreainvestment.com:9443/uapi/domestic-stock/v1/quotations/inquire-member-daily"
    headers = {
        "content-type": "application/json; utf-8",
        "authorization": f"Bearer {token}",
        "appkey": settings.KIS_APP_KEY,
        "appsecret": settings.KIS_APP_SECRET,
        "tr_id": "FHPST04540000"
    }
    
    # FID_COND_MRKT_DIV_CODE: J(KRX)
    # FID_INPUT_ISCD: 종목코드
    # FID_INPUT_ISCD_2: 회원사코드 (예: 012 키움, ??? JP)
    # FID_INPUT_DATE_1 / 2: 날짜 (당일) -> API 내부적으로 처리?
    # Doc: FID_INPUT_DATE_1 (Start Date), FID_INPUT_DATE_2 (End Date)
    today = datetime.now().strftime("%Y%m%d")
    
    params = {
        "FID_COND_MRKT_DIV_CODE": "J",
        "FID_INPUT_ISCD": code,
        "FID_INPUT_ISCD_2": member_code,
        "FID_INPUT_DATE_1": today,
        "FID_INPUT_DATE_2": today,
        "FID_SCTN_CLS_CODE": ""
    }
    
    try:
        res = requests.get(url, headers=headers, params=params, timeout=5.0)
        data = res.json()
        
        if res.status_code == 200 and 'output' in data:
            # output: array
            # ntby_qty (순매수 수량)
            return data['output']
        return []
    except Exception as e:
        print(f"⚠️ [K-Whale] 회원사별 매매동향 실패 ({code}-{member_code}): {e}")
        return []

def fetch_kr_volume_rank(token):
    """
    [REST] 국내주식 거래량 순위 (FHPST01710000)
    - K-Whale 후보군 선정용 (Top 30)
    """
    url = "https://openapi.koreainvestment.com:9443/uapi/domestic-stock/v1/quotations/volume-rank"
    headers = {
        "content-type": "application/json; utf-8",
        "authorization": f"Bearer {token}",
        "appkey": settings.KIS_APP_KEY,
        "appsecret": settings.KIS_APP_SECRET,
        "tr_id": "FHPST01710000",
        "custtype": "P"
    }
    
    # Correct Parameters verified by debug
    params = {
        "FID_COND_MRKT_DIV_CODE": "J",
        "FID_COND_SCR_DIV_CODE": "20171",
        "FID_INPUT_ISCD": "0000",
        "FID_DIV_CLS_CODE": "0",
        "FID_BLNG_CLS_CODE": "0", 
        "FID_TRGT_CLS_CODE": "0", 
        "FID_TRGT_EXLS_CLS_CODE": "0",
        "FID_INPUT_PRICE_1": "",
        "FID_INPUT_PRICE_2": "",
        "FID_VOL_CNT": "",
        "FID_INPUT_VOL_1": "",  # Unused? but keep empty for safety if needed
        "FID_INPUT_VOL_2": "",
        "FID_INPUT_DATE_1": ""
    }
    
    try:
        res = requests.get(url, headers=headers, params=params, timeout=5.0)
        data = res.json()
        if res.status_code == 200 and 'output' in data:
            return data['output']
        return []
    except Exception as e:
        print(f"⚠️ [K-Whale] 거래량 순위 조회 실패: {e}")
        return []

def fetch_kr_bulk_rank(token):
    """
    [REST] 국내주식 대량체결건수 상위 (FHKST190900C0)
    - K-Whale 후보군 보완용 (Top 30)
    - 매수 체결 건수 상위 종목 추출
    """
    url = "https://openapi.koreainvestment.com:9443/uapi/domestic-stock/v1/ranking/bulk-trans-num"
    headers = {
        "content-type": "application/json; utf-8",
        "authorization": f"Bearer {token}",
        "appkey": settings.KIS_APP_KEY,
        "appsecret": settings.KIS_APP_SECRET,
        "tr_id": "FHKST190900C0",
        "custtype": "P"
    }
    
    params = {
        "fid_cond_mrkt_div_code": "J",
        "fid_cond_scr_div_code": "11909",
        "fid_input_iscd": "0000",
        "fid_rank_sort_cls_code": "0",      # 0: 매수 상위
        "fid_div_cls_code": "0",
        "fid_input_price_1": "",
        "fid_aply_rang_prc_1": "",
        "fid_aply_rang_prc_2": "",
        "fid_input_iscd_2": "",
        "fid_trgt_exls_cls_code": "0",
        "fid_trgt_cls_code": "0",
        "fid_vol_cnt": ""
    }
    
    try:
        res = requests.get(url, headers=headers, params=params, timeout=10.0)
        data = res.json()
        if res.status_code == 200 and 'output' in data:
            return data['output']
        return []
    except Exception as e:
        print(f"⚠️ [K-Whale] 대량체결 순위 조회 실패: {e}")
        return []

def fetch_kr_foreign_estimate(token):
    """
    [REST] 외국계 매매종목 가집계 (FHKST644100C0)
    - 실시간 외국인 수급 (가집계) 조회
    - Returns: Dictionary {code: net_buy_qty, ...} or raw list
    """
    url = "https://openapi.koreainvestment.com:9443/uapi/domestic-stock/v1/quotations/frgnmem-trade-estimate"
    headers = {
        "content-type": "application/json; utf-8",
        "authorization": f"Bearer {token}",
        "appkey": settings.KIS_APP_KEY,
        "appsecret": settings.KIS_APP_SECRET,
        "tr_id": "FHKST644100C0",
        "custtype": "P"
    }
    
    # 순매수(0) 기준 정렬 (금액순)
    params = {
        "FID_COND_MRKT_DIV_CODE": "J",
        "FID_COND_SCR_DIV_CODE": "16441",
        "FID_INPUT_ISCD": "0000",        # All stocks
        "FID_RANK_SORT_CLS_CODE": "0",   # Sort by Amount (0)
        "FID_RANK_SORT_CLS_CODE_2": "0"  # Sort by Buy (0)
    }
    
    try:
        res = requests.get(url, headers=headers, params=params, timeout=5.0)
        data = res.json()
        if res.status_code == 200 and 'output' in data:
            return data['output']
        return []
    except Exception as e:
        print(f"⚠️ [K-Whale] 외국계 가집계 조회 실패: {e}")
        return []
