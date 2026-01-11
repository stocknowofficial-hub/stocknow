import time
import requests
import ujson
import redis
from datetime import datetime

# Configuration
REDIS_HOST = 'localhost'
REDIS_PORT = 6379
REDIS_CHANNEL = 'stock_alert'

def inject_redis(data):
    """Redis에 메시지 주입"""
    try:
        r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0, decode_responses=True)
        message = ujson.dumps(data)
        r.publish(REDIS_CHANNEL, message)
        print(f"🚀 [Redis Injected] Type: {data.get('type')} / Source: {data.get('name', 'Trump')}")
    except Exception as e:
        print(f"❌ [Redis Error] {e}")

# 1. 트럼프 분석 주입 (Context 생성)
def step_1_inject_trump():
    print("\n🏛️ [Step 1] 트럼프 게시글 주입 (Context 생성)")
    trump_data = {
        "type": "SNS_ANALYSIS",
        "market": "US",
        "author": "Donald J. Trump",
        "link": "https://truthsocial.com/@realDonaldTrump/posts/115866624593954329",
        "time": "2026-01-11T12:00:00Z",
        "text": "I will bring down Energy Prices by 50% in my first year! DRILL, BABY, DRILL! This will kill Inflation and make America RICH again. Also, Venezuela sanctions will be lifted if they behave. Cheap Oil is coming!"
    }
    inject_redis(trump_data)

# 2. 관련 급등주 분석 주입 (Recall 테스트)
def step_2_inject_stock():
    print("\n✈️ [Step 2] 관련주(항공) 급등 주입 (Recall 테스트)")
    stock_data = {
        "type": "CONDITION",
        "market": "KR",
        "code": "003490",
        "name": "대한항공",
        "price": "24500",
        "rate": "5.5" # 5.5% 급등
    }
    inject_redis(stock_data)

if __name__ == "__main__":
    print("🧪 [Context-Aware Test] 시작")
    
    # 트럼프 주입 (DB 저장 시간 고려)
    step_1_inject_trump()
    
    print("⏳ [Waiting] 분석 및 DB 저장을 위해 30초 대기...")
    for i in range(30, 0, -1):
        print(f"{i}...", end="\r")
        time.sleep(1)
    
    # 주식 주입 (위의 트럼프 분석을 인용하는지 확인)
    step_2_inject_stock()
    
    print("\n✅ 테스트 완료! 텔레그램/로그를 확인하세요.")
