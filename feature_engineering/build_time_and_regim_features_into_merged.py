import os
from dotenv import load_dotenv

load_dotenv() # This loads the variables from the .env file

import pandas as pd
import numpy as np
import ta
from sqlalchemy import create_engine

# Format: postgresql://username:password@host:port/database_name
DB_USER = 'postgres'
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_HOST = 'localhost'
DB_PORT = '5432'
DB_NAME = 'nifty_lstm_db'

# Database Connection
engine = create_engine(f'postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}')

def add_time_and_regime_features():
    print("1. Reading Master Features (Layers 2-7) from PostgreSQL...")
    df = pd.read_sql("SELECT * FROM master_features_l2_l7", engine)
    
    # Ensure date is a datetime object and sort chronologically
    df['date'] = pd.to_datetime(df['date'])
    df.sort_values(by=['Ticker', 'date'], inplace=True)
    
    print("2. Calculating Layer 8: Time Features...")
    # 0 = Monday, 4 = Friday
    df['day_of_week'] = df['date'].dt.dayofweek
    df['month'] = df['date'].dt.month
    df['quarter'] = df['date'].dt.quarter

    # 4. Expiry Week Regime (Approximation for the Indian Market)
    # The monthly F&O expiry is the last Thursday. The week leading up to it is highly volatile.
    # We flag days that fall between the 22nd and 28th of the month.
    df['expiry_week'] = ((df['date'].dt.day >= 22) & (df['date'].dt.day <= 28)).astype(int)

    # 5. Month-End Regime (1 if it is the last 5 days of the month)
    # dt.days_in_month gives us the last calendar day (e.g., 28, 30, 31)
    df['month_end'] = (df['date'].dt.day >= (df['date'].dt.days_in_month - 5)).astype(int)
    
    print("3. Calculating Layer 9: Regime Features...")
    
    def apply_regime(stock_df):
        # 1. Trend Strength (Using ADX - Average Directional Index)
        stock_df['trend_strength'] = ta.trend.adx(
            stock_df['high'], 
            stock_df['low'], 
            stock_df['close'], 
            window=14, 
            fillna=True
        )
            
        # 2. Volatility Regime (1 if current ATR is higher than its 50-day average)
        atr_50_avg = stock_df['atr_14'].rolling(window=50).mean()
        stock_df['volatility_regime'] = (stock_df['atr_14'] > atr_50_avg).astype(int)

        # 3. Above 200 DMA Regime
        sma_200 = ta.trend.sma_indicator(stock_df['close'], window=200)
        stock_df['sma_200'] = sma_200 # Temporarily store this to trigger dropna!
        stock_df['above_200dma'] = (stock_df['close'] > sma_200).astype(int)
        
        return stock_df

    # Apply complex rolling features per stock
    df = df.groupby('Ticker', group_keys=False).apply(apply_regime)
    
    # Because calculating a 200-day moving average requires 200 days of history, 
    # the first 199 days for every stock will now have NaNs in the 'sma_200' column.
    print("4. Cleaning up early NaN rows (caused by 200DMA)...")
    df.dropna(inplace=True)
    
    # Now that the dirty warmup rows are deleted, we can drop the temporary sma_200 column
    df.drop(columns=['sma_200'], inplace=True)
    
    print("5. Saving Final Master Dataset to PostgreSQL...")
    table_name = 'master_features_final'
    df.to_sql(table_name, engine, if_exists='replace', index=False)
    
    print(f"Success! {len(df)} fully engineered rows saved to '{table_name}'.")

if __name__ == "__main__":
    add_time_and_regime_features()