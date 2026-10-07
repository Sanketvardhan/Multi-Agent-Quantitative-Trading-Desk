import os
import time
import logging
from datetime import datetime
from typing import List, Dict, Any

from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
from sqlalchemy.orm import sessionmaker, declarative_base

from core.config import (
    DATABASE_URL, 
    ATR_SL_MULTIPLIER, 
    ATR_TP_MULTIPLIER, 
    MIN_EXPECTED_PROFIT_INR,
    INITIAL_CAPITAL,
    MAX_ALLOCATION_PER_TRADE
)
from models.intraday_inference import get_live_intraday_prediction

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("AlphaEngine")

# --- DATABASE SETUP ---
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class LiveMarketOpportunity(Base):
    __tablename__ = "live_opportunities"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String, unique=True, index=True)
    direction = Column(String)            # 'LONG' or 'SHORT'
    expected_high_pct = Column(Float)
    expected_low_pct = Column(Float)
    uncertainty = Column(Float)
    current_price = Column(Float)
    atr = Column(Float)
    suggested_sl = Column(Float)
    suggested_tp = Column(Float)
    net_expectancy_inr = Column(Float)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# Ensure pristine table structure on initialization
try:
    Base.metadata.create_all(bind=engine)
except Exception:
    pass

DEFAULT_BASKET = [
    "RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK", 
    "HINDUNILVR", "SBIN", "BHARTIARTL", "ITC", "KOTAKBANK",
    "LT", "AXISBANK", "ASIANPAINT", "MARUTI", "SUNPHARMA",
    "TITAN", "BAJFINANCE", "ADANIENT", "WIPRO", "HCLTECH",
    "TATASTEEL", "POWERGRID", "NTPC", "ONGC"
]

def scan_market(basket: List[str] = None) -> List[Dict[str, Any]]:
    """
    Executes high-speed quantitative scans across the universe, applying
    ATR-based risk geometry and transaction friction gating.
    """
    target_basket = basket if basket else DEFAULT_BASKET
    logger.info(f"⚙️ Initiating Alpha Engine scan across {len(target_basket)} tickers...")
    
    results = []
    
    for ticker in target_basket:
        try:
            pred = get_live_intraday_prediction(ticker)
            if pred.get("status") != "success":
                continue
                
            price = pred["current_price"]
            atr = pred["current_atr"]
            exp_high = pred["expected_high"]
            exp_low = pred["expected_low"]
            uncertainty = pred["uncertainty"]
            
            if price <= 0 or atr <= 0:
                continue
                
            # Directional Determination based on asymmetric reward/risk
            direction = None
            if exp_high >= 0.0020 and exp_high > (abs(exp_low) * 1.3):
                direction = "LONG"
                sl_price = round(price - (atr * ATR_SL_MULTIPLIER), 2)
                tp_price = round(price + (atr * ATR_TP_MULTIPLIER), 2)
                expected_gain_per_share = tp_price - price
            elif abs(exp_low) >= 0.0020 and abs(exp_low) > (exp_high * 1.3):
                direction = "SHORT"
                sl_price = round(price + (atr * ATR_SL_MULTIPLIER), 2)
                tp_price = round(price - (atr * ATR_TP_MULTIPLIER), 2)
                expected_gain_per_share = price - tp_price
            else:
                continue
                
            # Friction & Expectancy Gate:
            alloc_capital = INITIAL_CAPITAL * MAX_ALLOCATION_PER_TRADE
            est_shares = max(1, int(alloc_capital / price))
            gross_expected_gain = round(expected_gain_per_share * est_shares, 2)
            
            # Require meaningful monetary gain relative to trade friction
            if gross_expected_gain < MIN_EXPECTED_PROFIT_INR:
                logger.debug(f"Skipping {ticker}: Expected gain ₹{gross_expected_gain} below minimum threshold ₹{MIN_EXPECTED_PROFIT_INR}")
                continue
                
            results.append({
                "ticker": ticker,
                "direction": direction,
                "expected_high_pct": exp_high,
                "expected_low_pct": exp_low,
                "uncertainty": uncertainty,
                "current_price": price,
                "atr": atr,
                "suggested_sl": sl_price,
                "suggested_tp": tp_price,
                "net_expectancy_inr": gross_expected_gain
            })
            
            logger.info(f"🎯 Setup: {ticker} [{direction}] Price: ₹{price} | ATR: ₹{atr} | SL: ₹{sl_price} | TP: ₹{tp_price} | Est Gain: ₹{gross_expected_gain}")
            
        except Exception as e:
            logger.error(f"Error scanning {ticker}: {e}")
            
        time.sleep(0.1)
        
    if not results:
        logger.warning("No valid asymmetric setups found in this cycle.")
        return []
        
    sorted_setups = sorted(results, key=lambda x: x["net_expectancy_inr"], reverse=True)[:5]
    
    # Overwrite database with the top fresh setups
    db = SessionLocal()
    try:
        db.query(LiveMarketOpportunity).delete()
        for s in sorted_setups:
            db.add(LiveMarketOpportunity(
                ticker=s["ticker"],
                direction=s["direction"],
                expected_high_pct=s["expected_high_pct"],
                expected_low_pct=s["expected_low_pct"],
                uncertainty=s["uncertainty"],
                current_price=s["current_price"],
                atr=s["atr"],
                suggested_sl=s["suggested_sl"],
                suggested_tp=s["suggested_tp"],
                net_expectancy_inr=s["net_expectancy_inr"]
            ))
        db.commit()
        logger.info(f"✅ Successfully persisted top {len(sorted_setups)} setups to database.")
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to persist opportunities: {e}")
    finally:
        db.close()
        
    return sorted_setups

if __name__ == "__main__":
    scan_market(["MARUTI", "ADANIENT", "INFY", "TCS", "RELIANCE"])