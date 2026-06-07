import os
import json
import glob
from typing import List, Dict, Any
from dotenv import load_dotenv
from pydantic import BaseModel, Field

# LangChain & Google GenAI imports
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, END

# Load credentials from root .env file
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))

# --- 1. Define Type-Safe Structures ---
# class StockChoice(BaseModel):
#     ticker: str = Field(
#         description="The ticker symbol of the stock, e.g., 'ONGC'."
#     )
#     directive: str = Field(
#         description="The exact execution strategy for the intraday bot. Must be either 'LONG' if the AI prediction is positive/bullish, or 'SHORT' if the AI prediction is negative/bearish."
#     )
#     reasoning: str = Field(
#         description="A simple English explanation that explicitly includes the exact numbers (like P/E ratios, profit margins, and AI predictions) to mathematically prove why this stock and its corresponding trading directive were selected."
#     )

# --- 1. Define Type-Safe Structures ---
# class StockChoice(BaseModel):
#     ticker: str = Field(
#         description="The ticker symbol of the stock, e.g., 'ONGC'."
#     )
#     directive: str = Field(
#         description="The exact execution strategy for the intraday bot. Must be either 'LONG' or 'SHORT'."
#     )
#     confidence_tier: str = Field(
#         description="Must be 'HIGH', 'MEDIUM', or 'LOW'. Calculate this by comparing the AI_Swing_Expected_Return to the AI_Swing_Uncertainty. High confidence requires the return to be significantly larger than the uncertainty."
#     )
#     reasoning: str = Field(
#         description="A simple English explanation citing specific metrics. You MUST explain your risk assessment by comparing the AI predicted return to the AI uncertainty margin."
#     )


# --- 1. Define Type-Safe Structures ---
class StockChoice(BaseModel):
    ticker: str = Field(
        description="The ticker symbol of the stock, e.g., 'ONGC'."
    )
    directive: str = Field(
        description="The exact execution strategy for the intraday bot. Must be either 'LONG' or 'SHORT'."
    )
    confidence_tier: str = Field(
        description="Must be 'HIGH', 'MEDIUM', or 'LOW'. Calculate this by comparing the AI_Swing_Expected_Return to the AI_Swing_Uncertainty. High confidence requires the return to be significantly larger than the uncertainty."
    )
    reasoning: str = Field(
        description="A simple English explanation citing specific metrics. You MUST explain your risk assessment by comparing the AI predicted return to the AI uncertainty margin."
    )

class WatchlistSelection(BaseModel):
    selections: List[StockChoice] = Field(
        description="A list containing up to 4 high-quality stock allocations maximum for the day."
    )

# --- 2. Define LangGraph State Schema ---
class AgentState(BaseModel):
    raw_payload: Dict[str, Any] = {}
    structured_decision: WatchlistSelection = None

# --- 3. Folder Pathing Configurations ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)

FUNDAMENTALS_DIR = os.path.join(PROJECT_ROOT, 'Macro_and_Fundamental_Engine', 'daily_briefings')
SENTIMENT_DIR = os.path.join(PROJECT_ROOT, 'Live_Sentiment_Scraper', 'daily_briefings')

def get_latest_file(directory, prefix):
    search_pattern = os.path.join(directory, f'{prefix}_*.json')
    list_of_files = glob.glob(search_pattern)
    return max(list_of_files, key=os.path.getctime) if list_of_files else None

# --- 4. LangGraph Agent Nodes ---
def data_ingestion_node(state: AgentState) -> Dict:
    briefing_file = get_latest_file(FUNDAMENTALS_DIR, 'llm_briefing')
    sentiment_file = get_latest_file(SENTIMENT_DIR, 'llm_sentiment')
    
    if not briefing_file or not sentiment_file:
        raise FileNotFoundError("Missing raw briefing data JSON files.")
        
    with open(briefing_file, 'r') as f:
        market_data = json.load(f)
    with open(sentiment_file, 'r') as f:
        sentiment_data = json.load(f)

    raw_companies = market_data.get("company_fundamentals", {})
    filtered_companies = {}
    filtered_sentiment = {}

    for ticker, details in raw_companies.items():
        ai_signal = details.get("AI_Swing_Expected_Return")
        if ai_signal and ai_signal != "No Signal":
            filtered_companies[ticker] = details
            if ticker in sentiment_data.get("news_headlines", {}):
                filtered_sentiment[ticker] = sentiment_data["news_headlines"][ticker]

    mega_payload = {
        "macro_environment": market_data.get("macro_environment", {}),
        "general_market_news": sentiment_data.get("general_market_news", []),
        "company_fundamentals": filtered_companies,
        "news_headlines": filtered_sentiment
    }
    
    print(f" -> LangGraph Ingestion: Optimized problem space to {len(filtered_companies)} active candidates.")
    return {"raw_payload": mega_payload}

def portfolio_analysis_node(state: AgentState) -> Dict:
    print("Waking up Google Gemini-2.5-Flash-Lite Portfolio Manager...")
    
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash-lite",
        google_api_key=os.getenv("GOOGLE_API_KEY"),
        temperature=0.0
    )
    
    structured_llm = llm.with_structured_output(WatchlistSelection)
    
    # system_prompt = (
    #     "You are the Chief Investment Officer (CIO) of an elite quantitative hedge fund.\n"
    #     "Review the provided macroeconomic data, general news trends, specific company fundamentals, and technical AI predictions.\n\n"
    #     "Your goal is to select all good, highly viable opportunities from the provided list to trade today.\n\n"
    #     "Selection Constraints:\n"
    #     "1. ABSOLUTE SYSTEM CAP: Select up to 4 stocks maximum for the day.\n"
    #     "2. DIRECTIVE ALIGNMENT: For every stock selected, look at the 'AI_Swing_Expected_Return'. If it is a negative number, set the directive to 'SHORT'. If it is a positive number, set the directive to 'LONG'.\n"
    #     "3. DATA-BACKED EXPLANATIONS: Write explanations in a natural, clear, human manner, but you MUST quote the specific metrics (P/E, profit margins, AI predictions) to prove your macro and technical thesis."
    # )

    # system_prompt = (
    #     "You are the Chief Investment Officer (CIO) and Chief Risk Officer of an elite quantitative hedge fund.\n"
    #     "Review the macroeconomic data, specific company fundamentals, and technical AI predictions.\n\n"
    #     "Your goal is to select all good, highly viable opportunities from the provided list to trade today.\n\n"
    #     "Selection Constraints:\n"
    #     "1. ABSOLUTE SYSTEM CAP: Select up to 4 stocks maximum for the day.\n"
    #     "2. DIRECTIVE ALIGNMENT: Set the directive to 'SHORT' for negative AI returns, and 'LONG' for positive AI returns.\n"
    #     "3. RISK & UNCERTAINTY FILTERING: Do NOT blindly trust the 'AI_Swing_Expected_Return'. You MUST compare it to the 'AI_Swing_Uncertainty'. "
    #     "A smaller return with very low uncertainty is mathematically safer than a massive return with massive uncertainty. "
    #     "Do NOT select any stock where the Uncertainty is equal to or larger than the absolute value of the Expected Return.\n"
    #     "4. DATA-BACKED EXPLANATIONS: Write explanations in a natural, clear manner. You MUST quote the specific metrics (P/E, profit margins) AND explicitly state the ratio of AI Return vs AI Uncertainty to prove the trade is safe."
    # )

    system_prompt = (
        "You are the Chief Investment Officer (CIO) and Chief Risk Officer of an elite quantitative hedge fund.\n"
        "Review the macroeconomic data, specific company fundamentals, and technical AI predictions.\n\n"
        "Your goal is to select all good, highly viable opportunities from the provided list to trade today.\n\n"
        "Selection Constraints:\n"
        "1. ABSOLUTE SYSTEM CAP: Select up to 4 stocks maximum for the day.\n"
        "2. DIRECTIVE ALIGNMENT: Set the directive to 'SHORT' for negative AI returns, and 'LONG' for positive AI returns.\n"
        "3. RISK & UNCERTAINTY FILTERING: Do NOT blindly trust the 'AI_Swing_Expected_Return'. You MUST compare it to the 'AI_Swing_Uncertainty'. "
        "A smaller return with very low uncertainty is mathematically safer than a massive return with massive uncertainty. "
        "Do NOT select any stock where the Uncertainty is equal to or larger than the absolute value of the Expected Return.\n"
        "4. DATA-BACKED EXPLANATIONS: Write explanations in a natural, clear manner. You MUST quote the specific metrics (P/E, profit margins) AND explicitly state the ratio of AI Return vs AI Uncertainty to prove the trade is safe."
    )
    
    user_prompt = f"Today's Filtered Market Payload:\n{json.dumps(state.raw_payload, indent=2)}"
    
    decision = structured_llm.invoke([
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ])
    
    return {"structured_decision": decision}

# --- 5. Build the LangGraph State Engine Architecture ---
workflow = StateGraph(AgentState)

workflow.add_node("ingest_data", data_ingestion_node)
workflow.add_node("analyze_portfolio", portfolio_analysis_node)

workflow.set_entry_point("ingest_data")
workflow.add_edge("ingest_data", "analyze_portfolio")
workflow.add_edge("analyze_portfolio", END)

app = workflow.compile()

if __name__ == "__main__":
    print("=========================================================================")
    print("⛓️  STARTING DETERMINISTIC LANGGRAPH PIPELINE WITH GOOGLE GEMINI ⛓️ ")
    print("=========================================================================")
    
    try:
        final_state = app.invoke(AgentState())
        decision = final_state.get("structured_decision")
        
        print("\n=========================================================================")
        print("🎯 QUANT PORTFOLIO MANAGEMENT DECISION (STRATEGIC DIRECTIVES) 🎯")
        print("=========================================================================")
        
        # # Build the final configuration map dictionary
        # watchlist_config = {}
        # for item in decision.selections:
        #     print(f"\n📈 TARGET: {item.ticker} | 🛠️  STRATEGY: {item.directive}")
        #     print(f"   THESIS: {item.reasoning}")
            
        #     watchlist_config[item.ticker] = {
        #         "directive": item.directive,
        #         "reasoning": item.reasoning
        #     }

        # Build the final configuration map dictionary
        watchlist_config = {}
        for item in decision.selections:
            print(f"\n📈 TARGET: {item.ticker} | 🛠️  STRATEGY: {item.directive} | 🛡️ CONFIDENCE: {item.confidence_tier}")
            print(f"   THESIS: {item.reasoning}")
            
            watchlist_config[item.ticker] = {
                "directive": item.directive,
                "confidence_tier": item.confidence_tier,
                "reasoning": item.reasoning
            }
            
        print("=========================================================================")
        print(f"Final Active Portfolio Keys: {list(watchlist_config.keys())}")
        print("=========================================================================")
        
        # Dynamic guard rail truncate to keep top 4 dictionary configurations
        if len(watchlist_config) > 4:
            # watchlist_config = dict(list(watchlist_config.items())[:4])
            watchlist_config = {}
            for item in decision.selections:
                print(f"\n📈 TARGET: {item.ticker} | 🛠️  STRATEGY: {item.directive} | 🛡️ CONFIDENCE: {item.confidence_tier}")
                print(f"   THESIS: {item.reasoning}")
                
                watchlist_config[item.ticker] = {
                    "directive": item.directive,
                    "confidence_tier": item.confidence_tier,
                    "reasoning": item.reasoning
                }

        # Export the clean configuration dictionary object file
        watchlist_path = os.path.join(BASE_DIR, 'active_watchlist.json')
        with open(watchlist_path, 'w') as f:
            json.dump(watchlist_config, f, indent=2)
            
        print(f"Successfully saved clean dictionary configuration watchlist to: {watchlist_path}")
        
    except Exception as e:
        print(f"❌ LangGraph Runtime Framework Failure: {e}")