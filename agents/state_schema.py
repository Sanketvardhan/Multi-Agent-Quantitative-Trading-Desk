from typing import Dict, Any, List
from pydantic import BaseModel, Field

# ==========================================
# 1. PRE-MARKET CIO STATE
# ==========================================
# class StockChoice(BaseModel):
#     ticker: str
#     directive: str = Field(description="'LONG' or 'SHORT'")
#     confidence_tier: str = Field(description="'HIGH', 'MEDIUM', or 'LOW'")
#     reasoning: str

# class WatchlistSelection(BaseModel):
#     selections: List[StockChoice]

# class CIOState(BaseModel):
#     """The state whiteboard for the 08:45 AM Pre-Market Graph"""
#     target_tickers: List[str] = []                # List of Nifty 50 stocks to scan
#     swing_predictions: Dict[str, dict] = {}       # The raw output from the Swing AI Tool
#     structured_decision: WatchlistSelection = None # The final JSON from Gemini
#     error_logs: List[str] = []

class DailyPlaybookSchema(BaseModel):
    market_regime: str = Field(description="'BULLISH', 'BEARISH', or 'CHOPPY'")
    risk_level: str = Field(description="'AGGRESSIVE', 'MODERATE', or 'DEFENSIVE'")
    approved_sectors: List[str] = Field(description="e.g., ['IT', 'Banking', 'Pharma']")
    banned_sectors: List[str] = Field(description="e.g., ['Energy', 'Metals']")
    reasoning: str = Field(description="1-2 sentences explaining why, citing the math and news.")

class CIOState(BaseModel):
    """The state whiteboard for the 08:45 AM Pre-Market Graph"""
    target_tickers: List[str] = []                # List of Nifty 50 stocks to scan
    swing_predictions: Dict[str, dict] = {}       # The raw output from the Swing AI Tool
    structured_decision: DailyPlaybookSchema = None # The final Macro Playbook from Llama
    error_logs: List[str] = []

# ==========================================
# 2. INTRADAY COPILOT STATE
# ==========================================
# class TradeAlert(BaseModel):
#     ticker: str
#     action: str
#     entry_price: float
#     message: str
class TradeAlert(BaseModel):
    ticker: str
    action: str = Field(description="'EXECUTE LONG', 'EXECUTE SHORT', or 'HOLD'")
    entry_price: float = Field(description="The current live price of the stock")
    stop_loss: float = Field(description="Exact price to exit if the trade goes wrong")
    take_profit: float = Field(description="Exact price to take profits")
    position_size_advice: str = Field(description="Advice on share quantity based on a ₹1000 total risk")
    message: str
    
class IntradayState(BaseModel):
    """The state whiteboard for the 15-minute Intraday Graph"""
    watchlist_config: Dict[str, Any] = {}         # Loaded from active_watchlist.json
    intraday_predictions: Dict[str, dict] = {}    # The raw output from the Intraday AI Tool
    active_alerts: List[TradeAlert] = []          # The final alerts pushed to the human
    error_logs: List[str] = []