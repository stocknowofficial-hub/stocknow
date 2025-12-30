import asyncio
import websockets
import ujson
from common.config import settings
from common.redis_client import redis_client

async def run_condition_watcher(approval_key, access_token=None):
    """
    [국내 조건팀] HTS 조건식 'ReasonHunter' (강제 000번 접속)
    - 복잡한 조회 API 제거
    - 연결 끊김 방지 옵션 완비
    """
    
    # 묻지도 따지지도 않고 000번으로 갑니다.
    CONDITION_IDX = "000" 

    # 실전용 웹소켓 주소 확인
    uri = f"{settings.KIS_WEBSOCKET_URL}/tryitout/H0STCNI0"

    print(f"🕵️ [국내 조건팀] API 조회 건너뛰고 '000'번으로 직진합니다!")

    while True:
        try:
            print(f"🕵️ [국내 조건팀] 접속 시도 중... (Target: {CONDITION_IDX})")
            
            # [핵심] ping_interval=None, ping_timeout=None (좀비 모드: 절대 안 끊김)
            async with websockets.connect(uri, ping_interval=None, ping_timeout=None) as ws:
                print("🕵️ [국내 조건팀] 서버 문 열렸습니다! 구독 신청...")

                # 구독 요청
                body = {
                    "header": {
                        "approval_key": approval_key,
                        "custtype": "P",
                        "tr_type": "1",
                        "content-type": "utf-8"
                    },
                    "body": {
                        "input": {
                            "tr_id": "H0STCNI0", 
                            "tr_key": CONDITION_IDX 
                        }
                    }
                }
                await ws.send(ujson.dumps(body))

                # 데이터 수신 루프
                while True:
                    msg = await ws.recv()
                    
                    if isinstance(msg, bytes):
                        msg = msg.decode('utf-8')

                    # 1. 핑퐁 (연결 유지)
                    if "PINGPONG" in msg:
                        await ws.send(msg)
                        continue
                    
                    # 2. 데이터 수신
                    if msg.startswith('0') or msg.startswith('1'):
                        try:
                            parts = msg.split('|')
                            if len(parts) > 3:
                                raw_data = parts[3]
                                data = raw_data.split('^')
                                
                                code = data[0]
                                name = data[1]
                                price = data[2]
                                rate = data[3]
                                
                                payload = {
                                    "type": "CONDITION",
                                    "code": code,
                                    "name": name,
                                    "price": price,
                                    "rate": rate,
                                    "market": "KR"
                                }
                                await redis_client.publish(settings.REDIS_CHANNEL_STOCK, ujson.dumps(payload))
                                print(f"🔥 [KR 조건포착] {name}({code}) {rate}%")
                        except:
                            pass
                    
                    # 3. 에러 메시지 체크
                    else:
                        try:
                            msg_json = ujson.loads(msg)
                            if 'body' in msg_json and 'msg1' in msg_json['body']:
                                log_msg = msg_json['body']['msg1']
                                
                                # 중복 접속 에러 시 대기
                                if "ALREADY IN USE" in log_msg:
                                    print(f"⚠️ [서버] 기존 접속 해제 대기 중... (40초 휴식)")
                                    await asyncio.sleep(40)
                                    break
                                
                                # 성공 메시지는 로그만 살짝
                                if "SUBSCRIBE SUCCESS" in log_msg:
                                    print("🕵️ [국내 조건팀] 구독 승인 완료! 감시 시작.")

                        except:
                            pass

        except Exception as e:
            print(f"❌ [국내 조건팀] 연결 끊김 (10초 후 재시도): {e}")
            await asyncio.sleep(10)

            