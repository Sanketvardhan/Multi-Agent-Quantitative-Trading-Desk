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

class StockLSTM(nn.Module):
    def __init__(self, input_dim, hidden_dim, num_layers, dropout_rate):
        super(StockLSTM, self).__init__()
        self.hidden_dim = hidden_dim
        self.num_layers = num_layers
        self.lstm = nn.LSTM(input_dim, hidden_dim, num_layers, batch_first=True, dropout=dropout_rate)
        self.fc = nn.Linear(hidden_dim, 1)
        
    def forward(self, x):
        h0 = torch.zeros(self.num_layers, x.size(0), self.hidden_dim).to(device)
        c0 = torch.zeros(self.num_layers, x.size(0), self.hidden_dim).to(device)
        out, _ = self.lstm(x, (h0, c0))
        out = self.fc(out[:, -1, :])
        return out.squeeze(-1)

def run_trading_simulation():
    CACHE_FILE = 'model_training/mc_predictions_cache.csv'
    
    # --- SMART CACHING LOGIC ---
    if os.path.exists(CACHE_FILE):
        print(f"Loading cached MC Dropout predictions from {CACHE_FILE}...")
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
        
        print("3. Generating Probabilistic Predictions (MC Dropout: 50 passes per day)...")
        model = StockLSTM(input_dim=47, hidden_dim=64, num_layers=3, dropout_rate=0.48).to(device)
        model.load_state_dict(torch.load('weights/best_lstm_v1.pth', weights_only=True))
        
        model.train() # KEEP DROPOUT ACTIVE
        
        WINDOW_SIZE = 30
        MC_PASSES = 50
        results_list = []
        
        grouped_stocks = df.groupby('Ticker')
        
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
        print(f"\nSaving predictions to cache: {CACHE_FILE}")
        results_df.to_csv(CACHE_FILE, index=False)
    
    print("\n4. Running Simulation with Bayesian Filtering...")
    
    STARTING_CAPITAL = 10000.0
    FEE_PER_TRADE = 0.0005 
    STOCKS_PER_DAY = 3
    STOP_LOSS_PCT = -0.01 
    
    # --- LOOSENED BAYESIAN RULES ---
    # CONFIDENCE_THRESHOLD = 0.001 
    # UNCERTAINTY_LIMIT = 0.008 # Opened up from 0.002 to 0.008!

    # CONFIDENCE_THRESHOLD = 0.0015  # Demand a +0.15% expected return
    # UNCERTAINTY_LIMIT = 0.004      # Max uncertainty of 0.4%

    # CONFIDENCE_THRESHOLD = 0.0025  # Demand a huge +0.25% expected return
    # UNCERTAINTY_LIMIT = 0.005      # Max uncertainty of 0.5%

    CONFIDENCE_THRESHOLD = 0.001   # Normal +0.1% expected return
    UNCERTAINTY_LIMIT = 0.003      # Very strict 0.3% uncertainty limit
    
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
    print("📊 BAYESIAN MC DROPOUT BACKTEST RESULTS 📊")
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
    plt.plot(history_df['Date'], history_df['Capital'], color='blue', linewidth=2)
    plt.axhline(y=STARTING_CAPITAL, color='red', linestyle='--', label='Starting Capital')
    plt.title('Bayesian LSTM Strategy: ₹10,000 Equity Curve')
    plt.xlabel('Date')
    plt.ylabel('Portfolio Value (₹)')
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.savefig('model_training/equity_curve.png')

if __name__ == "__main__":
    run_trading_simulation()