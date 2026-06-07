import pandas as pd
import numpy as np
import torch
import torch.nn as nn
import joblib
import os
from sqlalchemy import create_engine
from dotenv import load_dotenv
from tqdm import tqdm

device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

# --- Dynamic Pathing ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SCALER_PATH = os.path.join(BASE_DIR, 'data_tensors', 'intraday_scaler.pkl')
WEIGHTS_PATH = os.path.join(BASE_DIR, '..', 'weights', 'best_intraday_attention.pth')
CACHE_DIR = os.path.join(BASE_DIR, 'cache')
os.makedirs(CACHE_DIR, exist_ok=True)
CACHE_FILE = os.path.join(CACHE_DIR, 'intraday_attention_cache.csv')

# ==========================================
# V4 COMPONENT: THE ATTENTION MECHANISM
# ==========================================
class Attention(nn.Module):
    def __init__(self, hidden_dim):
        super(Attention, self).__init__()
        self.attention = nn.Linear(hidden_dim, 1, bias=False)

    def forward(self, lstm_outputs):
        attn_weights = torch.softmax(self.attention(lstm_outputs), dim=1) 
        context_vector = torch.sum(attn_weights * lstm_outputs, dim=1) 
        return context_vector, attn_weights

# ==========================================
# THE INTRADAY ATTENTION ARCHITECTURE
# ==========================================
class StockCNNLSTMAttention(nn.Module):
    def __init__(self, input_dim, cnn_out_channels, kernel_size, hidden_dim, num_layers, dropout_rate):
        super(StockCNNLSTMAttention, self).__init__()
        pad = kernel_size // 2 
        
        self.conv1 = nn.Conv1d(in_channels=input_dim, out_channels=cnn_out_channels, kernel_size=kernel_size, padding=pad)
        self.relu = nn.ReLU()
        
        self.lstm = nn.LSTM(cnn_out_channels, hidden_dim, num_layers, batch_first=True, dropout=dropout_rate)
        
        self.attention = Attention(hidden_dim)
        self.fc = nn.Linear(hidden_dim, 1)
        
    def forward(self, x):
        x = x.permute(0, 2, 1) 
        x = self.conv1(x)
        x = self.relu(x)
        x = x.permute(0, 2, 1) 
        
        h0 = torch.zeros(self.lstm.num_layers, x.size(0), self.lstm.hidden_size).to(device)
        c0 = torch.zeros(self.lstm.num_layers, x.size(0), self.lstm.hidden_size).to(device)
        
        lstm_out, _ = self.lstm(x, (h0, c0))
        context_vector, _ = self.attention(lstm_out)
        
        out = self.fc(context_vector)
        return out.squeeze(-1)

def generate_intraday_cache():
    print("1. Loading Intraday Data from PostgreSQL...")
    load_dotenv(dotenv_path='../../.env') 
    DB_PASSWORD = os.getenv('DB_PASSWORD', 'root') 
    engine = create_engine(f'postgresql://postgres:{DB_PASSWORD}@localhost:5432/nifty_intraday_db')
    
    # We load the entire dataset so the backtester can run over any period
    df = pd.read_sql("SELECT * FROM processed_intraday_features", engine)
    df['date_time'] = pd.to_datetime(df['date_time'])
    df.sort_values(by=['ticker', 'date_time'], inplace=True)
    
    # exclude_cols = ['date_time', 'ticker', 'target_return', 'target_low_return']
    exclude_cols = ['date_time', 'ticker', 'target_return', 'target_low_return', 'target_high_return']
    feature_cols = [col for col in df.columns if col not in exclude_cols]
    
    print("2. Scaling all 26 Features...")
    scaler = joblib.load(SCALER_PATH)
    df[feature_cols] = scaler.transform(df[feature_cols])
    
    print("3. Initializing 1-Layer Intraday Attention Model...")
    model = StockCNNLSTMAttention(
        input_dim=26, 
        cnn_out_channels=128, 
        kernel_size=5,
        hidden_dim=128, 
        num_layers=1, 
        dropout_rate=0.0
    ).to(device)
    
    model.load_state_dict(torch.load(WEIGHTS_PATH, weights_only=True))
    model.eval() # Standard eval mode since dropout is 0.0 anyway
    
    WINDOW_SIZE = 60 # 60 periods for intraday
    results_list = []
    grouped_stocks = df.groupby('ticker')
    
    print("4. Generating Fast Deterministic Predictions...")
    with torch.no_grad():
        for ticker, stock_df in tqdm(grouped_stocks, desc="Analyzing Stocks", unit="stock"):
            if len(stock_df) <= WINDOW_SIZE:
                continue
                
            features = stock_df[feature_cols].values
            actual_returns = stock_df['target_return'].values
            actual_lows = stock_df['target_low_return'].values
            dates = stock_df['date_time'].values
            
            for i in range(len(stock_df) - WINDOW_SIZE):
                x_seq = torch.tensor(features[i : i + WINDOW_SIZE], dtype=torch.float32).unsqueeze(0).to(device)
                
                # Single rapid pass instead of 50 loops
                pred_mean = model(x_seq).item()
                
                results_list.append({
                    'date_time': dates[i + WINDOW_SIZE],
                    'ticker': ticker,
                    'Predicted_Return': pred_mean,
                    'Uncertainty': 0.0, # Hardcoded because there is no dropout variance
                    'Actual_Return': actual_returns[i + WINDOW_SIZE],
                    'Actual_Low': actual_lows[i + WINDOW_SIZE],
                    'Actual_High': stock_df['target_high_return'].values[i + WINDOW_SIZE]
                })
                
    results_df = pd.DataFrame(results_list)
    print(f"\nSaving Intraday predictions to cache: {CACHE_FILE}")
    results_df.to_csv(CACHE_FILE, index=False)
    print("Done! Ready for High-Frequency Simulation.")

if __name__ == "__main__":
    generate_intraday_cache()