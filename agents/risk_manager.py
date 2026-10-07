import os
import sys
import time
import logging
import pytz
import requests
from datetime import datetime
from typing import Dict, Any, List

# Ensure root directory is in sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
from sqlalchemy.orm import sessionmaker, declarative_base

from core.config import (
    DATABASE_URL,
    TRAILING_ATR_MULTIPLIER,
    COOLDOWN_MINUTES
)
from core.data_engine import data_engine

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("RiskGuardian")

# --- DATABASE SETUP ---
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
    status = Column(String, default="PENDING") # PENDING, ACTIVE, CLOSED_*, REJECTED
    
    live_price = Column(Float, nullable=True)
    peak_price = Column(Float, nullable=True)
    live_rsi = Column(Float, nullable=True)
    live_macd = Column(Float, nullable=True)
    current_pnl = Column(Float, nullable=True)
    risk_reasoning = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    activated_at = Column(DateTime, nullable=True)
    closed_at = Column(DateTime, nullable=True)

Base.metadata.create_all(bind=engine)

class RiskManagerAgent:
    """
    Guardian Risk Engine (Pure Dynamic Trailing Runner Mode).
    1. Removes static take-profit ceiling — lets winning trends run until reversal.
    2. Dynamic Chandelier ATR Trailing Stop ratchets stop-loss as profit grows.
    3. Breakeven / Profit-Floor lock once price moves > 0.8x ATR in favorable direction.
    4. Mandatory 15:15 IST EOD Auto-Squareoff so no intraday positions are held overnight.
    """
    def __init__(self, api_base_url: str = "http://127.0.0.1:8000"):
        self.db = SessionLocal()
        self.api_url = api_base_url
        self.ist = pytz.timezone('Asia/Kolkata')

    def _apply_cooldown(self, ticker: str):
        """Sends stopped-out ticker to the Penalty Box."""
        try:
            requests.post(
                f"{self.api_url}/api/cooldown/add", 
                json={"ticker": ticker, "minutes": COOLDOWN_MINUTES},
                timeout=2
            )
            logger.info(f"⏱️ Placed {ticker} into {COOLDOWN_MINUTES}-min Cooldown penalty box.")
        except Exception as e:
            logger.debug(f"Failed to post cooldown for {ticker}: {e}")

    def manage_active_positions(self):
        active_trades = self.db.query(Trade).filter(Trade.status == "ACTIVE").all()
        if not active_trades:
            return

        now_ist = datetime.now(self.ist)
        is_eod_squareoff = (now_ist.hour == 15 and now_ist.minute >= 15) or (now_ist.hour > 15)

        for trade in active_trades:
            ticker = trade.ticker
            context = data_engine.calculate_technical_context(ticker)
            live_price = context.get("current_price") or trade.entry_price
            atr = context.get("atr") or (live_price * 0.015)
            
            # Calculate Unrealized P&L
            if "SHORT" in trade.action:
                pnl_per_share = trade.entry_price - live_price
            else:
                pnl_per_share = live_price - trade.entry_price
                
            gross_pnl = round(pnl_per_share * trade.sizing, 2)
            trade.live_price = live_price
            trade.live_rsi = context.get("rsi_14")
            trade.live_macd = context.get("macd_hist")
            trade.current_pnl = gross_pnl
            
            # Minutes held calculation
            minutes_held = 0
            if trade.activated_at:
                minutes_held = int((datetime.utcnow() - trade.activated_at).total_seconds() / 60)

            # -------------------------------------------------------------
            # RULE 1: MANDATORY END-OF-DAY SQUARE-OFF (15:15 IST)
            # -------------------------------------------------------------
            if is_eod_squareoff:
                trade.status = "CLOSED_EOD_SQUAREOFF"
                trade.closed_at = datetime.utcnow()
                trade.risk_reasoning = "EOD Auto-Squareoff: Flattening position before 15:30 market close."
                self.db.commit()
                logger.info(f"🛑 [EOD EXIT] {ticker} closed at ₹{live_price}. Final PnL: ₹{gross_pnl}")
                continue

            # -------------------------------------------------------------
            # RULE 2: STOP LOSS / TRAILING PROFIT STOP BREACHES
            # (No static Take-Profit ceiling — we let winners run!)
            # -------------------------------------------------------------
            is_long_stop = (trade.action == "EXECUTE LONG" and live_price <= trade.stop_loss)
            is_short_stop = (trade.action == "EXECUTE SHORT" and live_price >= trade.stop_loss)

            if is_long_stop or is_short_stop:
                # Distinguish between trailing stop profit lock vs true loss
                is_profit_lock = (trade.action == "EXECUTE LONG" and trade.stop_loss > trade.entry_price) or \
                                 (trade.action == "EXECUTE SHORT" and trade.stop_loss < trade.entry_price)
                
                trade.status = "CLOSED_TRAILING_STOP" if is_profit_lock else "CLOSED_CUT_LOSS"
                trade.closed_at = datetime.utcnow()
                trade.risk_reasoning = f"Price breached stop level (₹{trade.stop_loss})."
                self.db.commit()
                
                logger.info(f"💥 [{'TRAILING PROFIT' if is_profit_lock else 'CUT LOSS'}] {ticker} closed @ ₹{live_price}. PnL: ₹{gross_pnl}")
                if not is_profit_lock:
                    self._apply_cooldown(ticker)
                continue

            # -------------------------------------------------------------
            # RULE 3: DYNAMIC CHANDELIER ATR TRAILING STOP & BREAKEVEN LOCK
            # -------------------------------------------------------------
            if trade.action == "EXECUTE LONG":
                if trade.peak_price is None or live_price > trade.peak_price:
                    trade.peak_price = live_price
                    
                # Standard Chandelier Trail: 1.2x ATR below peak
                new_trail_sl = round(trade.peak_price - (atr * TRAILING_ATR_MULTIPLIER), 2)
                
                # Breakeven+ floor lock once stock gains >= 0.8x ATR
                if trade.peak_price >= (trade.entry_price + (atr * 0.8)):
                    breakeven_sl = round(trade.entry_price + (atr * 0.15), 2)
                    new_trail_sl = max(new_trail_sl, breakeven_sl)

                if new_trail_sl > trade.stop_loss:
                    old_sl = trade.stop_loss
                    trade.stop_loss = new_trail_sl
                    trade.risk_reasoning = f"Chandelier ATR Trail: SL ratcheted to ₹{new_trail_sl} (Peak: ₹{trade.peak_price})."
                    logger.info(f"📈 [TRAIL SL] {ticker}: SL raised ₹{old_sl} ➔ ₹{new_trail_sl} (Peak ₹{trade.peak_price})")

            elif trade.action == "EXECUTE SHORT":
                if trade.peak_price is None or live_price < trade.peak_price:
                    trade.peak_price = live_price
                    
                new_trail_sl = round(trade.peak_price + (atr * TRAILING_ATR_MULTIPLIER), 2)
                
                if trade.peak_price <= (trade.entry_price - (atr * 0.8)):
                    breakeven_sl = round(trade.entry_price - (atr * 0.15), 2)
                    new_trail_sl = min(new_trail_sl, breakeven_sl)

                if new_trail_sl < trade.stop_loss:
                    old_sl = trade.stop_loss
                    trade.stop_loss = new_trail_sl
                    trade.risk_reasoning = f"Chandelier ATR Trail: SL ratcheted down to ₹{new_trail_sl} (Trough: ₹{trade.peak_price})."
                    logger.info(f"📉 [TRAIL SL] {ticker}: SL lowered ₹{old_sl} ➔ ₹{new_trail_sl} (Trough ₹{trade.peak_price})")

            # -------------------------------------------------------------
            # RULE 4: CONSOLIDATION TIME DECAY KILL SWITCH (>90 mins)
            # -------------------------------------------------------------
            if minutes_held >= 90 and abs(gross_pnl) < 10.0:
                trade.status = "CLOSED_TIME_DECAY"
                trade.closed_at = datetime.utcnow()
                trade.risk_reasoning = f"Time Decay: Position stagnant for {minutes_held} minutes. Capital freed."
                self.db.commit()
                logger.info(f"⏳ [TIME DECAY EXIT] {ticker} closed after {minutes_held} mins.")
                continue

        self.db.commit()

    def close(self):
        self.db.close()

if __name__ == "__main__":
    rm = RiskManagerAgent()
    try:
        rm.manage_active_positions()
    finally:
        rm.close()