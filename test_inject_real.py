import redis
import ujson
import time
from datetime import datetime

# Redis Config
REDIS_HOST = 'localhost'
REDIS_PORT = 6379
REDIS_CHANNEL = 'stock_alert'

def inject_test_data():
    r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0)
    
    # Test Data: Hanmi Semiconductor (Bearish)
    stocks = [
        {
            "type": "CONDITION",
            "code": "042700", # Hanmi Semiconductor
            "name": "한미반도체",
            "price": "142500", # Approx price, dummy for test
            "rate": "-5.06",   # Bearish!
            "time": datetime.now().strftime("%H%M%S")
        }
    ]

    print(f"🚀 Injecting Bearish Test Stock to {REDIS_CHANNEL}...")
    
    for stock in stocks:
        r.publish(REDIS_CHANNEL, ujson.dumps(stock))
        print(f"   Done: {stock['name']} ({stock['rate']}%)")
        time.sleep(1)

if __name__ == "__main__":
    inject_test_data()
