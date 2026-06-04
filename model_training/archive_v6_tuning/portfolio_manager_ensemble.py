import pandas as pd
import matplotlib.pyplot as plt
import os
from tqdm import tqdm

def run_ensemble_simulation():
    # 1. Load Both Brains
    V3_CACHE = 'model_training/cache/hybrid_mc_cache_V3.csv'      # Your V3 CNN+LSTM
    V4_CACHE = 'model_training/cache/attention_v4_mc_cache.csv' # Your V4 Attention
    
    if not os.path.exists(V3_CACHE) or not os.path.exists(V4_CACHE):
        print("Error: Missing one of the cache files. Ensure both V3 and V4 have generated predictions.")
        return
        
    print("Loading V3 Momentum Predictions...")
    v3_df = pd.read_csv(V3_CACHE)
    
    print("Loading V4 Attention Predictions...")
    v4_df = pd.read_csv(V4_CACHE)
    
    # 2. Merge the Brains on Date and Ticker
    # This aligns the predictions so we can compare them side-by-side
    merged_df = pd.merge(
        v3_df, 
        v4_df, 
        on=['Date', 'Ticker', 'Actual_Return', 'Actual_Low'], 
        suffixes=('_v3', '_v4')
    )
    merged_df['Date'] = pd.to_datetime(merged_df['Date'])
    
    print("\nRunning Multi-Agent Consensus Simulation...")
    
    # Financial Configuration
    STARTING_CAPITAL = 10000.0
    FEE_PER_TRADE = 0.0005 
    STOCKS_PER_DAY = 3

    # ==========================================
    # THE CONSENSUS FILTERS
    # We can use slightly looser filters because the models check each other
    # ==========================================
    # V3 (Aggressive) needs to see a solid momentum signal
    V3_CONFIDENCE = 0.0015
    V3_RISK = 0.0025
    
    # V4 (Conservative) needs to verify the structure/pivot
    V4_CONFIDENCE = 0.0010
    V4_RISK = 0.0020

    current_capital = STARTING_CAPITAL
    portfolio_history = []
    win_count = 0
    total_trades = 0
    peak_capital = STARTING_CAPITAL
    max_drawdown = 0.0
    
    unique_dates = sorted(merged_df['Date'].unique())
    
    for current_date in tqdm(unique_dates, desc="Simulating Trading Days", unit="day"):
        day_data = merged_df[merged_df['Date'] == current_date]
        
        # 3. THE HEDGE FUND LOGIC: Both models MUST agree
        valid_setups = day_data[
            (day_data['Predicted_Return_v3'] >= V3_CONFIDENCE) & 
            (day_data['Uncertainty_v3'] < V3_RISK) &
            (day_data['Predicted_Return_v4'] >= V4_CONFIDENCE) & 
            (day_data['Uncertainty_v4'] < V4_RISK)
        ]
        
        # Sort by V4's confidence (since it's the more accurate sniper)
        top_picks = valid_setups.sort_values(by='Predicted_Return_v4', ascending=False).head(STOCKS_PER_DAY)
        
        if len(top_picks) == 0:
            portfolio_history.append({'Date': current_date, 'Capital': current_capital})
            continue
            
        daily_profit = 0.0
        total_capital_deployed = 0.0
        
        for _, trade in top_picks.iterrows():
            # If both agree, we bet with medium/high conviction
            allocation_pct = 0.15      
            DYNAMIC_STOP_LOSS = -0.012 
                
            capital_allocated = current_capital * allocation_pct
            
            if total_capital_deployed + capital_allocated > current_capital:
                capital_allocated = current_capital - total_capital_deployed
                
            total_capital_deployed += capital_allocated
            
            if capital_allocated <= 0:
                continue

            total_trades += 1
            gross_return = trade['Actual_Return']
            intraday_low = trade['Actual_Low']
            
            if intraday_low <= DYNAMIC_STOP_LOSS:
                gross_return = DYNAMIC_STOP_LOSS
            
            net_return = gross_return - FEE_PER_TRADE
            
            if net_return > 0:
                win_count += 1
                
            daily_profit += capital_allocated * net_return
            
        current_capital += daily_profit
        portfolio_history.append({'Date': current_date, 'Capital': current_capital})
        
        if current_capital > peak_capital:
            peak_capital = current_capital
        drawdown = (peak_capital - current_capital) / peak_capital
        if drawdown > max_drawdown:
            max_drawdown = drawdown

    print("\n======================================")
    print("📊 MULTI-AGENT ENSEMBLE RESULTS (V3 + V4) 📊")
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
    plt.plot(history_df['Date'], history_df['Capital'], color='gold', linewidth=2)
    plt.axhline(y=STARTING_CAPITAL, color='red', linestyle='--', label='Starting Capital')
    plt.title('Hedge Fund Ensemble (V3 + V4): ₹10,000 Equity Curve')
    plt.xlabel('Date')
    plt.ylabel('Portfolio Value (₹)')
    plt.grid(True, alpha=0.3)
    plt.legend()
    os.makedirs('model_training/Plots', exist_ok=True)
    plt.savefig('model_training/Plots/ensemble_equity_curve.png')

if __name__ == "__main__":
    run_ensemble_simulation()