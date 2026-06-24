import os

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, cast, Date, Boolean
from sqlalchemy.orm import declarative_base, sessionmaker
from dotenv import load_dotenv
from datetime import datetime, time as datetime_time
from typing import Optional

# --- Load Environment & Database ---
load_dotenv()
DB_PASSWORD = os.getenv('DB_PASSWORD', 'root')
DATABASE_URL = f"postgresql://postgres:{DB_PASSWORD}@localhost:5432/nifty_intraday_db"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# # --- Database Schema (The Ledger) ---
# class Trade(Base):
#     __tablename__ = "trade_ledger"
    
#     id = Column(Integer, primary_key=True, index=True)
#     ticker = Column(String, index=True)
#     action = Column(String) # 'EXECUTE LONG' or 'EXECUTE SHORT'
#     entry_price = Column(Float)
#     take_profit = Column(Float)
#     stop_loss = Column(Float)
#     sizing = Column(Integer)
#     status = Column(String, default="PENDING") # PENDING, ACTIVE, REJECTED, CLOSED
#     created_at = Column(DateTime, default=datetime.utcnow)

class Trade(Base):
    __tablename__ = "trade_ledger"
    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String, index=True)
    action = Column(String) 
    entry_price = Column(Float)
    take_profit = Column(Float)
    stop_loss = Column(Float)
    sizing = Column(Integer)
    status = Column(String, default="PENDING") 
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # --- NEW LIVE METRICS ---
    live_price = Column(Float, nullable=True)
    live_rsi = Column(Float, nullable=True)
    live_macd = Column(Float, nullable=True)
    current_pnl = Column(Float, nullable=True)
    risk_reasoning = Column(String, nullable=True)
    activated_at = Column(DateTime, nullable=True)

    closed_at = Column(DateTime, nullable=True)

# Create the table in Postgres if it doesn't exist
Base.metadata.create_all(bind=engine)

# --- FastAPI App Setup ---
app = FastAPI(title="Vibe Trading Engine API")

# --- Pydantic Models for API Requests ---
class TradeCreate(BaseModel):
    ticker: str
    action: str
    entry_price: float
    take_profit: float
    stop_loss: float
    sizing: int

# ==========================================
# API ENDPOINTS
# ==========================================

# @app.post("/api/trades/propose")
# def propose_trade(trade: TradeCreate):
#     """Copilot uses this to submit a new trade proposal."""
#     db = SessionLocal()
    
#     existing_trade = db.query(Trade).filter(
#         Trade.ticker == trade.ticker, 
#         Trade.status.in_(["PENDING", "ACTIVE"])
#     ).first()
    
#     if existing_trade:
#         db.close()
#         return {"message": f"Trade for {trade.ticker} already exists. Ignored."}
    
#     db_trade = Trade(**trade.dict())
#     db.add(db_trade)
#     db.commit()
#     db.refresh(db_trade)
#     db.close()
    
#     return {"message": "Trade proposed successfully", "trade_id": db_trade.id}

@app.post("/api/trades/propose")
def propose_trade(trade: TradeCreate):
    """Copilot uses this to submit a new trade proposal."""
    db = SessionLocal()
    
    existing_trade = db.query(Trade).filter(
        Trade.ticker == trade.ticker, 
        Trade.status.in_(["PENDING", "ACTIVE"])
    ).first()
    
    if existing_trade:
        db.close()
        return {"message": f"Trade for {trade.ticker} already exists. Ignored."}
    
    # --- AUTO DEPLOY CHECK ---
    account_state = db.query(AccountState).first()
    is_auto = account_state.auto_deploy if account_state else False

    db_trade = Trade(**trade.dict())
    
    # If auto-deploy is on, instantly activate it and start the clock
    if is_auto:
        db_trade.status = "ACTIVE"
        db_trade.activated_at = datetime.utcnow()

    db.add(db_trade)
    db.commit()
    db.refresh(db_trade)
    db.close()
    
    return {"message": "Trade proposed successfully", "trade_id": db_trade.id}

# @app.get("/api/trades/pending")
# def get_pending_trades():
#     """React UI uses this to fetch trades waiting for human approval."""
#     db = SessionLocal()
#     trades = db.query(Trade).filter(Trade.status == "PENDING").all()
#     db.close()
#     return trades

@app.get("/api/trades/pending")
def get_pending_trades():
    """React UI uses this to fetch ONLY TODAY'S trades waiting for human approval."""
    db = SessionLocal()
    
    # Calculate the exact start of today in UTC (matching your Column's default)
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Filter for PENDING status AND created today
    trades = db.query(Trade).filter(
        Trade.status == "PENDING",
        Trade.created_at >= today_start
    ).all()
    
    db.close()
    return trades

# @app.get("/api/trades/active")
# def get_active_trades():
#     """React UI uses this to display live positions monitored by Risk Manager."""
#     db = SessionLocal()
#     trades = db.query(Trade).filter(Trade.status == "ACTIVE").all()
#     db.close()
    
#     # We enrich the DB fields to populate the advanced frontend UI details
#     enriched_trades = []
#     for t in trades:
#         enriched_trades.append({
#             "id": t.id,
#             "ticker": t.ticker,
#             "action": t.action,
#             "entry_price": t.entry_price,
#             "take_profit": t.take_profit,
#             "stop_loss": t.stop_loss,
#             "sizing": t.sizing,
#             "live_price": t.entry_price, # Handled natively inside risk_manager log cycles
#             "current_pnl": 0.0,          
#             "live_rsi": "Calculated",
#             "live_macd": "Active Scan",
#             "risk_reasoning": "Vibe Risk Engine actively tracking current structural market boundaries."
#         })
#     return enriched_trades

@app.get("/api/trades/active")
def get_active_trades():
    db = SessionLocal()
    trades = db.query(Trade).filter(Trade.status == "ACTIVE").all()
    db.close()
    
    enriched_trades = []
    for t in trades:
        enriched_trades.append({
            "id": t.id,
            "ticker": t.ticker,
            "action": t.action,
            "entry_price": t.entry_price,
            "take_profit": t.take_profit,
            "stop_loss": t.stop_loss,
            "sizing": t.sizing,
            # Pass the real data to React (fallback to entry price/defaults if Risk Manager hasn't scanned it yet)
            "live_price": t.live_price or t.entry_price, 
            "current_pnl": t.current_pnl or 0.0,          
            "live_rsi": t.live_rsi or "Scanning...",
            "live_macd": t.live_macd or "Scanning...",
            "risk_reasoning": t.risk_reasoning or "Awaiting first Risk Engine scan cycle...",
            "created_at": t.created_at,
            "activated_at": t.activated_at
        })
    return enriched_trades

# @app.post("/api/trades/{trade_id}/approve")
# def approve_trade(trade_id: int):
#     """React UI uses this when the human clicks 'YES'."""
#     db = SessionLocal()
#     trade = db.query(Trade).filter(Trade.id == trade_id).first()
#     if not trade:
#         raise HTTPException(status_code=404, detail="Trade not found")
        
#     trade.status = "ACTIVE"
#     db.commit()
#     db.close()
#     return {"message": f"Trade {trade_id} ACTIVE."}

@app.post("/api/trades/{trade_id}/approve")
def approve_trade(trade_id: int):
    """React UI uses this when the human clicks 'YES'."""
    db = SessionLocal()
    trade = db.query(Trade).filter(Trade.id == trade_id).first()
    if not trade:
        raise HTTPException(status_code=404, detail="Trade not found")
        
    trade.status = "ACTIVE"
    trade.activated_at = datetime.utcnow() # <-- START THE CLOCK HERE
    db.commit()
    db.close()
    return {"message": f"Trade {trade_id} ACTIVE."}

# @app.post("/api/trades/{trade_id}/reject")
# def reject_trade(trade_id: int):
#     """React UI uses this when the human clicks 'NO'."""
#     db = SessionLocal()
#     trade = db.query(Trade).filter(Trade.id == trade_id).first()
#     if not trade:
#         raise HTTPException(status_code=404, detail="Trade not found")
        
#     trade.status = "REJECTED"
#     db.commit()
#     db.close()
#     return {"message": f"Trade {trade_id} REJECTED."}

@app.post("/api/trades/{trade_id}/reject")
def reject_trade(trade_id: int):
    """React UI uses this when the human clicks 'NO'. Marks as REJECTED (Not Executed) for historical logs."""
    db = SessionLocal()
    trade = db.query(Trade).filter(Trade.id == trade_id).first()
    if not trade:
        raise HTTPException(status_code=404, detail="Trade not found")
        
    # Instead of deleting, we change state so it disappears from 'Pending' but stays in your database for future analytics
    trade.status = "REJECTED"
    db.commit()
    db.close()
    return {"message": f"Trade {trade_id} marked as REJECTED (Not Executed)."}

@app.get("/api/trades/closed")
def get_closed_trades():
    """React UI uses this to display trades finalized today."""
    db = SessionLocal()
    
    # Calculate the exact start of today in UTC to match your created_at columns
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Find any trade that starts with "CLOSED_" and was created today
    closed_trades = db.query(Trade).filter(
        Trade.status.like("CLOSED_%"),
        Trade.created_at >= today_start
    ).all()
    
    db.close()
    return closed_trades

@app.post("/api/trades/{trade_id}/emergency_stop")
def emergency_stop_trade(trade_id: int):
    """React UI uses this to manually kill an active trade."""
    db = SessionLocal()
    trade = db.query(Trade).filter(Trade.id == trade_id, Trade.status == "ACTIVE").first()
    
    if not trade:
        db.close()
        raise HTTPException(status_code=404, detail="Trade not found or already closed")
        
    # We use the last known live_price from the risk manager. If it hasn't been scanned yet, we fallback to entry.
    exit_price = trade.live_price or trade.entry_price
    
    # Calculate final locked P&L
    if "SHORT" in trade.action:
        pnl_per_share = trade.entry_price - exit_price
    else:
        pnl_per_share = exit_price - trade.entry_price
        
    final_pnl = round(pnl_per_share * trade.sizing, 2)
    
    trade.status = "CLOSED_MANUAL"
    trade.current_pnl = final_pnl
    trade.risk_reasoning = "MANUAL OVERRIDE: Position killed via dashboard."
    trade.closed_at = datetime.utcnow()
    
    db.commit()
    db.close()
    return {"message": f"Trade {trade_id} stopped manually."}

# 1. Add this new table schema below your Trade class
# class AccountState(Base):
#     __tablename__ = "account_state"
#     id = Column(Integer, primary_key=True, index=True)
#     current_capital = Column(Float, default=100000.0)

class AccountState(Base):
    __tablename__ = "account_state"
    id = Column(Integer, primary_key=True, index=True)
    current_capital = Column(Float, default=100000.0)
    auto_deploy = Column(Boolean, default=False)

# Create tables if they don't exist
Base.metadata.create_all(bind=engine)

# 2. Add these two endpoints to handle capital sync
@app.get("/api/account/capital")
def get_capital():
    db = SessionLocal()
    state = db.query(AccountState).first()
    if not state:
        # Initialize default if empty
        state = AccountState(current_capital=100000.0)
        db.add(state)
        db.commit()
        db.refresh(state)
    capital = state.current_capital
    db.close()
    return {"current_capital": capital}

class AutoDeployToggle(BaseModel):
    auto_deploy: bool

@app.get("/api/account/auto_deploy")
def get_auto_deploy():
    db = SessionLocal()
    state = db.query(AccountState).first()
    if not state:
        state = AccountState()
        db.add(state)
        db.commit()
        db.refresh(state)
    status = state.auto_deploy
    db.close()
    return {"auto_deploy": status}

@app.post("/api/account/auto_deploy")
def toggle_auto_deploy(data: AutoDeployToggle):
    db = SessionLocal()
    state = db.query(AccountState).first()
    if not state:
        state = AccountState()
        db.add(state)
    state.auto_deploy = data.auto_deploy
    db.commit()
    db.close()
    return {"message": "Auto-deploy updated", "auto_deploy": state.auto_deploy}

@app.post("/api/account/capital")
def update_capital(data: dict):
    db = SessionLocal()
    state = db.query(AccountState).first()
    if not state:
        state = AccountState()
        db.add(state)
    state.current_capital = float(data.get("current_capital", 100000.0))
    db.commit()
    db.close()
    return {"message": "Capital updated successfully", "current_capital": state.current_capital}