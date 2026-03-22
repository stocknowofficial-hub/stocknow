from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # =================================
    # 1. KIS (한국투자증권) 정보
    # =================================
    KIS_APP_KEY: str = ""
    KIS_APP_SECRET: str = ""
    KIS_ACCOUNT_NO: str = ""
    KIS_HTS_ID: str = ""
    
    # [추가된 부분] 모의투자 전용 서버 주소 (URL)
    # 실전투자 때는 .env에서 이 값을 덮어쓰면 됩니다.
    BACKEND_URL: str = "http://backend:8000"
    CLOUDFLARE_URL: str = "https://stock-now.pages.dev"

    # 모의
    # KIS_BASE_URL: str = "https://openapivts.koreainvestment.com:29443"
    # KIS_WEBSOCKET_URL: str = "ws://ops.koreainvestment.com:31000"

    # 실전
    KIS_BASE_URL: str = "https://openapi.koreainvestment.com:9443"
    KIS_WEBSOCKET_URL: str = "ws://ops.koreainvestment.com:21000"
    # =================================
    # 2. Redis 설정
    # =================================
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_CHANNEL_STOCK: str = "stock_alert"

    # =================================
    # 3. Telegram 설정
    # =================================
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_CHAT_ID: str = "" # (Legacy: for Admin/Error logs)

    # [New] Channels
    TELEGRAM_VIP_CHANNEL_ID: str = ""
    TELEGRAM_FREE_CHANNEL_ID: str = ""

    # [추가] 네이버 API 설정
    NAVER_CLIENT_ID: str = ""
    NAVER_CLIENT_SECRET: str = ""

    # 👇 이거 추가
    GOOGLE_API_KEY: str = ""

    # [Cron] Cloudflare API 인증 시크릿 (worker → Cloudflare)
    CRON_SECRET: str = ""

    # ✅ [Payment Secrets] 시크릿 링크용 비밀키 (유출 주의)
    # 실제 운영 시엔 .env로 빼는 것이 좋습니다.
    PAYMENT_SECRETS: dict = {
        "req_1m": "SECRET_1M_2026", # 1개월권
        "req_6m": "SECRET_6M_2026", # 6개월권 (3+3 이벤트)
        "req_1y": "SECRET_1Y_2026", # 1년권
    }

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore" 

    

settings = Settings()