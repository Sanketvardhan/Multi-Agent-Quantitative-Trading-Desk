import os
from dotenv import load_dotenv

load_dotenv() # This loads the variables from the .env file

import pandas as pd
import numpy as np
from sqlalchemy import create_engine


# Format: postgresql://username:password@host:port/database_name
DB_USER = 'postgres'
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_HOST = 'localhost'
DB_PORT = '5432'
DB_NAME = 'nifty_lstm_db'

# Database Connection
engine = create_engine(f'postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}')

print("Fetching data for validation...")
df = pd.read_sql("SELECT * FROM processed_features_l2_l6", engine)

print("\n--- 1. Checking for Fatal Errors (NaNs & Infinity) ---")
# This should be exactly 0. If it's not, the LSTM will crash.
inf_count = np.isinf(df.select_dtypes(include=[np.number])).sum().sum()
nan_count = df.isna().sum().sum()
print(f"Total Infinity values: {inf_count}")
print(f"Total NaN values: {nan_count}")

print("\n--- 2. Validating Mathematical Bounds ---")
# RSI must strictly be between 0 and 100. Let's verify.
print(f"RSI Min: {df['rsi_14'].min():.2f} (Should be >= 0)")
print(f"RSI Max: {df['rsi_14'].max():.2f} (Should be <= 100)")

# Stochastic RSI must be between 0 and 1.
print(f"Stoch RSI Min: {df['stoch_rsi'].min():.2f} (Should be >= 0)")
print(f"Stoch RSI Max: {df['stoch_rsi'].max():.2f} (Should be <= 1)")

print("\n--- 3. Validating Feature Distributions ---")
# Look at standard deviations to ensure features aren't wildly skewed
print(df[['daily_return', 'high_low_range', 'volume_change']].describe().round(4))