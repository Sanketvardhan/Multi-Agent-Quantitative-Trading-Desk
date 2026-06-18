# import os
# import sys
# import time
# from datetime import datetime, timedelta
# import pytz
# import pandas as pd

# # --- Add Agents directory to path so we can import the graphs ---
# BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# sys.path.append(os.path.join(BASE_DIR, 'agents'))

# from agents.state_schema import CIOState, IntradayState
# from agents.cio_graph import cio_app
# from agents.copilot_graph import copilot_app
# from agents.risk_manager import RiskManagerAgent 

# # ==========================================
# # 🛑 DEVELOPMENT TOGGLE
# # ==========================================
# TEST_MODE = False  

# def get_live_nifty50_clean_tickers():
#     """
#     Scrapes the current Nifty 50 constituents from Wikipedia
#     and extracts clean symbols matching the framework requirements.
#     """
#     print("\n[Data Layer] 🌍 Scraping current Nifty 50 index layout from Wikipedia...")
#     url = 'https://en.wikipedia.org/wiki/NIFTY_50'
#     headers = {
#         'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
#     }
#     try:
#         tables = pd.read_html(url, storage_options=headers)
#         nifty_table = None
#         for table in tables:
#             if 'Symbol' in table.columns:
#                 nifty_table = table
#                 break
                
#         if nifty_table is None:
#             raise ValueError("Target Symbol matrix format index layout missing.")
            
#         # Extract clean symbols (e.g. 'RELIANCE', 'TCS') without appending .NS
#         # because the internal graph architecture appends it during runtime data ingestion
#         tickers = nifty_table['Symbol'].astype(str).tolist()
#         print(f"✅ Success. Discovered {len(tickers)} live index components.")
#         return tickers
#     except Exception as e:
#         print(f"⚠️ Wikipedia parsing warning: {e}. Falling back to baseline tracking array.")
#         return ['RELIANCE', 'TCS', 'HDFCBANK', 'INFY', 'ITC', 'SBIN']

# def run_market_daemon():
#     ist = pytz.timezone('Asia/Kolkata')
#     target_minutes = [15, 30, 45, 0]
#     has_run_cio_today = False
    
#     print("🤖 Vibe Trading Production Daemon Initialized.")
    
#     if TEST_MODE:
#         print("⚠️ TEST MODE ACTIVE: Accelerating time!")
#         sim_time = datetime(2026, 6, 8, 8, 44, 55, tzinfo=ist)
#     else:
#         print("Watching IST clock in real-time...")

#     while True:
#         # --- 0. TIME ENGINE ---
#         if TEST_MODE:
#             now = sim_time
#             sim_time += timedelta(seconds=1)
#             time.sleep(0.001) 
#         else:
#             now = datetime.now(ist)
#             time.sleep(1)

#         is_weekday = now.weekday() < 5
#         if not is_weekday:
#             if not TEST_MODE: time.sleep(3600)
#             continue

#         # --- 1. PRE-MARKET PREP (08:45 AM) ---
#         if now.hour == 8 and now.minute >= 45 and not has_run_cio_today:
#             print(f"\n[{now.strftime('%H:%M:%S')} AM] 🌅 Pre-Market Phase Initiated.")
            
#             # Dynamically pull the entire 50-stock basket right before market open
#             nifty_50_basket = get_live_nifty50_clean_tickers()
            
#             initial_state = CIOState(target_tickers=nifty_50_basket)
#             try:
#                 print(f" -> Routing complete {len(nifty_50_basket)} stock matrix to CIO Agent sweep...")
#                 cio_app.invoke(initial_state)
#             except Exception as e:
#                 print(f"❌ CIO Graph Failed: {e}")
            
#             has_run_cio_today = True
#             if not TEST_MODE: time.sleep(60)

#         # --- 2. INTRADAY EXECUTION LOOP (09:15 AM to 03:30 PM) ---
#         is_market_open = (
#             (now.hour == 9 and now.minute >= 15) or 
#             (9 < now.hour < 15) or                  
#             (now.hour == 15 and now.minute <= 30)   
#         )
        
#         if is_market_open:
#             if now.minute in target_minutes and now.second == 1:
#                 print(f"\n--- ⏱️ CANDLE CLOSE: {now.strftime('%H:%M:%S')} IST ---")
                
#                 # --- STEP A: RISK MANAGER BACKGROUND MEMORY CHECK ---
#                 print(" -> Waking up Risk Manager to check open positions...")
#                 rm = RiskManagerAgent()
#                 try:
#                     rm.manage_active_positions()
#                 except Exception as e:
#                     print(f"❌ Risk Manager Processing Error: {e}")
#                 finally:
#                     rm.close()
                
#                 # --- STEP B: COPILOT ALLOCATION MONITOR ---
#                 print(" -> Waking up Intraday Copilot Agent for fresh entries...")
#                 try:
#                     copilot_app.invoke(IntradayState())
#                 except Exception as e:
#                     print(f"❌ Copilot Graph Failed: {e}")
                
#                 if not TEST_MODE: time.sleep(60)
                
#         # --- 3. END OF DAY RESET (03:31 PM) ---
#         if now.hour == 15 and now.minute == 31 and has_run_cio_today:
#             print(f"\n[{now.strftime('%H:%M:%S')} PM] 🛑 Market Closed. Resetting state.")
#             has_run_cio_today = False
            
#             if TEST_MODE:
#                 break
#             else:
#                 time.sleep(60)

# if __name__ == "__main__":
#     run_market_daemon()


import os
import sys
import time
from datetime import datetime, timedelta
import pytz
import pandas as pd

# --- Add Agents directory to path so we can import the graphs ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(BASE_DIR, 'agents'))

from agents.state_schema import CIOState, IntradayState
from agents.cio_graph import cio_app
from agents.copilot_graph import copilot_app
from agents.risk_manager import RiskManagerAgent 

# ==========================================
# 🛑 DEVELOPMENT TOGGLE
# ==========================================
TEST_MODE = False  

def get_live_nifty50_clean_tickers():
    """
    Scrapes the current Nifty 50 constituents from Wikipedia
    and extracts clean symbols matching the framework requirements.
    """
    print("\n[Data Layer] 🌍 Scraping current Nifty 50 index layout from Wikipedia...")
    url = 'https://en.wikipedia.org/wiki/NIFTY_50'
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    try:
        tables = pd.read_html(url, storage_options=headers)
        nifty_table = None
        for table in tables:
            if 'Symbol' in table.columns:
                nifty_table = table
                break
                
        if nifty_table is None:
            raise ValueError("Target Symbol matrix format index layout missing.")
            
        tickers = nifty_table['Symbol'].astype(str).tolist()
        print(f"✅ Success. Discovered {len(tickers)} live index components.")
        return tickers
    except Exception as e:
        print(f"⚠️ Wikipedia parsing warning: {e}. Falling back to baseline tracking array.")
        return ['RELIANCE', 'TCS', 'HDFCBANK', 'INFY', 'ITC', 'SBIN']

def run_market_daemon():
    ist = pytz.timezone('Asia/Kolkata')
    # target_minutes = [15, 30, 45, 0]
    # has_run_cio_today = False
    
    # # THE FIX: Track the last run minute to prevent skipped seconds
    # last_run_minute = -1

    # Decoupled timing schedules
    copilot_minutes = [15, 30, 45, 0]
    risk_minutes = [0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55]
    
    has_run_cio_today = False
    last_run_minute_copilot = -1
    last_run_minute_risk = -1
    
    print("🤖 Vibe Trading Production Daemon Initialized.")
    
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
            # THE FIX: Formatted AM/PM correctly
            print(f"\n[{now.strftime('%I:%M %p')}] 🌅 Pre-Market Phase Initiated.")
            
            nifty_50_basket = get_live_nifty50_clean_tickers()
            initial_state = CIOState(target_tickers=nifty_50_basket)
            try:
                print(f" -> Routing complete {len(nifty_50_basket)} stock matrix to CIO Agent sweep...")
                cio_app.invoke(initial_state)
            except Exception as e:
                print(f"❌ CIO Graph Failed: {e}")
            
            has_run_cio_today = True
            if not TEST_MODE: time.sleep(60)

        # # --- 2. INTRADAY EXECUTION LOOP (09:15 AM to 03:30 PM) ---
        # is_market_open = (
        #     (now.hour == 9 and now.minute >= 15) or 
        #     (9 < now.hour < 15) or                  
        #     (now.hour == 15 and now.minute <= 30)   
        # )
        
        # if is_market_open:
        #     # THE FIX: Trigger based on minute change, not exact second
        #     if now.minute in target_minutes and now.minute != last_run_minute:
                
        #         # THE FIX: Skip the 9:15 AM check. The first candle doesn't close until 9:30 AM!
        #         if now.hour == 9 and now.minute == 15:
        #             last_run_minute = now.minute
        #             continue
                
        #         last_run_minute = now.minute
        #         print(f"\n--- ⏱️ CANDLE CLOSE: {now.strftime('%I:%M %p')} IST ---")
                
        #         print(" -> Waking up Risk Manager to check open positions...")
        #         rm = RiskManagerAgent()
        #         try:
        #             rm.manage_active_positions()
        #         except Exception as e:
        #             print(f"❌ Risk Manager Processing Error: {e}")
        #         finally:
        #             rm.close()
                
        #         print(" -> Waking up Intraday Copilot Agent for fresh entries...")
        #         try:
        #             copilot_app.invoke(IntradayState())
        #         except Exception as e:
        #             print(f"❌ Copilot Graph Failed: {e}")
                
        # --- 2. INTRADAY EXECUTION LOOP (09:15 AM to 03:30 PM) ---
        is_market_open = (
            (now.hour == 9 and now.minute >= 15) or 
            (9 < now.hour < 15) or                  
            (now.hour == 15 and now.minute <= 30)   
        )
        
        if is_market_open:
            # --- STEP A: 5-MINUTE RISK MANAGER LOOP ---
            if now.minute in risk_minutes and now.minute != last_run_minute_risk:
                last_run_minute_risk = now.minute
                
                print(f"\n--- 🛡️ 5M RISK SCAN: {now.strftime('%I:%M %p')} IST ---")
                rm = RiskManagerAgent()
                try:
                    rm.manage_active_positions()
                except Exception as e:
                    print(f"❌ Risk Manager Processing Error: {e}")
                finally:
                    rm.close()

            # --- STEP B: 15-MINUTE COPILOT LOOP ---
            if now.minute in copilot_minutes and now.minute != last_run_minute_copilot:
                # Skip 9:15 AM check for the Copilot (no candle closed yet)
                if now.hour == 9 and now.minute == 15:
                    last_run_minute_copilot = now.minute
                    continue
                
                last_run_minute_copilot = now.minute
                print(f"\n--- ⚡ 15M COPILOT SCAN: {now.strftime('%I:%M %p')} IST ---")
                
                try:
                    copilot_app.invoke(IntradayState())
                except Exception as e:
                    print(f"❌ Copilot Graph Failed: {e}")
                    
        # --- 3. END OF DAY RESET (03:31 PM) ---
        if now.hour == 15 and now.minute >= 31 and has_run_cio_today:
            print(f"\n[{now.strftime('%I:%M %p')}] 🛑 Market Closed. Resetting state.")
            has_run_cio_today = False
            
            if TEST_MODE:
                break
            else:
                time.sleep(60)

if __name__ == "__main__":
    run_market_daemon()