import redis
import ujson
import time

# Redis 설정
REDIS_HOST = 'localhost'
REDIS_PORT = 6379
CHANNEL = 'stock_alert'

def inject_message(data):
    r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0, decode_responses=True)
    message = ujson.dumps(data)
    r.publish(CHANNEL, message)
    print(f"🚀 [Injection] Sent: {data.get('name')} ({data.get('type')})")

def run_test():
    print("🧪 [Test Mode] Injecting Mock Alerts for DB Verification...")

    # 1. 🇰🇷 한국 급등주 (가상 시나리오)
    inject_message({
        "type": "CONDITION",
        "market": "KR",
        "code": "005930",
        "name": "삼성전자",
        "price": "78500",
        "rate": "5.2" # 급등 상황 가정
    })
    time.sleep(2)

    # 2. 🇰🇷 한국 급락주 (가상 시나리오)
    inject_message({
        "type": "CONDITION",
        "market": "KR",
        "code": "086520",
        "name": "에코프로",
        "price": "150000",
        "rate": "-12.5" # 급락 상황 가정
    })
    time.sleep(2)

    # 3. 🇺🇸 미국 주식 (가상 시나리오)
    inject_message({
        "type": "CONDITION_US",
        "market": "US",
        "code": "TSLA",
        "name": "Tesla",
        "price": "245.00",
        "rate": "3.5"
    })
    time.sleep(2)

    # 4. 🏛️ 트럼프 SNS 분석 (사용자 요청)
    # 실제 기사 내용을 일부 발췌하거나, URL만 주면 Worker가 긁어오지만,
    # 여기서는 'Watcher'가 긁어온 것 처럼 'Text'를 넣어줘야 Worker가 분석함.
    # User provided link: https://truthsocial.com/@realDonaldTrump/posts/115868132990949589
    # (내용: 신용카드 이자율 10% 상한 제한 공약)
    trump_text = """
    I will be mandating a 10% INTEREST RATE CAP on Credit Cards, starting January 20th, 2026, for a period of one year. 
    Reviewing the current Marketing and Rates, this is a necessary step to help the American People get back on their feet! 
    The Banks are charging too much, and making record profits while the People suffer. MAKE AMERICA GREAT AGAIN!
    """
    
    inject_message({
        "type": "SNS_ANALYSIS",
        "author": "Donald J. Trump",
        "text": trump_text.strip(),
        "url": "https://truthsocial.com/@realDonaldTrump/posts/115868132990949589"
    })
    
    print("✅ All test messages injected! Check your Worker logs and DB.")

if __name__ == "__main__":
    run_test()
