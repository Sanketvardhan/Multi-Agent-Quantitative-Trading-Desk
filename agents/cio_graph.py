import os
import json
import time
from typing import Dict, Any
from dotenv import load_dotenv

# LangChain & LangGraph Imports
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, END

# Import our custom schemas and tools
from state_schema import CIOState, WatchlistSelection
from tools.model_tools import tool_get_swing_prediction, tool_get_stock_news

# --- Configuration ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(BASE_DIR, '.env'))

# ==========================================
# 1. LANGGRAPH NODES
# ==========================================
def run_full_market_sweep_node(state: CIOState):
    """Node 1: Sweeps the market, fetching BOTH Deep Learning Math and Sentiment News."""
    print("\n[CIO Agent] 🌍 Initiating Full Market Sweep (Math + Sentiment)...")
    
    market_data = {}
    
    for ticker in state.target_tickers:
        print(f"\n -> Analyzing {ticker}...")
        
        # 1. Get the Math
        try:
            quant_result = tool_get_swing_prediction.invoke({"ticker": ticker})
        except Exception as e:
            quant_result = {"status": "error", "message": str(e)}
            
        # 2. Get the News
        try:
            news_result = tool_get_stock_news.invoke({"ticker": ticker})
        except Exception as e:
            news_result = {"status": "error", "message": str(e)}
            
        # 3. Combine them only if the math succeeded
        if quant_result.get("status") == "success":
            market_data[ticker] = {
                "expected_return": quant_result.get("expected_return"),
                "uncertainty": quant_result.get("uncertainty"),
                "headlines": news_result.get("headlines", [])
            }
            print(f"    ✅ Math & News compiled successfully.")
        else:
            print(f"    ❌ Skipping {ticker} - Quant Engine Failed: {quant_result.get('message')}")
            
        # PACING: Wait 3 seconds so Yahoo doesn't rate limit us
        time.sleep(3)
            
    # We repurpose the 'swing_predictions' state variable to hold this combined data
    return {"swing_predictions": market_data}

def generate_decisions_node(state: CIOState):
    """Node 2: Gemini looks at the ENTIRE market and picks the absolute best 4."""
    print("\n[CIO Agent] 🤖 Waking up Gemini CIO to pick top stocks...")
    
    if not state.swing_predictions:
        print("❌ No valid market data generated. Aborting CIO decision.")
        return {"error_logs": ["No valid market data generated."]}

    # --- THE TIE-BREAKER FIX ---
    # Sort stocks by the absolute magnitude of the Expected Return
    # This forces Gemini to read the biggest predicted moves first!
    sorted_predictions = dict(sorted(
        state.swing_predictions.items(),
        key=lambda item: abs(item[1].get("expected_return", 0)),
        reverse=True
    ))

    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash-lite",
        google_api_key=os.getenv("GOOGLE_API_KEY"),
        temperature=0.0
    )
    
    structured_llm = llm.with_structured_output(WatchlistSelection)
    
    system_instruction = (
        "You are the Chief Investment Officer of an elite quantitative hedge fund.\n"
        "You are receiving a full market sweep containing deep-learning expected returns, MC Dropout uncertainty, and the latest news headlines.\n\n"
        "YOUR JOB:\n"
        "Review the entire list and select the ABSOLUTE BEST stocks for today's watchlist (Maximum 4).\n\n"
        "SELECTION RULES:\n"
        "1. QUANT EDGE: The absolute value of the expected return MUST be significantly larger than the uncertainty.\n"
        "2. SENTIMENT VETO: If a stock has a great quant edge, but the news headlines indicate a catastrophic fundamental event (e.g., CEO fired, massive lawsuit, factory fire), DO NOT select it.\n"
        "3. ALIGNMENT: 'SHORT' for negative expected returns, 'LONG' for positive.\n"
        "4. CONFIDENCE TIER: Calculate 'HIGH', 'MEDIUM', or 'LOW' strictly based on how much larger the return is than the uncertainty.\n"
        "5. REASONING: Your 1-sentence reasoning must cite BOTH the quant edge (the numbers) AND confirm that the news sentiment aligns (or is neutral)."
    )
    
    # Feed the entire sorted dictionary to Gemini
    user_payload = f"Full Market Data Sweep:\n{json.dumps(sorted_predictions, indent=2)}"
    
    decision = structured_llm.invoke([
        {"role": "system", "content": system_instruction},
        {"role": "user", "content": user_payload}
    ])
    
    return {"structured_decision": decision}

def export_configuration_node(state: CIOState):
    """Node 3: Formats and saves the top picks for the Intraday Copilot."""
    if not state.structured_decision:
        return {}
        
    print("\n[CIO Agent] 💾 Exporting Final Watchlist Configuration...")
    
    watchlist_config = {}
    for item in state.structured_decision.selections:
        print(f"\n📈 TARGET: {item.ticker} | 🛠️ STRATEGY: {item.directive} | 🛡️ CONFIDENCE: {item.confidence_tier}")
        print(f"   THESIS: {item.reasoning}")
        
        watchlist_config[item.ticker] = {
            "directive": item.directive,
            "confidence_tier": item.confidence_tier,
            "reasoning": item.reasoning
        }
        
    watchlist_path = os.path.join(BASE_DIR, 'active_watchlist.json')
    with open(watchlist_path, 'w') as f:
        json.dump(watchlist_config, f, indent=2)
        
    print(f"\n✅ Full Market CIO execution complete. Saved to: {watchlist_path}")
    return {}

# ==========================================
# 2. COMPILE THE STATE GRAPH
# ==========================================
workflow = StateGraph(CIOState)

workflow.add_node("scan_market", run_full_market_sweep_node)
workflow.add_node("make_decisions", generate_decisions_node)
workflow.add_node("export", export_configuration_node)

workflow.set_entry_point("scan_market")
workflow.add_edge("scan_market", "make_decisions")
workflow.add_edge("make_decisions", "export")
workflow.add_edge("export", END)

cio_app = workflow.compile()

# ==========================================
# 3. TEST EXECUTION
# ==========================================
if __name__ == "__main__":
    print("=========================================================")
    print("🌅 STARTING PRE-MARKET CIO AGENT WORKFLOW (MATH + NEWS)")
    print("=========================================================")
    
    # We test with 4 specific stocks. Expand this to the full Nifty 50 when ready!
    initial_state = CIOState(target_tickers=['RELIANCE', 'TCS', 'HDFCBANK', 'INFY'])
    
    try:
        cio_app.invoke(initial_state)
    except Exception as e:
        print(f"❌ LangGraph Execution Failed: {e}")