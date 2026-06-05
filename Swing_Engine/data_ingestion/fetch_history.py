import os
from dotenv import load_dotenv

load_dotenv() # This loads the variables from the .env file

import yfinance as yf
import pandas as pd
from sqlalchemy import create_engine

# --- 1. Database Configuration ---
# Format: postgresql://username:password@host:port/database_name
DB_USER = 'postgres'
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_HOST = 'localhost'
DB_PORT = '5432'
DB_NAME = 'nifty_lstm_db'

engine = create_engine(f'postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}')

# --- 2. Define the Target Stocks ---
# For testing the pipeline, we will start with just two major Nifty50 stocks
# Remember: yfinance requires the '.NS' suffix for the National Stock Exchange
# tickers = ['RELIANCE.NS', 'TCS.NS']

def get_nifty50_tickers():
    """
    Scrapes the current Nifty 50 constituents from Wikipedia
    and formats them for yfinance (appending '.NS').
    """
    print("Fetching live Nifty 50 ticker list...")
    url = 'https://en.wikipedia.org/wiki/NIFTY_50'
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    tables = pd.read_html(url, storage_options=headers)
    
    # Loop through all tables on the page to find the right one dynamically
    nifty_table = None
    for table in tables:
        # Check if 'Symbol' is a column in this specific table
        if 'Symbol' in table.columns:
            nifty_table = table
            break
            
    if nifty_table is None:
        raise ValueError("Could not find the Nifty 50 constituents table with a 'Symbol' column on Wikipedia.")
    
    # Extract the 'Symbol' column and append '.NS'
    tickers = nifty_table['Symbol'].astype(str) + '.NS'
    
    return tickers.tolist()

def fetch_and_store_historical_data(ticker_list, start_date='2015-01-01'):
    """
    Fetches historical OHLCV data and pushes it to PostgreSQL.
    """
    print(f"Starting data ingestion for {len(ticker_list)} tickers...")
    
    for ticker in ticker_list:
        print(f"Fetching data for {ticker}...")
        
        # Download the data using yfinance
        df = yf.download(ticker, start=start_date, progress=False)
        
        if df.empty:
            print(f"Warning: No data found for {ticker}.")
            continue
            
        # Clean up the dataframe structure for the database
        df.reset_index(inplace=True)
        df['Ticker'] = ticker # Add a column so we know which stock this is
        
        # yfinance sometimes returns MultiIndex columns, this flattens them
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
            
        # Standardize column names
        df.rename(columns={
            'Date': 'date',
            'Open': 'open',
            'High': 'high',
            'Low': 'low',
            'Close': 'close',
            'Volume': 'volume'
        }, inplace=True)
        
        # Select only the columns we need for Layer 1
        df = df[['date', 'Ticker', 'open', 'high', 'low', 'close', 'volume']]
        
        # --- 3. Push to PostgreSQL ---
        # if_exists='append' ensures we add to the table without overwriting history
        table_name = 'raw_ohlcv'
        try:
            df.to_sql(table_name, engine, if_exists='append', index=False)
            print(f"Successfully saved {len(df)} rows for {ticker} to '{table_name}' table.")
        except Exception as e:
            print(f"Database error for {ticker}: {e}")

if __name__ == "__main__":
    dynamic_tickers = get_nifty50_tickers()
    print(dynamic_tickers)
    fetch_and_store_historical_data(dynamic_tickers)