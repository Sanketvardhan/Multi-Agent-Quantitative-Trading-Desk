import os
import time
from datetime import datetime
from dotenv import load_dotenv

# Database Imports
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
from sqlalchemy.orm import sessionmaker, declarative_base

# --- DIRECT IMPORT (NO LANGCHAIN TOOLS) ---
from models.intraday_inference import get_live_intraday_prediction

# --- Configuration & Database Setup ---
load_dotenv()
DB_PASSWORD = os.getenv('DB_PASSWORD', 'root')
# Pointing to the new MAS database
DATABASE_URL = f"postgresql://postgres:{DB_PASSWORD}@localhost:5432/converse_db"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class LiveMarketOpportunity(Base):
    __tablename__ = "live_opportunities"
    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String, unique=True, index=True)
    expected_return = Column(Float)
    uncertainty = Column(Float, default=0.0) # Intraday doesn't use this, but we keep schema consistent
    atr = Column(Float)
    current_price = Column(Float)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# Define your tracking universe
NIFTY_50 = [
    "RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK", 
    "HINDUNILVR", "SBIN", "BHARTIARTL", "ITC", "KOTAKBANK",
    "LT", "AXISBANK", "ASIANPAINT", "MARUTI", "SUNPHARMA",
    "TITAN", "BAJFINANCE", "ADANIENT", "WIPRO", "HCLTECH"
]

def scan_market():
    """Runs the 15m PyTorch model on the Nifty 50 and updates the Top 5 opportunities."""
    print(f"\n=========================================================")
    print(f"⚙️ ALPHA ENGINE: Initiating Intraday Market Sweep @ {datetime.now().strftime('%H:%M:%S')}")
    print(f"=========================================================")
    
    results = []
    
    # 1. Loop through all stocks and fetch 15m predictions on the fly
    for ticker in NIFTY_50:
        print(f" -> Calculating 15m order flow for {ticker}...")
        try:
            # Direct Python call to your PyTorch script
            pred = get_live_intraday_prediction(ticker)
            
            if pred.get("status") == "success":
                # We rank them by the absolute size of the expected move
                magnitude = abs(pred.get("expected_return", 0))
                
                results.append({
                    "ticker": ticker,
                    "expected_return": pred.get("expected_return"),
                    "atr": pred.get("current_atr", 0.0),       # Required for Copilot Stop Loss
                    "current_price": pred.get("current_price", 0.0), # Required for Copilot Entry
                    "magnitude": magnitude
                })
        except Exception as e:
            print(f"   ❌ Failed to process {ticker}: {e}")
            
        time.sleep(2) # Micro-delay to avoid TradingView blocks
        
    if not results:
        print("⚠️ No valid predictions generated in this cycle.")
        return

    # 2. Sort by highest magnitude (The biggest expected intraday moves)
    sorted_results = sorted(results, key=lambda x: x["magnitude"], reverse=True)
    top_5 = sorted_results[:5]
    
    print("\n🏆 TOP 5 15-MINUTE SETUPS FOUND:")
    for rank, setup in enumerate(top_5, 1):
        print(f"  {rank}. {setup['ticker']} | Expected 15m Move: {setup['expected_return']:.4f}")

    # 3. Update the Shared Memory Database
    db = SessionLocal()
    try:
        # Clear the old stale setups from 15 minutes ago
        db.query(LiveMarketOpportunity).delete()
        
        # Insert the fresh Top 5
        for setup in top_5:
            new_opp = LiveMarketOpportunity(
                ticker=setup["ticker"],
                expected_return=setup["expected_return"],
                uncertainty=0.0, # Intraday has no dropout
                atr=setup["atr"],
                current_price=setup["current_price"]
            )
            db.add(new_opp)
            
        db.commit()
        print("\n✅ Database `live_opportunities` successfully overwritten. Copilot can now read this.")
    except Exception as e:
        db.rollback()
        print(f"\n❌ Database error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    scan_market()