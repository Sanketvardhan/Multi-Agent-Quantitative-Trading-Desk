# AI Stock Prediction System (Version 1)

## Project Vision

The goal of this project is to build a quantitative AI-powered stock selection system for the Indian stock market.

This is NOT a stock price prediction project.

This is NOT a chart pattern recognition project.

The objective is:

> Every evening after market close, predict which NIFTY50 stocks are most likely to generate positive intraday returns on the next trading day.

The system will then rank all stocks and identify the highest-probability trading opportunities.

Long-term objective:

- Generate profitable trading signals
- Estimate uncertainty and confidence
- Rank opportunities automatically
- Build a portfolio selection engine
- Eventually evolve into a complete AI trading assistant

---

# Current Status

## Phase 1 — Data Ingestion & Feature Engineering ✅ COMPLETED

Historical data has been collected for all NIFTY50 stocks.

Period:

2015 → Present

Each stock-day contains engineered features from multiple feature layers.

---

# Dataset Structure

Each row represents:

```text
One Stock
+
One Trading Day
```

---

## Layer 1 — OHLCV Features

Raw market data.

Features:

- open
- high
- low
- close
- volume

---

## Layer 2 — Price Derived Features

Features:

- daily_return
- open_gap
- intraday_return
- high_low_range
- body_size

---

## Layer 3 — Trend Features

Features:

- close_ema20_ratio
- close_ema50_ratio
- ema20_ema50_ratio
- SMA ratios
- EMA ratios

---

## Layer 4 — Momentum Features

Features:

- RSI14
- MACD
- MACD Signal
- MACD Histogram
- ROC5
- ROC10
- Stochastic RSI

---

## Layer 5 — Volatility Features

Features:

- ATR14
- ATR20
- Rolling Std 5
- Rolling Std 10
- Rolling Std 20
- Bollinger Width

---

## Layer 6 — Volume Features

Features:

- volume_ratio
- volume_change
- OBV
- VWAP_distance

---

## Layer 7 — Market Context Features

Features:

- BANKNIFTY return
- FINNIFTY return
- India VIX
- USDINR return
- Crude Oil return
- Gold return

---

## Layer 8 — Time Features

Features:

- day_of_week
- month
- quarter
- expiry_week
- month_end

---

## Layer 9 — Market Regime Features

Features:

- trend_strength
- volatility_regime
- above_200dma

---

# Trading Strategy

## Prediction Timing

Predictions are generated:

```text
After market close
(~4 PM)
```

using only information available up to that moment.

The model predicts:

```text
Tomorrow's trading session
```

---

## Trade Execution

The intended Version 1 strategy:

```text
Buy at next day's market open
↓
Hold throughout the day
↓
Sell at next day's market close
```

No overnight holding.

No multi-day positions.

No options trading.

No leverage.

Version 1 is strictly:

```text
Open → Close Intraday Trading
```

---

# Prediction Target

The primary target is:

```python
target_return = (
    next_day_close - next_day_open
) / next_day_open
```

Example:

Today:

```text
Prediction generated after market close
```

Tomorrow:

```text
Open = 1000
Close = 1030
```

Target:

```text
(1030 - 1000) / 1000

= 0.03

= +3%
```

The model learns to predict this value.

---

# Why This Target?

The project's objective is not:

```text
Will the stock go up tomorrow?
```

The objective is:

```text
Can we make money
buying at open
and selling at close?
```

The target directly measures the profitability of that strategy.

---

# Model Outputs

Version 1 should produce four outputs for every stock.

---

## Output 1 — Expected Intraday Return

Example:

```text
Reliance

Expected Return = +2.4%
```

---

## Output 2 — Direction Probability

Example:

```text
Probability(Return > 0)

= 81%
```

Meaning:

```text
81% chance
that the stock closes above its opening price.
```

---

## Output 3 — Confidence / Uncertainty

Example:

```text
Predicted Return = 2.4%

Uncertainty = ±0.5%
```

Meaning:

```text
Prediction is relatively reliable.
```

---

## Output 4 — Trade Score

A ranking score used to compare opportunities.

Example:

```text
Trade Score

=
Expected Return
/
Uncertainty
```

Higher score:

- Higher expected reward
- Lower uncertainty

Better trade candidate.

---

# Daily Workflow

Every trading day:

## Step 1

After market close:

Generate predictions for all NIFTY50 stocks.

---

## Step 2

For each stock predict:

- Expected Return
- Direction Probability
- Uncertainty
- Trade Score

---

## Step 3

Rank all stocks.

Example:

```text
1. Reliance
2. SBI
3. ICICI Bank
4. HDFC Bank
5. Infosys
```

---

## Step 4

Select top N opportunities.

Example:

```text
Top 5 stocks
```

---

## Step 5

Execute strategy:

```text
Buy at open
Sell at close
```

---

# Phase 2 — CURRENT PHASE

The objective of Phase 2 is:

```text
Convert raw feature dataset
into a supervised learning dataset.
```

---

## Task 1 — Create Target Variable

For every stock-day:

```python
target_return = (
    next_day_close - next_day_open
) / next_day_open
```

Store as:

```text
target_return
```

---

## Task 2 — Generate Training Sequences

Create rolling windows.

Example:

```text
Days 1–30
→ Predict Day 31 target_return

Days 2–31
→ Predict Day 32 target_return

Days 3–32
→ Predict Day 33 target_return
```

Recommended:

```text
Window Size = 30 Days
```

---

## Task 3 — Chronological Dataset Split

Use time-based splitting only.

Example:

Train:

```text
2015–2022
```

Validation:

```text
2023
```

Test:

```text
2024–Present
```

No random shuffling.

---

## Task 4 — Train Baseline Models

Before deep learning:

Train:

- Linear Regression
- Random Forest Regressor
- XGBoost Regressor

Purpose:

Determine whether the engineered features contain predictive signal.

---

## Task 5 — Evaluate Predictions

Metrics:

Regression:

- MAE
- RMSE
- R²

Direction:

- Accuracy
- Precision
- Recall

Financial:

- Average Return
- Sharpe Ratio
- Win Rate
- Maximum Drawdown

---

## Task 6 — Build Backtesting Engine

Simulate real trading.

Daily process:

```text
Predict
↓
Rank
↓
Select Top N
↓
Buy Open
↓
Sell Close
↓
Record Return
```

Backtesting must be performed on unseen data only.

---

# Phase 3

Only after baseline models are validated:

Train deep learning models.

Candidate architectures:

- LSTM
- GRU
- CNN + LSTM

Initial recommendation:

```text
CNN
↓
LSTM
↓
Dense Layers
↓
Return Prediction
```

---

# Future Versions

Planned additions:

- Monte Carlo Dropout
- Bayesian Neural Networks
- Model Ensembles
- News Sentiment
- Earnings Analysis
- GenAI Explanations
- Portfolio Optimization
- Position Sizing Engine

---

# Success Criteria

Version 1 is successful if:

1. The system predicts next-day intraday returns.
2. Stocks can be ranked effectively.
3. High-confidence opportunities are identified.
4. Backtesting outperforms naive selection methods.
5. Risk-adjusted returns are positive.

---

# Core Principle

The project goal is NOT:

```text
Predict stock prices.
```

The project goal is:

```text
Every evening,
identify tomorrow's highest-probability
intraday trading opportunities.
```