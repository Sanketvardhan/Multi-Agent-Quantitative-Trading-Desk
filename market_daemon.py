import os
import sys
import time
from datetime import datetime, timedelta
import pytz

# --- Add Agents directory to path so we can import the graphs ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(BASE_DIR, 'agents'))

from agents.state_schema import CIOState, IntradayState
from agents.cio_graph import cio_app
from agents.copilot_graph import copilot_app

# ==========================================
# 🛑 DEVELOPMENT TOGGLE
# ==========================================
TEST_MODE = True  

def run_market_daemon():
    ist = pytz.timezone('Asia/Kolkata')
    target_minutes = [15, 30, 45, 0]
    has_run_cio_today = False
    
    # The Master Watchlist for the CIO to sweep every morning
    NIFTY_TARGETS = ['RELIANCE', 'TCS', 'HDFCBANK', 'INFY', 'ITC', 'SBIN']
    
    print("🤖 Vib Trader Production Daemon Initialized.")
    
    if TEST_MODE:
        print("⚠️ TEST MODE ACTIVE: Accelerating time!")
        sim_time = datetime(2026, 6, 8, 8, 44, 55, tzinfo=ist)
    else:
        print("Watching IST clock in real-time...")

    while True:
        # --- 0. TIME ENGINE ---
        if TEST_MODE:
            now = sim_time
            sim_time += timedelta(seconds=1)
            time.sleep(0.001) 
        else:
            now = datetime.now(ist)
            time.sleep(1)

        is_weekday = now.weekday() < 5
        if not is_weekday:
            if not TEST_MODE: time.sleep(3600)
            continue

        # --- 1. PRE-MARKET PREP (08:45 AM) ---
        if now.hour == 8 and now.minute >= 45 and not has_run_cio_today:
            print(f"\n[{now.strftime('%H:%M:%S')} AM] 🌅 Pre-Market Phase Initiated.")
            
            initial_state = CIOState(target_tickers=NIFTY_TARGETS)
            try:
                cio_app.invoke(initial_state)
            except Exception as e:
                print(f"❌ CIO Graph Failed: {e}")
            
            has_run_cio_today = True
            if not TEST_MODE: time.sleep(60)

        # --- 2. INTRADAY EXECUTION LOOP (09:15 AM to 03:30 PM) ---
        is_market_open = (
            (now.hour == 9 and now.minute >= 15) or 
            (9 < now.hour < 15) or                  
            (now.hour == 15 and now.minute <= 30)   
        )
        
        if is_market_open:
            if now.minute in target_minutes and now.second == 1:
                print(f"\n--- ⏱️ CANDLE CLOSE: {now.strftime('%H:%M:%S')} IST ---")
                
                try:
                    copilot_app.invoke(IntradayState())
                except Exception as e:
                    print(f"❌ Copilot Graph Failed: {e}")
                
                if not TEST_MODE: time.sleep(60)
                
        # --- 3. END OF DAY RESET (03:31 PM) ---
        if now.hour == 15 and now.minute == 31 and has_run_cio_today:
            print(f"\n[{now.strftime('%H:%M:%S')} PM] 🛑 Market Closed. Resetting state.")
            has_run_cio_today = False
            
            if TEST_MODE:
                break
            else:
                time.sleep(60)

if __name__ == "__main__":
    run_market_daemon()