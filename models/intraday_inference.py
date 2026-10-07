import os
import torch
import torch.nn as nn
import joblib
import numpy as np
import pandas as pd
import ta
import warnings

# Use centralized data engine
from core.data_engine import data_engine

warnings.filterwarnings('ignore', category=FutureWarning)
warnings.filterwarnings('ignore', category=UserWarning)

# --- Device Configuration ---
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

# --- Dynamic Pathing ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WEIGHTS_DIR = os.path.join(BASE_DIR, 'weights')

SCALER_PATH = os.path.join(WEIGHTS_DIR, 'dual_intraday_attention_v3.pkl') 
WEIGHTS_PATH = os.path.join(WEIGHTS_DIR, 'dual_intraday_attention_v3.pth')

# ==========================================
# 1. PYTORCH ATTENTION ARCHITECTURE
# ==========================================
class Attention(nn.Module):
    def __init__(self, hidden_dim):
        super(Attention, self).__init__()
        self.attention = nn.Linear(hidden_dim, 1, bias=False)

    def forward(self, lstm_outputs):
        attn_weights = torch.softmax(self.attention(lstm_outputs), dim=1) 
        context_vector = torch.sum(attn_weights * lstm_outputs, dim=1) 
        return context_vector, attn_weights

class StockCNNLSTMAttention(nn.Module):
    def __init__(self, input_dim, cnn_out_channels, kernel_size, hidden_dim, num_layers, dropout_rate):
        super(StockCNNLSTMAttention, self).__init__()
        pad = kernel_size // 2 
        
        self.conv1 = nn.Conv1d(in_channels=input_dim, out_channels=cnn_out_channels, kernel_size=kernel_size, padding=pad)
        self.relu = nn.ReLU()
        self.lstm = nn.LSTM(cnn_out_channels, hidden_dim, num_layers, batch_first=True, dropout=dropout_rate)
        self.attention = Attention(hidden_dim)
        self.fc = nn.Linear(hidden_dim, 2)
        
    def forward(self, x):
        x = x.permute(0, 2, 1) 
        x = self.conv1(x)
        x = self.relu(x)
        x = x.permute(0, 2, 1) 
        
        h0 = torch.zeros(self.lstm.num_layers, x.size(0), self.lstm.hidden_size).to(x.device)
        c0 = torch.zeros(self.lstm.num_layers, x.size(0), self.lstm.hidden_size).to(x.device)
        
        lstm_out, _ = self.lstm(x, (h0, c0))
        context_vector, _ = self.attention(lstm_out)
        return self.fc(context_vector)

# ==========================================
# 2. FEATURE ENGINEERING (28 FEATURES)
# ==========================================
def fetch_live_intraday_tensor(ticker: str, window_size=60):
    df = data_engine.fetch_historical_bars(ticker, interval="15m", period="10d")
    
    if df.empty or len(df) < (window_size + 25):
        raise ValueError(f"Not enough live intraday data for {ticker}. Need at least {window_size + 25} bars.")
        
    # 1. Physics & Trend
    df['return_15m'] = df['close'].pct_change()
    df['candle_body'] = np.abs(df['close'] - df['open']) / df['open']
    df['upper_wick'] = (df['high'] - df[['open', 'close']].max(axis=1)) / df['open']
    df['lower_wick'] = (df[['open', 'close']].min(axis=1) - df['low']) / df['open']
    df['ema_9'] = ta.trend.ema_indicator(df['close'], window=9)
    df['ema_21'] = ta.trend.ema_indicator(df['close'], window=21)
    
    # 2. Macro Anchors
    df['ema_9_21_ratio'] = df['ema_9'] / df['ema_21']
    df['date_only'] = df['date_time'].dt.date
    df['daily_open'] = df.groupby('date_only')['open'].transform('first')
    df['dist_from_daily_open'] = (df['close'] - df['daily_open']) / df['daily_open']
    df.drop(columns=['date_only', 'daily_open'], inplace=True)
    
    # 3. Momentum & Volatility
    df['rsi_14'] = ta.momentum.rsi(df['close'], window=14)
    df['roc_4'] = ta.momentum.roc(df['close'], window=4) 
    macd = ta.trend.MACD(df['close'], window_fast=12, window_slow=26, window_sign=9)
    df['macd_hist'] = macd.macd_diff()
    df['atr_14'] = ta.volatility.average_true_range(df['high'], df['low'], df['close'], window=14)
    bollinger = ta.volatility.BollingerBands(df['close'], window=20, window_dev=2)
    df['bollinger_width'] = bollinger.bollinger_wband()
    df['bollinger_position'] = bollinger.bollinger_pband()
    
    # 4. Volume & Time
    df['volume_spike'] = df['volume'] / df['volume'].rolling(window=10).mean()
    df['vwap'] = ta.volume.volume_weighted_average_price(df['high'], df['low'], df['close'], df['volume'])
    df['vwap_distance'] = (df['close'] - df['vwap']) / df['vwap']
    df.drop(columns=['vwap'], inplace=True) 
    df['hour'] = df['date_time'].dt.hour
    df['minute'] = df['date_time'].dt.minute
    
    # 5. Micro Pivots
    df['open_equals_low'] = (df['open'] == df['low']).astype(int)
    df['open_equals_high'] = (df['open'] == df['high']).astype(int)
    df['pivot_point'] = (df['high'].shift(1) + df['low'].shift(1) + df['close'].shift(1)) / 3
    df['support_1'] = (2 * df['pivot_point']) - df['high'].shift(1)
    df['resistance_1'] = (2 * df['pivot_point']) - df['low'].shift(1)
    df['dist_to_pivot'] = (df['close'] - df['pivot_point']) / df['close']
    df['dist_to_s1'] = (df['close'] - df['support_1']) / df['close']
    df['dist_to_r1'] = (df['close'] - df['resistance_1']) / df['close']
    df.drop(columns=['pivot_point', 'support_1', 'resistance_1'], inplace=True)

    df.replace([np.inf, -np.inf], 0, inplace=True)
    df.fillna(0, inplace=True)
    
    # Extract feature columns
    exclude_cols = ['date_time', 'ticker', 'Stock Splits', 'Dividends']
    feature_cols = [col for col in df.columns if col not in exclude_cols]
    
    if len(feature_cols) != 28:
        raise ValueError(f"Feature mismatch! Model expects 28, got {len(feature_cols)}.")
        
    if not os.path.exists(SCALER_PATH):
        raise FileNotFoundError(f"Missing Scaler at {SCALER_PATH}")
        
    scaler = joblib.load(SCALER_PATH)
    scaled_features = scaler.transform(df[feature_cols])
    
    latest_atr = float(df['atr_14'].iloc[-1])
    live_price = data_engine.get_realtime_price(ticker) or float(df['close'].iloc[-1])
    latest_ema_21 = float(df['ema_21'].iloc[-1])
    latest_rsi_14 = float(df['rsi_14'].iloc[-1])
    
    final_sequence = scaled_features[-window_size:]
    tensor_input = torch.tensor(final_sequence, dtype=torch.float32).unsqueeze(0).to(device)
    
    return tensor_input, live_price, latest_atr, latest_ema_21, latest_rsi_14

# ==========================================
# 3. LIVE INFERENCE ENGINE
# ==========================================
def get_live_intraday_prediction(ticker: str) -> dict:
    try:
        tensor_input, current_price, current_atr, ema_21, rsi_14 = fetch_live_intraday_tensor(ticker, window_size=60)
        
        if not os.path.exists(WEIGHTS_PATH):
            raise FileNotFoundError(f"Weights not found at {WEIGHTS_PATH}")
            
        model = StockCNNLSTMAttention(
            input_dim=28, 
            cnn_out_channels=128, 
            kernel_size=5,
            hidden_dim=128, 
            num_layers=2, 
            dropout_rate=0.3881
        ).to(device)
        
        model.load_state_dict(torch.load(WEIGHTS_PATH, map_location=device, weights_only=True))
        model.eval() # Deterministic inference
        
        with torch.no_grad():
            out = model(tensor_input)
            expected_high = float(out[0][0].item())
            expected_low = float(out[0][1].item())
            
        # Calibrated baseline uncertainty
        uncertainty = abs(expected_high - abs(expected_low))
        
        return {
            "ticker": ticker,
            "expected_high": round(expected_high, 5),
            "expected_low": round(expected_low, 5),
            "uncertainty": round(uncertainty, 5),
            "current_price": round(float(current_price), 2),
            "current_atr": round(float(current_atr), 2),
            "ema_21": round(float(ema_21), 2),
            "rsi_14": round(float(rsi_14), 2),
            "status": "success"
        }
        
    except Exception as e:
        return {"ticker": ticker, "status": "error", "message": str(e)}

if __name__ == "__main__":
    result = get_live_intraday_prediction("RELIANCE")
    print(result)