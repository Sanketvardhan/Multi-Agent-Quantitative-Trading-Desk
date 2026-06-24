import os
import json
import time
from typing import Dict, Any
from dotenv import load_dotenv

from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, END
from pydantic import BaseModel, Field

from langchain_aws import ChatBedrock

from langchain_core.output_parsers import PydanticOutputParser

# Import our custom schemas and tools
from state_schema import IntradayState, TradeAlert
from tools.model_tools import tool_get_intraday_prediction

import requests
import re

# --- PORTFOLIO RISK RULES ---
# TOTAL_CAPITAL = 10000.0        # E.g., ₹1 Lakh total account size
RISK_PER_TRADE = 0.01           # 1% max loss if Stop Loss is hit (₹1000)
MAX_ALLOCATION = 0.20           # Never put more than 20% of total capital into one stock (₹20,000)

# --- FETCH LIVE CAPITAL FROM DATABASE/API ---
try:
    cap_response = requests.get("http://127.0.0.1:8000/api/account/capital")
    if cap_response.status_code == 200:
        total_capital = cap_response.json().get("current_capital", 10000.0)
    else:
        total_capital = 10000.0
except requests.exceptions.ConnectionError:
    print("   ⚠️ Could not reach API for capital. Defaulting to ₹10000.0")
    total_capital = 10000.0

# --- Configuration ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(BASE_DIR, '.env'))

# We need a wrapper Pydantic class for Gemini to return a list of alerts
class AlertList(BaseModel):
    alerts: list[TradeAlert]

# ==========================================
# 1. LANGGRAPH NODES
# ==========================================
def load_watchlist_node(state: IntradayState):
    """Node 1: Reads the CIO's daily instructions."""
    print("\n[Copilot Agent] 📂 Loading CIO Watchlist...")
    watchlist_path = os.path.join(BASE_DIR, 'active_watchlist.json')
    
    if not os.path.exists(watchlist_path):
        print("   ❌ No active watchlist found. Copilot going back to sleep.")
        return {"error_logs": ["Missing active_watchlist.json"]}
        
    with open(watchlist_path, 'r') as f:
        watchlist = json.load(f)
        
    print(f"   ✅ Watchlist loaded. Tracking {len(watchlist)} stocks.")
    return {"watchlist_config": watchlist}

def scan_intraday_node(state: IntradayState):
    """Node 2: Runs the 15-minute PyTorch model on the tracked stocks."""
    if state.error_logs:
        return {} # Skip if watchlist failed
        
    print("\n[Copilot Agent] ⚡ Scanning 15-minute order flow...")
    predictions = {}
    
    for ticker in state.watchlist_config.keys():
        print(f" -> Checking intraday momentum for {ticker}...")
        try:
            result = tool_get_intraday_prediction.invoke({"ticker": ticker})
            if result.get("status") == "success":
                predictions[ticker] = result
            else:
                print(f"    ❌ Error: {result.get('message')}")
        except Exception as e:
            print(f"    ❌ Tool failure: {e}")
            
        time.sleep(3) # Pacing to avoid Yahoo Rate Limits
            
    return {"intraday_predictions": predictions}

# def generate_alerts_node(state: IntradayState):
#     """Node 3: Gemini decides whether to pull the trigger."""
#     if state.error_logs or not state.intraday_predictions:
#         return {}
        
#     print("\n[Copilot Agent] 🤖 Analyzing Execution Triggers...")
    
#     llm = ChatGoogleGenerativeAI(
#         model="gemini-2.5-flash-lite",
#         google_api_key=os.getenv("GOOGLE_API_KEY"),
#         temperature=0.0
#     )
    
#     structured_llm = llm.with_structured_output(AlertList)
    
#     # system_instruction = (
#     #     "You are an algorithmic execution Copilot. Your job is to trigger trades.\n"
#     #     "You will receive a list of stocks with their CIO 'Daily Directive' (LONG or SHORT) and their live 15-minute Expected Return.\n\n"
#     #     "EXECUTION LOGIC:\n"
#     #     "1. If Daily Directive is SHORT and 15m Return is NEGATIVE -> Action: 'EXECUTE SHORT'\n"
#     #     "2. If Daily Directive is LONG and 15m Return is POSITIVE -> Action: 'EXECUTE LONG'\n"
#     #     "3. If they conflict (e.g., Daily is SHORT but 15m Return is POSITIVE) -> Action: 'HOLD' (Wait for better entry)\n\n"
#     #     "Provide a short, punchy message for each ticker explaining the action.\n"
#     #     "For the entry_price field, strictly input the absolute value of the live 15m Expected Return provided in the data."
#     # )
#     system_instruction = (
#         "You are an algorithmic execution Copilot for a human trader.\n"
#         "You receive the daily CIO bias, the live 15m expected return, the current_price, and the current_atr (Average True Range).\n\n"
#         "EXECUTION LOGIC:\n"
#         "1. If Daily is SHORT and 15m is NEGATIVE -> 'EXECUTE SHORT'\n"
#         "2. If Daily is LONG and 15m is POSITIVE -> 'EXECUTE LONG'\n"
#         "3. If they conflict -> 'HOLD'\n\n"
#         "RISK MANAGEMENT MATH (For EXECUTE actions only):\n"
#         "- Stop Loss (SL): Use 1.5x the ATR. (e.g., For a LONG: SL = current_price - (1.5 * current_atr)).\n"
#         "- Take Profit (TP): Target a 1:2 Risk/Reward. (e.g., For a LONG: TP = current_price + (3.0 * current_atr)).\n"
#         "- Position Size Advice: Calculate how many shares the human can buy if they only want to risk losing exactly ₹1000. "
#         "(Formula: 1000 / absolute difference between entry_price and stop_loss). Round to nearest whole share.\n\n"
#         "If the action is HOLD, set all numerical values to 0.0 and leave a short message explaining why."
#     )
    
#     payload = {
#         "cio_daily_bias": state.watchlist_config,
#         "live_15m_predictions": state.intraday_predictions
#     }
    
#     decision = structured_llm.invoke([
#         {"role": "system", "content": system_instruction},
#         {"role": "user", "content": json.dumps(payload, indent=2)}
#     ])
    
#     return {"active_alerts": decision.alerts}

def generate_alerts_node(state: IntradayState):
    """Node 3: Gemini decides whether to pull the trigger."""
    if state.error_logs or not state.intraday_predictions:
        return {}
        
    print("\n[Copilot Agent] 🤖 Analyzing Execution Triggers & Calculating Risk...")
    
    # # --- THE FIX: PYTHON HANDLES THE MATH ---
    # enriched_predictions = {}
    # for ticker, data in state.intraday_predictions.items():
    #     price = data.get('current_price', 0)
    #     atr = data.get('current_atr', 0)
        
    #     # Calculate strict risk metrics (1.5x ATR for SL, 3.0x ATR for TP)
    #     risk_per_share = 1.5 * atr
    #     sizing = int(1000 / risk_per_share) if risk_per_share > 0 else 0
        
    #     data['suggested_long_sl'] = round(price - risk_per_share, 2)
    #     data['suggested_long_tp'] = round(price + (3.0 * atr), 2)
        
    #     data['suggested_short_sl'] = round(price + risk_per_share, 2)
    #     data['suggested_short_tp'] = round(price - (3.0 * atr), 2)
        
    #     data['suggested_sizing'] = sizing
    #     enriched_predictions[ticker] = data

    # --- THE FIX: DYNAMIC PORTFOLIO MATH ---
    # max_risk_amount = TOTAL_CAPITAL * RISK_PER_TRADE          # e.g., ₹1000
    # max_capital_per_trade = TOTAL_CAPITAL * MAX_ALLOCATION    # e.g., ₹20,000

    # --- THE FIX: DYNAMIC PORTFOLIO MATH ---
    max_risk_amount = total_capital * RISK_PER_TRADE
    max_capital_per_trade = total_capital * MAX_ALLOCATION

    enriched_predictions = {}
    for ticker, data in state.intraday_predictions.items():
        price = data.get('current_price', 0)
        atr = data.get('current_atr', 0)
        
        # 1. Calculate Standard Risk Metrics
        risk_per_share = 1.5 * atr
        
        if risk_per_share > 0 and price > 0:
            # Step A: How many shares can we buy before we hit our ₹1000 Max Loss?
            risk_based_shares = int(max_risk_amount / risk_per_share)
            
            # Step B: How much would buying those shares actually cost?
            projected_cost = risk_based_shares * price
            
            # Step C: The Allocation Cap (The Guardian)
            if projected_cost > max_capital_per_trade:
                # If it costs too much, we ignore the risk rule and cap the shares by our maximum allowed capital
                final_sizing = int(max_capital_per_trade / price)
                cost_reason = f"Capped by {MAX_ALLOCATION*100}% Capital Limit"
            else:
                final_sizing = risk_based_shares
                cost_reason = f"Based on {RISK_PER_TRADE*100}% Risk Limit"
        else:
            final_sizing = 0
            cost_reason = "Invalid data"
            
        data['suggested_long_sl'] = round(price - risk_per_share, 2)
        data['suggested_long_tp'] = round(price + (3.0 * atr), 2)
        
        data['suggested_short_sl'] = round(price + risk_per_share, 2)
        data['suggested_short_tp'] = round(price - (3.0 * atr), 2)
        
        data['suggested_sizing'] = final_sizing
        data['sizing_logic'] = cost_reason
        enriched_predictions[ticker] = data

    # llm = ChatGoogleGenerativeAI(
    #     model="gemini-2.5-flash-lite",
    #     google_api_key=os.getenv("GOOGLE_API_KEY"),
    #     temperature=0.0
    # )

    # llm = ChatBedrock(
    #     model_id="meta.llama3-8b-instruct-v1:0",
    #     model_kwargs={"temperature": 0.2},
    #     region_name="us-east-1" # <-- Change this to your specific AWS region if different
    # )
    
    # structured_llm = llm.with_structured_output(AlertList)
    
    # system_instruction = (
    #     "You are an algorithmic execution Copilot. Your job is to trigger trades.\n"
    #     "You will receive the CIO bias, the live 15m expected return, and pre-calculated Risk Management metrics.\n\n"
    #     "EXECUTION LOGIC:\n"
    #     "1. If Daily Directive is SHORT and 15m Return is NEGATIVE -> Action: 'EXECUTE SHORT'\n"
    #     "2. If Daily Directive is LONG and 15m Return is POSITIVE -> Action: 'EXECUTE LONG'\n"
    #     "3. If they conflict -> Action: 'HOLD'\n\n"
    #     "DATA MAPPING (CRITICAL):\n"
    #     "- entry_price: Use 'current_price'.\n"
    #     "- stop_loss & take_profit: If LONG, strictly copy 'suggested_long_sl' and 'suggested_long_tp'. If SHORT, strictly copy 'suggested_short_sl' and 'suggested_short_tp'.\n"
    #     # "- position_size_advice: Strictly output 'Buy [suggested_sizing] shares to risk ₹1000'.\n"
    #     "- position_size_advice: Strictly copy this format -> 'Buy [suggested_sizing] shares ([sizing_logic])'.\n"
    #     "- If HOLD, set all numerical values to 0.0."
    # )
    
    # payload = {
    #     "cio_daily_bias": state.watchlist_config,
    #     "live_15m_predictions": enriched_predictions
    # }
    
    # decision = structured_llm.invoke([
    #     {"role": "system", "content": system_instruction},
    #     {"role": "user", "content": json.dumps(payload, indent=2)}
    # ])
    
    # return {"active_alerts": decision.alerts}

    llm = ChatBedrock(
        model_id="meta.llama3-8b-instruct-v1:0",
        model_kwargs={"temperature": 0.2},
        region_name="us-east-1"
    )
    
    # --- THE FIX: Explicitly parse the output ---
    parser = PydanticOutputParser(pydantic_object=AlertList)
    
    system_instruction = (
        "You are an algorithmic execution Copilot. Your job is to trigger trades.\n"
        "You will receive the CIO bias, the live 15m expected return, and pre-calculated Risk Management metrics.\n\n"
        "EXECUTION LOGIC:\n"
        "1. If Daily Directive is SHORT and 15m Return is NEGATIVE -> Action: 'EXECUTE SHORT'\n"
        "2. If Daily Directive is LONG and 15m Return is POSITIVE -> Action: 'EXECUTE LONG'\n"
        "3. If they conflict -> Action: 'HOLD'\n\n"
        "DATA MAPPING (CRITICAL):\n"
        "- entry_price: Use 'current_price'.\n"
        "- stop_loss & take_profit: If LONG, strictly copy 'suggested_long_sl' and 'suggested_long_tp'. If SHORT, strictly copy 'suggested_short_sl' and 'suggested_short_tp'.\n"
        "- position_size_advice: Strictly copy this format -> 'Buy [suggested_sizing] shares ([sizing_logic])'.\n"
        "- If HOLD, set all numerical values to 0.0.\n\n"
        # Inject the JSON schema instructions dynamically
        f"FORMAT REQUIREMENTS:\n{parser.get_format_instructions()}\n"
        "OUTPUT STRICTLY VALID JSON. DO NOT output any introductory text, markdown blocks, or explanations outside the JSON."
    )
    
    payload = {
        "cio_daily_bias": state.watchlist_config,
        "live_15m_predictions": enriched_predictions
    }
    
    # 1. Call the model normally (using llm instead of structured_llm)
    response = llm.invoke([
        {"role": "system", "content": system_instruction},
        {"role": "user", "content": json.dumps(payload, indent=2)}
    ])
    
    # 2. Parse the raw text back into your AlertList Pydantic object
    try:
        decision = parser.parse(response.content)
    except Exception as e:
        print(f" ❌ Failed to parse Llama 3 JSON: {e}")
        print(f" Raw Output: {response.content}")
        return {"error_logs": ["JSON Parse Error"]}
    
    return {"active_alerts": decision.alerts}

# def print_alerts_node(state: IntradayState):
#     """Node 4: Pushes the alerts to the human."""
#     if state.error_logs or not state.active_alerts:
#         return {}
        
#     print("\n=========================================================")
#     print("🔔 LIVE TRADE ALERTS")
#     print("=========================================================")
#     for alert in state.active_alerts:
#         if "EXECUTE" in alert.action:
#             print(f"🚨 {alert.ticker} | {alert.action} | Expected Move: {alert.entry_price}")
#             print(f"   💬 {alert.message}\n")
#         else:
#             print(f"⏸️ {alert.ticker} | {alert.action}")
#             print(f"   💬 {alert.message}\n")
            
    # return {}

def print_alerts_node(state: IntradayState):
    """Node 4: Pushes the alerts to the human."""
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
    """Node 4: Pushes the EXECUTE alerts to the FastAPI Database."""
    if state.error_logs or not state.active_alerts:
        return {}
        
    print("\n=========================================================")
    print("📡 ROUTING TRADE PROPOSALS TO DATABASE")
    print("=========================================================")
    
    for alert in state.active_alerts:
        if "EXECUTE" in alert.action:
            # Extract just the integer from the sizing string (e.g., "Buy 15 shares..." -> 15)
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
                # Send the POST request to your FastAPI server
                response = requests.post("http://127.0.0.1:8000/api/trades/propose", json=payload)
                
                if response.status_code == 200:
                    print(f"   ✅ Successfully sent {alert.ticker} proposal to API.")
                else:
                    print(f"   ⚠️ API rejected {alert.ticker}: {response.text}")
                    
            except requests.exceptions.ConnectionError:
                print(f"   ❌ FAILED: Is your FastAPI server running? Could not connect.")
                
        else:
            print(f"   ⏸️ {alert.ticker} | {alert.action} -> Skipped Database")
            
    return {}

# ==========================================
# 2. COMPILE THE STATE GRAPH
# ==========================================
workflow = StateGraph(IntradayState)

workflow.add_node("load_watchlist", load_watchlist_node)
workflow.add_node("scan_intraday", scan_intraday_node)
workflow.add_node("generate_alerts", generate_alerts_node)
workflow.add_node("print_alerts", print_alerts_node)
workflow.add_node("route_alerts", route_alerts_node)

workflow.set_entry_point("load_watchlist")
workflow.add_edge("load_watchlist", "scan_intraday")
workflow.add_edge("scan_intraday", "generate_alerts")
workflow.add_edge("generate_alerts", "print_alerts")
workflow.add_edge("print_alerts", "route_alerts")
workflow.add_edge("route_alerts", END)

copilot_app = workflow.compile()

# ==========================================
# 3. TEST EXECUTION
# ==========================================
if __name__ == "__main__":
    print("=========================================================")
    print("⏱️ STARTING INTRADAY COPILOT WORKFLOW")
    print("=========================================================")
    initial_state = IntradayState()
    try:
        copilot_app.invoke(initial_state)
    except Exception as e:
        print(f"❌ LangGraph Execution Failed: {e}")