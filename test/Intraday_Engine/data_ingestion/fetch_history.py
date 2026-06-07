import os
import yfinance as yf
import pandas as pd
from sqlalchemy import create_engine
from dotenv import load_dotenv
from tqdm import tqdm

# Load environment variables before setting up the database
load_dotenv(dotenv_path='../../.env') 

# --- 1. Database Configuration ---
# Format: postgresql://username:password@host:port/database_name
DB_USER = 'postgres'
DB_PASSWORD = os.getenv('DB_PASSWORD', 'root')
DB_HOST = 'localhost'
DB_PORT = '5432'
DB_NAME = 'nifty_intraday_db'  # Pointed specifically to your new Intraday database

engine = create_engine(f'postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}')

def get_nifty50_tickers():
    """
    Scrapes the current Nifty 50 constituents from Wikipedia
    and formats them for yfinance (appending '.NS').
    """
    print("Fetching live Nifty 50 ticker list from Wikipedia...")
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
        raise ValueError("Could not find the Nifty 50 constituents table with a 'Symbol' column.")
    
    tickers = nifty_table['Symbol'].astype(str) + '.NS'
    return tickers.tolist()

def fetch_all_intraday_data(ticker_list):
    """
    Fetches 60 days of 15-minute intraday data for all tickers 
    and pushes to the unified raw_intraday_prices table.
    """
    print(f"\nStarting data ingestion for {len(ticker_list)} tickers...")
    
    try:
        # Quick test to ensure the global engine is connected
        engine.connect()
        print(f"Successfully connected to {DB_NAME}!")
    except Exception as e:
        print(f"Database Connection Failed: {e}")
        return

    all_data = []
    
    for ticker in tqdm(ticker_list, desc="Downloading Intraday History"):
        try:
            # 15m interval allows a maximum history window of 60 days via yfinance
            stock = yf.Ticker(ticker)
            df = stock.history(period="60d", interval="15m")
            
            if df.empty:
                continue
                
            df.reset_index(inplace=True)
            
            # Remove timezone tracking to maintain pure naive timestamp format in Postgres
            if 'Datetime' in df.columns:
                df['Datetime'] = pd.to_datetime(df['Datetime']).dt.tz_localize(None)
                df.rename(columns={'Datetime': 'date_time'}, inplace=True)
            elif 'Date' in df.columns: # Fallback safety checks
                df['Date'] = pd.to_datetime(df['Date']).dt.tz_localize(None)
                df.rename(columns={'Date': 'date_time'}, inplace=True)
            
            df['Ticker'] = ticker
            
            # Handle possible MultiIndex formatting from yfinance
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
                
            # Standardize names to clean lowercase formats
            df.rename(columns={
                'Open': 'open',
                'High': 'high',
                'Low': 'low',
                'Close': 'close',
                'Volume': 'volume',
                'Ticker': 'ticker'
            }, inplace=True)
            
            # Select strict core features
            df = df[['date_time', 'ticker', 'open', 'high', 'low', 'close', 'volume']]
            all_data.append(df)
            
        except Exception as e:
            print(f"\nWarning: Failed to fetch data for {ticker}: {e}")

    # Push to SQL in a single fast execution block
    if all_data:
        final_df = pd.concat(all_data, ignore_index=True)
        table_name = 'raw_intraday_prices'
        
        print(f"\nPushing {len(final_df):,} total intraday rows to PostgreSQL...")
        try:
            # 'replace' handles clean complete history initialization over this step
            final_df.to_sql(table_name, engine, if_exists='replace', index=False)
            print(f"Successfully populated '{table_name}' table!")
        except Exception as e:
            print(f"Database insertion crash error: {e}")
    else:
        print("No intraday rows successfully extracted.")

if __name__ == "__main__":
    dynamic_tickers = get_nifty50_tickers()
    fetch_all_intraday_data(dynamic_tickers)