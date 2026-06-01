import os
from dotenv import load_dotenv

load_dotenv() # This loads the variables from the .env file

import pandas as pd
import numpy as np
import ta
from sqlalchemy import create_engine

# --- 1. Database Connection ---
DB_USER = 'postgres'
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_HOST = 'localhost'
DB_PORT = '5432'
DB_NAME = 'nifty_lstm_db'

engine = create_engine(f'postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}')

def calculate_technical_features(df):
    """
    Applies Layer 2 to Layer 6 feature engineering on a single stock's dataframe.
    """
    # Ensure data is sorted by date just in case
    df = df.sort_values('date')
    
    # ==========================================
    # LAYER 2: Price-Derived Features
    # ==========================================
    df['daily_return'] = df['close'].pct_change()
    df['open_gap'] = (df['open'] - df['close'].shift(1)) / df['close'].shift(1)
    df['intraday_return'] = (df['close'] - df['open']) / df['open']
    df['high_low_range'] = (df['high'] - df['low']) / df['close']
    df['body_size'] = np.abs(df['close'] - df['open']) / df['open']
    
    # ==========================================
    # LAYER 3: Trend Features
    # ==========================================
    df['sma_5'] = ta.trend.sma_indicator(df['close'], window=5)
    df['sma_10'] = ta.trend.sma_indicator(df['close'], window=10)
    df['sma_20'] = ta.trend.sma_indicator(df['close'], window=20)
    df['sma_50'] = ta.trend.sma_indicator(df['close'], window=50)
    df['ema_10'] = ta.trend.ema_indicator(df['close'], window=10)
    df['ema_20'] = ta.trend.ema_indicator(df['close'], window=20)
    df['ema_50'] = ta.trend.ema_indicator(df['close'], window=50)
    
    # ==========================================
    # LAYER 4: Momentum Features
    # ==========================================
    df['rsi_14'] = ta.momentum.rsi(df['close'], window=14)
    macd = ta.trend.MACD(df['close'])
    df['macd'] = macd.macd()
    df['macd_signal'] = macd.macd_signal()
    df['macd_hist'] = macd.macd_diff()
    df['roc_5'] = ta.momentum.roc(df['close'], window=5)
    df['roc_10'] = ta.momentum.roc(df['close'], window=10)
    
    # ==========================================
    # LAYER 5: Volatility Features
    # ==========================================
    df['stoch_rsi'] = ta.momentum.stochrsi(df['close'])
    df['atr_14'] = ta.volatility.average_true_range(df['high'], df['low'], df['close'], window=14)
    df['atr_20'] = ta.volatility.average_true_range(df['high'], df['low'], df['close'], window=20)
    df['rolling_std_5'] = df['close'].rolling(window=5).std()
    df['rolling_std_10'] = df['close'].rolling(window=10).std()
    df['rolling_std_20'] = df['close'].rolling(window=20).std()
    bollinger = ta.volatility.BollingerBands(df['close'])
    df['bollinger_width'] = bollinger.bollinger_wband()
    
    # ==========================================
    # LAYER 6: Volume Features
    # ==========================================
    df['volume_ratio'] = df['volume'] / df['volume'].rolling(window=20).mean()
    df['volume_change'] = df['volume'].pct_change()
    df['obv'] = ta.volume.on_balance_volume(df['close'], df['volume'])
    df['vwap'] = ta.volume.volume_weighted_average_price(df['high'], df['low'], df['close'], df['volume'])
    df['vwap_distance'] = (df['close'] - df['vwap']) / df['vwap']

    # Drop the absolute vwap since we only want the relative distance
    df.drop(columns=['vwap'], inplace=True)
    
    # NEUTRALIZE INFINITY: Replace any Infinity values (from divide-by-zero) with 0
    df.replace([np.inf, -np.inf], 0, inplace=True)
    
    return df

def run_pipeline():
    print("Fetching raw data from database...")
    # Load all raw data into memory
    raw_df = pd.read_sql("SELECT * FROM raw_ohlcv", engine)
    
    print(f"Applying technical indicators to {len(raw_df['Ticker'].unique())} tickers...")
    # Apply the feature function to each ticker independently
    processed_df = raw_df.groupby('Ticker', group_keys=False).apply(calculate_technical_features)
    
    # Drop rows with NaN values (the first 50 days will have NaNs because of the SMA_50)
    processed_df.dropna(inplace=True)
    
    print("Writing processed features to database...")
    table_name = 'processed_features_l2_l6'
    
    # Replace the table entirely if we run this script again
    processed_df.to_sql(table_name, engine, if_exists='replace', index=False)
    
    print(f"Success! {len(processed_df)} rows saved to '{table_name}'.")

if __name__ == "__main__":
    run_pipeline()