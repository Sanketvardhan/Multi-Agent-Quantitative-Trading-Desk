import pandas as pd
import numpy as np
import torch
import torch.nn as nn
import joblib
import os
import matplotlib.pyplot as plt
from sqlalchemy import create_engine
from dotenv import load_dotenv
from tqdm import tqdm

device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

# 1. The Updated Hybrid Architecture
class StockCNNLSTM(nn.Module):
    def __init__(self, input_dim, cnn_out_channels, kernel_size, hidden_dim, num_layers, dropout_rate):
        super(StockCNNLSTM, self).__init__()
        
        pad = kernel_size // 2 
        
        self.conv1 = nn.Conv1d(in_channels=input_dim, out_channels=cnn_out_channels, kernel_size=kernel_size, padding=pad)
        self.relu = nn.ReLU()
        self.lstm = nn.LSTM(cnn_out_channels, hidden_dim, num_layers, batch_first=True, dropout=dropout_rate)
        self.fc = nn.Linear(hidden_dim, 1)
        
    def forward(self, x):
        x = x.permute(0, 2, 1) 
        x = self.conv1(x)
        x = self.relu(x)
        x = x.permute(0, 2, 1) 
        
        h0 = torch.zeros(self.lstm.num_layers, x.size(0), self.lstm.hidden_size).to(device)
        c0 = torch.zeros(self.lstm.num_layers, x.size(0), self.lstm.hidden_size).to(device)
        out, _ = self.lstm(x, (h0, c0))
        out = self.fc(out[:, -1, :])
        return out.squeeze(-1)

def run_hybrid_simulation():
    # NEW CACHE FILE so it doesn't read the old LSTM data
    CACHE_FILE = 'model_training/cache/hybrid_mc_cache_V2.csv'
    
    if os.path.exists(CACHE_FILE):
        print(f"Loading cached Hybrid predictions from {CACHE_FILE}...")
        results_df = pd.read_csv(CACHE_FILE)
        results_df['Date'] = pd.to_datetime(results_df['Date'])
    else:
        print("1. Loading 2024 Test Data from PostgreSQL...")
        load_dotenv()
        DB_PASSWORD = os.getenv('DB_PASSWORD', 'root')
        engine = create_engine(f'postgresql://postgres:{DB_PASSWORD}@localhost:5432/nifty_lstm_db')
        
        df = pd.read_sql("SELECT * FROM model_ready_data WHERE date >= '2024-01-01'", engine)
        df['date'] = pd.to_datetime(df['date'])
        df.sort_values(by=['Ticker', 'date'], inplace=True)
        
        exclude_cols = ['date', 'Ticker', 'target_return', 'target_low_return']
        feature_cols = [col for col in df.columns if col not in exclude_cols]
        
        print("2. Scaling Features using saved Training rules...")
        scaler = joblib.load('model_training/data_tensors/feature_scaler.pkl')
        df[feature_cols] = scaler.transform(df[feature_cols])
        
        print("3. Generating Hybrid Probabilistic Predictions (50 passes per day)...")
        # INJECTING OPTUNA'S WINNING PARAMETERS
        # INJECTING THE ORIGINAL V1/V2 SKELETON
        model = StockCNNLSTM(
            input_dim=47,             # Back to 47 features
            cnn_out_channels=64,      # Back to 64 channels
            kernel_size=3,            # CRITICAL FIX: The error showed it used a kernel of 3!
            hidden_dim=64, 
            num_layers=2, 
            dropout_rate=0.514322973738394 # Original dropout
        ).to(device)
        
        model.load_state_dict(torch.load('weights/best_cnn_lstm_V2.pth', weights_only=True))
        model.train() # KEEP DROPOUT ACTIVE FOR BAYESIAN UNCERTAINTY
        
        WINDOW_SIZE = 30
        MC_PASSES = 50
        results_list = []
        
        grouped_stocks = df.groupby('Ticker')
        
        with torch.no_grad():
            for ticker, stock_df in tqdm(grouped_stocks, desc="Analyzing Stocks", unit="stock"):
                if len(stock_df) <= WINDOW_SIZE:
                    continue
                    
                # STRICTLY SLICE THE FIRST 47 FEATURES FOR THE V2 MODEL
                # This ignores the 5 new Pivot/Open-Low columns that V2 wasn't trained on
                features = stock_df[feature_cols].iloc[:, :47].values
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
        print(f"\nSaving new hybrid predictions to cache: {CACHE_FILE}")
        results_df.to_csv(CACHE_FILE, index=False)
    
    print("\n4. Running Simulation with Bayesian Filtering...")
    
    STARTING_CAPITAL = 10000.0
    FEE_PER_TRADE = 0.0005 
    STOCKS_PER_DAY = 3
    STOP_LOSS_PCT = -0.01 
    
    # Let's start with the "Balanced Approach" settings
    # CONFIDENCE_THRESHOLD = 0.0015
    # UNCERTAINTY_LIMIT = 0.004
    
    # CONFIDENCE_THRESHOLD = 0.0010  # Lowered to +0.10%
    # UNCERTAINTY_LIMIT = 0.0055     # Loosened to 0.55%

    # CONFIDENCE_THRESHOLD = 0.0015  # Keep at +0.15%
    # UNCERTAINTY_LIMIT = 0.0030     # Tightened from 0.4% to 0.3%

    # CONFIDENCE_THRESHOLD = 0.0025  # Demanding +0.25%
    # UNCERTAINTY_LIMIT = 0.0035     # Strict 0.35% risk

    CONFIDENCE_THRESHOLD = 0.0020  # Demanding +0.20%
    UNCERTAINTY_LIMIT = 0.0060     # Very loose 0.60% risk

    current_capital = STARTING_CAPITAL
    portfolio_history = []
    win_count = 0
    total_trades = 0
    peak_capital = STARTING_CAPITAL
    max_drawdown = 0.0
    
    unique_dates = sorted(results_df['Date'].unique())
    
    for current_date in tqdm(unique_dates, desc="Simulating Trading Days", unit="day"):
        day_data = results_df[results_df['Date'] == current_date]
        
        certain_picks = day_data[day_data['Uncertainty'] < UNCERTAINTY_LIMIT]
        confident_picks = certain_picks[certain_picks['Predicted_Return'] >= CONFIDENCE_THRESHOLD]
        top_picks = confident_picks.sort_values(by='Predicted_Return', ascending=False).head(STOCKS_PER_DAY)
        
        if len(top_picks) == 0:
            portfolio_history.append({'Date': current_date, 'Capital': current_capital})
            continue
            
        capital_per_stock = current_capital / len(top_picks)
        daily_profit = 0.0
        
        for _, trade in top_picks.iterrows():
            total_trades += 1
            gross_return = trade['Actual_Return']
            intraday_low = trade['Actual_Low']
            
            if intraday_low <= STOP_LOSS_PCT:
                gross_return = STOP_LOSS_PCT
            
            net_return = gross_return - FEE_PER_TRADE
            
            if net_return > 0:
                win_count += 1
                
            daily_profit += capital_per_stock * net_return
            
        current_capital += daily_profit
        portfolio_history.append({'Date': current_date, 'Capital': current_capital})
        
        if current_capital > peak_capital:
            peak_capital = current_capital
        drawdown = (peak_capital - current_capital) / peak_capital
        if drawdown > max_drawdown:
            max_drawdown = drawdown

    print("\n======================================")
    print("📊 FINAL HYBRID BACKTEST RESULTS 📊")
    print("======================================")
    
    final_return_pct = ((current_capital - STARTING_CAPITAL) / STARTING_CAPITAL) * 100
    win_rate = (win_count / total_trades) * 100 if total_trades > 0 else 0
    
    print(f"Starting Capital:   ₹{STARTING_CAPITAL:,.2f}")
    print(f"Final Capital:      ₹{current_capital:,.2f}")
    print(f"Total Return:       {final_return_pct:.2f}%")
    print(f"Total Trades Taken: {total_trades}")
    print(f"Strategy Win Rate:  {win_rate:.2f}%")
    print(f"Maximum Drawdown:   -{max_drawdown*100:.2f}%")
    
    history_df = pd.DataFrame(portfolio_history)
    plt.figure(figsize=(12, 6))
    plt.plot(history_df['Date'], history_df['Capital'], color='green', linewidth=2)
    plt.axhline(y=STARTING_CAPITAL, color='red', linestyle='--', label='Starting Capital')
    plt.title('Hybrid CNN+LSTM Strategy: ₹10,000 Equity Curve')
    plt.xlabel('Date')
    plt.ylabel('Portfolio Value (₹)')
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.savefig('model_training/cache/hybrid_equity_curve.png')   

if __name__ == "__main__":
    run_hybrid_simulation()