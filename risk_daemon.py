import os
import sys
import time
import logging
from datetime import datetime
import pytz

# Add agents directory to path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(BASE_DIR, 'agents'))

from agents.risk_manager import RiskManagerAgent

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("RiskDaemon")

def run_realtime_risk_core():
    logger.info("🛡️ High-Speed Real-Time Risk Core Active.")
    logger.info("   ⚡ Tick-by-Tick Evaluation: Chandelier ATR Trailing Stop, Hard Breaches & EOD Square-Off.")
    
    ist = pytz.timezone('Asia/Kolkata')
    risk_agent = RiskManagerAgent()
    
    while True:
        try:
            now_ist = datetime.now(ist)
            
            # Active market window guard (09:15 AM to 03:30 PM IST)
            is_market_hours = (
                (now_ist.hour == 9 and now_ist.minute >= 15) or 
                (9 < now_ist.hour < 15) or 
                (now_ist.hour == 15 and now_ist.minute <= 30)
            )
            
            if not is_market_hours:
                time.sleep(30)
                continue

            # Run deterministic position management
            risk_agent.manage_active_positions()
            
        except Exception as e:
            logger.error(f"❌ Risk Daemon Loop Exception: {e}")
            
        # Fast 15-second tick interval for responsive risk protection
        time.sleep(15)

if __name__ == "__main__":
    try:
        run_realtime_risk_core()
    except KeyboardInterrupt:
        logger.info("\n👋 Risk daemon safely terminated.")