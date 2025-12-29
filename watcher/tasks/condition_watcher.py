import asyncio
import websockets
import ujson
from common.config import settings
from common.redis_client import redis_client

async def run_condition_watcher(approval_key):
    """사용자 조건검색 (ReasonHunter) 감시"""
    uri = f"{settings.KIS_WEBSOCKET_URL}/tryitout/H0STCNI9"
    
    while True:
        try:
            print(f"🕵️ [조건팀] 'ReasonHunter(000)' 감시 시작... (ID: {settings.KIS_HTS_ID})")
            
            # ID 설정 안되어 있으면 경고
            if not settings.KIS_HTS_ID:
                print("🛑 [조건팀] .env에 KIS_HTS_ID가 없습니다! 설정해주세요.")
                await asyncio.sleep(10)
                continue

            async with websockets.connect(uri, ping_interval=None) as ws:                # 구독 요청
                body = {
                    "header": {
                        "approval_key": approval_key,
                        "custtype": "P",
                        "tr_type": "1",
                        "content-type": "utf-8"
                    },
                    "body": {
                        "input": {
                            "tr_id": "H0STCNI9", 
                            "tr_key": settings.KIS_HTS_ID, # <--- 여기가 핵심 수정 (ID 입력)
                            "seq": "000" # 첫 번째 조건
                        }
                    }
                }
                await ws.send(ujson.dumps(body))
                
                while True:
                    msg = await ws.recv()
                    if isinstance(msg, bytes): msg = msg.decode('utf-8')

                    if msg[0] in ['0', '1']:
                        parts = msg.split('|')
                        if len(parts) > 3:
                            data = parts[3].split('^')
                            payload = {
                                "type": "CONDITION",
                                "code": data[0],
                                "name": data[1],
                                "price": data[2],
                                "rate": data[3]
                            }
                            await redis_client.publish(settings.REDIS_CHANNEL_STOCK, ujson.dumps(payload))
                            print(f"🔥 [조건포착] {data[1]}({data[0]}) : {data[3]}% 상승!")
                    elif "PINGPONG" not in msg:
                        # 시스템 메시지 파싱해서 보여주기
                        try:
                            parsed = ujson.loads(msg)
                            msg1 = parsed.get('body', {}).get('msg1')
                            if msg1:
                                print(f"🕵️ [조건팀] 서버 응답: {msg1}")
                            else:
                                print(f"🕵️ [조건팀] 상태: {msg[:50]}...")
                        except:
                             print(f"🕵️ [조건팀] 상태: {msg[:50]}...")

        except Exception as e:
            print(f"❌ [조건팀] 연결 끊김 (5초 후 재접속): {e}")
            await asyncio.sleep(5)