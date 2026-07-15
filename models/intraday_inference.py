# import os
# import torch
# import torch.nn as nn
# import joblib
# import numpy as np
# import pandas as pd
# import ta
# import warnings
# from datetime import datetime, timedelta
# from tvDatafeed import TvDatafeed, Interval

# # Suppress warnings for cleaner console output
# warnings.filterwarnings('ignore', category=FutureWarning)
# warnings.filterwarnings('ignore', category=UserWarning)

# # --- Device Configuration ---
# device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

# # --- Dynamic Pathing ---
# BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# WEIGHTS_DIR = os.path.join(BASE_DIR, 'weights')

# SCALER_PATH = os.path.join(WEIGHTS_DIR, 'intraday_feature_scaler.pkl') 
# WEIGHTS_PATH = os.path.join(WEIGHTS_DIR, 'best_intraday_attention.pth')

# # ==========================================
# # 1. PYTORCH MODEL ARCHITECTURE
# # ==========================================
# class Attention(nn.Module):
#     def __init__(self, hidden_dim):
#         super(Attention, self).__init__()
#         self.attention = nn.Linear(hidden_dim, 1, bias=False)

#     def forward(self, lstm_outputs):
#         attn_weights = torch.softmax(self.attention(lstm_outputs), dim=1) 
#         context_vector = torch.sum(attn_weights * lstm_outputs, dim=1) 
#         return context_vector, attn_weights

# class StockCNNLSTMAttention(nn.Module):
#     def __init__(self, input_dim, cnn_out_channels, kernel_size, hidden_dim, num_layers, dropout_rate):
#         super(StockCNNLSTMAttention, self).__init__()
#         pad = kernel_size // 2 
        
#         self.conv1 = nn.Conv1d(in_channels=input_dim, out_channels=cnn_out_channels, kernel_size=kernel_size, padding=pad)
#         self.relu = nn.ReLU()
        
#         self.lstm = nn.LSTM(cnn_out_channels, hidden_dim, num_layers, batch_first=True, dropout=dropout_rate)
        
#         self.attention = Attention(hidden_dim)
#         self.fc = nn.Linear(hidden_dim, 1)
        
#     def forward(self, x):
#         x = x.permute(0, 2, 1) 
#         x = self.conv1(x)
#         x = self.relu(x)
#         x = x.permute(0, 2, 1) 
        
#         h0 = torch.zeros(self.lstm.num_layers, x.size(0), self.lstm.hidden_size).to(x.device)
#         c0 = torch.zeros(self.lstm.num_layers, x.size(0), self.lstm.hidden_size).to(x.device)
        
#         lstm_out, _ = self.lstm(x, (h0, c0))
#         context_vector, _ = self.attention(lstm_out)
        
#         out = self.fc(context_vector)
#         return out.squeeze(-1)

# # ==========================================
# # 2. DATA INGESTION & PREPROCESSING
# # ==========================================
# def fetch_live_intraday_tensor(ticker: str, window_size=60):
#     # Initialize TradingView Datafeed (Guest Mode)
#     tv = TvDatafeed()
#     clean_ticker = ticker.replace('.NS', '')
    
#     # Fetch directly from TradingView's NSE exchange data stream
#     df = tv.get_hist(symbol=clean_ticker, exchange='NSE', interval=Interval.in_15_minute, n_bars=250)
    
#     if df is None or df.empty or len(df) < (window_size + 25):
#         raise ValueError(f"Not enough live intraday data for {ticker} from TradingView.")
        
#     df.reset_index(inplace=True)
    
#     # Normalize datetime column name
#     df.rename(columns={'datetime': 'date_time'}, inplace=True)
#     df['ticker'] = ticker
    
#     # Layer 2: Micro-Structure
#     df['return_15m'] = df['close'].pct_change()
#     df['candle_body'] = np.abs(df['close'] - df['open']) / df['open']
#     df['upper_wick'] = (df['high'] - df[['open', 'close']].max(axis=1)) / df['open']
#     df['lower_wick'] = (df[['open', 'close']].min(axis=1) - df['low']) / df['open']
    
#     # Layer 3: Rapid Intraday Trend
#     df['ema_9'] = ta.trend.ema_indicator(df['close'], window=9)
#     df['ema_21'] = ta.trend.ema_indicator(df['close'], window=21)
    
#     # Layer 4: Momentum & Order Flow
#     df['rsi_14'] = ta.momentum.rsi(df['close'], window=14)
#     df['roc_4'] = ta.momentum.roc(df['close'], window=4) 
#     macd = ta.trend.MACD(df['close'], window_fast=12, window_slow=26, window_sign=9)
#     df['macd_hist'] = macd.macd_diff()
    
#     # Layer 5: Intraday Volatility
#     df['atr_14'] = ta.volatility.average_true_range(df['high'], df['low'], df['close'], window=14)
#     bollinger = ta.volatility.BollingerBands(df['close'], window=20, window_dev=2)
#     df['bollinger_width'] = bollinger.bollinger_wband()
#     df['bollinger_position'] = bollinger.bollinger_pband()
    
#     # Layer 6: Volume Anomalies & VWAP
#     df['volume_spike'] = df['volume'] / df['volume'].rolling(window=10).mean()
#     df['vwap'] = ta.volume.volume_weighted_average_price(df['high'], df['low'], df['close'], df['volume'])
#     df['vwap_distance'] = (df['close'] - df['vwap']) / df['vwap']
#     df.drop(columns=['vwap'], inplace=True) 

#     # Layer 7: Time Context 
#     df['hour'] = df['date_time'].dt.hour
#     df['minute'] = df['date_time'].dt.minute

#     # Layer 8: Intraday Extremes & Micro-Pivots
#     df['open_equals_low'] = (df['open'] == df['low']).astype(int)
#     df['open_equals_high'] = (df['open'] == df['high']).astype(int)
    
#     df['pivot_point'] = (df['high'].shift(1) + df['low'].shift(1) + df['close'].shift(1)) / 3
#     df['support_1'] = (2 * df['pivot_point']) - df['high'].shift(1)
#     df['resistance_1'] = (2 * df['pivot_point']) - df['low'].shift(1)
    
#     df['dist_to_pivot'] = (df['close'] - df['pivot_point']) / df['close']
#     df['dist_to_s1'] = (df['close'] - df['support_1']) / df['close']
#     df['dist_to_r1'] = (df['close'] - df['resistance_1']) / df['close']
    
#     df.drop(columns=['pivot_point', 'support_1', 'resistance_1'], inplace=True)
    
#     # Clean up
#     df.replace([np.inf, -np.inf], 0, inplace=True)
#     df.dropna(inplace=True) 
    
#     # Define exact features
#     exclude_cols = ['date_time', 'ticker', 'symbol']
#     feature_cols = [col for col in df.columns if col not in exclude_cols]
    
#     if len(feature_cols) != 26:
#         raise ValueError(f"Feature mismatch! Intraday Model expects 26, got {len(feature_cols)}: {feature_cols}")
        
#     if not os.path.exists(SCALER_PATH):
#         raise FileNotFoundError(f"Missing Scaler! Cannot predict without {SCALER_PATH}")
        
#     scaler = joblib.load(SCALER_PATH)
#     scaled_features = scaler.transform(df[feature_cols])
    
#     if len(scaled_features) < window_size:
#         raise ValueError(f"Not enough 15m periods left after dropping NaNs. Have {len(scaled_features)}, need {window_size}.")
        
#     current_price = df['close'].iloc[-1]
#     current_atr = df['atr_14'].iloc[-1]

#     final_sequence = scaled_features[-window_size:]
#     tensor_input = torch.tensor(final_sequence, dtype=torch.float32).unsqueeze(0).to(device)
    
#     return tensor_input, current_price, current_atr

# # ==========================================
# # 3. LIVE INFERENCE ENGINE
# # ==========================================
# def get_live_intraday_prediction(ticker: str) -> dict:
#     print(f"   [Intraday Engine] Scanning live 15m order flow for {ticker}...")
    
#     try:
#         tensor_input, current_price, current_atr = fetch_live_intraday_tensor(ticker, window_size=60)
        
#         if not os.path.exists(WEIGHTS_PATH):
#             raise FileNotFoundError(f"Weights not found at {WEIGHTS_PATH}")
            
#         model = StockCNNLSTMAttention(
#             input_dim=26, 
#             cnn_out_channels=128, 
#             kernel_size=5,
#             hidden_dim=128, 
#             num_layers=1, 
#             dropout_rate=0.0
#         ).to(device)
        
#         model.load_state_dict(torch.load(WEIGHTS_PATH, map_location=device, weights_only=True))
#         model.train() 
        
#         passes = 50
#         predictions = []
        
#         with torch.no_grad():
#             for _ in range(passes):
#                 out = model(tensor_input)
#                 predictions.append(out.item())
                
#         expected_return = np.mean(predictions)
#         uncertainty = np.std(predictions)
        
#         return {
#             "ticker": ticker,
#             "expected_return": round(float(expected_return), 6),
#             "uncertainty": round(float(uncertainty), 6),
#             "current_price": round(float(current_price), 2),
#             "current_atr": round(float(current_atr), 2),
#             "status": "success"
#         }
        
#     except Exception as e:
#         return {"ticker": ticker, "status": "error", "message": str(e)}

# if __name__ == "__main__":
#     result = get_live_intraday_prediction("RELIANCE")
#     print(result)

import os
import torch
import torch.nn as nn
import joblib
import numpy as np
import pandas as pd
import yfinance as yf
import ta
import warnings
import requests

warnings.filterwarnings('ignore', category=FutureWarning)
warnings.filterwarnings('ignore', category=UserWarning)

# --- Device Configuration ---
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

# --- Dynamic Pathing ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WEIGHTS_DIR = os.path.join(BASE_DIR, 'weights')

# Pointing to your newly pasted files!
SCALER_PATH = os.path.join(WEIGHTS_DIR, 'dual_intraday_attention_v3.pkl') 
WEIGHTS_PATH = os.path.join(WEIGHTS_DIR, 'dual_intraday_attention_v3.pth')

# ==========================================
# 1. V3 DUAL-BOUNDARY ARCHITECTURE
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
        
        # Dual outputs for High and Low boundaries
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
# 2. DATA INGESTION & 28-FEATURE ENGINEERING
# ==========================================
def fetch_live_intraday_tensor(ticker: str, window_size=60):
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36'
    })
    
    stock = yf.Ticker(f"{ticker}.NS" if not ticker.endswith(".NS") else ticker, session=session)
    df = stock.history(period="10d", interval="15m")
    
    if df.empty or len(df) < (window_size + 25):
        raise ValueError(f"Not enough live intraday data for {ticker}.")
        
    df.reset_index(inplace=True)
    date_col = 'Datetime' if 'Datetime' in df.columns else 'Date'
    df.rename(columns={date_col: 'date_time', 'Open': 'open', 'High': 'high', 'Low': 'low', 'Close': 'close', 'Volume': 'volume'}, inplace=True)
    df['date_time'] = pd.to_datetime(df['date_time']).dt.tz_localize(None)
    
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
    
    # Extract features
    exclude_cols = ['date_time', 'ticker', 'Stock Splits', 'Dividends']
    feature_cols = [col for col in df.columns if col not in exclude_cols]
    
    if len(feature_cols) != 28:
        raise ValueError(f"Feature mismatch! V3 Model expects 28, got {len(feature_cols)}.")
        
    scaler = joblib.load(SCALER_PATH)
    scaled_features = scaler.transform(df[feature_cols])
    
    current_price = df['close'].iloc[-1]
    
    final_sequence = scaled_features[-window_size:]
    tensor_input = torch.tensor(final_sequence, dtype=torch.float32).unsqueeze(0).to(device)
    
    return tensor_input, current_price

# ==========================================
# 3. LIVE MC DROPOUT INFERENCE ENGINE
# ==========================================
def get_live_intraday_prediction(ticker: str) -> dict:
    try:
        tensor_input, current_price = fetch_live_intraday_tensor(ticker, window_size=60)
        
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
        
        # MC Dropout enabled
        model.train() 
        
        passes = 50
        high_preds, low_preds = [], []
        
        with torch.no_grad():
            for _ in range(passes):
                out = model(tensor_input)
                high_preds.append(out[0][0].item())
                low_preds.append(out[0][1].item())
                
        expected_high = np.mean(high_preds)
        expected_low = np.mean(low_preds)
        uncertainty = np.std(high_preds) + np.std(low_preds)
        
        return {
            "ticker": ticker,
            "expected_high": float(expected_high),
            "expected_low": float(expected_low),
            "uncertainty": float(uncertainty),
            "current_price": float(current_price),
            "status": "success"
        }
        
    except Exception as e:
        return {"ticker": ticker, "status": "error", "message": str(e)}