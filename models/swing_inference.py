# import os
# import torch
# import torch.nn as nn
# import joblib
# import numpy as np
# import pandas as pd
# import ta
# import warnings
# import random
# import time
# from tvDatafeed import TvDatafeed, Interval

# # Suppress underlying layout warnings
# warnings.filterwarnings('ignore', category=FutureWarning)
# warnings.filterwarnings('ignore', category=UserWarning)

# # --- Device Configuration ---
# device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

# # --- Dynamic Pathing ---
# BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# WEIGHTS_DIR = os.path.join(BASE_DIR, 'weights')

# SCALER_PATH = os.path.join(WEIGHTS_DIR, 'swing_feature_scaler.pkl') 
# WEIGHTS_PATH = os.path.join(WEIGHTS_DIR, 'best_swing_attention_V4.pth')

# # TradingView Exchange & Symbol Structure Map
# MACRO_TICKERS = {
#     'NIFTY50': {'symbol': 'NIFTY', 'exchange': 'NSE'},
#     'BANKNIFTY': {'symbol': 'BANKNIFTY', 'exchange': 'NSE'},
#     'INDIAVIX': {'symbol': 'INDIAVIX', 'exchange': 'NSE'},
#     'USDINR': {'symbol': 'USDINR', 'exchange': 'FX_IDC'},
#     'CRUDEOIL': {'symbol': 'USOIL', 'exchange': 'TVC'},
#     'GOLD': {'symbol': 'GOLD', 'exchange': 'TVC'}
# }

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
# def fetch_live_tensor_data(ticker: str, lookback_days=320):
#     """
#     Downloads raw daily data via TradingView, applies macro frameworks, 
#     and packages calculations into a 52-feature inference matrix.
#     """
#     # 1. Initialize TradingView Interface
#     tv = TvDatafeed()
#     clean_ticker = ticker.replace('.NS', '')
    
#     time.sleep(random.uniform(0.2, 0.5))
    
#     # Fetch Base Historical Series from NSE
#     df = tv.get_hist(symbol=clean_ticker, exchange='NSE', interval=Interval.in_daily, n_bars=lookback_days)
    
#     if df is None or df.empty or len(df) < 230:
#         raise ValueError(f"Not enough live daily data for {ticker}. Need at least 230 rows.")
        
#     df.reset_index(inplace=True)
#     df.rename(columns={'datetime': 'date'}, inplace=True)
#     df['date'] = pd.to_datetime(df['date']).dt.tz_localize(None).dt.normalize()
    
#     # Core technical calculations
#     df['daily_return'] = df['close'].pct_change()
#     df['open_gap'] = (df['open'] - df['close'].shift(1)) / df['close'].shift(1)
#     df['intraday_return'] = (df['close'] - df['open']) / df['open']
#     df['high_low_range'] = (df['high'] - df['low']) / df['close']
#     df['body_size'] = np.abs(df['close'] - df['open']) / df['open']
    
#     df['sma_5'] = ta.trend.sma_indicator(df['close'], window=5)
#     df['sma_10'] = ta.trend.sma_indicator(df['close'], window=10)
#     df['sma_20'] = ta.trend.sma_indicator(df['close'], window=20)
#     df['sma_50'] = ta.trend.sma_indicator(df['close'], window=50)
#     df['ema_10'] = ta.trend.ema_indicator(df['close'], window=10)
#     df['ema_20'] = ta.trend.ema_indicator(df['close'], window=20)
#     df['ema_50'] = ta.trend.ema_indicator(df['close'], window=50)
    
#     df['rsi_14'] = ta.momentum.rsi(df['close'], window=14)
#     macd = ta.trend.MACD(df['close'])
#     df['macd'] = macd.macd()
#     df['macd_signal'] = macd.macd_signal()
#     df['macd_hist'] = macd.macd_diff()
#     df['roc_5'] = ta.momentum.roc(df['close'], window=5)
#     df['roc_10'] = ta.momentum.roc(df['close'], window=10)
    
#     df['stoch_rsi'] = ta.momentum.stochrsi(df['close'])
#     df['atr_14'] = ta.volatility.average_true_range(df['high'], df['low'], df['close'], window=14)
#     df['atr_20'] = ta.volatility.average_true_range(df['high'], df['low'], df['close'], window=20)
#     df['rolling_std_5'] = df['close'].rolling(window=5).std()
#     df['rolling_std_10'] = df['close'].rolling(window=10).std()
#     df['rolling_std_20'] = df['close'].rolling(window=20).std()
#     bollinger = ta.volatility.BollingerBands(df['close'])
#     df['bollinger_width'] = bollinger.bollinger_wband()
    
#     df['volume_ratio'] = df['volume'] / df['volume'].rolling(window=20).mean()
#     df['volume_change'] = df['volume'].pct_change()
#     df['obv'] = ta.volume.on_balance_volume(df['close'], df['volume'])
#     df['vwap_distance'] = (df['close'] - ta.volume.volume_weighted_average_price(df['high'], df['low'], df['close'], df['volume'])) / ta.volume.volume_weighted_average_price(df['high'], df['low'], df['close'], df['volume'])
#     df.replace([np.inf, -np.inf], 0, inplace=True)

#     # 2. Fetch Macro Grid Matrix via TradingView Streams
#     macro_data = {}
#     for name, config in MACRO_TICKERS.items():
#         time.sleep(random.uniform(0.1, 0.3))
#         m_df = tv.get_hist(symbol=config['symbol'], exchange=config['exchange'], interval=Interval.in_daily, n_bars=lookback_days)
        
#         if m_df is not None and not m_df.empty:
#             m_df.reset_index(inplace=True)
#             m_df.rename(columns={'datetime': 'date'}, inplace=True)
#             m_df['date'] = pd.to_datetime(m_df['date']).dt.tz_localize(None).dt.normalize()
#             m_df.set_index('date', inplace=True)
            
#             if name == 'INDIAVIX':
#                 macro_data[f'{name}_close'] = m_df['close']
#             else:
#                 macro_data[f'{name}_return'] = m_df['close'].pct_change()
                
#     macro_df = pd.DataFrame(macro_data)
#     macro_df.reset_index(inplace=True)
    
#     # Merge and forward fill gaps
#     df = pd.merge(df, macro_df, on='date', how='left')
#     df.ffill(inplace=True)
#     df.bfill(inplace=True)

#     # Contextual Calendar Metrics
#     df['day_of_week'] = df['date'].dt.dayofweek
#     df['month'] = df['date'].dt.month
#     df['quarter'] = df['date'].dt.quarter
#     df['expiry_week'] = ((df['date'].dt.day >= 22) & (df['date'].dt.day <= 28)).astype(int)
#     df['month_end'] = (df['date'].dt.day >= (df['date'].dt.days_in_month - 5)).astype(int)
    
#     df['trend_strength'] = ta.trend.adx(df['high'], df['low'], df['close'], window=14, fillna=True)
#     atr_50_avg = df['atr_14'].rolling(window=50).mean()
#     df['volatility_regime'] = (df['atr_14'] > atr_50_avg).astype(int)
    
#     sma_200 = ta.trend.sma_indicator(df['close'], window=200)
#     df['above_200dma'] = (df['close'] > sma_200).astype(int)
    
#     df['open_equals_low'] = (df['open'] == df['low']).astype(int)
#     df['open_equals_high'] = (df['open'] == df['high']).astype(int)
    
#     pivot_point = (df['high'] + df['low'] + df['close']) / 3
#     support_1 = (2 * pivot_point) - df['high']
#     resistance_1 = (2 * pivot_point) - df['low']
#     df['dist_to_pivot'] = (df['close'] - pivot_point) / df['close']
#     df['dist_to_s1'] = (df['close'] - support_1) / df['close']
#     df['dist_to_r1'] = (df['close'] - resistance_1) / df['close']
    
#     df.dropna(inplace=True)
    
#     # Filter feature space to match exact shapes
#     # exclude_cols = ['date', 'Symbol', 'Ticker', 'target_return', 'target_low_return', 'intraday_return']
#     exclude_cols = ['date', 'symbol', 'Symbol', 'Ticker', 'target_return', 'target_low_return', 'intraday_return']
#     feature_cols = [col for col in df.columns if col not in exclude_cols]
    
#     if len(feature_cols) != 52:
#         raise ValueError(f"Feature mismatch! Model expects 52, got {len(feature_cols)}: {feature_cols}")
        
#     if not os.path.exists(SCALER_PATH):
#         raise FileNotFoundError(f"Missing Scaler! Cannot predict without {SCALER_PATH}")
        
#     scaler = joblib.load(SCALER_PATH)
#     scaled_features = scaler.transform(df[feature_cols])
    
#     if len(scaled_features) < 30:
#         raise ValueError(f"Not enough clean sequence points left after dropping NaNs.")
        
#     final_sequence = scaled_features[-30:]
#     tensor_input = torch.tensor(final_sequence, dtype=torch.float32).unsqueeze(0).to(device)
    
#     return tensor_input

# # ==========================================
# # 3. LIVE INFERENCE ENGINE (MC DROPOUT)
# # ==========================================
# def get_live_swing_prediction(ticker: str) -> dict:
#     print(f"   [Neural Net] Running live macro-inference for {ticker}...")
    
#     try:
#         tensor_input = fetch_live_tensor_data(ticker)
        
#         if not os.path.exists(WEIGHTS_PATH):
#             raise FileNotFoundError(f"Weights not found at {WEIGHTS_PATH}")
            
#         model = StockCNNLSTMAttention(
#             input_dim=52, 
#             cnn_out_channels=128, 
#             kernel_size=5,
#             hidden_dim=64, 
#             num_layers=2, 
#             dropout_rate=0.32768562460671624
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
#             "status": "success"
#         }
        
#     except Exception as e:
#         return {"ticker": ticker, "status": "error", "message": str(e)}

# if __name__ == "__main__":
#     result = get_live_swing_prediction("INFY")
#     print(result)


import os
import torch
import torch.nn as nn
import joblib
import numpy as np
import pandas as pd
import ta
import warnings
import random
import time
from tvDatafeed import TvDatafeed, Interval

# Suppress underlying layout warnings
warnings.filterwarnings('ignore', category=FutureWarning)
warnings.filterwarnings('ignore', category=UserWarning)

# --- Device Configuration ---
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

# --- Dynamic Pathing ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WEIGHTS_DIR = os.path.join(BASE_DIR, 'weights')

SCALER_PATH = os.path.join(WEIGHTS_DIR, 'swing_feature_scaler.pkl') 
WEIGHTS_PATH = os.path.join(WEIGHTS_DIR, 'best_swing_attention_V4.pth')

# TradingView Exchange & Symbol Structure Map
MACRO_TICKERS = {
    'NIFTY50': {'symbol': 'NIFTY', 'exchange': 'NSE'},
    'BANKNIFTY': {'symbol': 'BANKNIFTY', 'exchange': 'NSE'},
    'INDIAVIX': {'symbol': 'INDIAVIX', 'exchange': 'NSE'},
    'USDINR': {'symbol': 'USDINR', 'exchange': 'FX_IDC'},
    'CRUDEOIL': {'symbol': 'USOIL', 'exchange': 'TVC'},
    'GOLD': {'symbol': 'GOLD', 'exchange': 'TVC'}
}

# ==========================================
# 0. GLOBAL CACHE SETUP
# ==========================================
# Initialize TradingView ONCE for the entire script run
print("Initializing Global TradingView Session...")
global_tv = TvDatafeed()

# Store the macro data in RAM so we don't re-download it 50 times
cached_macro_df = None 

# ==========================================
# 1. PYTORCH MODEL ARCHITECTURE
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
        self.fc = nn.Linear(hidden_dim, 1)
        
    def forward(self, x):
        x = x.permute(0, 2, 1) 
        x = self.conv1(x)
        x = self.relu(x)
        x = x.permute(0, 2, 1) 
        
        h0 = torch.zeros(self.lstm.num_layers, x.size(0), self.lstm.hidden_size).to(x.device)
        c0 = torch.zeros(self.lstm.num_layers, x.size(0), self.lstm.hidden_size).to(x.device)
        
        lstm_out, _ = self.lstm(x, (h0, c0))
        context_vector, _ = self.attention(lstm_out)
        
        out = self.fc(context_vector)
        return out.squeeze(-1)

# ==========================================
# 2. DATA INGESTION & PREPROCESSING
# ==========================================
def fetch_live_tensor_data(ticker: str, lookback_days=320):
    """
    Downloads raw daily data via TradingView, applies macro frameworks, 
    and packages calculations into a 52-feature inference matrix.
    """
    global global_tv, cached_macro_df # Access the global cache
    
    clean_ticker = ticker.replace('.NS', '')
    
    # Slight pacing for the individual stock download
    time.sleep(random.uniform(0.5, 1.5))
    
    # 1. Fetch Base Historical Series from NSE
    df = global_tv.get_hist(symbol=clean_ticker, exchange='NSE', interval=Interval.in_daily, n_bars=lookback_days)
    
    if df is None or df.empty or len(df) < 230:
        raise ValueError(f"Not enough live daily data for {ticker}. Need at least 230 rows.")
        
    df.reset_index(inplace=True)
    df.rename(columns={'datetime': 'date'}, inplace=True)
    df['date'] = pd.to_datetime(df['date']).dt.tz_localize(None).dt.normalize()
    
    # Core technical calculations
    df['daily_return'] = df['close'].pct_change()
    df['open_gap'] = (df['open'] - df['close'].shift(1)) / df['close'].shift(1)
    df['intraday_return'] = (df['close'] - df['open']) / df['open']
    df['high_low_range'] = (df['high'] - df['low']) / df['close']
    df['body_size'] = np.abs(df['close'] - df['open']) / df['open']
    
    df['sma_5'] = ta.trend.sma_indicator(df['close'], window=5)
    df['sma_10'] = ta.trend.sma_indicator(df['close'], window=10)
    df['sma_20'] = ta.trend.sma_indicator(df['close'], window=20)
    df['sma_50'] = ta.trend.sma_indicator(df['close'], window=50)
    df['ema_10'] = ta.trend.ema_indicator(df['close'], window=10)
    df['ema_20'] = ta.trend.ema_indicator(df['close'], window=20)
    df['ema_50'] = ta.trend.ema_indicator(df['close'], window=50)
    
    df['rsi_14'] = ta.momentum.rsi(df['close'], window=14)
    macd = ta.trend.MACD(df['close'])
    df['macd'] = macd.macd()
    df['macd_signal'] = macd.macd_signal()
    df['macd_hist'] = macd.macd_diff()
    df['roc_5'] = ta.momentum.roc(df['close'], window=5)
    df['roc_10'] = ta.momentum.roc(df['close'], window=10)
    
    df['stoch_rsi'] = ta.momentum.stochrsi(df['close'])
    df['atr_14'] = ta.volatility.average_true_range(df['high'], df['low'], df['close'], window=14)
    df['atr_20'] = ta.volatility.average_true_range(df['high'], df['low'], df['close'], window=20)
    df['rolling_std_5'] = df['close'].rolling(window=5).std()
    df['rolling_std_10'] = df['close'].rolling(window=10).std()
    df['rolling_std_20'] = df['close'].rolling(window=20).std()
    bollinger = ta.volatility.BollingerBands(df['close'])
    df['bollinger_width'] = bollinger.bollinger_wband()
    
    df['volume_ratio'] = df['volume'] / df['volume'].rolling(window=20).mean()
    df['volume_change'] = df['volume'].pct_change()
    df['obv'] = ta.volume.on_balance_volume(df['close'], df['volume'])
    df['vwap_distance'] = (df['close'] - ta.volume.volume_weighted_average_price(df['high'], df['low'], df['close'], df['volume'])) / ta.volume.volume_weighted_average_price(df['high'], df['low'], df['close'], df['volume'])
    df.replace([np.inf, -np.inf], 0, inplace=True)

    # ==========================================
    # 2. FETCH MACRO GRID (WITH CACHING!)
    # ==========================================
    if cached_macro_df is None:
        print("   🌐 Downloading Global Macro Data (Once per day)...")
        macro_data = {}
        for name, config in MACRO_TICKERS.items():
            time.sleep(random.uniform(0.5, 1.0)) # Pace the initial download
            m_df = global_tv.get_hist(symbol=config['symbol'], exchange=config['exchange'], interval=Interval.in_daily, n_bars=lookback_days)
            
            if m_df is not None and not m_df.empty:
                m_df.reset_index(inplace=True)
                m_df.rename(columns={'datetime': 'date'}, inplace=True)
                m_df['date'] = pd.to_datetime(m_df['date']).dt.tz_localize(None).dt.normalize()
                m_df.set_index('date', inplace=True)
                
                if name == 'INDIAVIX':
                    macro_data[f'{name}_close'] = m_df['close']
                else:
                    macro_data[f'{name}_return'] = m_df['close'].pct_change()
                    
        # Save to global cache
        cached_macro_df = pd.DataFrame(macro_data)
        cached_macro_df.reset_index(inplace=True)
    
    # Use a copy of the cached data to prevent accidental overrides
    macro_df = cached_macro_df.copy()
    
    # Merge and forward fill gaps
    df = pd.merge(df, macro_df, on='date', how='left')
    df.ffill(inplace=True)
    df.bfill(inplace=True)

    # Contextual Calendar Metrics
    df['day_of_week'] = df['date'].dt.dayofweek
    df['month'] = df['date'].dt.month
    df['quarter'] = df['date'].dt.quarter
    df['expiry_week'] = ((df['date'].dt.day >= 22) & (df['date'].dt.day <= 28)).astype(int)
    df['month_end'] = (df['date'].dt.day >= (df['date'].dt.days_in_month - 5)).astype(int)
    
    df['trend_strength'] = ta.trend.adx(df['high'], df['low'], df['close'], window=14, fillna=True)
    atr_50_avg = df['atr_14'].rolling(window=50).mean()
    df['volatility_regime'] = (df['atr_14'] > atr_50_avg).astype(int)
    
    sma_200 = ta.trend.sma_indicator(df['close'], window=200)
    df['above_200dma'] = (df['close'] > sma_200).astype(int)
    
    df['open_equals_low'] = (df['open'] == df['low']).astype(int)
    df['open_equals_high'] = (df['open'] == df['high']).astype(int)
    
    pivot_point = (df['high'] + df['low'] + df['close']) / 3
    support_1 = (2 * pivot_point) - df['high']
    resistance_1 = (2 * pivot_point) - df['low']
    df['dist_to_pivot'] = (df['close'] - pivot_point) / df['close']
    df['dist_to_s1'] = (df['close'] - support_1) / df['close']
    df['dist_to_r1'] = (df['close'] - resistance_1) / df['close']
    
    df.dropna(inplace=True)
    
    # Filter feature space to match exact shapes
    exclude_cols = ['date', 'symbol', 'Symbol', 'Ticker', 'target_return', 'target_low_return', 'intraday_return']
    feature_cols = [col for col in df.columns if col not in exclude_cols]
    
    if len(feature_cols) != 52:
        raise ValueError(f"Feature mismatch! Model expects 52, got {len(feature_cols)}: {feature_cols}")
        
    if not os.path.exists(SCALER_PATH):
        raise FileNotFoundError(f"Missing Scaler! Cannot predict without {SCALER_PATH}")
        
    scaler = joblib.load(SCALER_PATH)
    scaled_features = scaler.transform(df[feature_cols])
    
    if len(scaled_features) < 30:
        raise ValueError(f"Not enough clean sequence points left after dropping NaNs.")
        
    final_sequence = scaled_features[-30:]
    tensor_input = torch.tensor(final_sequence, dtype=torch.float32).unsqueeze(0).to(device)
    
    return tensor_input

# ==========================================
# 3. LIVE INFERENCE ENGINE (MC DROPOUT)
# ==========================================
def get_live_swing_prediction(ticker: str) -> dict:
    print(f"   [Neural Net] Running live macro-inference for {ticker}...")
    
    try:
        tensor_input = fetch_live_tensor_data(ticker)
        
        if not os.path.exists(WEIGHTS_PATH):
            raise FileNotFoundError(f"Weights not found at {WEIGHTS_PATH}")
            
        model = StockCNNLSTMAttention(
            input_dim=52, 
            cnn_out_channels=128, 
            kernel_size=5,
            hidden_dim=64, 
            num_layers=2, 
            dropout_rate=0.32768562460671624
        ).to(device)
        
        model.load_state_dict(torch.load(WEIGHTS_PATH, map_location=device, weights_only=True))
        model.train()
        
        passes = 50
        predictions = []
        
        with torch.no_grad():
            for _ in range(passes):
                out = model(tensor_input)
                predictions.append(out.item())
                
        expected_return = np.mean(predictions)
        uncertainty = np.std(predictions)
        
        return {
            "ticker": ticker,
            "expected_return": round(float(expected_return), 6),
            "uncertainty": round(float(uncertainty), 6),
            "status": "success"
        }
        
    except Exception as e:
        return {"ticker": ticker, "status": "error", "message": str(e)}

if __name__ == "__main__":
    result = get_live_swing_prediction("INFY")
    print(result)