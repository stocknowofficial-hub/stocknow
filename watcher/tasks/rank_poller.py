import asyncio
import requests
import ujson
from datetime import datetime
from common.config import settings
from common.redis_client import redis_client

async def run_rank_poller(access_token):
    """
    지정된 시간에 '상승률 Top N'과 '하락률 Top N'을 조회하여 전송
    """
    
    # ==========================================
    # [설정] 여기서 숫자만 바꾸면 개수가 변합니다!
    TOP_N = 5 
    # ==========================================

    # 알림 보낼 시간 (시:분)
    TARGET_TIMES = ["09:00", "10:00", "13:00", "15:20"] 
    last_sent_time = ""

    # KIS API URL (등락률 순위)
    # *주의: 모의투자(VTS)는 이 URL이 지원 안 될 수도 있습니다. 
    # 만약 에러나면 실전투자 URL로 바꾸거나, 모의투자용 거래량 순위로 임시 복귀해야 합니다.
    url = f"{settings.KIS_BASE_URL}/uapi/domestic-stock/v1/ranking/fluctuation"
    
    headers = {
        "content-type": "application/json; utf-8",
        "authorization": f"Bearer {access_token}",
        "appkey": settings.KIS_APP_KEY,
        "appsecret": settings.KIS_APP_SECRET,
        "tr_id": "FHPST01700000" # 등락률 순위 TR ID
    }
    
    # 공통 파라미터 (일단 세팅해둠)
    base_params = {
        "fid_cond_mrkt_div_code": "J", # J: 주식
        "fid_cond_scr_div_code": "20170",
        "fid_input_iscd": "0000", # 전체
        "fid_rank_sort_cls_code": "0", # 0:상승, 1:하락 (아래에서 동적으로 변경)
        "fid_input_cnt_1": str(TOP_N), # 조회 개수
        "fid_prc_cls_code": "0",
        "fid_input_price_1": "",
        "fid_input_price_2": "",
        "fid_vol_cnt": "",
        "fid_trgt_cls_code": "0"
    }

    print(f"📊 [랭킹팀] 대기 중... (상승/하락 각각 {TOP_N}개, 시간: {TARGET_TIMES})")

    while True:
        try:
            now = datetime.now()
            current_time_str = now.strftime("%H:%M")

            # 목표 시간이고, 아직 안 보냈다면 실행
            if current_time_str in TARGET_TIMES and current_time_str != last_sent_time:
                print(f"⏰ [랭킹팀] {current_time_str} 정기 리포트 생성 시작!")
                
                report_data = []

                # --- 1. 상승률(Rising) 조회 ---
                base_params["fid_rank_sort_cls_code"] = "0" # 0 = 상승
                res_rise = requests.get(url, headers=headers, params=base_params)
                
                if res_rise.status_code == 200:
                    items = res_rise.json().get('output', []) or []
                    for item in items[:TOP_N]:
                        name = item.get('hts_kor_isnm', '-')
                        rate = item.get('prdy_ctrt', '0')
                        report_data.append(f"📈 {name} (+{rate}%)")
                else:
                    print(f"⚠️ 상승률 조회 실패: {res_rise.status_code}")
                
                # API 연속 호출 시 0.5초 매너 대기 (오류 방지)
                await asyncio.sleep(0.5)

                # --- 2. 하락률(Falling) 조회 ---
                base_params["fid_rank_sort_cls_code"] = "1" # 1 = 하락
                res_fall = requests.get(url, headers=headers, params=base_params)
                
                if res_fall.status_code == 200:
                    items = res_fall.json().get('output', []) or []
                    for item in items[:TOP_N]:
                        name = item.get('hts_kor_isnm', '-')
                        rate = item.get('prdy_ctrt', '0')
                        report_data.append(f"📉 {name} ({rate}%)")
                else:
                    print(f"⚠️ 하락률 조회 실패: {res_fall.status_code}")

                # --- 3. Redis 전송 ---
                if report_data:
                    payload = {
                        "type": "RANKING",
                        "time": current_time_str,
                        "data": report_data
                    }
                    await redis_client.publish(settings.REDIS_CHANNEL_STOCK, ujson.dumps(payload))
                    print(f"🚀 [전송완료] 상승/하락 랭킹 리포트 발송 완료!")
                    last_sent_time = current_time_str
                else:
                    print("💤 데이터가 없어서 전송하지 않았습니다.")

        except Exception as e:
            print(f"❌ [랭킹팀] 에러: {e}")
        
        await asyncio.sleep(60) # 1분 대기