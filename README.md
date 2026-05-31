# Nifty50 LSTM Predictor (Phase 1)

An end-of-day binary classification tool predicting the closing direction of Nifty50 stocks using Recurrent Neural Networks (LSTM).

## Architecture Overview
This project processes raw OHLCV data into a 9-layer feature set before feeding it into the LSTM. 

### Data Pipeline
* **Ingestion:** `yfinance` (Historical Training) / `nselib` (Daily Production)
* **Storage:** Local PostgreSQL Database
* **Scaling:** `MinMaxScaler` / `StandardScaler` applied pre-database insertion.

### The 9-Layer Feature Engineering Stack
1. **Raw OHLCV:** Date, Open, High, Low, Close, Volume.
2. **Price-Derived:** Daily returns, intraday returns, high-low range, body size.
3. **Trend:** SMA (5, 10, 20, 50), EMA (10, 20, 50).
4. **Momentum:** RSI (14), MACD, MACD Signal, MACD Histogram, ROC (5, 10).
5. **Volatility:** Stochastic RSI, ATR (14, 20), Rolling Std (5, 10, 20), Bollinger Width.
6. **Volume:** Volume ratio, Volume change, OBV, VWAP distance.
7. **Market Context:** BANKNIFTY, FINNIFTY, India VIX, USDINR, Crude Oil, Gold returns.
8. **Time:** Day of week, Month, Quarter.
9. **Regime:** Expiry week, Month end, Trend strength, Volatility regime, Above-200dma.

## Project Structure
* `/data_ingestion` - Scripts to pull market data and push to PostgreSQL.
* `/feature_engineering` - Vectorized pandas logic for the 9-layer stack.
* `/model_training` - LSTM architecture, sliding window updates, and scaling.
* `/weights` - Local model checkpoints (.pt / .h5).