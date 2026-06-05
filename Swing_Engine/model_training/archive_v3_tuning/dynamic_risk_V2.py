import pandas as pd
import matplotlib.pyplot as plt
import os

def run_dynamic_risk_simulation():
    CACHE_FILE = 'model_training/cache/hybrid_mc_cache_V2.csv'
    
    if not os.path.exists(CACHE_FILE):
        print("Error: Cache file not found. Run the hybrid prediction script first.")
        return
        
    print(f"Loading cached Hybrid predictions from {CACHE_FILE}...")
    results_df = pd.read_csv(CACHE_FILE)
    results_df['Date'] = pd.to_datetime(results_df['Date'])
    
    print("\nRunning Simulation with DYNAMIC POSITION SIZING & DYNAMIC STOP-LOSS...")
    
    # Financial Configuration
    STARTING_CAPITAL = 10000.0
    FEE_PER_TRADE = 0.0005 
    STOCKS_PER_DAY = 3

    CONFIDENCE_THRESHOLD = 0.0020  # Demanding +0.20%
    UNCERTAINTY_LIMIT = 0.0060     # Very loose 0.60% risk    
    
    current_capital = STARTING_CAPITAL
    portfolio_history = []
    win_count = 0
    total_trades = 0
    peak_capital = STARTING_CAPITAL
    max_drawdown = 0.0
    
    unique_dates = sorted(results_df['Date'].unique())
    
    for current_date in unique_dates:
        day_data = results_df[results_df['Date'] == current_date]
        
        # Apply your winning filters
        certain_picks = day_data[day_data['Uncertainty'] < UNCERTAINTY_LIMIT]
        confident_picks = certain_picks[certain_picks['Predicted_Return'] >= CONFIDENCE_THRESHOLD]
        top_picks = confident_picks.sort_values(by='Predicted_Return', ascending=False).head(STOCKS_PER_DAY)
        
        if len(top_picks) == 0:
            portfolio_history.append({'Date': current_date, 'Capital': current_capital})
            continue
            
        daily_profit = 0.0
        total_capital_deployed = 0.0
        
        for _, trade in top_picks.iterrows():
            uncertainty = trade['Uncertainty']
            
            # --- DYNAMIC POSITION SIZING & STOP-LOSS LOGIC ---
            # Tier 1: High Conviction (Low Uncertainty) -> Bet Heavy, Tight Stop
            if uncertainty < 0.004:
                allocation_pct = 0.25      # Deploy 25% of total portfolio
                DYNAMIC_STOP_LOSS = -0.008 # Keep a tight -0.8% leash
            # Tier 2: Medium Conviction (High Uncertainty) -> Bet Light, Loose Stop
            else:
                allocation_pct = 0.12      # Deploy 12% of total portfolio
                DYNAMIC_STOP_LOSS = -0.015 # Give it a looser -1.5% leash
                
            capital_allocated = current_capital * allocation_pct
            
            # Safety Check: Prevent deploying more than 100% of capital in a single day
            if total_capital_deployed + capital_allocated > current_capital:
                capital_allocated = current_capital - total_capital_deployed
                
            total_capital_deployed += capital_allocated
            
            if capital_allocated <= 0:
                continue

            total_trades += 1
            gross_return = trade['Actual_Return']
            intraday_low = trade['Actual_Low']
            
            # Apply Dynamic Stop-Loss
            if intraday_low <= DYNAMIC_STOP_LOSS:
                gross_return = DYNAMIC_STOP_LOSS
            
            # Reality Check: Deduct Fees
            net_return = gross_return - FEE_PER_TRADE
            
            if net_return > 0:
                win_count += 1
                
            daily_profit += capital_allocated * net_return
            
        current_capital += daily_profit
        portfolio_history.append({'Date': current_date, 'Capital': current_capital})
        
        # Drawdown Tracking
        if current_capital > peak_capital:
            peak_capital = current_capital
        drawdown = (peak_capital - current_capital) / peak_capital
        if drawdown > max_drawdown:
            max_drawdown = drawdown

    print("\n======================================")
    print("📊 DYNAMIC RISK BACKTEST RESULTS 📊")
    print("======================================")
    
    final_return_pct = ((current_capital - STARTING_CAPITAL) / STARTING_CAPITAL) * 100
    win_rate = (win_count / total_trades) * 100 if total_trades > 0 else 0
    
    print(f"Starting Capital:   ₹{STARTING_CAPITAL:,.2f}")
    print(f"Final Capital:      ₹{current_capital:,.2f}")
    print(f"Total Return:       {final_return_pct:.2f}%")
    print(f"Total Trades Taken: {total_trades}")
    print(f"Strategy Win Rate:  {win_rate:.2f}%")
    print(f"Maximum Drawdown:   -{max_drawdown*100:.2f}%")
    
    # Plotting
    history_df = pd.DataFrame(portfolio_history)
    plt.figure(figsize=(12, 6))
    plt.plot(history_df['Date'], history_df['Capital'], color='purple', linewidth=2)
    plt.axhline(y=STARTING_CAPITAL, color='red', linestyle='--', label='Starting Capital')
    plt.title('Dynamic Sizing & Stop-Loss Strategy: ₹10,000 Equity Curve')
    plt.xlabel('Date')
    plt.ylabel('Portfolio Value (₹)')
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.savefig('model_training/dynamic_equity_curve.png')

if __name__ == "__main__":
    run_dynamic_risk_simulation()