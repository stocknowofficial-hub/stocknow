import asyncio
import websockets
import ujson
from common.config import settings
from common.redis_client import redis_client

async def run_vi_watcher(approval_key):
    """시장 전체 VI(급등락) 감시 - Safe Mode"""
    uri = f"{settings.KIS_WEBSOCKET_URL}/tryitout/H1SEVENT"
    
    while True:
        try:
            print(f"👮 [VI팀] 감시 시작합니다...")
            async with websockets.connect(uri) as ws:
                # 구독 요청
                body = {
                    "header": {"approval_key": approval_key, "custtype": "P", "tr_type": "1", "content-type": "utf-8"},
                    "body": {"input": {"tr_id": "H1SEVENT", "tr_key": "1"}} # 1: 코스피/코스닥 전체
                }
                await ws.send(ujson.dumps(body))
                
                while True:
                    msg = await ws.recv()
                    if isinstance(msg, bytes): msg = msg.decode('utf-8')
                    
                    # 데이터 수신 (0:실시간, 1:TR)
                    if msg[0] in ['0', '1']:
                        try:
                            # 1차 파싱 (헤더|본문)
                            parts = msg.split('|')
                            if len(parts) > 3:
                                # 2차 파싱 (데이터^나열)
                                raw_data = parts[3]
                                data = raw_data.split('^')
                                
                                # [안전장치] 데이터 개수가 충분한지 확인
                                if len(data) > 13:
                                    # 인덱스 매핑 (문서 기준 + 경험치)
                                    # 0:코드, 1:시간, 2:구분, 11:등락률, 13:가격
                                    code = data[0]
                                    time_str = data[1]
                                    status = data[2] # VI발동구분
                                    rate = data[11]  # 등락률
                                    price = data[13] # 가격

                                    payload = {
                                        "type": "VI",
                                        "code": code,
                                        "status": status,
                                        "price": price,
                                        "rate": rate,
                                        "time": time_str
                                    }
                                    await redis_client.publish(settings.REDIS_CHANNEL_STOCK, ujson.dumps(payload))
                                    print(f"🚨 [VI발동] {code} / {price}원 ({rate}%)")
                                else:
                                    # 데이터가 짧게 왔을 때 (죽지 않고 로그만 남김)
                                    print(f"⚠️ [VI팀] 데이터 포맷 이상 (길이 부족): {raw_data[:50]}...")

                        except Exception as parse_error:
                            # 파싱하다 에러나도 죽지 않음
                            print(f"⚠️ [VI팀] 파싱 에러 (무시됨): {parse_error}")

                    elif "PINGPONG" not in msg:
                        # PINGPONG 제외 잡다한 시스템 메시지는 무시하거나 로그 찍기
                        pass

        except Exception as e:
            print(f"❌ [VI팀] 연결 끊김 (5초 후 재접속): {e}")
            await asyncio.sleep(5)