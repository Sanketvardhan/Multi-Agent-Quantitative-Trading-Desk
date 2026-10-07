import os
import logging
from datetime import datetime, timedelta
from typing import Optional, List

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean, JSON
from sqlalchemy.orm import declarative_base, sessionmaker

from core.config import DATABASE_URL, INITIAL_CAPITAL

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("API")

# --- UNIFIED DATABASE SETUP ---
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Trade(Base):
    __tablename__ = "trade_ledger"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String, index=True)
    action = Column(String) 
    entry_price = Column(Float)
    take_profit = Column(Float)
    stop_loss = Column(Float)
    sizing = Column(Integer)
    status = Column(String, default="PENDING") 
    
    live_price = Column(Float, nullable=True)
    peak_price = Column(Float, nullable=True)
    live_rsi = Column(Float, nullable=True)
    live_macd = Column(Float, nullable=True)
    current_pnl = Column(Float, nullable=True)
    risk_reasoning = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    activated_at = Column(DateTime, nullable=True)
    closed_at = Column(DateTime, nullable=True)

class AccountState(Base):
    __tablename__ = "account_state"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, index=True)
    current_capital = Column(Float, default=INITIAL_CAPITAL)
    auto_deploy = Column(Boolean, default=False)

class Cooldown(Base):
    __tablename__ = "cooldown_ledger"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String, unique=True, index=True)
    cooldown_until = Column(DateTime)
    reason = Column(String, nullable=True)

class DailyPlaybookDB(Base):
    __tablename__ = "daily_playbook"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, index=True)
    date = Column(DateTime, default=datetime.utcnow)
    market_regime = Column(String) 
    risk_level = Column(String)    
    approved_sectors = Column(JSON) 
    banned_sectors = Column(JSON)   
    reasoning = Column(String)
    top_headlines = Column(JSON, nullable=True)
    sector_sentiments = Column(JSON, nullable=True)

Base.metadata.create_all(bind=engine)

# --- FASTAPI APP INITIALIZATION ---
app = FastAPI(title="Autonomous Quantitative Trading Engine API")

# Enable CORS for React Frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- PYDANTIC SCHEMAS ---
class TradeCreate(BaseModel):
    ticker: str
    action: str
    entry_price: float
    take_profit: float
    stop_loss: float
    sizing: int
    reasoning: Optional[str] = None

class AutoDeployToggle(BaseModel):
    auto_deploy: bool

class CapitalUpdate(BaseModel):
    current_capital: float

class CooldownRequest(BaseModel):
    ticker: str
    minutes: int = 45

# ==========================================
# 1. TRADE PROPOSALS & LEDGER ENDPOINTS
# ==========================================
@app.post("/api/trades/propose")
def propose_trade(trade: TradeCreate):
    db = SessionLocal()
    try:
        # Prevent duplicates for currently active or pending tickers
        existing = db.query(Trade).filter(
            Trade.ticker == trade.ticker,
            Trade.status.in_(["PENDING", "ACTIVE"])
        ).first()
        
        if existing:
            return {"message": f"Trade for {trade.ticker} already exists in status {existing.status}."}

        account = db.query(AccountState).first()
        is_auto = account.auto_deploy if account else False

        db_trade = Trade(
            ticker=trade.ticker,
            action=trade.action,
            entry_price=trade.entry_price,
            take_profit=trade.take_profit,
            stop_loss=trade.stop_loss,
            sizing=trade.sizing,
            peak_price=trade.entry_price,
            risk_reasoning=trade.reasoning
        )

        if db_trade.sizing <= 0:
            db_trade.status = "IGNORED_LOW_FUNDS"
        elif is_auto:
            db_trade.status = "ACTIVE"
            db_trade.activated_at = datetime.utcnow()
        else:
            db_trade.status = "PENDING"

        db.add(db_trade)
        db.commit()
        db.refresh(db_trade)
        return {"message": "Trade processed", "trade_id": db_trade.id, "status": db_trade.status}
    finally:
        db.close()

@app.get("/api/trades/pending")
def get_pending_trades():
    db = SessionLocal()
    try:
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        return db.query(Trade).filter(
            Trade.status == "PENDING",
            Trade.created_at >= today_start
        ).all()
    finally:
        db.close()

@app.post("/api/trades/{trade_id}/approve")
def approve_trade(trade_id: int):
    db = SessionLocal()
    try:
        trade = db.query(Trade).filter(Trade.id == trade_id).first()
        if not trade:
            raise HTTPException(status_code=404, detail="Trade not found")
        trade.status = "ACTIVE"
        trade.activated_at = datetime.utcnow()
        trade.peak_price = trade.entry_price
        db.commit()
        return {"message": f"Trade {trade_id} activated successfully."}
    finally:
        db.close()

@app.post("/api/trades/{trade_id}/reject")
def reject_trade(trade_id: int):
    db = SessionLocal()
    try:
        trade = db.query(Trade).filter(Trade.id == trade_id).first()
        if not trade:
            raise HTTPException(status_code=404, detail="Trade not found")
        trade.status = "REJECTED"
        db.commit()
        return {"message": f"Trade {trade_id} rejected."}
    finally:
        db.close()

@app.get("/api/trades/active")
def get_active_trades():
    db = SessionLocal()
    try:
        trades = db.query(Trade).filter(Trade.status == "ACTIVE").all()
        enriched = []
        for t in trades:
            enriched.append({
                "id": t.id,
                "ticker": t.ticker,
                "action": t.action,
                "entry_price": t.entry_price,
                "take_profit": t.take_profit,
                "stop_loss": t.stop_loss,
                "sizing": t.sizing,
                "live_price": t.live_price or t.entry_price,
                "current_pnl": t.current_pnl or 0.0,
                "live_rsi": t.live_rsi or 50.0,
                "live_macd": t.live_macd or 0.0,
                "risk_reasoning": t.risk_reasoning or "Monitoring position...",
                "created_at": t.created_at,
                "activated_at": t.activated_at
            })
        return enriched
    finally:
        db.close()

@app.get("/api/trades/closed")
def get_closed_trades():
    db = SessionLocal()
    try:
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        return db.query(Trade).filter(
            Trade.status.like("CLOSED_%"),
            Trade.created_at >= today_start
        ).all()
    finally:
        db.close()

@app.post("/api/trades/{trade_id}/emergency_stop")
def emergency_stop_trade(trade_id: int):
    db = SessionLocal()
    try:
        trade = db.query(Trade).filter(Trade.id == trade_id, Trade.status == "ACTIVE").first()
        if not trade:
            raise HTTPException(status_code=404, detail="Trade not found or already closed")
            
        exit_price = trade.live_price or trade.entry_price
        if "SHORT" in trade.action:
            pnl_per_share = trade.entry_price - exit_price
        else:
            pnl_per_share = exit_price - trade.entry_price
            
        trade.status = "CLOSED_MANUAL"
        trade.current_pnl = round(pnl_per_share * trade.sizing, 2)
        trade.risk_reasoning = "MANUAL OVERRIDE: Position killed via dashboard."
        trade.closed_at = datetime.utcnow()
        db.commit()
        return {"message": f"Trade {trade_id} stopped manually."}
    finally:
        db.close()

# ==========================================
# 2. ACCOUNT & CAPITAL MANAGEMENT
# ==========================================
@app.get("/api/account/capital")
def get_capital():
    db = SessionLocal()
    try:
        state = db.query(AccountState).first()
        if not state:
            state = AccountState(current_capital=INITIAL_CAPITAL)
            db.add(state)
            db.commit()
            db.refresh(state)
        return {"current_capital": state.current_capital}
    finally:
        db.close()

@app.post("/api/account/capital")
def update_capital(data: CapitalUpdate):
    db = SessionLocal()
    try:
        state = db.query(AccountState).first()
        if not state:
            state = AccountState()
            db.add(state)
        state.current_capital = data.current_capital
        db.commit()
        return {"message": "Capital updated", "current_capital": state.current_capital}
    finally:
        db.close()

@app.get("/api/account/auto_deploy")
def get_auto_deploy():
    db = SessionLocal()
    try:
        state = db.query(AccountState).first()
        if not state:
            state = AccountState()
            db.add(state)
            db.commit()
            db.refresh(state)
        return {"auto_deploy": state.auto_deploy}
    finally:
        db.close()

@app.post("/api/account/auto_deploy")
def toggle_auto_deploy(data: AutoDeployToggle):
    db = SessionLocal()
    try:
        state = db.query(AccountState).first()
        if not state:
            state = AccountState()
            db.add(state)
        state.auto_deploy = data.auto_deploy
        db.commit()
        return {"message": "Auto-deploy updated", "auto_deploy": state.auto_deploy}
    finally:
        db.close()

# ==========================================
# 3. PENALTY BOX (COOLDOWN LEDGER)
# ==========================================
@app.post("/api/cooldown/add")
def add_cooldown(req: CooldownRequest):
    db = SessionLocal()
    try:
        release_time = datetime.utcnow() + timedelta(minutes=req.minutes)
        cd = db.query(Cooldown).filter(Cooldown.ticker == req.ticker).first()
        if cd:
            cd.cooldown_until = release_time
        else:
            cd = Cooldown(ticker=req.ticker, cooldown_until=release_time)
            db.add(cd)
        db.commit()
        return {"message": f"{req.ticker} in cooldown until {release_time}"}
    finally:
        db.close()

@app.get("/api/cooldown/check/{ticker}")
def check_cooldown(ticker: str):
    db = SessionLocal()
    try:
        cd = db.query(Cooldown).filter(Cooldown.ticker == ticker).first()
        if cd and cd.cooldown_until > datetime.utcnow():
            return {"in_cooldown": True, "release_time": cd.cooldown_until}
        return {"in_cooldown": False}
    finally:
        db.close()

@app.get("/api/cooldown/all")
def get_all_cooldowns():
    db = SessionLocal()
    try:
        now = datetime.utcnow()
        cds = db.query(Cooldown).filter(Cooldown.cooldown_until > now).all()
        return [{"ticker": c.ticker, "release_time": c.cooldown_until, "reason": c.reason} for c in cds]
    finally:
        db.close()

# ==========================================
# 4. MACRO CIO INTELLIGENCE & NEWS ENDPOINTS
# ==========================================
@app.get("/api/macro/playbook")
def get_macro_playbook():
    db = SessionLocal()
    try:
        playbook = db.query(DailyPlaybookDB).order_by(DailyPlaybookDB.id.desc()).first()
        if not playbook:
            return {
                "market_regime": "NEUTRAL",
                "risk_level": "MODERATE",
                "approved_sectors": ["IT", "Banking", "Auto"],
                "banned_sectors": [],
                "reasoning": "Pre-market sweep pending initialization.",
                "top_headlines": [],
                "sector_sentiments": {}
            }
        return {
            "id": playbook.id,
            "date": playbook.date,
            "market_regime": playbook.market_regime,
            "risk_level": playbook.risk_level,
            "approved_sectors": playbook.approved_sectors or [],
            "banned_sectors": playbook.banned_sectors or [],
            "reasoning": playbook.reasoning,
            "top_headlines": playbook.top_headlines or [],
            "sector_sentiments": playbook.sector_sentiments or {}
        }
    finally:
        db.close()

@app.get("/api/macro/news")
def get_live_news():
    try:
        from core.news_engine import news_engine
        return news_engine.fetch_market_news()
    except Exception as e:
        return {"headlines": [], "sentiment": {"score": 0.0, "label": "NEUTRAL"}, "error": str(e)}

@app.get("/api/health")
def health_check():
    return {"status": "online", "timestamp": datetime.utcnow()}