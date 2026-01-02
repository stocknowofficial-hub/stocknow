import asyncio
import json
import redis.asyncio as redis

# ==========================================
# ⚙️ 설정
# ==========================================
REDIS_HOST = 'localhost'
REDIS_PORT = 6379
CHANNEL_STOCK = 'stock_alert' # NewsCrawler가 듣고 있는 채널

async def send_dummy_signals():
    # 1. Redis 연결
    r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0, decode_responses=True)
    
    print(f"🚀 [Tester] 가상 주식 신호 발사 준비 완료! (Target: {CHANNEL_STOCK})")
    print(f"🐌 [Slow Mode] Local LLM 보호를 위해 30초 간격으로 전송합니다.")

    # ==========================================
    # 🧪 테스트 시나리오 데이터
    # ==========================================
    scenarios = [
        {
            "desc": "1. 네이버 (국내 대형주)",
            "data": {
                "type": "CONDITION",
                "code": "035420",
                "name": "NAVER",
                "price": "215000",
                "rate": "3.5",
                "market": "KR"
            }
        },
        {
            "desc": "2. 엔비디아 (미국 주식 - CONDITION_US)",
            "data": {
                "type": "CONDITION_US",
                "code": "NVDA",
                "name": "엔비디아", # 네이버 검색을 위해 한글 이름 사용 권장
                "price": "135.50",
                "rate": "4.2",
                "market": "US",
                "exchange": "NASDAQ"
            }
        }
    ]

    # ==========================================
    # 📡 신호 전송 루프
    # ==========================================
    for idx, scenario in enumerate(scenarios):
        description = scenario['desc']
        payload = scenario['data']
        stock_name = payload['name']

        print(f"\n📡 [전송 {idx+1}/{len(scenarios)}] {description}")
        
        # Redis로 JSON 문자열 발행 (Publish)
        await r.publish(CHANNEL_STOCK, json.dumps(payload, ensure_ascii=False))
        
        print(f"   👉 '{stock_name}' 신호 전송 완료.")
        
        # 마지막 전송 후에는 대기할 필요 없음 (하지만 LLM이 돌고 있으니 프로세스 유지를 위해 대기해도 됨)
        if idx < len(scenarios) - 1:
            print(f"   💤 Local LLM 쿨타임 (30초 대기 중)...")
            for i in range(30, 0, -5): # 5초마다 카운트다운
                print(f"      {i}초...", end="\r")
                await asyncio.sleep(5)
            print("      Go! 🚀        ")
        else:
            print("   ✅ 모든 신호 전송 완료! (AI 분석 결과를 기다리세요)")

    await r.aclose()

if __name__ == "__main__":
    try:
        asyncio.run(send_dummy_signals())
    except KeyboardInterrupt:
        print("테스트 중단됨")