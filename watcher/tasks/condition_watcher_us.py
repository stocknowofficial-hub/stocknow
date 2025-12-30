import asyncio
import websockets
import ujson
from common.config import settings
from common.redis_client import redis_client

async def run_condition_watcher_us(approval_key):
    """
    [해외 감시팀] 미국 주식 실시간 체결 감시 (좀비 모드)
    - ping_timeout=None 추가로 데이터가 없어도 연결 유지
    """
    
    # [설정] 다시 10개로 늘려도 됩니다! (옵션 켰으니 버틸 겁니다)
    WATCH_LIST = [
        "TSLA", "NVDA", "AAPL", "MSFT", "AMZN", "GOOGL", "AMD", "PLTR",
        "COIN", "MSTR"
    ]
    
    tr_id = "HDFSCNT0"
    uri = f"{settings.KIS_WEBSOCKET_URL}/tryitout/{tr_id}"
    
    while True:
        try:
            print(f"🇺🇸 [해외 감시팀] 연결 시도 중... (Target: {len(WATCH_LIST)}개)")
            
            # [핵심 수정] ping_timeout=None 추가! (이게 없어서 끊긴 겁니다)
            async with websockets.connect(uri, ping_interval=None, ping_timeout=None) as ws:
                print("🇺🇸 [해외 감시팀] 서버 접속 성공! 구독 신청 시작...")

                # 1. 구독 신청 (0.1초 간격)
                for ticker in WATCH_LIST:
                    body = {
                        "header": {
                            "approval_key": approval_key,
                            "custtype": "P",
                            "tr_type": "1",
                            "content-type": "utf-8"
                        },
                        "body": {
                            "input": {
                                "tr_id": tr_id,
                                "tr_key": f"D{ticker}"
                            }
                        }
                    }
                    await ws.send(ujson.dumps(body))
                    await asyncio.sleep(0.1)
                
                print(f"🇺🇸 [해외 감시팀] 구독 완료! 무한 대기 모드 진입.")

                # 2. 수신 루프
                while True:
                    msg = await ws.recv()
                    
                    if isinstance(msg, bytes):
                        msg = msg.decode('utf-8')

                    # 핑퐁 유지
                    if "PINGPONG" in msg:
                        await ws.send(msg)
                        continue

                    # 데이터 수신
                    if msg.startswith('0') or msg.startswith('1'):
                        try:
                            parts = msg.split('|')
                            if len(parts) > 3:
                                raw_data_chunk = parts[3]
                                data_list = raw_data_chunk.split('^')
                                
                                field_count = 26 
                                for i in range(0, len(data_list), field_count):
                                    if i + field_count > len(data_list): break
                                    
                                    row = data_list[i : i+field_count]
                                    symbol = row[0]
                                    
                                    try:
                                        price = float(row[1])
                                        rate = float(row[4])
                                    except:
                                        continue

                                    # [조건 감시] 급등락 (±3%)
                                    if rate >= 3.0 or rate <= -3.0:
                                        emoji = "🔥" if rate > 0 else "🥶"
                                        payload = {
                                            "type": "CONDITION",
                                            "code": symbol,
                                            "name": symbol,
                                            "price": price,
                                            "rate": rate,
                                            "market": "US"
                                        }
                                        await redis_client.publish(settings.REDIS_CHANNEL_STOCK, ujson.dumps(payload))
                                        print(f"{emoji} [US 포착] {symbol} ${price} ({rate}%)")

                        except Exception:
                            pass

        except Exception as e:
            print(f"⚠️ [해외팀] 재접속 시도... ({e})")
            await asyncio.sleep(5)