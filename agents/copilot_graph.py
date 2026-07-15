# import os
# import json
# import time
# import requests
# import re
# from datetime import datetime
# from typing import Dict, Any
# from dotenv import load_dotenv

# from pydantic import BaseModel, Field
# from langgraph.graph import StateGraph, END
# from langchain_aws import ChatBedrock
# from langchain_core.output_parsers import PydanticOutputParser
# from tvDatafeed import TvDatafeed, Interval

# # Database Imports for Alpha Engine Shared Memory
# from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, JSON
# from sqlalchemy.orm import sessionmaker, declarative_base

# # Import our custom schemas
# from state_schema import IntradayState, TradeAlert

# # --- CONFIGURATION ---
# BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# load_dotenv(os.path.join(BASE_DIR, '.env'))

# # --- PORTFOLIO RISK RULES ---
# RISK_PER_TRADE = 0.01           # 1% max loss if Stop Loss is hit
# MAX_ALLOCATION = 0.20           # Never put more than 20% of total capital into one stock

# # --- SHARED MEMORY DATABASE SETUP ---
# DB_PASSWORD = os.getenv('DB_PASSWORD', 'root')
# DATABASE_URL = f"postgresql://postgres:{DB_PASSWORD}@localhost:5432/converse_db"

# engine = create_engine(DATABASE_URL)
# SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
# Base = declarative_base()

# class LiveMarketOpportunity(Base):
#     """The Shared Memory table populated by alpha_engine.py"""
#     __tablename__ = "live_opportunities"
#     id = Column(Integer, primary_key=True, index=True)
#     ticker = Column(String, unique=True, index=True)
#     expected_return = Column(Float)
#     uncertainty = Column(Float)
#     atr = Column(Float)
#     current_price = Column(Float)
#     updated_at = Column(DateTime)

# class DailyPlaybookDB(Base):
#     """The Shared Memory table populated by cio_graph.py"""
#     __tablename__ = "daily_playbook"
#     id = Column(Integer, primary_key=True, index=True)
#     date = Column(DateTime, default=datetime.utcnow)
#     market_regime = Column(String) 
#     risk_level = Column(String)    
#     approved_sectors = Column(JSON) 
#     banned_sectors = Column(JSON)   
#     reasoning = Column(String)

# # Wrapper Pydantic class for LLM Output
# class AlertList(BaseModel):
#     alerts: list[TradeAlert]

# # ==========================================
# # 0. HELPER FUNCTIONS
# # ==========================================
# def get_live_market_regime():
#     """Copilot's independent eyes on the broader market."""
#     try:
#         tv = TvDatafeed()
#         df = tv.get_hist(symbol='NIFTY', exchange='NSE', interval=Interval.in_daily, n_bars=2)
#         if df is not None and not df.empty:
#             today_open = df['open'].iloc[-1]
#             current_price = df['close'].iloc[-1]
#             pct_change = ((current_price - today_open) / today_open) * 100
            
#             if pct_change > 0.15:
#                 return f"BULLISH (Nifty is UP {pct_change:.2f}% from open)"
#             elif pct_change < -0.15:
#                 return f"BEARISH (Nifty is DOWN {pct_change:.2f}% from open)"
#             else:
#                 return f"NEUTRAL/CHOPPY (Nifty is flat at {pct_change:.2f}%)"
#     except Exception as e:
#         print(f" ⚠️ Could not fetch NIFTY regime: {e}")
#     return "UNKNOWN"

# # ==========================================
# # 1. LANGGRAPH NODES
# # ==========================================
# def load_context_node(state: IntradayState):
#     """Node 1: Reads the CIO's Daily Playbook from PostgreSQL."""
#     print("\n[Copilot Agent] 📂 Loading Macro Context from Shared Memory...")
    
#     db = SessionLocal()
#     playbook = db.query(DailyPlaybookDB).order_by(DailyPlaybookDB.id.desc()).first()
#     db.close()
    
#     if not playbook:
#         print("   ❌ No active playbook found. Did the CIO run?")
#         return {"error_logs": ["Missing Daily Playbook"]}
        
#     print(f"   ✅ Playbook loaded. Regime: {playbook.market_regime}")
    
#     # Pack it into the state variable
#     playbook_data = {
#         "market_regime": playbook.market_regime,
#         "risk_level": playbook.risk_level,
#         "approved_sectors": playbook.approved_sectors,
#         "banned_sectors": playbook.banned_sectors
#     }
    
#     return {"watchlist_config": playbook_data}

# def fetch_alpha_signals_node(state: IntradayState):
#     """Node 2: Reads the Top 5 setups from the DB and checks the Penalty Box."""
#     if state.error_logs:
#         return {}
        
#     print("\n[Copilot Agent] ⚡ Querying Shared Memory for Alpha Engine Setups...")
    
#     db = SessionLocal()
#     opportunities = db.query(LiveMarketOpportunity).all()
#     db.close()
    
#     if not opportunities:
#         print("   ❌ No live opportunities found in database. Is alpha_engine.py running?")
#         return {"error_logs": ["No Alpha Signals"]}
        
#     predictions = {}
#     for opp in opportunities:
#         ticker = opp.ticker
        
#         # --- THE PENALTY BOX CHECK ---
#         try:
#             cd_res = requests.get(f"http://127.0.0.1:8000/api/cooldown/check/{ticker}")
#             if cd_res.status_code == 200 and cd_res.json().get("in_cooldown"):
#                 print(f"   🛑 Skipping {ticker} - Currently in 60-minute Cooldown.")
#                 continue # Skip sizing math, don't send to LLM
#         except requests.exceptions.ConnectionError:
#             pass # API might be down, proceed normally
            
#         predictions[ticker] = {
#             "expected_return": opp.expected_return,
#             "current_price": opp.current_price,
#             "current_atr": opp.atr
#         }
        
#     return {"intraday_predictions": predictions}

# def generate_alerts_node(state: IntradayState):
#     """Node 3: Llama 3 decides whether to execute the Alpha setups."""
#     if state.error_logs or not state.intraday_predictions:
#         return {}
        
#     print("\n[Copilot Agent] 🤖 Calculating Sizing & Requesting Execution Authority...")
    
#     # Fetch live capital from API
#     try:
#         cap_response = requests.get("http://127.0.0.1:8000/api/account/capital")
#         total_capital = cap_response.json().get("current_capital", 100000.0) if cap_response.status_code == 200 else 100000.0
#     except requests.exceptions.ConnectionError:
#         total_capital = 100000.0

#     max_risk_amount = total_capital * RISK_PER_TRADE
#     max_capital_per_trade = total_capital * MAX_ALLOCATION

#     # Sizing Math
#     enriched_predictions = {}
#     for ticker, data in state.intraday_predictions.items():
#         price = data.get('current_price', 0)
#         atr = data.get('current_atr', 0)
#         # risk_per_share = 1.5 * atr
#         risk_per_share = 1.0 * atr
        
#         if risk_per_share > 0 and price > 0:
#             risk_based_shares = int(max_risk_amount / risk_per_share)
#             projected_cost = risk_based_shares * price
            
#             if projected_cost > max_capital_per_trade:
#                 final_sizing = int(max_capital_per_trade / price)
#                 cost_reason = f"Capped by {MAX_ALLOCATION*100}% Capital Limit"
#             else:
#                 final_sizing = risk_based_shares
#                 cost_reason = f"Based on {RISK_PER_TRADE*100}% Risk Limit"
#         else:
#             final_sizing = 0
#             cost_reason = "Invalid data"
            
#         # data['suggested_long_sl'] = round(price - risk_per_share, 2)
#         # data['suggested_long_tp'] = round(price + (3.0 * atr), 2)
#         # data['suggested_short_sl'] = round(price + risk_per_share, 2)
#         # data['suggested_short_tp'] = round(price - (3.0 * atr), 2)

#         # Take Profit is exactly what PyTorch predicted
#         expected_move_abs = price * abs(data.get('expected_return', 0))
        
#         data['suggested_long_sl'] = round(price - risk_per_share, 2)
#         data['suggested_long_tp'] = round(price + expected_move_abs, 2)
#         data['suggested_short_sl'] = round(price + risk_per_share, 2)
#         data['suggested_short_tp'] = round(price - expected_move_abs, 2)
#         data['suggested_sizing'] = final_sizing
#         data['sizing_logic'] = cost_reason
#         enriched_predictions[ticker] = data

#     # Llama 3 Call
#     llm = ChatBedrock(
#         model_id="meta.llama3-8b-instruct-v1:0",
#         model_kwargs={"temperature": 0.1},
#         region_name="us-east-1"
#     )
    
#     parser = PydanticOutputParser(pydantic_object=AlertList)
#     market_regime = get_live_market_regime()
#     print(f"   📊 Live NIFTY 50 Regime: {market_regime}")
    
#     system_instruction = (
#         "You are an elite quantitative Execution Copilot. You have TRUE AUTONOMY.\n"
#         "You receive the human CIO's Daily Playbook, the live 15m expected return of the Top 5 setups, and the LIVE NIFTY 50 Market Regime.\n\n"
#         "YOUR PRIME DIRECTIVE:\n"
#         "Never trade against the broader market. If the Nifty is Bearish, DO NOT take Longs.\n\n"
#         "EXECUTION LOGIC:\n"
#         "1. ALIGNED: If Nifty is BEARISH and the 15m return is NEGATIVE -> 'EXECUTE SHORT'.\n"
#         "2. ALIGNED: If Nifty is BULLISH and the 15m return is POSITIVE -> 'EXECUTE LONG'.\n"
#         "3. CIO VETO: If the CIO Playbook has a 'banned_sector' and the stock belongs to it -> 'HOLD'.\n"
#         "4. CONFLICT: If there is conflict between the 15m return and the Regime -> 'HOLD'.\n\n"
#         "DATA MAPPING (CRITICAL):\n"
#         "- entry_price: Use 'current_price'.\n"
#         "- stop_loss & take_profit: If LONG, copy 'suggested_long_sl' and 'suggested_long_tp'. If SHORT, copy 'suggested_short_sl' and 'suggested_short_tp'.\n"
#         "- position_size_advice: Copy this format -> 'Buy [suggested_sizing] shares ([sizing_logic])'.\n"
#         "- If HOLD, set all numerical values to 0.0.\n\n"
#         f"FORMAT REQUIREMENTS:\n{parser.get_format_instructions()}\n"
#         "CRITICAL: OUTPUT STRICTLY VALID JSON ONLY. DO NOT add any conversational text before or after the JSON."
#     )
    
#     payload = {
#         "live_nifty_50_regime": market_regime,
#         "cio_daily_playbook": state.watchlist_config,
#         "live_15m_predictions": enriched_predictions
#     }
    
#     response = llm.invoke([
#         {"role": "system", "content": system_instruction},
#         {"role": "user", "content": json.dumps(payload, indent=2)}
#     ])
    
#     # --- THE REGEX JSON FIX ---
#     raw_text = response.content
#     try:
#         decision = parser.parse(raw_text)
#     except Exception:
#         print("   ⚠️ LLM added conversational text. Extracting JSON via Regex...")
#         try:
#             json_match = re.search(r'\{.*\}', raw_text, re.DOTALL)
#             if json_match:
#                 clean_json = json_match.group(0)
#                 parsed_dict = json.loads(clean_json)
#                 decision = AlertList(**parsed_dict)
#             else:
#                 raise ValueError("No JSON block found in output.")
#         except Exception as e:
#             print(f" ❌ Failed to extract JSON: {e}")
#             return {"error_logs": ["JSON Parse Error"]}
    
#     return {"active_alerts": decision.alerts}

# def print_alerts_node(state: IntradayState):
#     """Node 4: Pushes the alerts to the human."""
#     if state.error_logs or not state.active_alerts:
#         return {}
        
#     print("\n=========================================================")
#     print("🔔 LIVE TRADE ALERTS")
#     print("=========================================================")
#     for alert in state.active_alerts:
#         if "EXECUTE" in alert.action:
#             print(f"🚨 {alert.ticker} | {alert.action} @ ₹{alert.entry_price}")
#             print(f"   🎯 Target (TP): ₹{alert.take_profit}")
#             print(f"   🛡️ Stop Loss (SL): ₹{alert.stop_loss}")
#             print(f"   ⚖️ Sizing: {alert.position_size_advice}")
#             print(f"   💬 {alert.message}\n")
#         else:
#             print(f"⏸️ {alert.ticker} | {alert.action}")
#             print(f"   💬 {alert.message}\n")
            
#     return {}

# def route_alerts_node(state: IntradayState):
#     """Node 5: Pushes the EXECUTE alerts to the FastAPI Database."""
#     if state.error_logs or not state.active_alerts:
#         return {}
        
#     print("\n=========================================================")
#     print("📡 ROUTING TRADE PROPOSALS TO DATABASE")
#     print("=========================================================")
    
#     for alert in state.active_alerts:
#         if "EXECUTE" in alert.action:
#             sizing_match = re.search(r'\d+', alert.position_size_advice)
#             sizing_int = int(sizing_match.group()) if sizing_match else 0
            
#             payload = {
#                 "ticker": alert.ticker,
#                 "action": alert.action,
#                 "entry_price": alert.entry_price,
#                 "take_profit": alert.take_profit,
#                 "stop_loss": alert.stop_loss,
#                 "sizing": sizing_int
#             }
#             try:
#                 response = requests.post("http://127.0.0.1:8000/api/trades/propose", json=payload)
#                 if response.status_code == 200:
#                     print(f"   ✅ Successfully sent {alert.ticker} proposal to API.")
#                 else:
#                     print(f"   ⚠️ API rejected {alert.ticker}: {response.text}")
#             except requests.exceptions.ConnectionError:
#                 print(f"   ❌ FAILED: Is your FastAPI server running?")
#         else:
#             print(f"   ⏸️ {alert.ticker} | Skipped Database")
            
#     return {}

# # ==========================================
# # 2. COMPILE THE STATE GRAPH
# # ==========================================
# workflow = StateGraph(IntradayState)

# workflow.add_node("load_context", load_context_node)
# workflow.add_node("fetch_alpha", fetch_alpha_signals_node)
# workflow.add_node("generate_alerts", generate_alerts_node)
# workflow.add_node("print_alerts", print_alerts_node)
# workflow.add_node("route_alerts", route_alerts_node)

# workflow.set_entry_point("load_context")
# workflow.add_edge("load_context", "fetch_alpha")
# workflow.add_edge("fetch_alpha", "generate_alerts")
# workflow.add_edge("generate_alerts", "print_alerts")
# workflow.add_edge("print_alerts", "route_alerts")
# workflow.add_edge("route_alerts", END)

# copilot_app = workflow.compile()

# if __name__ == "__main__":
#     print("=========================================================")
#     print("⏱️ STARTING INTRADAY COPILOT WORKFLOW (DECOUPLED)")
#     print("=========================================================")
#     try:
#         copilot_app.invoke(IntradayState())
#     except Exception as e:
#         print(f"❌ LangGraph Execution Failed: {e}")

import os
import json
import time
import requests
import re
from datetime import datetime
from typing import Dict, Any
from dotenv import load_dotenv

from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, END
from langchain_aws import ChatBedrock
from langchain_core.output_parsers import PydanticOutputParser
from tvDatafeed import TvDatafeed, Interval

# Database Imports for Alpha Engine Shared Memory
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, JSON
from sqlalchemy.orm import sessionmaker, declarative_base

# Import our custom schemas
from state_schema import IntradayState, TradeAlert

# --- CONFIGURATION ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(BASE_DIR, '.env'))

# --- PORTFOLIO RISK RULES ---
RISK_PER_TRADE = 0.01           # 1% max loss if Stop Loss is hit
MAX_ALLOCATION = 0.20           # Never put more than 20% of total capital into one stock

# --- SHARED MEMORY DATABASE SETUP ---
DB_PASSWORD = os.getenv('DB_PASSWORD', 'root')
DATABASE_URL = f"postgresql://postgres:{DB_PASSWORD}@localhost:5432/converse_db"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class LiveMarketOpportunity(Base):
    """The Shared Memory table populated by alpha_engine.py"""
    __tablename__ = "live_opportunities"
    __table_args__ = {'extend_existing': True} 
    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String, unique=True, index=True)
    direction = Column(String) 
    expected_high_pct = Column(Float) 
    expected_low_pct = Column(Float)  
    uncertainty = Column(Float)
    current_price = Column(Float)
    updated_at = Column(DateTime)

class DailyPlaybookDB(Base):
    """The Shared Memory table populated by cio_graph.py"""
    __tablename__ = "daily_playbook"
    id = Column(Integer, primary_key=True, index=True)
    date = Column(DateTime, default=datetime.utcnow)
    market_regime = Column(String) 
    risk_level = Column(String)    
    approved_sectors = Column(JSON) 
    banned_sectors = Column(JSON)   
    reasoning = Column(String)

class AlertList(BaseModel):
    alerts: list[TradeAlert]

# ==========================================
# 0. HELPER FUNCTIONS
# ==========================================
def get_live_market_regime():
    try:
        tv = TvDatafeed()
        df = tv.get_hist(symbol='NIFTY', exchange='NSE', interval=Interval.in_daily, n_bars=2)
        if df is not None and not df.empty:
            today_open = df['open'].iloc[-1]
            current_price = df['close'].iloc[-1]
            pct_change = ((current_price - today_open) / today_open) * 100
            
            if pct_change > 0.15:
                return f"BULLISH (Nifty is UP {pct_change:.2f}% from open)"
            elif pct_change < -0.15:
                return f"BEARISH (Nifty is DOWN {pct_change:.2f}% from open)"
            else:
                return f"NEUTRAL/CHOPPY (Nifty is flat at {pct_change:.2f}%)"
    except Exception as e:
        print(f" ⚠️ Could not fetch NIFTY regime: {e}")
    return "UNKNOWN"

# ==========================================
# 1. LANGGRAPH NODES
# ==========================================
def load_context_node(state: IntradayState):
    print("\n[Copilot Agent] 📂 Loading Macro Context from Shared Memory...")
    
    db = SessionLocal()
    playbook = db.query(DailyPlaybookDB).order_by(DailyPlaybookDB.id.desc()).first()
    db.close()
    
    if not playbook:
        print("   ❌ No active playbook found. Did the CIO run?")
        return {"error_logs": ["Missing Daily Playbook"]}
        
    print(f"   ✅ Playbook loaded. Regime: {playbook.market_regime}")
    
    playbook_data = {
        "market_regime": playbook.market_regime,
        "risk_level": playbook.risk_level,
        "approved_sectors": playbook.approved_sectors,
        "banned_sectors": playbook.banned_sectors
    }
    
    return {"watchlist_config": playbook_data}

def fetch_alpha_signals_node(state: IntradayState):
    if state.error_logs:
        return {}
        
    print("\n[Copilot Agent] ⚡ Querying Shared Memory for Alpha Engine Setups...")
    
    db = SessionLocal()
    opportunities = db.query(LiveMarketOpportunity).all()
    db.close()
    
    if not opportunities:
        print("   ❌ No live opportunities found in database.")
        return {"error_logs": ["No Alpha Signals"]}
        
    predictions = {}
    for opp in opportunities:
        ticker = opp.ticker
        
        try:
            cd_res = requests.get(f"http://127.0.0.1:8000/api/cooldown/check/{ticker}")
            if cd_res.status_code == 200 and cd_res.json().get("in_cooldown"):
                print(f"   🛑 Skipping {ticker} - Currently in 60-minute Cooldown.")
                continue 
        except requests.exceptions.ConnectionError:
            pass 
            
        # V3 SCHEMA ALIGNMENT: Mapping Dual Boundaries properly
        predictions[ticker] = {
            "direction_signal": opp.direction,
            "expected_high_pct": opp.expected_high_pct,
            "expected_low_pct": opp.expected_low_pct,
            "current_price": opp.current_price,
            "uncertainty": opp.uncertainty
        }
        
    return {"intraday_predictions": predictions}

def generate_alerts_node(state: IntradayState):
    if state.error_logs or not state.intraday_predictions:
        return {}
        
    print("\n[Copilot Agent] 🤖 Calculating Sizing & Requesting Execution Authority...")
    
    try:
        cap_response = requests.get("http://127.0.0.1:8000/api/account/capital")
        total_capital = cap_response.json().get("current_capital", 100000.0) if cap_response.status_code == 200 else 100000.0
    except requests.exceptions.ConnectionError:
        total_capital = 100000.0

    max_risk_amount = total_capital * RISK_PER_TRADE
    max_capital_per_trade = total_capital * MAX_ALLOCATION

    # V3 SIZING MATH: Using actual predicted floors instead of ATR
    enriched_predictions = {}
    for ticker, data in state.intraday_predictions.items():
        price = data.get('current_price', 0)
        direction = data.get('direction_signal')
        exp_high = data.get('expected_high_pct', 0)
        exp_low = data.get('expected_low_pct', 0)
        
        # Risk per share is explicitly derived from the PyTorch predicted floor
        risk_per_share = price * abs(exp_low) 
        
        if risk_per_share > 0 and price > 0:
            risk_based_shares = int(max_risk_amount / risk_per_share)
            projected_cost = risk_based_shares * price
            
            if projected_cost > max_capital_per_trade:
                final_sizing = int(max_capital_per_trade / price)
                cost_reason = f"Capped by {MAX_ALLOCATION*100}% Capital Limit"
            else:
                final_sizing = risk_based_shares
                cost_reason = f"Based on {RISK_PER_TRADE*100}% Risk Limit"
        else:
            final_sizing = 0
            cost_reason = "Invalid risk parameters"
            
        data['suggested_long_sl'] = round(price - risk_per_share, 2)
        data['suggested_long_tp'] = round(price + (price * exp_high), 2)
        data['suggested_short_sl'] = round(price + risk_per_share, 2)
        data['suggested_short_tp'] = round(price - (price * exp_high), 2)
        data['suggested_sizing'] = final_sizing
        data['sizing_logic'] = cost_reason
        enriched_predictions[ticker] = data

    llm = ChatBedrock(
        model_id="meta.llama3-8b-instruct-v1:0",
        model_kwargs={"temperature": 0.1},
        region_name="us-east-1"
    )
    
    parser = PydanticOutputParser(pydantic_object=AlertList)
    market_regime = get_live_market_regime()
    print(f"   📊 Live NIFTY 50 Regime: {market_regime}")
    
    # # V3 PROMPT ALIGNMENT
    # system_instruction = (
    #     "You are an elite quantitative Execution Copilot. You have TRUE AUTONOMY.\n"
    #     "You receive the human CIO's Daily Playbook, the 'direction_signal' (LONG/SHORT) from the Alpha Engine, and the LIVE NIFTY 50 Market Regime.\n\n"
    #     "YOUR PRIME DIRECTIVE:\n"
    #     "Never trade against the broader market. If the Nifty is Bearish, DO NOT take Longs.\n\n"
    #     "EXECUTION LOGIC:\n"
    #     "1. ALIGNED: If Nifty is BEARISH and the direction_signal is 'SHORT' -> 'EXECUTE SHORT'.\n"
    #     "2. ALIGNED: If Nifty is BULLISH and the direction_signal is 'LONG' -> 'EXECUTE LONG'.\n"
    #     "3. CIO VETO: If the CIO Playbook has a 'banned_sector' and the stock belongs to it -> 'HOLD'.\n"
    #     "4. CONFLICT: If there is conflict between the direction_signal and the Regime -> 'HOLD'.\n\n"
    #     "DATA MAPPING (CRITICAL):\n"
    #     "- entry_price: Use 'current_price'.\n"
    #     "- stop_loss & take_profit: If LONG, copy 'suggested_long_sl' and 'suggested_long_tp'. If SHORT, copy 'suggested_short_sl' and 'suggested_short_tp'.\n"
    #     "- position_size_advice: Copy this format -> 'Buy [suggested_sizing] shares ([sizing_logic])'.\n"
    #     "- If HOLD, set all numerical values to 0.0.\n\n"
    #     f"FORMAT REQUIREMENTS:\n{parser.get_format_instructions()}\n"
    #     "CRITICAL: OUTPUT STRICTLY VALID JSON ONLY. DO NOT add any conversational text before or after the JSON."
    # )

    # V3 PROMPT ALIGNMENT
    system_instruction = (
        "You are an elite quantitative Execution Copilot. You have TRUE AUTONOMY.\n"
        "You receive the human CIO's Daily Playbook, the 'direction_signal' (LONG/SHORT) from the Alpha Engine, and the LIVE NIFTY 50 Market Regime.\n\n"
        "YOUR PRIME DIRECTIVE:\n"
        "Never trade against the broader market. If the Nifty is Bearish, DO NOT take Longs.\n\n"
        "EXECUTION LOGIC:\n"
        "1. ALIGNED: If Nifty is BEARISH and the direction_signal is 'SHORT' -> 'EXECUTE SHORT'.\n"
        "2. ALIGNED: If Nifty is BULLISH and the direction_signal is 'LONG' -> 'EXECUTE LONG'.\n"
        "3. DYNAMIC SECTOR RISK: If a stock belongs to a 'banned_sector' but its direction_signal is perfectly aligned with the Nifty Regime, DO NOT issue a HOLD. Instead, approve the execution but explicitly modify the 'position_size_advice' to reduce the pre-calculated shares by 50% to mitigate sector headwinds.\n"
        "4. CONFLICT: If there is conflict between the direction_signal and the Regime -> 'HOLD'.\n\n"
        "DATA MAPPING (CRITICAL):\n"
        "- entry_price: Use 'current_price'.\n"
        "- stop_loss & take_profit: If LONG, copy 'suggested_long_sl' and 'suggested_long_tp'. If SHORT, copy 'suggested_short_sl' and 'suggested_short_tp'.\n"
        "- position_size_advice: Copy this format -> 'Buy [suggested_sizing] shares ([sizing_logic])'. Ensure you halve the suggested_sizing integer if Rule 3 was triggered.\n"
        "- If HOLD, set all numerical values to 0.0.\n\n"
        f"FORMAT REQUIREMENTS:\n{parser.get_format_instructions()}\n"
        "CRITICAL: OUTPUT STRICTLY VALID JSON ONLY. DO NOT add any conversational text before or after the JSON."
    )
    
    payload = {
        "live_nifty_50_regime": market_regime,
        "cio_daily_playbook": state.watchlist_config,
        "alpha_engine_setups": enriched_predictions
    }
    
    response = llm.invoke([
        {"role": "system", "content": system_instruction},
        {"role": "user", "content": json.dumps(payload, indent=2)}
    ])
    
    # raw_text = response.content
    # try:
    #     decision = parser.parse(raw_text)
    # except Exception:
    #     print("   ⚠️ LLM added conversational text. Extracting JSON via Regex...")
    #     try:
    #         json_match = re.search(r'\{.*\}', raw_text, re.DOTALL)
    #         if json_match:
    #             clean_json = json_match.group(0)
    #             parsed_dict = json.loads(clean_json)
    #             decision = AlertList(**parsed_dict)
    #         else:
    #             raise ValueError("No JSON block found in output.")
    #     except Exception as e:
    #         print(f" ❌ Failed to extract JSON: {e}")
    #         return {"error_logs": ["JSON Parse Error"]}
    
    # return {"active_alerts": decision.alerts}

    # --- UPGRADED BULLETPROOF JSON EXTRACTOR ---
    # raw_text = response.content
    # try:
    #     # First, try a clean direct parse
    #     decision = parser.parse(raw_text)
    # except Exception:
    #     print("   ⚠️ LLM included conversational framing or markdown. Stripping wrapper tags...")
    #     try:
    #         # Isolate the exact object boundary by finding the absolute first '{' and last '}'
    #         start_idx = raw_text.find('{')
    #         end_idx = raw_text.rfind('}')
            
    #         if start_idx != -1 and end_idx != -1:
    #             clean_json = raw_text[start_idx:end_idx + 1]
    #             parsed_dict = json.loads(clean_json)
    #             decision = AlertList(**parsed_dict)
    #         else:
    #             raise ValueError("No valid JSON brackets located in the model string payload.")
    #     except Exception as e:
    #         print(f" ❌ Failed to extract JSON block: {e}")
    #         print(f" Raw Text Output was: {raw_text}")
    #         return {"error_logs": ["JSON Parse Error"]}
    
    # return {"active_alerts": decision.alerts}

    # --- UPGRADED ARRAY-AWARE JSON EXTRACTOR ---
    raw_text = response.content.strip()
    decision = None
    
    try:
        # Step 1: Try the clean standard Pydantic parse
        decision = parser.parse(raw_text)
    except Exception:
        print("   ⚠️ LLM layout mismatch. Executing deep structural breakdown...")
        try:
            # Step 2: Clean out any markdown wrapper clutter if present
            if "```json" in raw_text:
                raw_text = raw_text.split("```json")[1].split("```")[0].strip()
            elif "```" in raw_text:
                raw_text = raw_text.split("```")[1].split("```")[0].strip()
                
            # Find boundaries of the outermost JSON structural container
            first_bracket = raw_text.find('[')
            first_brace = raw_text.find('{')
            
            # CASE A: The LLM returned a raw array/list [...]
            if first_bracket != -1 and (first_brace == -1 or first_bracket < first_brace):
                end_bracket = raw_text.rfind(']')
                clean_json = raw_text[first_bracket:end_bracket + 1]
                parsed_list = json.loads(clean_json)
                
                # Automatically wrap the raw array into the dictionary structure expected by AlertList
                decision = AlertList(alerts=parsed_list)
                print("   ✅ Successfully intercepted and wrapped raw JSON array structure.")
                
            # CASE B: The LLM returned a standard wrapped dictionary object {...}
            elif first_brace != -1:
                end_brace = raw_text.rfind('}')
                clean_json = raw_text[first_brace:end_brace + 1]
                parsed_dict = json.loads(clean_json)
                
                # Check if it's already got the root key or needs to be wrapped
                if "alerts" in parsed_dict:
                    decision = AlertList(**parsed_dict)
                else:
                    decision = AlertList(alerts=[parsed_dict])
                print("   ✅ Successfully extracted standard JSON object structure.")
            else:
                raise ValueError("No valid structural JSON elements found in string output.")
                
        except Exception as e:
            print(f" ❌ Critical JSON Restructuring Failure: {e}")
            print(f" Raw Text Output was:\n{response.content}")
            return {"error_logs": ["JSON Parse Error"]}
            
    return {"active_alerts": decision.alerts}

def print_alerts_node(state: IntradayState):
    if state.error_logs or not state.active_alerts:
        return {}
        
    print("\n=========================================================")
    print("🔔 LIVE TRADE ALERTS")
    print("=========================================================")
    for alert in state.active_alerts:
        if "EXECUTE" in alert.action:
            print(f"🚨 {alert.ticker} | {alert.action} @ ₹{alert.entry_price}")
            print(f"   🎯 Target (TP): ₹{alert.take_profit}")
            print(f"   🛡️ Stop Loss (SL): ₹{alert.stop_loss}")
            print(f"   ⚖️ Sizing: {alert.position_size_advice}")
            print(f"   💬 {alert.message}\n")
        else:
            print(f"⏸️ {alert.ticker} | {alert.action}")
            print(f"   💬 {alert.message}\n")
            
    return {}

def route_alerts_node(state: IntradayState):
    if state.error_logs or not state.active_alerts:
        return {}
        
    print("\n=========================================================")
    print("📡 ROUTING TRADE PROPOSALS TO DATABASE")
    print("=========================================================")
    
    for alert in state.active_alerts:
        if "EXECUTE" in alert.action:
            sizing_match = re.search(r'\d+', alert.position_size_advice)
            sizing_int = int(sizing_match.group()) if sizing_match else 0
            
            payload = {
                "ticker": alert.ticker,
                "action": alert.action,
                "entry_price": alert.entry_price,
                "take_profit": alert.take_profit,
                "stop_loss": alert.stop_loss,
                "sizing": sizing_int
            }
            try:
                response = requests.post("http://127.0.0.1:8000/api/trades/propose", json=payload)
                if response.status_code == 200:
                    print(f"   ✅ Successfully sent {alert.ticker} proposal to API.")
                else:
                    print(f"   ⚠️ API rejected {alert.ticker}: {response.text}")
            except requests.exceptions.ConnectionError:
                print(f"   ❌ FAILED: Is your FastAPI server running?")
        else:
            print(f"   ⏸️ {alert.ticker} | Skipped Database")
            
    return {}

# ==========================================
# 2. COMPILE THE STATE GRAPH
# ==========================================
workflow = StateGraph(IntradayState)

workflow.add_node("load_context", load_context_node)
workflow.add_node("fetch_alpha", fetch_alpha_signals_node)
workflow.add_node("generate_alerts", generate_alerts_node)
workflow.add_node("print_alerts", print_alerts_node)
workflow.add_node("route_alerts", route_alerts_node)

workflow.set_entry_point("load_context")
workflow.add_edge("load_context", "fetch_alpha")
workflow.add_edge("fetch_alpha", "generate_alerts")
workflow.add_edge("generate_alerts", "print_alerts")
workflow.add_edge("print_alerts", "route_alerts")
workflow.add_edge("route_alerts", END)

copilot_app = workflow.compile()

if __name__ == "__main__":
    print("=========================================================")
    print("⏱️ STARTING INTRADAY COPILOT WORKFLOW (V3 DUAL-BOUNDARY)")
    print("=========================================================")
    try:
        copilot_app.invoke(IntradayState())
    except Exception as e:
        print(f"❌ LangGraph Execution Failed: {e}")