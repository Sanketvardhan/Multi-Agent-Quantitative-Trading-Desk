# import os
# import sys
# import time
# import warnings
# import json
# from datetime import datetime
# import pytz
# import yfinance as yf
# from dotenv import load_dotenv

# # Add agents directory to system path
# BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# sys.path.append(os.path.join(BASE_DIR, 'agents'))

# from agents.risk_manager import RiskManagerAgent, Trade, SessionLocal

# warnings.filterwarnings('ignore')

# def get_realtime_ticker_price(ticker: str) -> float:
#     """
#     Fetches the latest snapshot price from yfinance instantly.
#     Using standard ticker symbols without full history blocks is free and incredibly fast.
#     """
#     try:
#         clean_ticker = ticker if ticker.endswith('.NS') else f"{ticker}.NS"
#         stock = yf.Ticker(clean_ticker)
#         # Fast extraction via current live quote info dict
#         fast_info = stock.fast_info
#         if 'last_price' in fast_info and fast_info['last_price'] is not None:
#             return round(float(fast_info['last_price']), 2)
            
#         # Fallback to history snapshot if fast_info fails
#         df = stock.history(period="1d", interval="1m")
#         if not df.empty:
#             return round(float(df['Close'].iloc[-1]), 2)
#     except Exception as e:
#         print(f"   ❌ Error fetching fast tick price for {ticker}: {e}")
#     return None

# def run_realtime_risk_core():
#     print("🛡️ High-Speed Real-Time Risk Core Active. Monitoring database rows continuously...")
#     ist = pytz.timezone('Asia/Kolkata')
    
#     # Initialize the cognitive agent layer once for EOD/Time decay rules
#     agent = RiskManagerAgent()
    
#     # Trailing step threshold percentage (e.g., 0.1% price movement triggers an SL ratchet up)
#     TRAILING_STEP_PCT = 0.001 
    
#     while True:
#         now_ist = datetime.now(ist)
        
#         # Guard rail: Only run while the market window is active (9:15 AM to 3:30 PM)
#         is_market_hours = (now_ist.hour == 9 and now_ist.minute >= 15) or (9 < now_ist.hour < 15) or (now_ist.hour == 15 and now_ist.minute <= 30)
        
#         if not is_market_hours:
#             print("💤 Market is closed. Risk core sleeping for 60 seconds...")
#             time.sleep(60)
#             continue
            
#         db = SessionLocal()
#         try:
#             active_trades = db.query(Trade).filter(Trade.status == "ACTIVE").all()
            
#             for trade in active_trades:
#                 live_price = get_realtime_ticker_price(trade.ticker)
#                 if not live_price:
#                     continue
                    
#                 # Calculate basic baseline performance parameters
#                 if "SHORT" in trade.action:
#                     gross_pnl = round((trade.entry_price - live_price) * trade.sizing, 2)
#                 else:
#                     gross_pnl = round((live_price - trade.entry_price) * trade.sizing, 2)
                    
#                 # --- FAST PATH A: HARD RISK BREACH (PURE MATH) ---
#                 is_long_stop = (trade.action == "EXECUTE LONG" and live_price <= trade.stop_loss)
#                 is_short_stop = (trade.action == "EXECUTE SHORT" and live_price >= trade.stop_loss)
                
#                 if is_long_stop or is_short_stop:
#                     trade.status = "CLOSED_CUT_LOSS"
#                     trade.live_price = live_price
#                     trade.current_pnl = gross_pnl
#                     trade.closed_at = datetime.utcnow()
#                     trade.risk_reasoning = f"Real-time math core triggered safety exit. Price crossed Stop Loss floor."
#                     db.commit()
#                     print(f"💥 [HARD EXIT] {trade.ticker} closed instantly via math core. PnL: ₹{gross_pnl}")
#                     agent._apply_cooldown(trade.ticker)
#                     continue
                    
#                 # --- FAST PATH B: REAL-TIME TRAILING MECHANIC (PURE MATH) ---
#                 if trade.action == "EXECUTE LONG" and live_price > trade.entry_price:
#                     # Calculate how much the price has moved above entry
#                     gain_pct = (live_price - trade.entry_price) / trade.entry_price
#                     # Calculate a dynamic trailing floor sitting 0.15% below the current peak
#                     calculated_sl = round(live_price * (1.0 - 0.0015), 2)
                    
#                     # Only trail the stop loss UPward, never downward
#                     if calculated_sl > trade.stop_loss:
#                         old_sl = trade.stop_loss
#                         trade.stop_loss = calculated_sl
#                         trade.live_price = live_price
#                         trade.current_pnl = gross_pnl
#                         trade.risk_reasoning = f"Math core rachet active. Trailing SL tracked up to ₹{calculated_sl}."
#                         db.commit()
#                         print(f"📈 [RATON TRAIL] {trade.ticker} Stop Loss locked in higher: ₹{old_sl} -> ₹{calculated_sl}")
                        
#                 elif trade.action == "EXECUTE SHORT" and live_price < trade.entry_price:
#                     # Trailing logic for active short allocations
#                     calculated_sl = round(live_price * (1.0 + 0.0015), 2)
#                     if calculated_sl < trade.stop_loss:
#                         old_sl = trade.stop_loss
#                         trade.stop_loss = calculated_sl
#                         trade.live_price = live_price
#                         trade.current_pnl = gross_pnl
#                         db.commit()
#                         print(f"📉 [RATON TRAIL] {trade.ticker} Stop Loss trailed lower: ₹{old_sl} -> ₹{calculated_sl}")

#                 # --- COGNITIVE PATH C: TIME-DECAY & EOD CRONS (LLM EXCEPTION ONLY) ---
#                 minutes_held = 0
#                 if trade.activated_at:
#                     minutes_held = int((datetime.utcnow() - trade.activated_at).total_seconds() / 60)
                    
#                 is_eod_window = (now_ist.hour == 15 and now_ist.minute >= 15)
#                 is_time_decay_reached = (minutes_held >= 90 and abs(gross_pnl) < 15)
                
#                 if is_eod_window or is_time_decay_reached:
#                     print(f"🧠 [COGNITIVE ESCALATION] Escalating {trade.ticker} to LLM for tactical evaluation...")
#                     db.close() # Release connection context before calling the agent instance
#                     agent.manage_active_positions()
#                     db = SessionLocal() # Re-open database handle for subsequent loops
                    
#         except Exception as e:
#             print(f"❌ Real-time risk loop error: {e}")
#         finally:
#             db.close()
            
#         # High-frequency tick pause (15 seconds) safely within standard free limits
#         time.sleep(30)

# if __name__ == "__main__":
#     try:
#         run_realtime_risk_core()
#     except KeyboardInterrupt:
#         print("\n👋 Risk daemon terminated by developer request.")
import os
import sys
import time
import warnings
from datetime import datetime
import pytz
import yfinance as yf
from dotenv import load_dotenv

# Add agents directory to system path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(BASE_DIR, 'agents'))

from agents.risk_manager import RiskManagerAgent, Trade, SessionLocal

warnings.filterwarnings('ignore')

def get_realtime_ticker_price(ticker: str) -> float:
    """
    Fetches the latest snapshot price from yfinance instantly.
    """
    try:
        clean_ticker = ticker if ticker.endswith('.NS') else f"{ticker}.NS"
        stock = yf.Ticker(clean_ticker)
        fast_info = stock.fast_info
        if 'last_price' in fast_info and fast_info['last_price'] is not None:
            return round(float(fast_info['last_price']), 2)
            
        df = stock.history(period="1d", interval="1m")
        if not df.empty:
            return round(float(df['Close'].iloc[-1]), 2)
    except Exception as e:
        print(f"   ❌ Error fetching fast tick price for {ticker}: {e}")
    return None

def run_realtime_risk_core():
    print("🛡️ High-Speed Real-Time Risk Core Initialized.")
    print("   ⚡ 30-Sec Fast Track: Math Trailing SL & Hard Exit Protection")
    print("   🧠 5-Min Slow Track: Full RSI/MACD & LLM Cognitive Sweep")
    
    ist = pytz.timezone('Asia/Kolkata')
    agent = RiskManagerAgent()
    last_5m_run_minute = -1

    while True:
        now_ist = datetime.now(ist)
        
        # Guard rail: Only run while the market window is active (9:15 AM to 3:30 PM)
        is_market_hours = (
            (now_ist.hour == 9 and now_ist.minute >= 15) or 
            (9 < now_ist.hour < 15) or 
            (now_ist.hour == 15 and now_ist.minute <= 30)
        )
        
        if not is_market_hours:
            print("💤 Market is closed. Risk daemon sleeping for 60 seconds...")
            time.sleep(60)
            continue

        db = SessionLocal()
        try:
            active_trades = db.query(Trade).filter(Trade.status == "ACTIVE").all()
            
            if active_trades:
                # ==========================================
                # ⚡ 1. FAST TRACK (EVERY 30 SECONDS - PURE MATH)
                # ==========================================
                for trade in active_trades:
                    live_price = get_realtime_ticker_price(trade.ticker)
                    if not live_price:
                        continue
                        
                    # Calculate live PnL
                    if "SHORT" in trade.action:
                        gross_pnl = round((trade.entry_price - live_price) * trade.sizing, 2)
                    else:
                        gross_pnl = round((live_price - trade.entry_price) * trade.sizing, 2)
                        
                    trade.live_price = live_price
                    trade.current_pnl = gross_pnl

                    # --- HARD EXIT BREACH CHECKS ---
                    is_long_stop = (trade.action == "EXECUTE LONG" and live_price <= trade.stop_loss)
                    is_short_stop = (trade.action == "EXECUTE SHORT" and live_price >= trade.stop_loss)

                    if is_long_stop or is_short_stop:
                        # Determine if this exit locked in a profit or was a cut-loss
                        is_profit_exit = (
                            (trade.action == "EXECUTE LONG" and trade.stop_loss > trade.entry_price) or 
                            (trade.action == "EXECUTE SHORT" and trade.stop_loss < trade.entry_price)
                        )
                        
                        trade.status = "CLOSED_TRAILING_STOP" if is_profit_exit else "CLOSED_CUT_LOSS"
                        trade.closed_at = datetime.utcnow()
                        trade.risk_reasoning = f"Real-time math exit. Price crossed trailing floor/ceiling at ₹{trade.stop_loss}."
                        db.commit()
                        
                        exit_label = "TRAILING PROFIT LOCK" if is_profit_exit else "CUT LOSS"
                        print(f"💥 [{exit_label}] {trade.ticker} closed at ₹{live_price}. Final PnL: ₹{gross_pnl}")
                        
                        # Only apply cooldown on true losses
                        if not is_profit_exit:
                            agent._apply_cooldown(trade.ticker)
                        continue

                    # --- DYNAMIC TRAILING SL & TARGET EXPANSION ---
                    if trade.action == "EXECUTE LONG":
                        # Dynamic trailing floor: 0.15% below peak price
                        calculated_sl = round(live_price * (1.0 - 0.0015), 2)
                        
                        if calculated_sl > trade.stop_loss:
                            old_sl = trade.stop_loss
                            trade.stop_loss = calculated_sl
                            
                            # RUNNER MODE: Expand target by 0.8% if price approaches within 0.5% of TP
                            if live_price >= (trade.take_profit * 0.995):
                                trade.take_profit = round(live_price * 1.008, 2)
                                print(f"🚀 [RUNNER MODE] {trade.ticker} target expanded to ₹{trade.take_profit}")

                            trade.risk_reasoning = f"⚡ Dynamic Trailing Active. SL ratcheted up to ₹{calculated_sl}."
                            db.commit()
                            print(f"📈 [TRAIL SL] {trade.ticker}: ₹{old_sl} ➔ ₹{calculated_sl}")

                    elif trade.action == "EXECUTE SHORT":
                        calculated_sl = round(live_price * (1.0 + 0.0015), 2)
                        if calculated_sl < trade.stop_loss:
                            old_sl = trade.stop_loss
                            trade.stop_loss = calculated_sl
                            
                            if live_price <= (trade.take_profit * 1.005):
                                trade.take_profit = round(live_price * 0.992, 2)
                                print(f"🚀 [RUNNER MODE] {trade.ticker} target lowered to ₹{trade.take_profit}")

                            trade.risk_reasoning = f"⚡ Dynamic Trailing Active. SL ratcheted down to ₹{calculated_sl}."
                            db.commit()
                            print(f"📉 [TRAIL SL] {trade.ticker}: ₹{old_sl} ➔ ₹{calculated_sl}")

            db.commit()

            # ==========================================
            # 🧠 2. SLOW TRACK (EVERY 5 MINUTES - FULL AI & INDICATOR SWEEP)
            # ==========================================
            if now_ist.minute % 5 == 0 and now_ist.minute != last_5m_run_minute:
                last_5m_run_minute = now_ist.minute
                print(f"\n[{now_ist.strftime('%I:%M %p')}] 🔍 Triggering 5-Minute Cognitive AI & Technical Indicator Sweep...")
                
                db.close()  # Close handle before calling agent method
                try:
                    agent.manage_active_positions()
                except Exception as e:
                    print(f"❌ Cognitive sweep error: {e}")
                db = SessionLocal()

        except Exception as e:
            print(f"❌ Risk daemon loop error: {e}")
        finally:
            db.close()

        # Sleep for 30 seconds before the next fast tick evaluation
        time.sleep(30)

if __name__ == "__main__":
    try:
        run_realtime_risk_core()
    except KeyboardInterrupt:
        print("\n👋 Risk daemon terminated by developer request.")