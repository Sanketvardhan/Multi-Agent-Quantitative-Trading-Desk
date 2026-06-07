import pandas as pd
import matplotlib.pyplot as plt
import os
from tqdm import tqdm

# --- Dynamic Pathing ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CACHE_FILE = os.path.join(BASE_DIR, 'cache', 'intraday_attention_cache.csv')
PLOT_DIR = os.path.join(BASE_DIR, 'Plots')
os.makedirs(PLOT_DIR, exist_ok=True)

def run_intraday_simulation():
    if not os.path.exists(CACHE_FILE):
        print(f"Error: Cache file not found at {CACHE_FILE}.")
        return

    print(f"Loading cached Intraday predictions from {CACHE_FILE}...")
    results_df = pd.read_csv(CACHE_FILE)
    results_df['date_time'] = pd.to_datetime(results_df['date_time'])
    
    print("\nRunning HIGH-FREQUENCY Simulation with FIXED 1:2.1 RISK-REWARD RATIO...")
    
    # Financial Configuration
    STARTING_CAPITAL = 10000.0
    FEE_PER_TRADE = 0.0005  # 0.05% flat slippage/brokerage
    STOCKS_PER_INTERVAL = 1 # Stick to the apex setup
    
    # AI SIGNAL FILTER
    # CONFIDENCE_THRESHOLD = 0.0035 # Trigger threshold for the AI signal
    CONFIDENCE_THRESHOLD = 0.0042 # Trigger threshold for the AI signal
    
    current_capital = STARTING_CAPITAL
    portfolio_history = []
    win_count = 0
    total_trades = 0
    peak_capital = STARTING_CAPITAL
    max_drawdown = 0.0
    
    unique_times = sorted(results_df['date_time'].unique())
    
    for current_time in tqdm(unique_times, desc="Simulating 15m Intervals", unit="bar"):
        bar_data = results_df[results_df['date_time'] == current_time]
        
        confident_picks = bar_data[bar_data['Predicted_Return'] >= CONFIDENCE_THRESHOLD]
        top_picks = confident_picks.sort_values(by='Predicted_Return', ascending=False).head(STOCKS_PER_INTERVAL)
        
        if len(top_picks) == 0:
            portfolio_history.append({'date_time': current_time, 'Capital': current_capital})
            continue
            
        daily_profit = 0.0
        total_capital_deployed = 0.0
        
        for _, trade in top_picks.iterrows():
            # --- THE PROFESSIONAL FIXED RATIO ---
            # # We ignore the exact prediction magnitude and enforce a strict mathematical edge.
            # allocation_pct = 0.20          # Deploy 20% of capital per trade
            # FIXED_STOP_LOSS = -0.003       # -0.30% Stop Loss
            # FIXED_TAKE_PROFIT = 0.0065     # +0.65% Take Profit

            # --- THE HIGH-FREQUENCY SCALPER RATIO ---
            allocation_pct = 0.25          # Deploy 25% of capital on Apex setups
            FIXED_STOP_LOSS = -0.0015      # Tight -0.15% Scalper Stop
            FIXED_TAKE_PROFIT = 0.0035     # +0.35% Scalper Target (Highly achievable in 15 mins)
                
            capital_allocated = current_capital * allocation_pct
            
            if total_capital_deployed + capital_allocated > current_capital:
                capital_allocated = current_capital - total_capital_deployed
                
            total_capital_deployed += capital_allocated
            
            if capital_allocated <= 0:
                continue

            total_trades += 1
            
            # The True Intraday Extremes
            intraday_low = trade['Actual_Low']
            intraday_high = trade['Actual_High'] 
            gross_return = trade['Actual_Return'] # Default to close if neither target hits
            
            # 1. Check Stop Loss First (Conservative backtesting rule)
            if intraday_low <= FIXED_STOP_LOSS:
                gross_return = FIXED_STOP_LOSS
            # 2. Check Take Profit Second
            elif intraday_high >= FIXED_TAKE_PROFIT:
                gross_return = FIXED_TAKE_PROFIT
            
            # Deduct round-trip fees (The ultimate reality check)
            net_return = gross_return - FEE_PER_TRADE
            
            if net_return > 0:
                win_count += 1
                
            daily_profit += capital_allocated * net_return
            
        current_capital += daily_profit
        portfolio_history.append({'date_time': current_time, 'Capital': current_capital})
        
        if current_capital > peak_capital:
            peak_capital = current_capital
        drawdown = (peak_capital - current_capital) / peak_capital
        if drawdown > max_drawdown:
            max_drawdown = drawdown

    print("\n======================================")
    print("📊 FINAL INTRADAY ENGINE RESULTS 📊")
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
    plt.plot(history_df['date_time'], history_df['Capital'], color='emerald' if final_return_pct > 0 else 'crimson', linewidth=1.5)
    plt.axhline(y=STARTING_CAPITAL, color='black', linestyle='--', label='Starting Capital')
    plt.title('Professional Intraday Engine: 1:2.1 Fixed Ratio')
    plt.xlabel('Date/Time')
    plt.ylabel('Portfolio Value (₹)')
    plt.grid(True, alpha=0.3)
    plt.legend()
    
    plot_path = os.path.join(PLOT_DIR, 'intraday_final_curve.png')
    plt.savefig(plot_path)
    print(f"Final equity curve saved to {plot_path}")

if __name__ == "__main__":
    run_intraday_simulation()