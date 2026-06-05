import pandas as pd
import matplotlib.pyplot as plt
import os
from tqdm import tqdm

def run_dynamic_risk_simulation():
    # 1. Pointing to the NEW V4 Attention Cache
    CACHE_FILE = 'model_training/cache/attention_v4_mc_cache.csv'
    
    if not os.path.exists(CACHE_FILE):
        print(f"Error: Cache file not found at {CACHE_FILE}. Run the cache generator first.")
        return
        
    print(f"Loading cached V4 Attention predictions from {CACHE_FILE}...")
    results_df = pd.read_csv(CACHE_FILE)
    results_df['Date'] = pd.to_datetime(results_df['Date'])
    
    print("\nRunning Simulation with DYNAMIC POSITION SIZING & DYNAMIC STOP-LOSS...")
    
    # Financial Configuration
    STARTING_CAPITAL = 10000.0
    FEE_PER_TRADE = 0.0005 
    STOCKS_PER_DAY = 3

    # V4 SNIPER SETTINGS (Carried over from V3 calibration)
    # CONFIDENCE_THRESHOLD = 0.0040  # Demanding +0.40% expected return 
    # UNCERTAINTY_LIMIT = 0.0017     # Strict Risk Control 

    # V4 CALIBRATED SNIPER SETTINGS (Based on Attention Distribution)
    # CONFIDENCE_THRESHOLD = 0.0015  # Demanding top ~2.5% of expected returns
    # UNCERTAINTY_LIMIT = 0.0020     # Cuts out the most chaotic top 15% of the market

    # V4 OPTIMIZED SNIPER SETTINGS 
    # CONFIDENCE_THRESHOLD = 0.0026  # Isolates the top ~1.5% highest conviction setups
    # UNCERTAINTY_LIMIT = 0.0016     # Tighter filter to bypass higher volatility regimes

    # V4 FINAL BALANCED CALIBRATION
    CONFIDENCE_THRESHOLD = 0.0021  # Widens the gate to capture the top ~1.8% of setups
    UNCERTAINTY_LIMIT = 0.0018     # Offers an optimal balance between trade volume and risk
    
    current_capital = STARTING_CAPITAL
    portfolio_history = []
    win_count = 0
    total_trades = 0
    peak_capital = STARTING_CAPITAL
    max_drawdown = 0.0
    
    unique_dates = sorted(results_df['Date'].unique())
    
    for current_date in tqdm(unique_dates, desc="Simulating Trading Days", unit="day"):
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
            
            # --- V4 DYNAMIC POSITION SIZING & STOP-LOSS LOGIC ---
            # Tier 1: High Conviction (Low Uncertainty) -> Bet Heavy, Tight Stop
            # if uncertainty < 0.0012:       
            #     allocation_pct = 0.25      # Deploy 25% of total portfolio
            #     DYNAMIC_STOP_LOSS = -0.008 # Keep a tight -0.8% leash
            
            # --- V4 DYNAMIC POSITION SIZING & STOP-LOSS LOGIC ---
            # Tier 1: High Conviction (Low Uncertainty) -> Bet Heavy, Tight Stop
            if uncertainty < 0.0013:       # Adjusted based on V4's 50th percentile
                allocation_pct = 0.25      # Deploy 25% of total portfolio
                DYNAMIC_STOP_LOSS = -0.008 # Keep a tight -0.8% leash
            
            # Tier 2: Medium Conviction -> Bet Light, Loose Stop
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
    print("📊 V4 ATTENTION BACKTEST RESULTS 📊")
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
    plt.plot(history_df['Date'], history_df['Capital'], color='blue', linewidth=2)
    plt.axhline(y=STARTING_CAPITAL, color='red', linestyle='--', label='Starting Capital')
    plt.title('V4 Attention Strategy: ₹10,000 Equity Curve (2024 Unseen Data)')
    plt.xlabel('Date')
    plt.ylabel('Portfolio Value (₹)')
    plt.grid(True, alpha=0.3)
    plt.legend()
    os.makedirs('model_training/cache', exist_ok=True)
    plt.savefig('model_training/Plots/attention_equity_curve.png')

if __name__ == "__main__":
    run_dynamic_risk_simulation()