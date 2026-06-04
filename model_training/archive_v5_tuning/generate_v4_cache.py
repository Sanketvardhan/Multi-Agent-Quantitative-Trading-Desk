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
# THE V4 ARCHITECTURE
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

def generate_v4_cache():
    # Brand new cache file for the Attention model
    CACHE_FILE = 'model_training/cache/attention_v4_mc_cache.csv'
    
    print("1. Loading 2024 Test Data from PostgreSQL...")
    load_dotenv()
    DB_PASSWORD = os.getenv('DB_PASSWORD') 
    engine = create_engine(f'postgresql://postgres:{DB_PASSWORD}@localhost:5432/nifty_lstm_db')
    
    df = pd.read_sql("SELECT * FROM model_ready_data WHERE date >= '2024-01-01'", engine)
    df['date'] = pd.to_datetime(df['date'])
    df.sort_values(by=['Ticker', 'date'], inplace=True)
    
    exclude_cols = ['date', 'Ticker', 'target_return', 'target_low_return']
    feature_cols = [col for col in df.columns if col not in exclude_cols]
    
    print("2. Scaling all 52 Features...")
    scaler = joblib.load('model_training/data_tensors/feature_scaler.pkl')
    df[feature_cols] = scaler.transform(df[feature_cols])
    
    print("3. Initializing V4 Attention Model...")
    # Injecting V4 Parameters
    model = StockCNNLSTMAttention(
        input_dim=52, 
        cnn_out_channels=128, 
        kernel_size=5,
        hidden_dim=64, 
        num_layers=2, 
        dropout_rate=0.32768562460671624
    ).to(device)
    
    model.load_state_dict(torch.load('weights/best_attention_V4.pth', weights_only=True))
    model.train() # KEEP DROPOUT ACTIVE FOR BAYESIAN UNCERTAINTY
    
    WINDOW_SIZE = 30
    MC_PASSES = 50
    results_list = []
    
    grouped_stocks = df.groupby('Ticker')
    
    print("4. Generating Probabilistic Predictions (50 passes per day)...")
    with torch.no_grad():
        for ticker, stock_df in tqdm(grouped_stocks, desc="Analyzing Stocks", unit="stock"):
            if len(stock_df) <= WINDOW_SIZE:
                continue
                
            features = stock_df[feature_cols].values
            actual_returns = stock_df['target_return'].values
            actual_lows = stock_df['target_low_return'].values
            dates = stock_df['date'].values
            
            for i in range(len(stock_df) - WINDOW_SIZE):
                x_seq = torch.tensor(features[i : i + WINDOW_SIZE], dtype=torch.float32).unsqueeze(0).to(device)
                
                mc_predictions = []
                for _ in range(MC_PASSES):
                    pred = model(x_seq).item()
                    mc_predictions.append(pred)
                
                pred_mean = np.mean(mc_predictions) 
                pred_std = np.std(mc_predictions)   
                
                results_list.append({
                    'Date': dates[i + WINDOW_SIZE],
                    'Ticker': ticker,
                    'Predicted_Return': pred_mean,
                    'Uncertainty': pred_std,
                    'Actual_Return': actual_returns[i + WINDOW_SIZE],
                    'Actual_Low': actual_lows[i + WINDOW_SIZE]
                })
                
    results_df = pd.DataFrame(results_list)
    os.makedirs('model_training/cache', exist_ok=True)
    print(f"\nSaving V4 predictions to cache: {CACHE_FILE}")
    results_df.to_csv(CACHE_FILE, index=False)
    print("Done! Ready for Dynamic Risk Simulation.")

if __name__ == "__main__":
    generate_v4_cache()