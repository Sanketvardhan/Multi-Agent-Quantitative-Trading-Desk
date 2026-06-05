# import pandas as pd
# import numpy as np
# import os
# import joblib
# from sqlalchemy import create_engine
# from sklearn.preprocessing import StandardScaler
# from dotenv import load_dotenv

# load_dotenv()
# DB_PASSWORD = os.getenv('DB_PASSWORD', 'root')
# engine = create_engine(f'postgresql://postgres:{DB_PASSWORD}@localhost:5432/nifty_lstm_db')

# # Configuration
# WINDOW_SIZE = 30
# SAVE_DIR = 'model_training/data_tensors/'
# os.makedirs(SAVE_DIR, exist_ok=True)

# def create_sequences(df, feature_cols, target_col):
#     """
#     Takes a dataframe for a SINGLE stock and generates 30-day sliding windows.
#     """
#     X, y = [], []
    
#     # Extract underlying numpy arrays for speed
#     data_features = df[feature_cols].values
#     data_target = df[target_col].values
    
#     # Slide the 30-day window across the stock's timeline
#     for i in range(len(df) - WINDOW_SIZE):
#         X.append(data_features[i : i + WINDOW_SIZE])
#         y.append(data_target[i + WINDOW_SIZE])
        
#     return np.array(X), np.array(y)

# def build_deep_learning_dataset():
#     print("1. Loading Model-Ready Data from PostgreSQL...")
#     df = pd.read_sql("SELECT * FROM model_ready_data", engine)
#     df['date'] = pd.to_datetime(df['date'])
#     df.sort_values(by=['Ticker', 'date'], inplace=True)
    
#     print("2. Performing Chronological Split...")
#     train_df = df[df['date'].dt.year <= 2022].copy()
#     val_df = df[df['date'].dt.year == 2023].copy()
#     test_df = df[df['date'].dt.year >= 2024].copy()
    
#     # Identify feature columns (everything except date, Ticker, and target)
#     exclude_cols = ['date', 'Ticker', 'target_return']
#     feature_cols = [col for col in df.columns if col not in exclude_cols]
    
#     print("3. Scaling Features (Preventing Data Leakage)...")
#     scaler = StandardScaler()
    
#     # Fit scaler ONLY on training features, then transform all
#     train_df[feature_cols] = scaler.fit_transform(train_df[feature_cols])
#     val_df[feature_cols] = scaler.transform(val_df[feature_cols])
#     test_df[feature_cols] = scaler.transform(test_df[feature_cols])
    
#     # Save the scaler so we can use it in live production later!
#     joblib.dump(scaler, os.path.join(SAVE_DIR, 'feature_scaler.pkl'))
    
#     print("4. Generating 3D Sliding Sequences (Window = 30 days)...")
    
#     def process_split(split_df, split_name):
#         X_list, y_list = [], []
        
#         # Group by ticker so 30-day windows don't overlap between Reliance and TCS
#         for ticker, stock_df in split_df.groupby('Ticker'):
#             # If a stock (like JIOFIN) doesn't have enough days to form a window, skip it
#             if len(stock_df) <= WINDOW_SIZE:
#                 continue
                
#             X_stock, y_stock = create_sequences(stock_df, feature_cols, 'target_return')
#             X_list.append(X_stock)
#             y_list.append(y_stock)
            
#         # Concatenate all stocks together into final master tensors
#         X_final = np.concatenate(X_list, axis=0)
#         y_final = np.concatenate(y_list, axis=0)
        
#         print(f"   {split_name} Set -> X: {X_final.shape}, y: {y_final.shape}")
        
#         # Save locally as fast-loading binary files
#         np.save(os.path.join(SAVE_DIR, f'X_{split_name}.npy'), X_final)
#         np.save(os.path.join(SAVE_DIR, f'y_{split_name}.npy'), y_final)
        
#     process_split(train_df, 'train')
#     process_split(val_df, 'val')
#     process_split(test_df, 'test')
    
#     print(f"\nSuccess! 3D Tensors saved to '{SAVE_DIR}'. Ready for Neural Network.")

# if __name__ == "__main__":
#     build_deep_learning_dataset()

import pandas as pd
import numpy as np
import os
import joblib
from sqlalchemy import create_engine
from sklearn.preprocessing import StandardScaler
from dotenv import load_dotenv

load_dotenv()
DB_PASSWORD = os.getenv('DB_PASSWORD', 'root')
engine = create_engine(f'postgresql://postgres:{DB_PASSWORD}@localhost:5432/nifty_lstm_db')

# Configuration
WINDOW_SIZE = 30
SAVE_DIR = 'model_training/data_tensors/'
os.makedirs(SAVE_DIR, exist_ok=True)

def create_sequences(df, feature_cols, target_col):
    X, y = [], []
    data_features = df[feature_cols].values
    data_target = df[target_col].values
    
    for i in range(len(df) - WINDOW_SIZE):
        X.append(data_features[i : i + WINDOW_SIZE])
        y.append(data_target[i + WINDOW_SIZE])
        
    return np.array(X), np.array(y)

def build_deep_learning_dataset():
    print("1. Loading Model-Ready Data from PostgreSQL...")
    df = pd.read_sql("SELECT * FROM model_ready_data", engine)
    df['date'] = pd.to_datetime(df['date'])
    df.sort_values(by=['Ticker', 'date'], inplace=True)
    
    print("2. Performing Chronological Split...")
    train_df = df[df['date'].dt.year <= 2022].copy()
    val_df = df[df['date'].dt.year == 2023].copy()
    test_df = df[df['date'].dt.year >= 2024].copy()
    
    # CRITICAL FIX: Explicitly exclude target_low_return so it doesn't get fed into the AI
    exclude_cols = ['date', 'Ticker', 'target_return', 'target_low_return']
    feature_cols = [col for col in df.columns if col not in exclude_cols]
    
    print("3. Scaling Features (Preventing Data Leakage)...")
    scaler = StandardScaler()
    
    train_df[feature_cols] = scaler.fit_transform(train_df[feature_cols])
    val_df[feature_cols] = scaler.transform(val_df[feature_cols])
    test_df[feature_cols] = scaler.transform(test_df[feature_cols])
    
    joblib.dump(scaler, os.path.join(SAVE_DIR, 'feature_scaler.pkl'))
    
    print("4. Generating 3D Sliding Sequences (Window = 30 days)...")
    
    def process_split(split_df, split_name):
        X_list, y_list = [], []
        
        for ticker, stock_df in split_df.groupby('Ticker'):
            if len(stock_df) <= WINDOW_SIZE:
                continue
                
            X_stock, y_stock = create_sequences(stock_df, feature_cols, 'target_return')
            X_list.append(X_stock)
            y_list.append(y_stock)
            
        X_final = np.concatenate(X_list, axis=0)
        y_final = np.concatenate(y_list, axis=0)
        
        print(f"   {split_name} Set -> X: {X_final.shape}, y: {y_final.shape}")
        
        np.save(os.path.join(SAVE_DIR, f'X_{split_name}.npy'), X_final)
        np.save(os.path.join(SAVE_DIR, f'y_{split_name}.npy'), y_final)
        
    process_split(train_df, 'train')
    process_split(val_df, 'val')
    process_split(test_df, 'test')
    
    print(f"\nSuccess! 3D Tensors saved to '{SAVE_DIR}'. Ready for Neural Network.")

if __name__ == "__main__":
    build_deep_learning_dataset()