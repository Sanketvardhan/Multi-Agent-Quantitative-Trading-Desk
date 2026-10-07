import os
import sys
import json
import logging
import requests
import pytz
from datetime import datetime, timedelta
from typing import Dict, Any, List

# Ensure root directory is in sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, JSON
from sqlalchemy.orm import sessionmaker, declarative_base

from core.config import (
    DATABASE_URL,
    RISK_PER_TRADE,
    MAX_ALLOCATION_PER_TRADE,
    INITIAL_CAPITAL,
    MAX_OPEN_POSITIONS,
    MAX_DAILY_TRADES,
    MAX_LOSSES_PER_TICKER_DAILY,
    MAX_TRADES_PER_TICKER_DAILY
)
from core.data_engine import data_engine
from core.news_engine import news_engine

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("TacticalCopilot")

# --- DATABASE SETUP ---
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class LiveMarketOpportunity(Base):
    __tablename__ = "live_opportunities"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String, unique=True, index=True)
    direction = Column(String)
    expected_high_pct = Column(Float)
    expected_low_pct = Column(Float)
    uncertainty = Column(Float)
    current_price = Column(Float)
    atr = Column(Float)
    suggested_sl = Column(Float)
    suggested_tp = Column(Float)
    net_expectancy_inr = Column(Float)
    updated_at = Column(DateTime)

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

class TradeLedgerDB(Base):
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
    current_pnl = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    closed_at = Column(DateTime, nullable=True)

# Ticker to Sector Lookup Map
TICKER_SECTOR_MAP = {
    "INFY": "IT", "TCS": "IT", "WIPRO": "IT", "TECHM": "IT", "HCLTECH": "IT",
    "HDFCBANK": "Banking", "ICICIBANK": "Banking", "SBIN": "Banking", "AXISBANK": "Banking", "KOTAKBANK": "Banking", "BAJFINANCE": "Banking",
    "MARUTI": "Auto", "TATAMOTORS": "Auto", "M&M": "Auto", "HEROMOTOCO": "Auto", "BAJAJ-AUTO": "Auto",
    "TATASTEEL": "Metals", "JSWSTEEL": "Metals", "HINDALCO": "Metals", "COALINDIA": "Metals", "ADANIENT": "Metals",
    "SUNPHARMA": "Pharma", "DRREDDY": "Pharma", "CIPLA": "Pharma", "DIVISLAB": "Pharma",
    "RELIANCE": "Energy", "ONGC": "Energy", "BPCL": "Energy", "IOC": "Energy", "POWERGRID": "Energy", "NTPC": "Energy",
    "ITC": "FMCG", "HINDUNILVR": "FMCG", "NESTLEIND": "FMCG", "BRITANNIA": "FMCG", "ASIANPAINT": "FMCG", "TITAN": "FMCG"
}

class TacticalCopilotEngine:
    """
    Deterministic Quantitative Execution Copilot with:
    - Tier 2 Breaking News & Red-Flag Catalyst Gating
    - Sector Banning & Macro Alignment
    - Portfolio Pacing (Max Concurrent Positions & Max Daily Trades)
    - 2-Strikes Daily Ticker Lock
    """
    def __init__(self, api_base_url: str = "http://127.0.0.1:8000"):
        self.api_url = api_base_url
        self.db = SessionLocal()
        self.ist = pytz.timezone('Asia/Kolkata')

    def get_live_nifty_regime(self) -> str:
        """Determines market trend based on live NIFTY 50 index movement relative to today's open."""
        price = data_engine.get_realtime_price("^NSEI")
        bars = data_engine.fetch_historical_bars("^NSEI", interval="15m", period="2d")
        
        if not bars.empty:
            today_date = bars['date_time'].dt.date.iloc[-1]
            today_bars = bars[bars['date_time'].dt.date == today_date]
            today_open = float(today_bars['open'].iloc[0]) if not today_bars.empty else float(bars['open'].iloc[-1])
            
            latest_price = price or float(bars['close'].iloc[-1])
            pct_change = ((latest_price - today_open) / today_open) * 100
            
            if pct_change > 0.25:
                return "BULLISH"
            elif pct_change < -0.25:
                return "BEARISH"
            else:
                return "CHOPPY"
        return "NEUTRAL"

    def is_in_cooldown(self, ticker: str) -> bool:
        """Checks API to see if stock is in the penalty box."""
        try:
            res = requests.get(f"{self.api_url}/api/cooldown/check/{ticker}", timeout=2)
            if res.status_code == 200:
                return res.json().get("in_cooldown", False)
        except Exception:
            pass
        return False

    def get_account_capital(self) -> float:
        """Fetches live capital from API."""
        try:
            res = requests.get(f"{self.api_url}/api/account/capital", timeout=2)
            if res.status_code == 200:
                return float(res.json().get("current_capital", INITIAL_CAPITAL))
        except Exception:
            pass
        return INITIAL_CAPITAL

    def get_today_stats(self) -> Dict[str, Any]:
        """Calculates today's trade count, active count, realized PnL, and per-ticker metrics."""
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        
        today_trades = self.db.query(TradeLedgerDB).filter(TradeLedgerDB.created_at >= today_start).all()
        total_trades_today = len(today_trades)
        
        active_positions = [t for t in today_trades if t.status in ("ACTIVE", "PENDING")]
        active_count = len(active_positions)
        
        closed_trades = [t for t in today_trades if t.status.startswith("CLOSED_")]
        realized_pnl = sum(t.current_pnl or 0.0 for t in closed_trades)
        
        ticker_losses = {}
        ticker_trades_count = {}
        
        for t in closed_trades:
            ticker_trades_count[t.ticker] = ticker_trades_count.get(t.ticker, 0) + 1
            # Count as loss strike if status is CLOSED_CUT_LOSS or PnL is negative
            is_negative = (t.current_pnl is not None and t.current_pnl < 0) or t.status == "CLOSED_CUT_LOSS"
            if is_negative:
                ticker_losses[t.ticker] = ticker_losses.get(t.ticker, 0) + 1
                
        active_tickers = {t.ticker for t in active_positions}
                
        return {
            "total_trades_today": total_trades_today,
            "active_count": active_count,
            "realized_pnl": realized_pnl,
            "ticker_losses": ticker_losses,
            "ticker_trades_count": ticker_trades_count,
            "active_tickers": active_tickers
        }

    def execute_evaluation_cycle(self) -> List[Dict[str, Any]]:
        logger.info("⚡ Tactical Copilot evaluating fresh setups with Breaking News Guard...")
        
        now_ist = datetime.now(self.ist)
        stats = self.get_today_stats()
        
        # -------------------------------------------------------------
        # SAFEGUARD 0: OPENING BELL BLACKOUT (09:15 - 09:30 AM IST)
        # Prevents getting swept by opening candle spread & whipsaw volatility
        # -------------------------------------------------------------
        if now_ist.hour == 9 and now_ist.minute < 30:
            logger.info("⏸️ Opening Bell Blackout (09:15-09:30 IST): Awaiting morning price discovery & opening range settlement.")
            return []

        # -------------------------------------------------------------
        # SAFEGUARD 1: MAX DAILY TRADES LIMIT (Default: 6 trades/day)
        # -------------------------------------------------------------
        if stats["total_trades_today"] >= MAX_DAILY_TRADES:
            logger.info(f"🛑 Daily Trade Quota Reached: {stats['total_trades_today']}/{MAX_DAILY_TRADES} trades taken today. Quality filter active.")
            return []

        # -------------------------------------------------------------
        # SAFEGUARD 2: MAX CONCURRENT OPEN POSITIONS (Default: 3 active)
        # -------------------------------------------------------------
        available_slots = MAX_OPEN_POSITIONS - stats["active_count"]
        if available_slots <= 0:
            logger.info(f"⏸️ Portfolio Full: {stats['active_count']}/{MAX_OPEN_POSITIONS} active positions. Waiting for exits.")
            return []

        # 1. Load Macro Context & Regime
        playbook = self.db.query(DailyPlaybookDB).order_by(DailyPlaybookDB.id.desc()).first()
        banned_sectors = [s.upper() for s in (playbook.banned_sectors or [])] if playbook else []
        
        live_regime = self.get_live_nifty_regime()
        total_capital = self.get_account_capital()
        
        logger.info(f"📊 Market Regime: {live_regime} | Active Positions: {stats['active_count']}/{MAX_OPEN_POSITIONS} | Today's PnL: ₹{stats['realized_pnl']:.2f}")
        
        # 2. Query Setups from Alpha Engine (Sorted by Net Expectancy)
        opportunities = self.db.query(LiveMarketOpportunity).order_by(LiveMarketOpportunity.net_expectancy_inr.desc()).all()
        if not opportunities:
            logger.info("No active opportunities in database.")
            return []
            
        proposals = []
        max_risk_amount = total_capital * RISK_PER_TRADE
        max_capital_per_trade = total_capital * MAX_ALLOCATION_PER_TRADE
        
        is_late_session = (now_ist.hour == 13 and now_ist.minute >= 30) or (now_ist.hour >= 14)
        
        for opp in opportunities:
            if len(proposals) >= available_slots:
                break
                
            ticker = opp.ticker
            direction = opp.direction
            sector = TICKER_SECTOR_MAP.get(ticker, "General")
            
            # Check A: Already holding active position
            if ticker in stats["active_tickers"]:
                continue
                
            # Check B1: 2-Strikes Daily Ticker Loss Lock (Any 2 loss-exits lock the stock)
            if stats["ticker_losses"].get(ticker, 0) >= MAX_LOSSES_PER_TICKER_DAILY:
                logger.info(f"🛑 Skipping {ticker}: Hit {MAX_LOSSES_PER_TICKER_DAILY} loss strikes today. Locked for the session.")
                continue

            # Check B2: Max Daily Trades Per Stock (Max 2 total attempts per stock)
            if stats["ticker_trades_count"].get(ticker, 0) >= MAX_TRADES_PER_TICKER_DAILY:
                logger.info(f"🛑 Skipping {ticker}: Maximum daily trade quota ({MAX_TRADES_PER_TICKER_DAILY} trades) reached for this ticker today.")
                continue

            # Check C: Cooldown Penalty Box
            if self.is_in_cooldown(ticker):
                logger.info(f"🛑 Skipping {ticker}: In active Cooldown penalty box.")
                continue
                
            # Check D: Macro Banned Sector Check
            if sector.upper() in banned_sectors:
                logger.info(f"🛑 Skipping {ticker}: Sector '{sector}' is BANNED by Macro CIO Playbook.")
                continue

            # -------------------------------------------------------------
            # TIER 2 NEWS CHECK: Breaking Intraday Red-Flag Catalyst Guard
            # -------------------------------------------------------------
            ticker_news = news_engine.fetch_ticker_news(ticker)
            headlines = ticker_news.get("headlines", [])
            top_headline = headlines[0]["title"] if headlines else ""
            
            if direction == "LONG" and ticker_news.get("has_breaking_negative"):
                logger.info(f"🛑 VETO {ticker} [LONG]: Breaking negative catalyst detected ('{top_headline}').")
                continue
            elif direction == "SHORT" and ticker_news.get("has_breaking_positive"):
                logger.info(f"🛑 VETO {ticker} [SHORT]: Breaking positive catalyst detected ('{top_headline}').")
                continue

            # Check E: Late-Session Counter-Trend Ban (after 01:30 PM)
            is_counter_trend = (live_regime == "BEARISH" and direction == "LONG") or \
                               (live_regime == "BULLISH" and direction == "SHORT")
                               
            if is_late_session and is_counter_trend:
                logger.info(f"⏸️ Skipping {ticker} [{direction}]: Counter-trend strictly prohibited in late session ({now_ist.strftime('%I:%M %p')}) against {live_regime} Nifty.")
                continue
                
            # Check F: Regime Alignment & Sizing Scale
            sizing_scale = 1.0
            if is_counter_trend:
                magnitude = opp.expected_high_pct if direction == "LONG" else abs(opp.expected_low_pct)
                if magnitude >= 0.0035:
                    sizing_scale = 0.50
                    logger.info(f"⚡ {ticker} [{direction}]: Strong alpha breakout ({magnitude*100:.2f}%). Allocating 50% defensive size.")
                else:
                    logger.info(f"⏸️ Skipping {ticker} [{direction}]: Weak counter-trend in {live_regime} Nifty regime.")
                    continue
            elif live_regime == "CHOPPY":
                sizing_scale = 0.75
                
            # Check G: Volatility-Adjusted Sizing Math
            price = opp.current_price
            sl_price = opp.suggested_sl
            tp_price = opp.suggested_tp
            
            risk_per_share = abs(price - sl_price)
            if risk_per_share <= 0 or price <= 0:
                continue
                
            base_risk_shares = int(max_risk_amount / risk_per_share)
            base_capital_shares = int(max_capital_per_trade / price)
            raw_shares = min(base_risk_shares, base_capital_shares)
            
            # High-Beta ATR Volatility Dampener (protects against large swings in volatile stocks like ADANIENT)
            if opp.atr and price > 0 and (opp.atr / price) > 0.009:
                volatility_discount = max(0.60, 1.0 - ((opp.atr / price - 0.009) * 25))
                sizing_scale = sizing_scale * volatility_discount
                
            final_shares = max(1, int(raw_shares * sizing_scale))
            
            action_label = f"EXECUTE {direction}"
            reason_str = f"Quant {direction} ({sizing_scale*100:.0f}% size) in {live_regime} market. Sector: {sector}."
            if top_headline:
                reason_str += f" News cue: '{top_headline}'."
                
            proposal = {
                "ticker": ticker,
                "action": action_label,
                "entry_price": price,
                "stop_loss": sl_price,
                "take_profit": tp_price,
                "sizing": final_shares,
                "reasoning": reason_str
            }
            
            # Route to API
            try:
                res = requests.post(f"{self.api_url}/api/trades/propose", json=proposal, timeout=3)
                if res.status_code == 200:
                    logger.info(f"🚀 Dispatched {ticker} {action_label} ({final_shares} shares) to Trade Ledger.")
                    proposals.append(proposal)
                    stats["active_tickers"].add(ticker)
                else:
                    logger.warning(f"API proposal notice for {ticker}: {res.text}")
            except Exception as e:
                logger.info(f"Proposal generated for {ticker} ({final_shares} shares). (API notice: {e})")
                proposals.append(proposal)
                stats["active_tickers"].add(ticker)
                
        return proposals

    def close(self):
        self.db.close()

# Exportable runner
def run_copilot():
    copilot = TacticalCopilotEngine()
    try:
        return copilot.execute_evaluation_cycle()
    finally:
        copilot.close()

if __name__ == "__main__":
    run_copilot()