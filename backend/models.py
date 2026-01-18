from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.sql import func
from .database import Base

class Subscriber(Base):
    __tablename__ = "subscribers"

    chat_id = Column(String, primary_key=True, index=True)
    username = Column(String, nullable=True)     # ✅ 텔레그램 아이디 (@handle)
    name = Column(String, nullable=True)
    tier = Column(String, default="FREE")        # ✅ FREE, BASIC, PRO
    expiry_date = Column(DateTime, nullable=True)# ✅ 유료 기간 만료일 (Null=무제한/Free)
    payment_cycle = Column(String, nullable=True)# ✅ MONTHLY, YEARLY
    referrer_id = Column(String, nullable=True)  # ✅ [New] 추천인 Chat ID
    
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class StockLog(Base):
    __tablename__ = "stock_logs"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String)
    name = Column(String)
    price = Column(String, nullable=True)
    rate = Column(String, nullable=True)
    summary = Column(String) # AI 요약
    sentiment = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class MarketLog(Base):
    __tablename__ = "market_logs"

    id = Column(Integer, primary_key=True, index=True)
    category = Column(String) # BRIEFING, TRUMP
    title = Column(String)
    content = Column(String) # AI 요약/분석 전문
    sentiment = Column(String, nullable=True)
    sectors = Column(String, nullable=True) # ✅ [New] 관련 섹터 (JSON or String)
    topics = Column(String, nullable=True)  # ✅ [New] 핵심 주제 (JSON or String)
    original_url = Column(String, nullable=True) # 원문 링크 (SNS/뉴스)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
