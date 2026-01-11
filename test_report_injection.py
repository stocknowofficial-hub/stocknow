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
        print(f"🚀 [Redis Injected] Type: {data.get('type')} / Source: {data.get('source')}")
    except Exception as e:
        print(f"❌ [Redis Error] {e}")

# 1. BlackRock 2026 Outlook 주입
def step_1_inject_blackrock():
    print("\n🏛️ [Step 1] BlackRock 2026 Outlook 주입")
    text = """
    BlackRock Investment Institute: 2026 Investment Outlook.
    Mega forces trump macro. As we enter 2026, the global economy is being transformed by AI. 
    There is no room for a neutral stance. We advocate for active investing.
    
    Key Themes:
    1. AI Buildout: Over $500 billion invested in data centers. We expect this to accelerate. AI is the primary driver of productivity.
    2. Market Concentration: Largest US stocks account for a growing share. Customized diversification is key.
    3. Low Carbon Transition: Infrastructure for AI requires massive energy. 
    
    Asset Allocation:
    - Overweight: US Equities (AI Theme), Japanese Stocks.
    - Opportunities: Private Credit, Infrastructure (supporting AI/Energy).
    - Underweight: Long-term bonds due to fiscal concerns.
    
    Risks: Geopolitical fragmentation (Venezuela, Ukraine) and potential inflation resurgence.
    """
    
    data = {
        "type": "REPORT_ANALYSIS",
        "source": "BlackRock",
        "title": "2026 Global Outlook: Mega Forces",
        "text": text,
        "url": "https://www.blackrock.com/2026-outlook",
        "time": "2026-01-05 09:00:00"
    }
    inject_redis(data)

# 2. Kiwoom 2026 Jan Strategy 주입
def step_2_inject_kiwoom():
    print("\n🇰🇷 [Step 2] Kiwoom 2026년 1월 증시 전망 주입")
    text = """
    키움증권 1월 주간 전략: 코스피 5200선 돌파 기대.
    
    1. 반도체 슈퍼사이클: AI 수요 폭증으로 HBM 및 서버용 D램 가격이 지속 상승 중.
       삼성전자 목표주가 17만원 상향 (KB, 신한도 동참).
    
    2. 매크로 환경: 미국 금리 인하 기대감과 한국 수출 호조. 
       특히 반도체 수출이 역대 최고치를 경신할 것으로 전망.
    
    3. 주목할 섹터:
       - 반도체 (삼성전자, SK하이닉스): 실적 레벨업.
       - 전력설비 (LS Electric): AI 데이터센터 전력 수요 급증.
       - 조선/방산: 수주 잔고 확대.
    
    4. 리스크: 단기 급등에 따른 차익 매물 출회 가능성. 미국 12월 CPI 발표 유의.
    """
    
    data = {
        "type": "REPORT_ANALYSIS",
        "source": "Kiwoom",
        "title": "1월 증시 전망: 반도체 슈퍼사이클과 5200p",
        "text": text,
        "url": "https://www.kiwoom.com/research/jan-2026",
        "time": "2026-01-11 08:00:00"
    }
    inject_redis(data)

# 3. 삼성전자 급등 주입 (Kiwoom 리포트 Recall 테스트)
def step_3_inject_stock():
    print("\n📈 [Step 3] 삼성전자 급등 주입 (Recall 테스트)")
    stock_data = {
        "type": "CONDITION",
        "market": "KR",
        "code": "005930",
        "name": "삼성전자",
        "price": "98000",
        "rate": "4.2" # 4.2% 급등
    }
    inject_redis(stock_data)

if __name__ == "__main__":
    print("🧪 [Report Analysis Test] 시작")
    
    step_1_inject_blackrock()
    time.sleep(2) # 순서 보장
    
    step_2_inject_kiwoom()
    
    print("⏳ [Waiting] 리포트 분석 및 저장을 위해 45초 대기...")
    for i in range(45, 0, -1):
        print(f"{i}...", end="\r")
        time.sleep(1)
        
    step_3_inject_stock()
    
    print("\n✅ 테스트 완료! 로그를 확인하세요.")
