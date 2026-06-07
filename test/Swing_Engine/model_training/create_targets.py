# import pandas as pd
# from sqlalchemy import create_engine

# # Load environment variables if you set up the .env file!
# import os
# from dotenv import load_dotenv
# load_dotenv()

# DB_PASSWORD = os.getenv('DB_PASSWORD', 'root') # Fallback to 'root' if .env fails
# engine = create_engine(f'postgresql://postgres:{DB_PASSWORD}@localhost:5432/nifty_lstm_db')

# def engineer_target_variable():
#     print("1. Loading Master Features from PostgreSQL...")
#     df = pd.read_sql("SELECT * FROM master_features_final", engine)
    
#     # Ensure chronological order per stock (CRITICAL for shifting data)
#     df['date'] = pd.to_datetime(df['date'])
#     df.sort_values(by=['Ticker', 'date'], inplace=True)
    
#     print("2. Calculating Intraday Target Returns...")
    
#     def calculate_intraday_target(stock_df):
#         # Calculate the return if you bought at the open and sold at the close
#         stock_df['intraday_return'] = (stock_df['close'] - stock_df['open']) / stock_df['open']
        
#         # SHIFT -1: We shift tomorrow's intraday return up to today's row.
#         # This means today's features are aligned with tomorrow's trading outcome.
#         stock_df['target_return'] = stock_df['intraday_return'].shift(-1)
        
#         return stock_df

#     # Apply the shift strictly per stock so Reliance's data doesn't bleed into TCS's data
#     df = df.groupby('Ticker', group_keys=False).apply(calculate_intraday_target)
    
#     print("3. Cleaning up final NaNs...")
#     # The very last day of our dataset won't have a "tomorrow", so target_return will be NaN.
#     # We drop the temporary column and the final NaN row.
#     df.drop(columns=['intraday_return'], inplace=True)
#     df.dropna(subset=['target_return'], inplace=True)
    
#     print("4. Saving Model-Ready Dataset to PostgreSQL...")
#     table_name = 'model_ready_data'
#     df.to_sql(table_name, engine, if_exists='replace', index=False)
    
#     print(f"Success! {len(df)} rows ready for machine learning saved to '{table_name}'.")

# if __name__ == "__main__":
#     engineer_target_variable()


import pandas as pd
from sqlalchemy import create_engine
import os
from dotenv import load_dotenv

load_dotenv()

DB_PASSWORD = os.getenv('DB_PASSWORD', 'root')
engine = create_engine(f'postgresql://postgres:{DB_PASSWORD}@localhost:5432/nifty_lstm_db')

def engineer_target_variable():
    print("1. Loading Master Features from PostgreSQL...")
    df = pd.read_sql("SELECT * FROM master_features_final", engine)
    
    # Ensure chronological order per stock
    df['date'] = pd.to_datetime(df['date'])
    df.sort_values(by=['Ticker', 'date'], inplace=True)
    
    print("2. Calculating Intraday Targets and Stop-Loss Levels...")
    
    def calculate_intraday_target(stock_df):
        # --- ORIGINAL TARGET (For Model Prediction) ---
        stock_df['intraday_return'] = (stock_df['close'] - stock_df['open']) / stock_df['open']
        stock_df['target_return'] = stock_df['intraday_return'].shift(-1)
        
        # --- NEW PATH B TARGET (For Backtester Stop-Loss) ---
        # Calculates the deepest percentage drop from the Open price
        stock_df['intraday_low_return'] = (stock_df['low'] - stock_df['open']) / stock_df['open']
        stock_df['target_low_return'] = stock_df['intraday_low_return'].shift(-1)
        
        return stock_df

    # Apply the shift strictly per stock
    df = df.groupby('Ticker', group_keys=False).apply(calculate_intraday_target)
    
    print("3. Cleaning up temporary math columns...")
    df.drop(columns=['intraday_return', 'intraday_low_return'], inplace=True)
    df.dropna(subset=['target_return', 'target_low_return'], inplace=True)
    
    print("4. Saving Model-Ready Dataset to PostgreSQL...")
    table_name = 'model_ready_data'
    df.to_sql(table_name, engine, if_exists='replace', index=False)
    
    print(f"Success! {len(df)} rows saved to '{table_name}' with Stop-Loss data embedded.")

if __name__ == "__main__":
    engineer_target_variable()