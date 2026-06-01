import os
from dotenv import load_dotenv

load_dotenv() # This loads the variables from the .env file

import yfinance as yf
import pandas as pd
from sqlalchemy import create_engine

# Format: postgresql://username:password@host:port/database_name
DB_USER = 'postgres'
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_HOST = 'localhost'
DB_PORT = '5432'
DB_NAME = 'nifty_lstm_db'

# Database Connection
engine = create_engine(f'postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}')

# Removed FINNIFTY due to broken Yahoo Finance history
MACRO_TICKERS = {
    'NIFTY50': '^NSEI',
    'BANKNIFTY': '^NSEBANK',
    'INDIAVIX': '^INDIAVIX',
    'USDINR': 'INR=X',
    'CRUDEOIL': 'CL=F',
    'GOLD': 'GC=F'
}

def fetch_and_save_macro():
    print("Fetching macro context data from yfinance...")
    macro_data = {}
    
    for name, ticker in MACRO_TICKERS.items():
        print(f"Downloading {name}...")
        df = yf.download(ticker, start='2015-01-01', progress=False)
        
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
            
        if name == 'INDIAVIX':
            macro_data[f'{name}_close'] = df['Close']
        else:
            macro_data[f'{name}_return'] = df['Close'].pct_change()
            
    macro_df = pd.DataFrame(macro_data)
    macro_df.index.name = 'date'
    macro_df.reset_index(inplace=True)
    
    # Strip timezones and normalize to midnight
    macro_df['date'] = pd.to_datetime(macro_df['date']).dt.tz_localize(None).dt.normalize()
    
    print("Saving raw macro data to PostgreSQL...")
    macro_df.to_sql('raw_macro_context', engine, if_exists='replace', index=False)
    print("Success! Raw macro data saved.")

if __name__ == "__main__":
    fetch_and_save_macro()