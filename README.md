## 🔄 Data Flow & Lifecycle

### 1. The Macro Strategist (Pre-Market)

* **Trigger:** `market_daemon.py` at 08:45 AM IST.

* **Process:** The **CIO Agent** sweeps the market, analyzes global news sentiment, and calculates broad sector risks.

* **Output:** Saves a structured **Daily Playbook** to the `daily_playbook` database table.

* **Significance:** This provides the strategic "guardrails" for all other agents.

### 2. The Alpha Engine (The Hunter)

* **Trigger:** Every 15 minutes by `market_daemon.py`.

* **Process:** Pure Python script runs PyTorch `StockCNNLSTMAttention` models across the Nifty 50.

* **Output:** Overwrites the `live_opportunities` table with the top setups based on absolute return magnitude.

* **Significance:** Decoupled from LLMs for speed and zero cost.

### 3. The Tactical Copilot (The Sniper)

* **Trigger:** Every 15 minutes (30 seconds after Alpha Engine).

* **Process:**

  1. Reads the `Daily Playbook` (CIO instructions).
  2. Reads `live_opportunities` (Alpha signals).
  3. Checks the `cooldown_ledger` (Penalty Box).
  4. Evaluates against the current Nifty Trend.

* **Output:** Routes trade proposals to the `FastAPI` endpoint.

### 4. The Guardian (Risk Manager)

* **Trigger:** Every 5 minutes.

* **Process:** Scans the `trade_ledger` for `ACTIVE` trades. Evaluates live price action vs. RSI/MACD indicators.

* **Output:** Updates P&L in real-time. If a trade is stopped out, it automatically updates the `cooldown_ledger` to prevent revenge trading.

## 🧩 Agent Roles

<br />

**Agent**

**Technology**

**Responsibility**

**CIO**

Llama 3 + News API

Macro-regime, sector bias, risk appetite.

**Alpha**

PyTorch + TradingView

Quantitive setup discovery (Math only).

**Copilot**

Llama 3 + LangGraph

Sizing, execution logic, and alignment checks.

**Risk Manager**

Llama 3 + TA Lib

Trailing stops, profit-taking, and circuit breaking.

## 🛠️ Key Technical Differentiators

* **Zero-Cost Alpha Discovery:** By using a pure Python script for the Alpha Engine, the system scans the entire Nifty 50 universe at \$0 cost, leaving your LLM budget for high-level tactical decision-making.

* **The Penalty Box (Circuit Breaker):** If the Risk Manager cuts a loss, the stock is automatically blacklisted in the `cooldown_ledger` for 60 minutes, physically preventing the Copilot from re-entering the trade until the market settles.

* **Shared Memory Architecture:** Using PostgreSQL as the "truth" allows you to plug in a React frontend, a mobile app, or a Telegram bot without changing any of the backend agent logic.
