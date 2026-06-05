import os
import pandas as pd
import numpy as np
import ta
from sqlalchemy import create_engine
from dotenv import load_dotenv

# Load environment variables
load_dotenv(dotenv_path='../../.env') 

# --- 1. Database Configuration ---
DB_USER = 'postgres'
DB_PASSWORD = os.getenv('DB_PASSWORD', 'root')
DB_HOST = 'localhost'
DB_PORT = '5432'
DB_NAME = 'nifty_intraday_db'  

engine = create_engine(f'postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}')

def calculate_intraday_features(df):
    """
    Applies Layer 2 to Layer 9 feature engineering specifically tuned for 15-minute intraday data.
    """
    # Ensure data is sorted by time chronologically
    df = df.sort_values('date_time')
    
    # ==========================================
    # LAYER 2: Micro-Structure (Candle Physics)
    # ==========================================
    df['return_15m'] = df['close'].pct_change()
    df['candle_body'] = np.abs(df['close'] - df['open']) / df['open']
    df['upper_wick'] = (df['high'] - df[['open', 'close']].max(axis=1)) / df['open']
    df['lower_wick'] = (df[['open', 'close']].min(axis=1) - df['low']) / df['open']
    
    # ==========================================
    # LAYER 3: Rapid Intraday Trend
    # ==========================================
    df['ema_9'] = ta.trend.ema_indicator(df['close'], window=9)
    df['ema_21'] = ta.trend.ema_indicator(df['close'], window=21)
    
    # ==========================================
    # LAYER 4: Momentum & Order Flow
    # ==========================================
    df['rsi_14'] = ta.momentum.rsi(df['close'], window=14)
    df['roc_4'] = ta.momentum.roc(df['close'], window=4) 
    
    macd = ta.trend.MACD(df['close'], window_fast=12, window_slow=26, window_sign=9)
    df['macd_hist'] = macd.macd_diff()
    
    # ==========================================
    # LAYER 5: Intraday Volatility
    # ==========================================
    df['atr_14'] = ta.volatility.average_true_range(df['high'], df['low'], df['close'], window=14)
    bollinger = ta.volatility.BollingerBands(df['close'], window=20, window_dev=2)
    df['bollinger_width'] = bollinger.bollinger_wband()
    df['bollinger_position'] = bollinger.bollinger_pband()
    
    # ==========================================
    # LAYER 6: Volume Anomalies & VWAP
    # ==========================================
    df['volume_spike'] = df['volume'] / df['volume'].rolling(window=10).mean()
    df['vwap'] = ta.volume.volume_weighted_average_price(df['high'], df['low'], df['close'], df['volume'])
    df['vwap_distance'] = (df['close'] - df['vwap']) / df['vwap']
    df.drop(columns=['vwap'], inplace=True) 

    # ==========================================
    # LAYER 7: Time Context 
    # ==========================================
    df['hour'] = df['date_time'].dt.hour
    df['minute'] = df['date_time'].dt.minute

    # ==========================================
    # LAYER 8: Intraday Extremes & Micro-Pivots
    # ==========================================
    df['open_equals_low'] = (df['open'] == df['low']).astype(int)
    df['open_equals_high'] = (df['open'] == df['high']).astype(int)
    
    # Micro-pivots based on the LAST 15-minute candle
    df['pivot_point'] = (df['high'].shift(1) + df['low'].shift(1) + df['close'].shift(1)) / 3
    df['support_1'] = (2 * df['pivot_point']) - df['high'].shift(1)
    df['resistance_1'] = (2 * df['pivot_point']) - df['low'].shift(1)
    
    df['dist_to_pivot'] = (df['close'] - df['pivot_point']) / df['close']
    df['dist_to_s1'] = (df['close'] - df['support_1']) / df['close']
    df['dist_to_r1'] = (df['close'] - df['resistance_1']) / df['close']
    
    df.drop(columns=['pivot_point', 'support_1', 'resistance_1'], inplace=True)

    # ==========================================
    # LAYER 9: Targets & Stop-Loss Variables
    # ==========================================
    # Model Target: The close-to-close return of the next 15-minute candle
    df['target_return'] = df['close'].shift(-1) / df['close'] - 1
    
    # Backtester Target: The maximum downside of the next 15-minute candle
    df['target_low_return'] = (df['low'].shift(-1) - df['close']) / df['close']

    # Backtester Take-Profit: The maximum upside of the next 15-minute candle
    df['target_high_return'] = (df['high'].shift(-1) - df['close']) / df['close']

    # ==========================================
    # DATA CLEANING
    # ==========================================
    df.replace([np.inf, -np.inf], 0, inplace=True)
    
    # Drop the very last row of each stock because it has no "next" candle target
    df.dropna(subset=['target_return', 'target_low_return', 'target_high_return'], inplace=True)
    
    # Fill any remaining NaNs from rolling averages with 0
    df.fillna(0, inplace=True)
    
    return df

def run_intraday_pipeline():
    print("Fetching 15-minute raw data from database...")
    raw_df = pd.read_sql("SELECT * FROM raw_intraday_prices", engine)
    
    print(f"Applying intraday algorithmic indicators and targets to {len(raw_df['ticker'].unique())} tickers...")
    
    # We use a lambda to avoid the pandas grouping deprecation warning while keeping the 'ticker' column intact
    processed_df = raw_df.groupby('ticker', group_keys=False).apply(lambda x: calculate_intraday_features(x))
    
    print("Writing processed intraday features to database...")
    table_name = 'processed_intraday_features'
    
    # Replace the table entirely
    processed_df.to_sql(table_name, engine, if_exists='replace', index=False)
    
    print(f"Success! {len(processed_df)} fully prepared rows saved to '{table_name}'.")

if __name__ == "__main__":
    run_intraday_pipeline()