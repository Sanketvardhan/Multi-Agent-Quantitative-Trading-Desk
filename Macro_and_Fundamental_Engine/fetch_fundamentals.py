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

SWING_CACHE_PATH = r"C:\Users\Tuf_F15\Desktop\codes\Python\Project\stock_predictor\Swing_Engine\model_training\cache\attention_v4_mc_cache.csv"

def get_dynamic_watchlist():
    print("Scraping live Nifty 50 constituents from Wikipedia...")
    url = 'https://en.wikipedia.org/wiki/NIFTY_50'
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    tables = pd.read_html(url, storage_options=headers)
    nifty_table = None
    for table in tables:
        if 'Symbol' in table.columns:
            nifty_table = table
            break
            
    if nifty_table is None:
        raise ValueError("Could not find the Nifty 50 table.")
    
    # Create a dictionary like {'RELIANCE': 'RELIANCE.NS'}
    watchlist = {}
    for symbol in nifty_table['Symbol']:
        watchlist[symbol] = f"{symbol}.NS"
        
    return watchlist

def fetch_daily_macro_context():
    print("Gathering Macro-Economic Environment...")
    vix_ticker = yf.Ticker('^INDIAVIX')
    vix_history = vix_ticker.history(period='5d')
    current_vix = vix_history['Close'].iloc[-1] if not vix_history.empty else "N/A"
    
    macro_data = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "india_vix": round(current_vix, 2) if isinstance(current_vix, float) else current_vix,
        "market_sentiment": "High Volatility" if isinstance(current_vix, float) and current_vix > 18 else "Stable"
    }
    return macro_data

def fetch_stock_fundamentals(watchlist):
    print(f"Gathering Fundamental Valuations for {len(watchlist)} stocks...")
    fundamentals = {}
    
    for name, ticker_symbol in tqdm(watchlist.items(), desc="Fetching YF Data"):
        try:
            stock = yf.Ticker(ticker_symbol)
            info = stock.info
            
            fundamentals[name] = {
                "sector": info.get('sector', 'Unknown'),
                "forward_PE": info.get('forwardPE', 'N/A'),
                "trailing_PE": info.get('trailingPE', 'N/A'),
                "profit_margin_pct": round(info.get('profitMargins', 0) * 100, 2) if info.get('profitMargins') else 'N/A',
                "debt_to_equity": info.get('debtToEquity', 'N/A'),
                "current_price": info.get('currentPrice', 'N/A')
            }
        except Exception as e:
            fundamentals[name] = {"error": "Data unavailable"}
            
    return fundamentals

def merge_swing_ai_predictions(fundamentals, watchlist):
    print("Injecting Swing Engine AI Predictions...")
    if not os.path.exists(SWING_CACHE_PATH):
        print(f"  -> WARNING: Swing cache not found at {SWING_CACHE_PATH}. Skipping AI data.")
        return fundamentals

    try:
        swing_df = pd.read_csv(SWING_CACHE_PATH)
        latest_date = swing_df['Date'].max()
        latest_preds = swing_df[swing_df['Date'] == latest_date]
        
        for name in fundamentals.keys():
            yfinance_symbol = watchlist.get(name, "")
            pred_row = latest_preds[(latest_preds['Ticker'] == name) | (latest_preds['Ticker'] == yfinance_symbol)]
            
            if not pred_row.empty:
                fundamentals[name]['AI_Swing_Expected_Return'] = round(pred_row['Predicted_Return'].values[0], 4)
                fundamentals[name]['AI_Swing_Uncertainty'] = round(pred_row['Uncertainty'].values[0], 4)
            else:
                fundamentals[name]['AI_Swing_Expected_Return'] = "No Signal"
                fundamentals[name]['AI_Swing_Uncertainty'] = "N/A"
                
    except Exception as e:
        print(f"  -> Error merging Swing Data: {e}")
        
    return fundamentals

def generate_llm_briefing():
    watchlist = get_dynamic_watchlist()
    macro = fetch_daily_macro_context()
    stocks = fetch_stock_fundamentals(watchlist)
    stocks_with_ai = merge_swing_ai_predictions(stocks, watchlist)
    
    llm_payload = {
        "system_status": "PRE-MARKET BRIEFING",
        "macro_environment": macro,
        "company_fundamentals": stocks_with_ai
    }
    
    date_str = macro["date"]
    file_path = os.path.join(OUTPUT_DIR, f'llm_briefing_{date_str}.json')
    
    with open(file_path, 'w') as f:
        json.dump(llm_payload, f, indent=2) 
        
    print(f"\nSuccess! Full Nifty 50 LLM Briefing saved to: {file_path}")

if __name__ == "__main__":
    generate_llm_briefing()