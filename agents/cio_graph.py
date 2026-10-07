import os
import sys
import json
import logging
from datetime import datetime
from typing import Dict, Any, List
from dotenv import load_dotenv

# Ensure root directory is in sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from sqlalchemy import create_engine, Column, Integer, String, JSON, DateTime, text
from sqlalchemy.orm import sessionmaker, declarative_base
from pydantic import BaseModel, Field

from core.config import DATABASE_URL
from core.data_engine import data_engine
from core.news_engine import news_engine

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("MacroCIO")

# --- DATABASE SETUP ---
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

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

# Auto-migrate new columns if missing
try:
    with engine.connect() as conn:
        conn.execute(text("ALTER TABLE daily_playbook ADD COLUMN IF NOT EXISTS top_headlines JSON;"))
        conn.execute(text("ALTER TABLE daily_playbook ADD COLUMN IF NOT EXISTS sector_sentiments JSON;"))
        conn.commit()
except Exception as e:
    logger.debug(f"DB column auto-migration note: {e}")

class DailyPlaybookSchema(BaseModel):
    market_regime: str = Field(description="'BULLISH', 'BEARISH', or 'CHOPPY'")
    risk_level: str = Field(description="'AGGRESSIVE', 'MODERATE', or 'DEFENSIVE'")
    approved_sectors: List[str] = Field(description="e.g., ['IT', 'Banking', 'Pharma']")
    banned_sectors: List[str] = Field(description="e.g., ['Energy', 'Metals']")
    reasoning: str = Field(description="Summary of macro regime, news drivers, and sector bias.")
    top_headlines: List[Dict[str, str]] = Field(default_factory=list)
    sector_sentiments: Dict[str, Any] = Field(default_factory=dict)

ALL_MONITORED_SECTORS = ["IT", "Banking", "Auto", "Metals", "Pharma", "Energy", "FMCG"]

def run_macro_cio_sweep(target_tickers: List[str] = None) -> DailyPlaybookSchema:
    """
    Executes Pre-Market Macro Analysis using:
    1. Quantitative Benchmarks (Nifty 50, India VIX)
    2. Real-Time Indian Market News Headlines
    3. Multi-Sector Sentiment Breadth (IT, Banking, Metals, Auto, Pharma, Energy, FMCG)
    """
    logger.info("🌅 [CIO Agent] Initiating Pre-Market Macro Strategy & News Sweep...")
    
    # 1. Fetch Macro Benchmarks
    vix_context = data_engine.calculate_technical_context("^INDIAVIX")
    vix_price = vix_context.get("current_price", 14.0)
    
    nifty_context = data_engine.calculate_technical_context("^NSEI")
    nifty_price = nifty_context.get("current_price", 24000.0)
    nifty_rsi = nifty_context.get("rsi_14", 50.0)
    
    # 2. Fetch Live Market News
    market_news = news_engine.fetch_market_news()
    market_headlines = market_news.get("headlines", [])
    market_sentiment = market_news.get("sentiment", {})
    
    # 3. Fetch Sector Sentiment Breadth
    sector_sentiments = {}
    approved_sectors = []
    banned_sectors = []
    
    for sector in ALL_MONITORED_SECTORS:
        sec_data = news_engine.fetch_sector_news(sector)
        sec_sentiment = sec_data.get("sentiment", {})
        sector_sentiments[sector] = {
            "score": sec_sentiment.get("score", 0.0),
            "label": sec_sentiment.get("label", "NEUTRAL"),
            "has_red_flag": sec_sentiment.get("has_red_flag", False),
            "top_headline": sec_data.get("headlines", [{}])[0].get("title", "") if sec_data.get("headlines") else ""
        }
        
        # Sector Classification Rules:
        if sec_sentiment.get("has_red_flag") or sec_sentiment.get("label") == "BEARISH":
            banned_sectors.append(sector)
        elif sec_sentiment.get("label") == "BULLISH":
            approved_sectors.append(sector)
        else:
            # Neutral sectors default to approved if market is not heavily bearish
            if nifty_rsi >= 45:
                approved_sectors.append(sector)
            else:
                banned_sectors.append(sector)

    # 4. Determine Global Market Regime & Risk Level
    if vix_price > 18.0 or market_sentiment.get("label") == "BEARISH":
        risk_level = "DEFENSIVE"
    elif vix_price < 13.0 and market_sentiment.get("label") == "BULLISH":
        risk_level = "AGGRESSIVE"
    else:
        risk_level = "MODERATE"
        
    if nifty_rsi > 58:
        market_regime = "BULLISH"
    elif nifty_rsi < 42:
        market_regime = "BEARISH"
    else:
        market_regime = "CHOPPY"
        
    # Safety fallback if empty
    if not approved_sectors:
        approved_sectors = ["IT", "Pharma", "FMCG"]
        
    headline_snippet = market_headlines[0]["title"] if market_headlines else "Market consolidating near key support levels."
    reasoning = (
        f"Nifty RSI @ {nifty_rsi:.1f} | India VIX @ {vix_price:.2f} ({risk_level} Risk). "
        f"Regime: {market_regime}. Leading Catalyst: '{headline_snippet}'. "
        f"Approved Sectors: {', '.join(approved_sectors)}. Banned Sectors: {', '.join(banned_sectors) if banned_sectors else 'None'}."
    )
    
    playbook = DailyPlaybookSchema(
        market_regime=market_regime,
        risk_level=risk_level,
        approved_sectors=approved_sectors,
        banned_sectors=banned_sectors,
        reasoning=reasoning,
        top_headlines=market_headlines,
        sector_sentiments=sector_sentiments
    )
    
    # 5. Persist to Unified Shared Database
    db = SessionLocal()
    try:
        db.query(DailyPlaybookDB).delete()
        db.add(DailyPlaybookDB(
            market_regime=playbook.market_regime,
            risk_level=playbook.risk_level,
            approved_sectors=playbook.approved_sectors,
            banned_sectors=playbook.banned_sectors,
            reasoning=playbook.reasoning,
            top_headlines=playbook.top_headlines,
            sector_sentiments=playbook.sector_sentiments
        ))
        db.commit()
        logger.info(f"✅ Macro Playbook persisted to Database. Regime: {market_regime} | Risk: {risk_level}")
        logger.info(f"📰 Top Catalyst: {headline_snippet}")
        logger.info(f"🟢 Approved Sectors: {', '.join(approved_sectors)}")
        if banned_sectors:
            logger.info(f"🔴 Banned Sectors: {', '.join(banned_sectors)}")
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to persist playbook: {e}")
    finally:
        db.close()
        
    return playbook

if __name__ == "__main__":
    pb = run_macro_cio_sweep()