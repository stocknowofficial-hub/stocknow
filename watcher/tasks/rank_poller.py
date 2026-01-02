import asyncio
import requests
import ujson
from datetime import datetime
from common.config import settings
from common.redis_client import redis_client

async def run_rank_poller(access_token):
    """
    [국내 폴링팀] 대장주/관심주 시세 리포트 전송 (주기 변경 가능)
    """
    
    # ====================================================
    # [설정] 몇 분마다 알림을 보낼까요? (숫자만 바꾸세요!)
    # 10 -> 10분, 20분, 30분...
    # 30 -> 매시 0분, 30분
    # 60 -> 매시 정각(0분)
    SEND_INTERVAL_MINUTES = 60
    # ====================================================

    # 감시할 종목 (삼성전자, 하이닉스, LG엔솔, 현대차, 에코프로)
    TARGET_CODES = ["005930", "000660", "373220", "005380", "086520"]

    # 주식현재가 시세 URL (국내)
    url = f"{settings.KIS_BASE_URL}/uapi/domestic-stock/v1/quotations/inquire-price"
    
    headers = {
        "content-type": "application/json; utf-8",
        "authorization": f"Bearer {access_token}",
        "appkey": settings.KIS_APP_KEY,
        "appsecret": settings.KIS_APP_SECRET,
        "tr_id": "FHKST01010100"
    }

    print(f"📊 [국내 폴링팀] 대장주 모니터링 시작! ({SEND_INTERVAL_MINUTES}분 간격)(08:00 ~ 16:00 가동)")
    # 중복 발송 방지용
    last_sent_minute = -1 

    while True:
        try:
            now = datetime.now()
            current_hour = now.hour
            current_minute = now.minute
            current_time_str = now.strftime("%H:%M")
            if 8 <= current_hour < 16:
                # [핵심 로직] 설정한 간격에 맞는지 확인
                is_time_to_send = (current_minute % SEND_INTERVAL_MINUTES == 0)

                # 시간 맞고 + 이번 분에 아직 안 보냈으면 -> 발송
                if is_time_to_send and (current_minute != last_sent_minute):
                    
                    print(f"⏰ [국내 폴링팀] {current_time_str} 리포트 생성 시작!")
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
                                
                                # 안전하게 정수 변환 (데이터가 없을 경우 대비 0 처리)
                                try:
                                    price = int(output.get('stck_prpr', '0'))
                                    rate = float(output.get('prdy_ctrt', '0.0'))
                                except ValueError:
                                    price = 0
                                    rate = 0.0
                                
                                emoji = "📈" if rate > 0 else "📉"
                                if rate == 0: emoji = "➖"

                                # 가격 천단위 콤마
                                report_data.append(f"{emoji} {name} {price:,}원 ({rate}%)")
                        
                        # API 호출 부하 방지
                        await asyncio.sleep(0.2)

                    if report_data:
                        payload = {
                            "type": "RANKING",
                            "time": current_time_str,
                            "data": report_data
                        }
                        await redis_client.publish(settings.REDIS_CHANNEL_STOCK, ujson.dumps(payload))
                        print(f"🚀 [전송완료] {current_time_str} 국내 리포트 발송 완료!")
                        
                        last_sent_minute = current_minute
            else:
                # 근무 시간이 아니면 조용히 로그 한 번만 찍고 넘어가거나, 그냥 쉼
                # (너무 자주 찍히면 로그 더러워지니 생략 가능)
                pass

        except Exception as e:
            print(f"❌ [국내 폴링팀] 에러: {e}")
        
        # [절대 수정 금지] 무조건 1분만 자고 일어나서 시계 확인 (연결 유지 핵심)
        await asyncio.sleep(60)