import os
import sys
import time
import logging
from datetime import datetime, timedelta
import pytz

# Add agents directory to path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(BASE_DIR, 'agents'))

from agents.cio_graph import run_macro_cio_sweep, DailyPlaybookDB, SessionLocal
from agents.copilot_graph import run_copilot
from alpha_engine import scan_market

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("MarketDaemon")

# Development simulation toggle
TEST_MODE = False

def check_or_initialize_daily_playbook(ist_now: datetime) -> bool:
    """
    Checks if a Daily Playbook already exists for today's date.
    If missing (e.g. daemon started after 08:45 AM), it runs the CIO sweep immediately.
    """
    db = SessionLocal()
    try:
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        playbook = db.query(DailyPlaybookDB).filter(DailyPlaybookDB.date >= today_start).first()
        
        if playbook:
            logger.info(f"📊 Active Daily Playbook found for today ({playbook.market_regime} | Risk: {playbook.risk_level}).")
            return True
        else:
            logger.info("⚠️ No Daily Playbook found for today. Triggering Macro CIO Sweep on startup...")
            run_macro_cio_sweep()
            return True
    except Exception as e:
        logger.error(f"Error checking daily playbook: {e}")
        try:
            run_macro_cio_sweep()
            return True
        except Exception as sweep_err:
            logger.error(f"CIO Sweep fallback failed: {sweep_err}")
            return False
    finally:
        db.close()

def run_market_daemon():
    ist = pytz.timezone('Asia/Kolkata')
    copilot_minutes = [15, 30, 45, 0]
    
    logger.info("🤖 Quantitative Multi-Agent Market Daemon Initialized.")
    
    # -------------------------------------------------------------
    # STARTUP CHECK: Ensure Today's Macro Playbook Exists
    # -------------------------------------------------------------
    now = datetime.now(ist)
    has_run_cio_today = check_or_initialize_daily_playbook(now)
    last_run_minute_copilot = -1
    
    while True:
        now = datetime.now(ist)
        is_weekday = now.weekday() < 5
        
        if not is_weekday and not TEST_MODE:
            logger.info("Weekend detected. Sleeping for 1 hour...")
            time.sleep(3600)
            continue
            
        # -------------------------------------------------------------
        # 1. PRE-MARKET MACRO PREPARATION (08:45 AM IST)
        # -------------------------------------------------------------
        if now.hour == 8 and now.minute >= 45 and not has_run_cio_today:
            logger.info(f"🌅 [{now.strftime('%I:%M %p')}] Initiating Scheduled Pre-Market Macro Strategy Sweep...")
            try:
                run_macro_cio_sweep()
                has_run_cio_today = True
            except Exception as e:
                logger.error(f"❌ CIO Macro Sweep Failed: {e}")
                
            time.sleep(60)

        # -------------------------------------------------------------
        # 2. INTRADAY EXECUTION SCAN (09:15 AM to 03:30 PM IST)
        # -------------------------------------------------------------
        is_market_open = (
            (now.hour == 9 and now.minute >= 15) or 
            (9 < now.hour < 15) or                  
            (now.hour == 15 and now.minute <= 30)   
        )
        
        if is_market_open:
            if now.minute in copilot_minutes and now.minute != last_run_minute_copilot:
                if now.hour == 9 and now.minute == 15:
                    # Wait until first 15-minute candle closes at 09:30
                    last_run_minute_copilot = now.minute
                    continue
                    
                last_run_minute_copilot = now.minute
                logger.info(f"\n⚡ [{now.strftime('%I:%M %p')} IST] 15-Minute Candle Close: Triggering Quantitative Cycle...")
                
                # Phase 1: High-Speed Mathematical Alpha Scanner
                try:
                    logger.info(" -> Scanning Universe with PyTorch Alpha Engine...")
                    scan_market()
                except Exception as e:
                    logger.error(f"❌ Alpha Engine Scan Error: {e}")
                    
                # Phase 2: Deterministic Tactical Sizing & Execution Router
                try:
                    logger.info(" -> Running Tactical Copilot Execution & Sizing...")
                    run_copilot()
                except Exception as e:
                    logger.error(f"❌ Copilot Execution Error: {e}")

        # -------------------------------------------------------------
        # 3. END OF DAY RESET (03:31 PM IST)
        # -------------------------------------------------------------
        if now.hour == 15 and now.minute >= 31 and has_run_cio_today:
            logger.info(f"🛑 [{now.strftime('%I:%M %p')}] Market Closed. Resetting Daily State Flags.")
            has_run_cio_today = False
            time.sleep(60)

        time.sleep(1)

if __name__ == "__main__":
    run_market_daemon()