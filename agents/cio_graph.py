# import os
# import json
# import time
# from typing import Dict, Any
# from dotenv import load_dotenv

# # LangChain & LangGraph Imports
# from langchain_google_genai import ChatGoogleGenerativeAI
# from langgraph.graph import StateGraph, END

# # AWS LangChain & LangGraph 
# from langchain_aws import ChatBedrock

# from langchain_core.output_parsers import PydanticOutputParser

# # Import our custom schemas and tools
# from state_schema import CIOState, WatchlistSelection
# from tools.model_tools import tool_get_swing_prediction, tool_get_stock_news

# # --- Configuration ---
# BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# load_dotenv(os.path.join(BASE_DIR, '.env'))

# # ==========================================
# # 1. LANGGRAPH NODES
# # ==========================================
# def run_full_market_sweep_node(state: CIOState):
#     """Node 1: Sweeps the market, fetching BOTH Deep Learning Math and Sentiment News."""
#     print("\n[CIO Agent] 🌍 Initiating Full Market Sweep (Math + Sentiment)...")
    
#     market_data = {}
    
#     for ticker in state.target_tickers:
#         print(f"\n -> Analyzing {ticker}...")
        
#         # 1. Get the Math
#         try:
#             quant_result = tool_get_swing_prediction.invoke({"ticker": ticker})
#         except Exception as e:
#             quant_result = {"status": "error", "message": str(e)}
            
#         # 2. Get the News
#         try:
#             news_result = tool_get_stock_news.invoke({"ticker": ticker})
#         except Exception as e:
#             news_result = {"status": "error", "message": str(e)}
            
#         # 3. Combine them only if the math succeeded
#         if quant_result.get("status") == "success":
#             market_data[ticker] = {
#                 "expected_return": quant_result.get("expected_return"),
#                 "uncertainty": quant_result.get("uncertainty"),
#                 "headlines": news_result.get("headlines", [])
#             }
#             print(f"    ✅ Math & News compiled successfully.")
#         else:
#             print(f"    ❌ Skipping {ticker} - Quant Engine Failed: {quant_result.get('message')}")
            
#         # PACING: Wait 3 seconds so Yahoo doesn't rate limit us
#         time.sleep(3)
            
#     # We repurpose the 'swing_predictions' state variable to hold this combined data
#     return {"swing_predictions": market_data}

# def generate_decisions_node(state: CIOState):
#     """Node 2: Gemini looks at the ENTIRE market and picks the absolute best 4."""
#     print("\n[CIO Agent] 🤖 Waking up Gemini CIO to pick top stocks...")
    
#     if not state.swing_predictions:
#         print("❌ No valid market data generated. Aborting CIO decision.")
#         return {"error_logs": ["No valid market data generated."]}

#     # --- THE TIE-BREAKER FIX ---
#     # Sort stocks by the absolute magnitude of the Expected Return
#     # This forces Gemini to read the biggest predicted moves first!
#     sorted_predictions = dict(sorted(
#         state.swing_predictions.items(),
#         key=lambda item: abs(item[1].get("expected_return", 0)),
#         reverse=True
#     ))

#     # llm = ChatGoogleGenerativeAI(
#     #     model="gemini-2.5-flash-lite",
#     #     google_api_key=os.getenv("GOOGLE_API_KEY"),
#     #     temperature=0.0
#     # )
 
#     llm = ChatBedrock(
#         # model_id="us.anthropic.claude-sonnet-4-5-20250929-v1:0",
#         model_id="meta.llama3-70b-instruct-v1:0",
#         model_kwargs={"temperature": 0.2},
#         region_name="us-east-1" # <-- Change this to your specific AWS region if different
#     )
    
#     # structured_llm = llm.with_structured_output(WatchlistSelection)
#     parser = PydanticOutputParser(pydantic_object=WatchlistSelection)
    
#     system_instruction = (
#         "You are the Chief Investment Officer of an elite quantitative hedge fund.\n"
#         "You are receiving a full market sweep containing deep-learning expected returns, MC Dropout uncertainty, and the latest news headlines.\n\n"
#         "YOUR JOB:\n"
#         "Review the entire list and select the ABSOLUTE BEST stocks for today's watchlist (Maximum 4).\n\n"
#         "SELECTION RULES:\n"
#         "1. QUANT EDGE: The absolute value of the expected return MUST be significantly larger than the uncertainty.\n"
#         "2. SENTIMENT VETO: If a stock has a great quant edge, but the news headlines indicate a catastrophic fundamental event (e.g., CEO fired, massive lawsuit, factory fire), DO NOT select it.\n"
#         "3. ALIGNMENT: 'SHORT' for negative expected returns, 'LONG' for positive.\n"
#         "4. CONFIDENCE TIER: Calculate 'HIGH', 'MEDIUM', or 'LOW' strictly based on how much larger the return is than the uncertainty.\n"
#         "5. REASONING: Your 1-sentence reasoning must cite BOTH the quant edge (the numbers) AND confirm that the news sentiment aligns (or is neutral)."
#         f"FORMAT REQUIREMENTS:\n{parser.get_format_instructions()}\n"
#         "OUTPUT STRICTLY VALID JSON ONLY. DO NOT output any introductory text or markdown blocks."
#     )
    
#     # Feed the entire sorted dictionary to Gemini
#     user_payload = f"Full Market Data Sweep:\n{json.dumps(sorted_predictions, indent=2)}"
    
#     # decision = structured_llm.invoke([
#     #     {"role": "system", "content": system_instruction},
#     #     {"role": "user", "content": user_payload}
#     # ])

#     response = llm.invoke([
#         {"role": "system", "content": system_instruction},
#         {"role": "user", "content": user_payload}
#     ])
    
#     # 2. Parse the raw text back into your WatchlistSelection Pydantic object
#     try:
#         decision = parser.parse(response.content)
#     except Exception as e:
#         print(f" ❌ Failed to parse Llama 3 JSON: {e}")
#         print(f" Raw Output: {response.content}")
#         return {"error_logs": ["JSON Parse Error"]}
    
#     return {"structured_decision": decision}

# def export_configuration_node(state: CIOState):
#     """Node 3: Formats and saves the top picks for the Intraday Copilot."""
#     if not state.structured_decision:
#         return {}
        
#     print("\n[CIO Agent] 💾 Exporting Final Watchlist Configuration...")
    
#     watchlist_config = {}
#     for item in state.structured_decision.selections:
#         print(f"\n📈 TARGET: {item.ticker} | 🛠️ STRATEGY: {item.directive} | 🛡️ CONFIDENCE: {item.confidence_tier}")
#         print(f"   THESIS: {item.reasoning}")
        
#         watchlist_config[item.ticker] = {
#             "directive": item.directive,
#             "confidence_tier": item.confidence_tier,
#             "reasoning": item.reasoning
#         }
        
#     watchlist_path = os.path.join(BASE_DIR, 'active_watchlist.json')
#     with open(watchlist_path, 'w') as f:
#         json.dump(watchlist_config, f, indent=2)
        
#     print(f"\n✅ Full Market CIO execution complete. Saved to: {watchlist_path}")
#     return {}

# # ==========================================
# # 2. COMPILE THE STATE GRAPH
# # ==========================================
# workflow = StateGraph(CIOState)

# workflow.add_node("scan_market", run_full_market_sweep_node)
# workflow.add_node("make_decisions", generate_decisions_node)
# workflow.add_node("export", export_configuration_node)

# workflow.set_entry_point("scan_market")
# workflow.add_edge("scan_market", "make_decisions")
# workflow.add_edge("make_decisions", "export")
# workflow.add_edge("export", END)

# cio_app = workflow.compile()

# # ==========================================
# # 3. TEST EXECUTION
# # ==========================================
# if __name__ == "__main__":
#     print("=========================================================")
#     print("🌅 STARTING PRE-MARKET CIO AGENT WORKFLOW (MATH + NEWS)")
#     print("=========================================================")
    
#     # We test with 4 specific stocks. Expand this to the full Nifty 50 when ready!
#     # initial_state = CIOState(target_tickers=['RELIANCE', 'TCS', 'HDFCBANK', 'INFY'])/
#     initial_state = CIOState(target_tickers=["ADANIENT","ADANIPORTS","APOLLOHOSP","ASIANPAINT","AXISBANK","BAJAJ-AUTO","BAJFINANCE","BAJAJFINSV","BEL","BHARTIARTL","CIPLA","COALINDIA","DRREDDY","EICHERMOT","ETERNAL","GRASIM","HCLTECH","HDFCBANK","HDFCLIFE","HINDALCO","HINDUNILVR","ICICIBANK","INDIGO","INFY","ITC","JIOFIN","JSWSTEEL","KOTAKBANK","LT","M&M","MARUTI","MAXHEALTH","NESTLEIND","NTPC","ONGC","POWERGRID","RELIANCE","SBILIFE","SHRIRAMFIN","SBIN","SUNPHARMA","TCS","TATACONSUM","TMPV","TATASTEEL","TECHM","TITAN","TRENT","ULTRACEMCO","WIPRO"])
    
#     try:
#         cio_app.invoke(initial_state)
#     except Exception as e:
#         print(f"❌ LangGraph Execution Failed: {e}")


import os
import json
import time
from typing import Dict, Any
from dotenv import load_dotenv

# Database Imports for Shared Memory
from sqlalchemy import create_engine, Column, Integer, String, JSON, DateTime
from sqlalchemy.orm import sessionmaker, declarative_base
from datetime import datetime

# LangChain & LangGraph Imports
from langgraph.graph import StateGraph, END
from langchain_aws import ChatBedrock
from langchain_core.output_parsers import PydanticOutputParser

# Import our custom schemas and tools
from state_schema import CIOState, DailyPlaybookSchema
from tools.model_tools import tool_get_swing_prediction, tool_get_stock_news

# --- Configuration ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(BASE_DIR, '.env'))

# --- SHARED MEMORY DATABASE SETUP ---
DB_PASSWORD = os.getenv('DB_PASSWORD', 'root')
DATABASE_URL = f"postgresql://postgres:{DB_PASSWORD}@localhost:5432/converse_db"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class DailyPlaybookDB(Base):
    __tablename__ = "daily_playbook"
    id = Column(Integer, primary_key=True, index=True)
    date = Column(DateTime, default=datetime.utcnow)
    market_regime = Column(String) 
    risk_level = Column(String)    
    approved_sectors = Column(JSON) 
    banned_sectors = Column(JSON)   
    reasoning = Column(String)

# ==========================================
# 1. LANGGRAPH NODES
# ==========================================
def run_full_market_sweep_node(state: CIOState):
    """Node 1: Sweeps the market, fetching BOTH Deep Learning Math and Sentiment News."""
    print("\n[CIO Agent] 🌍 Initiating Macro Market Sweep (Math + Sentiment)...")
    
    market_data = {}
    for ticker in state.target_tickers:
        print(f" -> Analyzing {ticker}...")
        try:
            quant_result = tool_get_swing_prediction.invoke({"ticker": ticker})
        except Exception as e:
            quant_result = {"status": "error", "message": str(e)}
            
        try:
            news_result = tool_get_stock_news.invoke({"ticker": ticker})
        except Exception as e:
            news_result = {"status": "error", "message": str(e)}
            
        if quant_result.get("status") == "success":
            market_data[ticker] = {
                "expected_return": quant_result.get("expected_return"),
                "uncertainty": quant_result.get("uncertainty"),
                "headlines": news_result.get("headlines", [])
            }
        else:
            print(f"    ❌ Skipping {ticker} - Quant Engine Failed.")
            
        time.sleep(2) # Pacing
            
    return {"swing_predictions": market_data}

# def generate_decisions_node(state: CIOState):
#     """Node 2: Llama 3 acts as the Macro Strategist to set the Daily Playbook."""
#     print("\n[CIO Agent] 🤖 Waking up CIO to generate Macro Playbook...")
    
#     if not state.swing_predictions:
#         return {"error_logs": ["No valid market data generated."]}

#     # Sort stocks by the absolute magnitude of Expected Return
#     sorted_predictions = dict(sorted(
#         state.swing_predictions.items(),
#         key=lambda item: abs(item[1].get("expected_return", 0)),
#         reverse=True
#     ))

#     llm = ChatBedrock(
#         model_id="meta.llama3-8b-instruct-v1:0", # Or 70b if you have it
#         model_kwargs={"temperature": 0.2},
#         region_name="us-east-1" 
#     )
    
#     parser = PydanticOutputParser(pydantic_object=DailyPlaybookSchema)
    
#     system_instruction = (
#         "You are the Chief Investment Officer of a quantitative hedge fund.\n"
#         "You are receiving a full market sweep containing deep-learning expected returns, MC Dropout uncertainty, and news headlines.\n\n"
#         "YOUR JOB:\n"
#         "Do NOT pick specific stocks. Your job is to analyze the data and generate a 'Daily Playbook' for the execution bots.\n\n"
#         "SELECTION RULES:\n"
#         "1. Identify the overarching trend based on the math. Are most high-magnitude expected returns negative? Then the regime is BEARISH.\n"
#         "2. Identify which sectors the top movers belong to (e.g., IT, Banking, Energy). Put the sectors with high absolute returns and low uncertainty in 'approved_sectors'.\n"
#         "3. Put sectors with catastrophic news or high uncertainty in 'banned_sectors'.\n"
#         "4. Set Risk Level: 'AGGRESSIVE' if uncertainty is generally low, 'DEFENSIVE' if uncertainty is high.\n\n"
#         f"FORMAT REQUIREMENTS:\n{parser.get_format_instructions()}\n"
#         "OUTPUT STRICTLY VALID JSON ONLY."
#     )
    
#     user_payload = f"Full Market Data Sweep:\n{json.dumps(sorted_predictions, indent=2)}"
    
#     response = llm.invoke([
#         {"role": "system", "content": system_instruction},
#         {"role": "user", "content": user_payload}
#     ])
    
#     try:
#         decision = parser.parse(response.content)
#     except Exception as e:
#         print(f" ❌ Failed to parse JSON: {e}")
#         return {"error_logs": ["JSON Parse Error"]}
    
#     return {"structured_decision": decision}

def generate_decisions_node(state: CIOState):
    """Node 2: Llama 3 acts as the Macro Strategist to set the Daily Playbook."""
    print("\n[CIO Agent] 🤖 Waking up CIO to generate Macro Playbook...")
    
    if not state.swing_predictions:
        return {"error_logs": ["No valid market data generated."]}

    # Sort stocks by the absolute magnitude of Expected Return
    sorted_predictions = dict(sorted(
        state.swing_predictions.items(),
        key=lambda item: abs(item[1].get("expected_return", 0)),
        reverse=True
    ))

    llm = ChatBedrock(
        model_id="meta.llama3-8b-instruct-v1:0", 
        model_kwargs={"temperature": 0.1}, # Lowered temp slightly for stricter formatting
        region_name="us-east-1" 
    )
    
    parser = PydanticOutputParser(pydantic_object=DailyPlaybookSchema)
    
    system_instruction = (
        "You are the Chief Investment Officer of a quantitative hedge fund.\n"
        "You are receiving a market sweep containing deep-learning expected returns, MC Dropout uncertainty, and news headlines.\n\n"
        "YOUR JOB:\n"
        "Analyze the data and generate a 'Daily Playbook' for the execution bots.\n\n"
        "SELECTION RULES:\n"
        "1. Identify the overarching trend. Are most high-magnitude expected returns negative? Then the regime is BEARISH.\n"
        "2. Identify which sectors the top movers belong to. Put the sectors with high absolute returns and low uncertainty in 'approved_sectors'.\n"
        "3. Put sectors with catastrophic news or high uncertainty in 'banned_sectors'.\n"
        "4. Set Risk Level: 'AGGRESSIVE' if uncertainty is generally low, 'DEFENSIVE' if uncertainty is high.\n"
        "5. If you do not have enough data to pick sectors, just leave the arrays empty: [].\n\n"
        f"FORMAT REQUIREMENTS:\n{parser.get_format_instructions()}\n"
        "CRITICAL: OUTPUT STRICTLY VALID JSON ONLY. DO NOT add any conversational text before or after the JSON. DO NOT use markdown formatting."
    )
    
    user_payload = f"Market Data Sweep:\n{json.dumps(sorted_predictions, indent=2)}"
    
    response = llm.invoke([
        {"role": "system", "content": system_instruction},
        {"role": "user", "content": user_payload}
    ])
    
    # --- THE FIX: BULLETPROOF JSON EXTRACTION ---
    raw_text = response.content
    try:
        # Attempt 1: Try the strict LangChain parser first
        decision = parser.parse(raw_text)
    except Exception:
        # Attempt 2: If the LLM was chatty, surgically extract the JSON block
        print("   ⚠️ LLM added conversational text. Extracting JSON via Regex...")
        try:
            import re
            # Find everything between the first { and the last }
            json_match = re.search(r'\{.*\}', raw_text, re.DOTALL)
            if json_match:
                clean_json = json_match.group(0)
                parsed_dict = json.loads(clean_json)
                decision = DailyPlaybookSchema(**parsed_dict)
            else:
                raise ValueError("No JSON block found in output.")
        except Exception as e:
            print(f" ❌ Failed to extract JSON: {e}")
            print(f" Raw Output: {raw_text}")
            return {"error_logs": ["JSON Parse Error"]}
    
    return {"structured_decision": decision}

def export_configuration_node(state: CIOState):
    """Node 3: Saves the Playbook to PostgreSQL for the Copilot."""
    if not state.structured_decision:
        return {}
        
    print("\n[CIO Agent] 💾 Exporting Final Macro Playbook to Database...")
    playbook = state.structured_decision
    
    print(f"\n📊 REGIME: {playbook.market_regime} | 🛡️ RISK: {playbook.risk_level}")
    print(f"✅ APPROVED SECTORS: {', '.join(playbook.approved_sectors)}")
    print(f"🚫 BANNED SECTORS: {', '.join(playbook.banned_sectors)}")
    print(f"💬 THESIS: {playbook.reasoning}\n")
    
    db = SessionLocal()
    try:
        # We delete yesterday's playbook so the Copilot only reads today's
        db.query(DailyPlaybookDB).delete()
        
        new_pb = DailyPlaybookDB(
            market_regime=playbook.market_regime,
            risk_level=playbook.risk_level,
            approved_sectors=playbook.approved_sectors,
            banned_sectors=playbook.banned_sectors,
            reasoning=playbook.reasoning
        )
        db.add(new_pb)
        db.commit()
        print("✅ Playbook successfully injected into Shared Memory.")
    except Exception as e:
        db.rollback()
        print(f"❌ Database error: {e}")
    finally:
        db.close()
        
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

if __name__ == "__main__":
    print("=========================================================")
    print("🌅 STARTING PRE-MARKET CIO AGENT WORKFLOW")
    print("=========================================================")
    
    # Passing a sample list to test. Expand to Nifty 50 later.
    # initial_state = CIOState(target_tickers=['RELIANCE', 'TCS', 'HDFCBANK', 'INFY'])
    initial_state = CIOState(target_tickers=["ADANIENT","ADANIPORTS","APOLLOHOSP","ASIANPAINT","AXISBANK","BAJAJ-AUTO","BAJFINANCE","BAJAJFINSV","BEL","BHARTIARTL","CIPLA","COALINDIA","DRREDDY","EICHERMOT","ETERNAL","GRASIM","HCLTECH","HDFCBANK","HDFCLIFE","HINDALCO","HINDUNILVR","ICICIBANK","INDIGO","INFY","ITC","JIOFIN","JSWSTEEL","KOTAKBANK","LT","M&M","MARUTI","MAXHEALTH","NESTLEIND","NTPC","ONGC","POWERGRID","RELIANCE","SBILIFE","SHRIRAMFIN","SBIN","SUNPHARMA","TCS","TATACONSUM","TMPV","TATASTEEL","TECHM","TITAN","TRENT","ULTRACEMCO","WIPRO"])
    
    
    try:
        cio_app.invoke(initial_state)
    except Exception as e:
        print(f"❌ LangGraph Execution Failed: {e}")