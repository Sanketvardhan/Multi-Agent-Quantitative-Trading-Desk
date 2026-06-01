# AI Stock Prediction System

## Project Overview

This project aims to build a quantitative AI-based stock prediction system for the Indian stock market.

The long-term goal is to generate profitable trading signals using machine learning, deep learning, uncertainty estimation, and eventually GenAI-based market analysis.

This is NOT a simple stock-price prediction project.

The objective is to identify the best trading opportunities across NIFTY50 stocks while avoiding low-confidence or potentially loss-making trades.

---

# Current Project Status

## Phase 1: Data Ingestion & Feature Engineering ✅ COMPLETED

Historical data has been collected for all NIFTY50 stocks from:

2015 → Present

The dataset contains engineered features organized into multiple layers.

---

# Dataset Structure

Each row represents a single stock on a single trading day.

## Layer 1: OHLCV

- Open
- High
- Low
- Close
- Volume

---

## Layer 2: Price Derived Features

- daily_return
- open_gap
- intraday_return
- high_low_range
- body_size

---

## Layer 3: Trend Features

- SMA ratios
- EMA ratios
- close_ema20_ratio
- close_ema50_ratio
- ema20_ema50_ratio

---

## Layer 4: Momentum Features

- RSI14
- MACD
- MACD Signal
- MACD Histogram
- ROC5
- ROC10
- Stochastic RSI

---

## Layer 5: Volatility Features

- ATR14
- ATR20
- Rolling Std 5
- Rolling Std 10
- Rolling Std 20
- Bollinger Width

---

## Layer 6: Volume Features

- volume_ratio
- volume_change
- OBV
- VWAP_distance

---

## Layer 7: Market Context Features

- BANKNIFTY return
- FINNIFTY return
- India VIX
- USDINR return
- Crude Oil return
- Gold return

---

## Layer 8: Time Features

- day_of_week
- month
- quarter
- expiry_week
- month_end

---

## Layer 9: Regime Features

- trend_strength
- volatility_regime
- above_200dma

---

# Project Goal (Version 1)

The objective is NOT to predict exact stock prices.

The objective is:

For each NIFTY50 stock, predict:

1. Expected Next-Day Return
2. Probability of Price Going Up
3. Trend Strength
4. Prediction Confidence / Uncertainty

These predictions will later be used to rank stocks and generate trading decisions.

---

# Trading Philosophy

At market open:

The system evaluates all NIFTY50 stocks.

Example output:

Reliance

- Expected Return: +2.8%
- Up Probability: 81%
- Confidence: High

TCS

- Expected Return: +0.2%
- Up Probability: 54%
- Confidence: Low

The system ranks stocks and selects the highest-quality opportunities.

Goal:

Maximize portfolio return while avoiding low-confidence trades.

---

# Why Not Only Predict Up/Down?

A stock can move:

+0.05%

and technically be classified as "UP".

That prediction has little trading value.

Therefore Version 1 focuses primarily on:

Expected Return Prediction

while also deriving:

- Direction
- Trend Strength
- Confidence

from model outputs.

---

# Version 1 Architecture

Initial approach:

Input:

Past 30 trading days

Features:

~40-60 engineered features

Output:

Expected Next-Day Return

Future outputs:

- Direction Probability
- Confidence Estimate
- Trend Strength Score

---

# Phase 2 (CURRENT PHASE)

The next phase is NOT LSTM training.

The next phase is:

Target Engineering
+
Sequence Generation
+
Baseline Models
+
Backtesting Framework

---

# Phase 2 Tasks

## Task 1: Create Prediction Target

For each stock-day:

next_day_return

= (close[t+1] - close[t]) / close[t]

Store as:

target_return

Example:

Today Close = 1000

Tomorrow Close = 1020

target_return = 0.02

---

## Task 2: Generate Rolling Sequences

Create LSTM-ready windows.

Example:

Days 1-30
→ Predict Day 31 Return

Days 2-31
→ Predict Day 32 Return

Days 3-32
→ Predict Day 33 Return

Input shape:

(window_size, num_features)

Recommended:

(30, N)

---

## Task 3: Dataset Split

Use chronological split.

Example:

Train:
2015 - 2022

Validation:
2023

Test:
2024 - Present

NO random shuffling allowed.

---

## Task 4: Baseline Models

Before training LSTM:

Train simple models:

- Linear Regression
- Random Forest
- XGBoost

Purpose:

Establish baseline performance.

Deep learning must outperform these baselines.

---

## Task 5: Evaluation Metrics

Evaluate:

Regression:

- MAE
- RMSE

Directional Metrics:

- Direction Accuracy

Financial Metrics:

- Portfolio Return
- Sharpe Ratio
- Maximum Drawdown
- Win Rate

---

## Task 6: Build Backtesting Engine

For every day:

1. Generate predictions
2. Rank stocks
3. Select top N stocks
4. Simulate trades
5. Measure profitability

Example:

Select Top 5 predicted returns each day.

Backtest on unseen data.

---

# Phase 3 (After Phase 2 Validation)

Only after proving profitability using baseline models:

Train:

CNN + LSTM

Architecture:

Input
→ 1D CNN
→ LSTM
→ Dense Layers
→ Return Prediction

Future additions:

- Monte Carlo Dropout
- Bayesian Neural Networks
- Ensemble Models

for uncertainty estimation.

---

# Success Criteria For Version 1

The system should be able to:

1. Evaluate all NIFTY50 stocks daily.
2. Predict next-day expected return.
3. Estimate confidence.
4. Rank opportunities.
5. Avoid weak/uncertain trades.
6. Produce profitable backtest results.

Only after achieving this should more advanced architectures be explored.

---

# Important Principle

The project goal is NOT:

"Predict stock prices."

The project goal is:

"Generate high-confidence trading decisions that outperform naive market strategies."