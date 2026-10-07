import os
from dotenv import load_dotenv

# Base paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(BASE_DIR, '.env'))

# --- UNIFIED DATABASE CONFIGURATION ---
DB_PASSWORD = os.getenv('DB_PASSWORD', 'root')
DB_USER = os.getenv('DB_USER', 'postgres')
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_NAME = os.getenv('DB_NAME', 'converse_db')

DATABASE_URL = os.getenv('DATABASE_URL', f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}")

# --- CAPITAL & RISK MANAGEMENT CONFIGURATION ---
INITIAL_CAPITAL = float(os.getenv('INITIAL_CAPITAL', 10000.0))
RISK_PER_TRADE = float(os.getenv('RISK_PER_TRADE', 0.015))        # 1.5% max risk per trade
MAX_ALLOCATION_PER_TRADE = float(os.getenv('MAX_ALLOCATION', 0.25)) # 25% max capital in single stock
MAX_OPEN_POSITIONS = int(os.getenv('MAX_OPEN_POSITIONS', 3))       # Maximum concurrent positions (max 3)
MAX_DAILY_TRADES = int(os.getenv('MAX_DAILY_TRADES', 6))           # Maximum total trades per day (max 6)
MAX_LOSSES_PER_TICKER_DAILY = int(os.getenv('MAX_LOSSES_PER_TICKER_DAILY', 2)) # 2 loss strikes and locked for the day
MAX_TRADES_PER_TICKER_DAILY = int(os.getenv('MAX_TRADES_PER_TICKER_DAILY', 2)) # Max 2 total trades per stock per day

# --- VOLATILITY & EXECUTION TUNING ---
ATR_PERIOD = 14
ATR_SL_MULTIPLIER = float(os.getenv('ATR_SL_MULTIPLIER', 1.5))     # SL at 1.5x ATR distance
ATR_TP_MULTIPLIER = float(os.getenv('ATR_TP_MULTIPLIER', 2.5))     # Expected target ratio for setup gating
TRAILING_ATR_MULTIPLIER = float(os.getenv('TRAILING_ATR_MULTIPLIER', 1.2)) # Trailing floor at 1.2x ATR from peak

# --- DAILY PROFIT PROTECTION CIRCUIT BREAKER ---
DAILY_PROFIT_LOCK_THRESHOLD = float(os.getenv('DAILY_PROFIT_LOCK_THRESHOLD', 300.0)) # ₹300+ triggers profit lock
DAILY_PROFIT_MAX_DRAWDOWN = float(os.getenv('DAILY_PROFIT_MAX_DRAWDOWN', 0.30))       # Halt if 30% of peak is lost

# --- MINIMUM FRICTION THRESHOLD ---
# Minimum required monetary gross expected profit to overcome round-trip brokerage + STT + taxes
MIN_EXPECTED_PROFIT_INR = float(os.getenv('MIN_EXPECTED_PROFIT_INR', 15.0))
ESTIMATED_BROKERAGE_TURNOVER_PCT = float(os.getenv('ESTIMATED_FEE_PCT', 0.0008)) # 0.08% estimated friction

# --- COOLDOWN PENALTY BOX ---
COOLDOWN_MINUTES = int(os.getenv('COOLDOWN_MINUTES', 45))          # Minutes to ban a stopped-out stock

# --- DATA INGESTION CONFIGURATION ---
DATA_PROVIDER = os.getenv('DATA_PROVIDER', 'hybrid')               # 'hybrid', 'nse_direct', 'yfinance'
DATA_CACHE_TTL_SECONDS = int(os.getenv('DATA_CACHE_TTL', 60))      # In-memory quote cache TTL
