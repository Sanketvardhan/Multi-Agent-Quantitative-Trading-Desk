# import os
# import time
# from datetime import datetime
# from dotenv import load_dotenv

# # Database Imports
# from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
# from sqlalchemy.orm import sessionmaker, declarative_base

# # --- DIRECT IMPORT (NO LANGCHAIN TOOLS) ---
# from models.intraday_inference import get_live_intraday_prediction

# # --- Configuration & Database Setup ---
# load_dotenv()
# DB_PASSWORD = os.getenv('DB_PASSWORD', 'root')
# # Pointing to the new MAS database
# DATABASE_URL = f"postgresql://postgres:{DB_PASSWORD}@localhost:5432/converse_db"

# engine = create_engine(DATABASE_URL)
# SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
# Base = declarative_base()

# class LiveMarketOpportunity(Base):
#     __tablename__ = "live_opportunities"
#     id = Column(Integer, primary_key=True, index=True)
#     ticker = Column(String, unique=True, index=True)
#     expected_return = Column(Float)
#     uncertainty = Column(Float, default=0.0) # Intraday doesn't use this, but we keep schema consistent
#     atr = Column(Float)
#     current_price = Column(Float)
#     updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# # Define your tracking universe
# NIFTY_50 = [
#     "RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK", 
#     "HINDUNILVR", "SBIN", "BHARTIARTL", "ITC", "KOTAKBANK",
#     "LT", "AXISBANK", "ASIANPAINT", "MARUTI", "SUNPHARMA",
#     "TITAN", "BAJFINANCE", "ADANIENT", "WIPRO", "HCLTECH"
# ]

# def scan_market():
#     """Runs the 15m PyTorch model on the Nifty 50 and updates the Top 5 opportunities."""
#     print(f"\n=========================================================")
#     print(f"⚙️ ALPHA ENGINE: Initiating Intraday Market Sweep @ {datetime.now().strftime('%H:%M:%S')}")
#     print(f"=========================================================")
    
#     results = []
    
#     # 1. Loop through all stocks and fetch 15m predictions on the fly
#     for ticker in NIFTY_50:
#         print(f" -> Calculating 15m order flow for {ticker}...")
#         try:
#             # Direct Python call to your PyTorch script
#             pred = get_live_intraday_prediction(ticker)
            
#             if pred.get("status") == "success":
#                 # We rank them by the absolute size of the expected move
#                 magnitude = abs(pred.get("expected_return", 0))
                
#                 # Dynamic Friction Filter (e.g., Minimum 0.35% expected move required)
#                 if magnitude < 0.0035:
#                     print(f"   ⚠️ {ticker} expected move ({magnitude:.4f}) too small. Skipping.")
#                     continue

#                 results.append({
#                     "ticker": ticker,
#                     "expected_return": pred.get("expected_return"),
#                     "atr": pred.get("current_atr", 0.0),       # Required for Copilot Stop Loss
#                     "current_price": pred.get("current_price", 0.0), # Required for Copilot Entry
#                     "magnitude": magnitude
#                 })
#         except Exception as e:
#             print(f"   ❌ Failed to process {ticker}: {e}")
            
#         time.sleep(2) # Micro-delay to avoid TradingView blocks
        
#     if not results:
#         print("⚠️ No valid predictions generated in this cycle.")
#         return

#     # 2. Sort by highest magnitude (The biggest expected intraday moves)
#     sorted_results = sorted(results, key=lambda x: x["magnitude"], reverse=True)
#     top_5 = sorted_results[:5]
    
#     print("\n🏆 TOP 5 15-MINUTE SETUPS FOUND:")
#     for rank, setup in enumerate(top_5, 1):
#         print(f"  {rank}. {setup['ticker']} | Expected 15m Move: {setup['expected_return']:.4f}")

#     # 3. Update the Shared Memory Database
#     db = SessionLocal()
#     try:
#         # Clear the old stale setups from 15 minutes ago
#         db.query(LiveMarketOpportunity).delete()
        
#         # Insert the fresh Top 5
#         for setup in top_5:
#             new_opp = LiveMarketOpportunity(
#                 ticker=setup["ticker"],
#                 expected_return=setup["expected_return"],
#                 uncertainty=0.0, # Intraday has no dropout
#                 atr=setup["atr"],
#                 current_price=setup["current_price"]
#             )
#             db.add(new_opp)
            
#         db.commit()
#         print("\n✅ Database `live_opportunities` successfully overwritten. Copilot can now read this.")
#     except Exception as e:
#         db.rollback()
#         print(f"\n❌ Database error: {e}")
#     finally:
#         db.close()

# if __name__ == "__main__":
#     scan_market()


import os
from dotenv import load_dotenv
load_dotenv()
import time
from datetime import datetime
from dotenv import load_dotenv

# Database Imports
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
from sqlalchemy.orm import sessionmaker, declarative_base

# --- DIRECT IMPORT (Must update this file next!) ---
from models.intraday_inference import get_live_intraday_prediction

# Add dynamic fallback loading
MIN_MOVE = float(os.getenv('MIN_MOVE_THRESHOLD', 0.0025))
RR_RATIO = float(os.getenv('RISK_REWARD_RATIO', 1.5))

# --- Configuration & Database Setup ---
load_dotenv()
DB_PASSWORD = os.getenv('DB_PASSWORD', 'root')
DATABASE_URL = f"postgresql://postgres:{DB_PASSWORD}@localhost:5432/converse_db"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# --- NEW DUAL-BOUNDARY SCHEMA ---
class LiveMarketOpportunity(Base):
    __tablename__ = "live_opportunities"
    # We drop and recreate the table to apply the new columns
    __table_args__ = {'extend_existing': True} 
    
    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String, unique=True, index=True)
    direction = Column(String) # 'LONG' or 'SHORT'
    expected_high_pct = Column(Float) # The 1-Hour Ceiling
    expected_low_pct = Column(Float)  # The 1-Hour Floor
    uncertainty = Column(Float)       # MC Dropout Confidence
    current_price = Column(Float)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# Recreate the table with the new schema
Base.metadata.drop_all(bind=engine, tables=[LiveMarketOpportunity.__table__])
Base.metadata.create_all(bind=engine)

NIFTY_50 = [
    "RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK", 
    "HINDUNILVR", "SBIN", "BHARTIARTL", "ITC", "KOTAKBANK",
    "LT", "AXISBANK", "ASIANPAINT", "MARUTI", "SUNPHARMA",
    "TITAN", "BAJFINANCE", "ADANIENT", "WIPRO", "HCLTECH"
]

def scan_market(nifty_50_basket):
    """Runs the V3 PyTorch model and filters for Asymmetric Risk/Reward."""
    print(f"\n=========================================================")
    print(f"⚙️ ALPHA ENGINE: Initiating Dual-Boundary Sweep @ {datetime.now().strftime('%H:%M:%S')}")
    print(f"=========================================================")
    
    results = []
    
    for ticker in nifty_50_basket:
        print(f" -> Scanning 1-Hour Geometry for {ticker}...")
        try:
            # This calls the MC Dropout inference script
            pred = get_live_intraday_prediction(ticker)
            
            if pred.get("status") == "success":
                exp_high = pred["expected_high"]
                exp_low = pred["expected_low"]
                uncertainty = pred["uncertainty"]

                # 🔍 DIAGNOSTIC PRINT: See what the model is actually thinking
                print(f"      [RAW PREDICTION] High: {exp_high*100:.3f}% | Low: {exp_low*100:.3f}%")
                
                # --- SMART EXECUTION FILTER (From Cell 9) ---
                # direction = None
                # magnitude = 0
                
                # # Check for LONG setup (Reward > 2x Risk)
                # if exp_high >= 0.005 and exp_high > (abs(exp_low) * 2.0):
                #     direction = "LONG"
                #     magnitude = exp_high
                    
                # # Check for SHORT setup (Downside Reward > 2x Upside Risk)
                # elif abs(exp_low) >= 0.005 and abs(exp_low) > (exp_high * 2.0):
                #     direction = "SHORT"
                #     magnitude = abs(exp_low)

                # --- CALIBRATED SMART EXECUTION FILTER ---
                # direction = None
                # magnitude = 0
                
                # # Relaxing the minimum floor to 0.25% and Risk/Reward to 1.5x
                # if exp_high >= 0.0025 and exp_high > (abs(exp_low) * 1.5):
                #     direction = "LONG"
                #     magnitude = exp_high
                    
                # elif abs(exp_low) >= 0.0025 and abs(exp_low) > (exp_high * 1.5):
                #     direction = "SHORT"
                #     magnitude = abs(exp_low)

                # --- DYNAMIC ALGORTIHMIC FILTER ---
                direction = None
                magnitude = 0
                
                # Check for LONG setup (Using Tunable Config Env Parameters)
                if exp_high >= MIN_MOVE and exp_high > (abs(exp_low) * RR_RATIO):
                    direction = "LONG"
                    magnitude = exp_high
                    
                # Check for SHORT setup 
                elif abs(exp_low) >= MIN_MOVE and abs(exp_low) > (exp_high * RR_RATIO):
                    direction = "SHORT"
                    magnitude = abs(exp_low)
                
                if direction:
                    print(f"   🎯 Valid {direction} Setup Found! Reward: {magnitude*100:.2f}% | Uncertainty: {uncertainty:.4f}")
                    results.append({
                        "ticker": ticker,
                        "direction": direction,
                        "expected_high": exp_high,
                        "expected_low": exp_low,
                        "uncertainty": uncertainty,
                        "current_price": pred["current_price"],
                        "magnitude": magnitude
                    })
                else:
                    print(f"   ⚠️ Skipping {ticker}: Too choppy or poor Risk/Reward.")

        except Exception as e:
            print(f"   ❌ Failed to process {ticker}: {e}")
            
        time.sleep(2) 
        
    if not results:
        print("⚠️ No valid 2:1 Risk/Reward setups generated in this cycle.")
        return

    # Sort by the largest expected moves
    sorted_results = sorted(results, key=lambda x: x["magnitude"], reverse=True)
    top_5 = sorted_results[:5]
    
    print("\n🏆 TOP ASYMMETRIC OPPORTUNITIES FOUND:")
    for rank, setup in enumerate(top_5, 1):
        print(f"  {rank}. {setup['ticker']} [{setup['direction']}] | Target: {setup['magnitude']*100:.2f}%")

    # Update Database
    db = SessionLocal()
    try:
        db.query(LiveMarketOpportunity).delete()
        for setup in top_5:
            new_opp = LiveMarketOpportunity(
                ticker=setup["ticker"],
                direction=setup["direction"],
                expected_high_pct=setup["expected_high"],
                expected_low_pct=setup["expected_low"],
                uncertainty=setup["uncertainty"],
                current_price=setup["current_price"]
            )
            db.add(new_opp)
            
        db.commit()
        print("\n✅ Database `live_opportunities` successfully overwritten.")
    except Exception as e:
        db.rollback()
        print(f"\n❌ Database error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    scan_market(NIFTY_50)