import os
import warnings
import pandas as pd
import numpy as np
import joblib
from sklearn.preprocessing import StandardScaler
from sqlalchemy import create_engine
from dotenv import load_dotenv

# Suppress Pandas FutureWarnings for cleaner terminal output
warnings.filterwarnings('ignore', category=FutureWarning)

# Load environment variables
load_dotenv(dotenv_path='../../.env') 

# --- 1. Database Configuration ---
DB_USER = 'postgres'
DB_PASSWORD = os.getenv('DB_PASSWORD', 'root')
DB_HOST = 'localhost'
DB_PORT = '5432'
DB_NAME = 'nifty_intraday_db'  

engine = create_engine(f'postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}')

# --- 2. Dynamic Pathing Configuration ---
# This guarantees the folder is created exactly where this script lives
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SAVE_DIR = os.path.join(BASE_DIR, 'data_tensors')
os.makedirs(SAVE_DIR, exist_ok=True)
WINDOW_SIZE = 60 # 60 periods = ~2.5 market days on a 15m chart

def create_sequences(df, feature_cols, target_col):
    X, y = [], []
    data_features = df[feature_cols].values
    data_target = df[target_col].values
    
    for i in range(len(df) - WINDOW_SIZE):
        X.append(data_features[i : i + WINDOW_SIZE])
        y.append(data_target[i + WINDOW_SIZE])
        
    return np.array(X, dtype=np.float32), np.array(y, dtype=np.float32)

def build_intraday_tensors():
    print("1. Loading processed intraday features from PostgreSQL...")
    df = pd.read_sql("SELECT * FROM processed_intraday_features", engine)
    
    # Sort strictly by ticker and time
    df.sort_values(by=['ticker', 'date_time'], inplace=True)
    
    exclude_cols = ['date_time', 'ticker', 'target_return', 'target_low_return', 'target_high_return']
    feature_cols = [col for col in df.columns if col not in exclude_cols]
    
    print(f"Total Intraday Features: {len(feature_cols)}")
    
    print("2. Performing Chronological Time-Based Split...")
    unique_dates = df['date_time'].dt.date.unique()
    unique_dates.sort()
    
    test_cutoff = pd.to_datetime(unique_dates[-10])
    val_cutoff = pd.to_datetime(unique_dates[-20])
    
    train_df = df[df['date_time'] < val_cutoff].copy()
    val_df = df[(df['date_time'] >= val_cutoff) & (df['date_time'] < test_cutoff)].copy()
    test_df = df[df['date_time'] >= test_cutoff].copy()
    
    print("3. Scaling Features (Preventing Data Leakage)...")
    scaler = StandardScaler()
    
    train_df.loc[:, feature_cols] = scaler.fit_transform(train_df[feature_cols])
    val_df.loc[:, feature_cols] = scaler.transform(val_df[feature_cols])
    test_df.loc[:, feature_cols] = scaler.transform(test_df[feature_cols])
    
    joblib.dump(scaler, os.path.join(SAVE_DIR, 'intraday_scaler.pkl'))
    
    print(f"4. Generating 3D Sliding Sequences (Window = {WINDOW_SIZE} periods)...")
    
    def process_split(split_df, split_name):
        X_list, y_list = [], []
        
        for ticker, stock_df in split_df.groupby('ticker'):
            if len(stock_df) <= WINDOW_SIZE:
                continue
                
            X_stock, y_stock = create_sequences(stock_df, feature_cols, 'target_return')
            X_list.append(X_stock)
            y_list.append(y_stock)
            
        X_final = np.concatenate(X_list, axis=0)
        y_final = np.concatenate(y_list, axis=0)
        
        print(f"   {split_name.capitalize()} Set -> X: {X_final.shape}, y: {y_final.shape}")
        
        np.save(os.path.join(SAVE_DIR, f'X_{split_name}.npy'), X_final)
        np.save(os.path.join(SAVE_DIR, f'y_{split_name}.npy'), y_final)
        
    process_split(train_df, 'train')
    process_split(val_df, 'val')
    process_split(test_df, 'test')
    
    print(f"\nSuccess! 3D Tensors saved to '{SAVE_DIR}'. Ready for Neural Network.")

if __name__ == "__main__":
    build_intraday_tensors()