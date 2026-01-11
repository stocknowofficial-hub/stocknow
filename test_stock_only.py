import redis
import ujson

REDIS_HOST = 'localhost'
REDIS_PORT = 6379
REDIS_CHANNEL = 'stock_alert'

def inject_stock():
    print("\n✈️ [Test] 대한항공 급등 주입 (한국어 Note 확인용)")
    stock_data = {
        "type": "CONDITION",
        "market": "KR",
        "code": "003490",
        "name": "대한항공",
        "price": "24500",
        "rate": "5.5" 
    }
    
    r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0, decode_responses=True)
    r.publish(REDIS_CHANNEL, ujson.dumps(stock_data))
    print(f"🚀 [Injected] 대한항공 분석 요청 전송 완료")

if __name__ == "__main__":
    inject_stock()
