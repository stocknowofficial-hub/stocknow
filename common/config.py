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
    KIS_BASE_URL: str = "https://openapivts.koreainvestment.com:29443"
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
    TELEGRAM_CHAT_ID: str = ""

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore" 

settings = Settings()