from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from pydantic import BaseModel
from typing import List
import os
import requests as http_requests
import ujson

from . import models, database
from common.config import settings
from common.redis_client import redis_client

# DB 테이블 생성
models.Base.metadata.create_all(bind=database.engine)

app = FastAPI(title="Reason Hunter API")

# ✅ Logger Setup
from common.logger import setup_logger
logger = setup_logger("Backend", "logs/backend", "backend.log")

# ✅ [CORS 설정] 프론트엔드(Next.js:3000) 접근 허용
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # 개발 편의상 전체 허용 (보안상 추후 프론트 주소로 한정 권장)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic Model
class SubscriberCreate(BaseModel):
    chat_id: str
    name: str | None = None
    username: str | None = None # ✅ 추가
    referrer_id: str | None = None # ✅ [New] 추천인 ID

class SubscriberResponse(BaseModel):
    chat_id: str
    is_active: bool
    rewarded_referrer_id: str | None = None # ✅ [New] 보상받은 추천인 ID (알림용)

class SubscriberDetail(BaseModel):
    chat_id: str
    username: str | None = None # ✅ 추가
    name: str | None = None
    tier: str # ✅ 추가
    referrer_id: str | None = None # ✅ [New] Admin 표시용
    expiry_date: datetime | None = None # ✅ 추가
    is_active: bool
    created_at: datetime | None = None

    class Config:
        from_attributes = True # ORM 모드 (Pydantic v2)

@app.post("/subscribers", response_model=SubscriberResponse)
def create_subscriber(sub: SubscriberCreate, db: Session = Depends(database.get_db)):
    db_sub = db.query(models.Subscriber).filter(models.Subscriber.chat_id == sub.chat_id).first()
    if db_sub:
        # 이미 존재하면 활성화 & 정보 최신화
        if not db_sub.is_active:
            db_sub.is_active = True
        
        # 이름/Username이 바뀌었을 수도 있으니 업데이트
        if sub.name: db_sub.name = sub.name
        if sub.username: db_sub.username = sub.username
        
        db.commit()
        db.refresh(db_sub)
        logger.info(f"👤 Subscriber Updated: {db_sub.name} ({db_sub.chat_id})")
        return db_sub
    
    # 신규 생성 (🎁 2주 무료 체험 적용)
    new_sub = models.Subscriber(
        chat_id=sub.chat_id, 
        name=sub.name,
        username=sub.username,
        tier="PRO", # ✅ 기본값 PRO (체험판)
        referrer_id=sub.referrer_id, # ✅ [New] 신규 가입 시에만 추천인 기록
        expiry_date=datetime.now() + timedelta(days=14) # ✅ 14일 뒤 만료
    )
    db.add(new_sub)
    
    # ✅ [Referral Reward] 추천인 보상 로직 (신규 가입 시에만)
    if sub.referrer_id:
        # 추천인 조회 (Referrer = Chat ID)
        referrer = db.query(models.Subscriber).filter(models.Subscriber.chat_id == sub.referrer_id).first()
        if referrer:
            # 보상: +14일 (2주) 연장
            # 만료일이 지났으면 '지금'부터 +14일, 안 지났으면 '기존만료일' +14일
            current_expiry = referrer.expiry_date or datetime.now()
            if current_expiry < datetime.now():
                current_expiry = datetime.now()
            
            referrer.expiry_date = current_expiry + timedelta(days=14)
            
            # ✅ [Cap Update] 최대 연장 한도 (60일 = 약 8주)
            max_limit = datetime.now() + timedelta(days=60)
            if referrer.expiry_date > max_limit:
                referrer.expiry_date = max_limit
                logger.info(f"   ⚠️ [Cap Reached] Extension limited to 60 days.")
            logger.info(f"🎁 [Referral Reward] {referrer.name} ({referrer.chat_id}) Extended by 14 days (New Expiry: {referrer.expiry_date})")
            
            # [Notification Trigger] Response에 실어보냄
            new_sub.rewarded_referrer_id = referrer.chat_id

    db.commit()
    db.refresh(new_sub)
    logger.info(f"✨ New Subscriber (Trial Logic): {new_sub.name} ({new_sub.chat_id}) - Expires: {new_sub.expiry_date}")
    return new_sub

@app.get("/subscribers", response_model=List[str])
def get_active_subscribers(db: Session = Depends(database.get_db)):
    subs = db.query(models.Subscriber).filter(models.Subscriber.is_active == True).all()
    return [sub.chat_id for sub in subs]

# ✅ [Admin] 상세 조회 (이름, 가입일, 활성여부 포함)
@app.get("/subscribers/detail", response_model=List[SubscriberDetail])
def get_all_subscribers(db: Session = Depends(database.get_db)):
    return db.query(models.Subscriber).all()

# ✅ [Admin] 정보 수정 (Tier, Active 등)
class SubscriberUpdate(BaseModel):
    is_active: bool | None = None
    tier: str | None = None
    username: str | None = None
    name: str | None = None
    expiry_date: datetime | None = None # ✅ Expiry Update Support

@app.put("/subscribers/{chat_id}")
def update_subscriber(chat_id: str, update: SubscriberUpdate, db: Session = Depends(database.get_db)):
    sub = db.query(models.Subscriber).filter(models.Subscriber.chat_id == chat_id).first()
    if not sub:
        raise HTTPException(status_code=404, detail="Subscriber not found")
    
    if update.is_active is not None: sub.is_active = update.is_active
    if update.tier is not None: sub.tier = update.tier
    if update.username is not None: sub.username = update.username
    if update.name is not None: sub.name = update.name
    if update.expiry_date is not None: sub.expiry_date = update.expiry_date
    
    # Tier 변경 시 만료일 처리 로직 (예: PRO -> 30일 뒤, FREE -> Null)은 프론트에서 처리하거나 여기서 처리
    # 일단은 단순 Field Update만 수행
    
    db.commit()
    db.refresh(sub)
    return sub

@app.delete("/subscribers/{chat_id}")
def delete_subscriber(chat_id: str, db: Session = Depends(database.get_db)):
    sub = db.query(models.Subscriber).filter(models.Subscriber.chat_id == chat_id).first()
    if not sub:
        raise HTTPException(status_code=404, detail="Subscriber not found")
    
    db.delete(sub)
    db.commit()
    return {"message": "Deleted successfully"}

# ✅ [Analysis] 분석 결과 저장 (Split DB)
class StockLogCreate(BaseModel):
    code: str
    name: str
    price: str | None = None
    rate: str | None = None
    summary: str
    sentiment: str | None = None

class MarketLogCreate(BaseModel):
    category: str # BRIEFING, TRUMP
    title: str
    content: str
    sentiment: str | None = None
    sectors: str | None = None # ✅ [New]
    topics: str | None = None # ✅ [New]
    original_url: str | None = None

@app.post("/analysis/stock")
def create_stock_log(log: StockLogCreate, db: Session = Depends(database.get_db)):
    db_log = models.StockLog(
        code=log.code,
        name=log.name,
        price=log.price,
        rate=log.rate,
        summary=log.summary,
        sentiment=log.sentiment
    )
    db.add(db_log)
    db.commit()
    logger.info(f"💾 Stock Log Saved: {log.name} ({log.code})")
    return db_log

@app.post("/analysis/market")
def create_market_log(log: MarketLogCreate, db: Session = Depends(database.get_db)):
    db_log = models.MarketLog(
        category=log.category,
        title=log.title,
        content=log.content,
        sentiment=log.sentiment,
        sectors=log.sectors, # ✅ [New]
        topics=log.topics,   # ✅ [New]
        original_url=log.original_url
    )
    db.add(db_log)
    db.commit()
    logger.info(f"💾 Market Log Saved: {log.title} [{log.category}]")
    return db_log

@app.get("/analysis/market/recent")
def get_recent_market_logs(days: int = 7, db: Session = Depends(database.get_db)):
    """최근 N일간의 시장 브리핑/분석 로그 조회 (Context 주입용)"""
    cutoff_date = datetime.now() - timedelta(days=days)
    logs = db.query(models.MarketLog).filter(
        models.MarketLog.created_at >= cutoff_date
    ).order_by(models.MarketLog.created_at.desc()).all()
    
    return [
        {
            "date": log.created_at.strftime("%Y-%m-%d"),
            "category": log.category,
            "title": log.title,
            "sectors": log.sectors,
            "topics": log.topics,
            "summary": log.content[:200] + "..." # 전문은 너무 기니 앞부분만 or 필요시 전체
        }
        for log in logs
    ]

@app.get("/")
def read_root():
    return {"message": "Reason Hunter Backend is Running"}


# ✅ [Manual Analysis] PDF 리포트 → Watcher 분석 파이프라인 트리거
class AnalyzeRequest(BaseModel):
    pdf_url: str
    source: str        # 증권사명 (예: 키움증권)
    title: str | None = None   # 생략 시 자동 생성
    report_date: str | None = None  # YYYY-MM-DD (생략 시 오늘)

DOWNLOAD_DIR = os.path.abspath("data/reports")

@app.post("/analyze")
async def analyze_report(req: AnalyzeRequest):
    """PDF URL을 받아 다운로드 후 Watcher 분석 파이프라인으로 전달"""
    try:
        os.makedirs(DOWNLOAD_DIR, exist_ok=True)

        resp = http_requests.get(
            req.pdf_url,
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=30,
        )
        if resp.status_code != 200:
            raise HTTPException(status_code=400, detail=f"PDF 다운로드 실패: HTTP {resp.status_code}")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        source_slug = req.source.replace(" ", "_").lower()
        saved_path = os.path.join(DOWNLOAD_DIR, f"{source_slug}_{timestamp}.pdf")

        with open(saved_path, "wb") as f:
            f.write(resp.content)

        date_str = req.report_date or datetime.now().strftime("%Y-%m-%d")
        title = req.title or f"{req.source} 리포트 ({date_str})"

        payload = {
            "type": "REPORT_ANALYSIS",
            "source": req.source,
            "title": title,
            "file_path": saved_path,
            "url": req.pdf_url,
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        await redis_client.publish(settings.REDIS_CHANNEL_STOCK, ujson.dumps(payload))

        logger.info(f"🚀 [Analyze] Published: {title} ({req.source})")
        return {"ok": True, "message": "분석 요청이 전송되었습니다.", "title": title}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ [Analyze] 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))
