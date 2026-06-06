import os
import yfinance as yf
import pandas as pd
import json
from datetime import datetime
from tqdm import tqdm

# --- Dynamic Pathing ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, 'daily_briefings')
os.makedirs(OUTPUT_DIR, exist_ok=True)

def get_dynamic_watchlist():
    print("Scraping live Nifty 50 constituents from Wikipedia...")
    url = 'https://en.wikipedia.org/wiki/NIFTY_50'
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    tables = pd.read_html(url, storage_options=headers)
    nifty_table = next((t for t in tables if 'Symbol' in t.columns), None)
    
    if nifty_table is None:
        raise ValueError("Could not find the Nifty 50 table.")
    
    watchlist = {symbol: f"{symbol}.NS" for symbol in nifty_table['Symbol']}
    return watchlist

def fetch_general_market_news():
    print("Grabbing Broad Macro-Market Headlines...")
    try:
        # We scrape the Nifty 50 Index (^NSEI) to get top national market news
        index_ticker = yf.Ticker('^NSEI')
        news = index_ticker.news
        
        general_news = []
        for article in news[:5]: # Grab the top 5 biggest stories of the day
            title = article.get('title', '')
            publisher = article.get('publisher', 'Unknown')
            if title:
                general_news.append(f"[{publisher}] {title}")
                
        return general_news if general_news else ["No major national news trending right now."]
    except Exception as e:
        return [f"Failed to fetch general market news: {e}"]

def fetch_live_sentiment():
    watchlist = get_dynamic_watchlist()
    
    # NEW: The payload now has a dedicated section for general world/market news
    sentiment_payload = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "general_market_news": fetch_general_market_news(),
        "news_headlines": {}
    }
    
    print(f"Scraping specific financial news for {len(watchlist)} stocks...")
    for name, ticker_symbol in tqdm(watchlist.items(), desc="Reading Headlines"):
        try:
            stock = yf.Ticker(ticker_symbol)
            news = stock.news
            
            recent_news = []
            for article in news[:3]:
                title = article.get('title', '')
                publisher = article.get('publisher', 'Unknown')
                if title:
                    recent_news.append(f"[{publisher}] {title}")
            
            if recent_news:
                sentiment_payload["news_headlines"][name] = recent_news
            else:
                sentiment_payload["news_headlines"][name] = ["No recent significant news."]
                
        except Exception as e:
            sentiment_payload["news_headlines"][name] = ["News scraping failed."]

    date_str = sentiment_payload["date"]
    file_path = os.path.join(OUTPUT_DIR, f'llm_sentiment_{date_str}.json')
    
    with open(file_path, 'w') as f:
        json.dump(sentiment_payload, f, indent=2)
        
    print(f"\nSuccess! Sentiment Briefing saved to: {file_path}")

if __name__ == "__main__":
    fetch_live_sentiment()