import asyncio
import ujson
from common.config import settings
from common.redis_client import redis_client

async def send_dummy_data():
    print(f"🚀 [Tester] 다양한 종목 뉴스 테스트 시작!")

    # 1. [조건검색] 카카오 (악재/호재 뉴스 체크)
    case_1 = {
        "type": "CONDITION",
        "code": "035720",
        "name": "카카오",
        "price": "54300",
        "rate": "3.12"
    }
    
    # 2. [VI 발동] 에코프로 (이름 없이 코드로만 줘도 뉴스를 찾는지 테스트)
    # * Worker 로직상 name이 없으면 code("086520")로 검색함
    case_2 = {
        "type": "VI",
        "code": "086520", 
        "name": "에코프로", # VI watcher는 원래 이름 안주지만, 테스트 위해 추가
        "status": "발동",
        "price": "650000",
        "rate": "12.5",
        "time": "10:15:00"
    }

    # 3. [조건검색] 하이브 (엔터주 뉴스)
    case_3 = {
        "type": "CONDITION",
        "code": "352820",
        "name": "하이브",
        "price": "245000",
        "rate": "-4.5" # 하락 뉴스
    }

    # 전송
    print("📡 1. 카카오 (조건검색) 전송")
    await redis_client.publish(settings.REDIS_CHANNEL_STOCK, ujson.dumps(case_1))
    await asyncio.sleep(2) # 뉴스 검색 시간 고려해서 2초 대기

    print("📡 2. 에코프로 (VI) 전송")
    await redis_client.publish(settings.REDIS_CHANNEL_STOCK, ujson.dumps(case_2))
    await asyncio.sleep(2)

    print("📡 3. 하이브 (조건검색) 전송")
    await redis_client.publish(settings.REDIS_CHANNEL_STOCK, ujson.dumps(case_3))
    
    print("✅ 테스트 데이터 전송 완료! 텔레그램을 확인하세요.")
    await redis_client.close()

if __name__ == "__main__":
    asyncio.run(send_dummy_data())