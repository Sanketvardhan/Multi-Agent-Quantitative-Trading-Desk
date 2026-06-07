import os
import sys
from langchain.tools import tool
import yfinance as yf
import requests

# --- Dynamic Pathing ---
# Add the root project directory to sys.path so we can import from models/
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(BASE_DIR)

from models.swing_inference import get_live_swing_prediction
from models.intraday_inference import get_live_intraday_prediction

@tool
def tool_get_swing_prediction(ticker: str) -> dict:
    """
    Fetches the live expected return and uncertainty for a given Nifty 50 ticker.
    Use this tool during Pre-Market analysis to find swing/directional setups for the day.
    """
    return get_live_swing_prediction(ticker)

@tool
def tool_get_intraday_prediction(ticker: str) -> dict:
    """
    Fetches the live 15-minute expected return for a given stock.
    Use this tool during live market hours to trigger precise execution entries.
    """
    return get_live_intraday_prediction(ticker)

@tool
def tool_get_stock_news(ticker: str) -> dict:
    """
    Fetches the latest 3 news headlines for a given stock to determine fundamental sentiment.
    """
    print(f"   [News Engine] Scraping latest headlines for {ticker}...")
    try:
        # Stealth Mode
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0'
        })
        
        stock = yf.Ticker(f"{ticker}.NS", session=session)
        news_items = stock.news
        
        if not news_items:
            return {"ticker": ticker, "headlines": ["No recent news found."], "status": "success"}
            
        # Extract just the titles to save LLM tokens
        headlines = [item['title'] for item in news_items[:3]] # Grab top 3
        return {"ticker": ticker, "headlines": headlines, "status": "success"}
        
    except Exception as e:
        return {"ticker": ticker, "status": "error", "message": str(e)}
    
