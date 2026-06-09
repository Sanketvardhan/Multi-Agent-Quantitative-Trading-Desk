# import os
# import yfinance as yf
# import pandas as pd
# import ta
# import requests
# from datetime import datetime
# from pydantic import BaseModel, Field

# # Database Imports
# from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
# from sqlalchemy.orm import sessionmaker, declarative_base

# # LangChain Imports
# from langchain_google_genai import ChatGoogleGenerativeAI
# from dotenv import load_dotenv

# # --- Configuration & Database Setup ---
# load_dotenv()
# DB_PASSWORD = os.getenv('DB_PASSWORD', 'root')
# DATABASE_URL = f"postgresql://postgres:{DB_PASSWORD}@localhost:5432/nifty_intraday_db"

# engine = create_engine(DATABASE_URL)
# SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
# Base = declarative_base()

# class Trade(Base):
#     __tablename__ = "trade_ledger"
#     id = Column(Integer, primary_key=True, index=True)
#     ticker = Column(String, index=True)
#     action = Column(String)
#     entry_price = Column(Float)
#     take_profit = Column(Float)
#     stop_loss = Column(Float)
#     sizing = Column(Integer)
#     status = Column(String, default="PENDING")
#     created_at = Column(DateTime, default=datetime.utcnow)

# # --- Pydantic Schema for LLM Output ---
# class RiskDecision(BaseModel):
#     decision: str = Field(description="'HOLD', 'TRAIL_STOP_LOSS', 'FORCE_CLOSE', 'TAKE_PROFIT', or 'CUT_LOSS'")
#     new_stop_loss: float = Field(description="The updated Stop Loss. If HOLD, FORCE_CLOSE, TAKE_PROFIT, or CUT_LOSS, keep it the same as the current stop loss.")
#     reasoning: str = Field(description="A 1-sentence explanation citing the live indicators (RSI/MACD) and the current profit/loss.")

# # --- The Cognitive Agent ---
# class RiskManagerAgent:
#     def __init__(self):
#         self.db = SessionLocal()
#         # Initialize Gemini with 0.0 temperature for strict logic
#         self.llm = ChatGoogleGenerativeAI(
#             model="gemini-2.5-flash-lite",
#             google_api_key=os.getenv("GOOGLE_API_KEY"),
#             temperature=0.0
#         )
#         self.structured_llm = self.llm.with_structured_output(RiskDecision)

#     def fetch_live_technical_context(self, ticker: str) -> dict:
#         """Fetches live price and calculates basic intraday indicators for context."""
#         try:
#             session = requests.Session()
#             session.headers.update({'User-Agent': 'Mozilla/5.0'})
#             stock = yf.Ticker(f"{ticker}.NS", session=session)
            
#             # Fetch 5 days of 15m data to get enough candles for indicators
#             df = stock.history(period="5d", interval="15m")
#             if df.empty: return {}

#             # Calculate basic momentum indicators
#             df['rsi_14'] = ta.momentum.rsi(df['Close'], window=14)
#             macd = ta.trend.MACD(df['Close'])
#             df['macd_hist'] = macd.macd_diff()
#             df['atr_14'] = ta.volatility.average_true_range(df['High'], df['Low'], df['Close'], window=14)
            
#             # Grab the very last candle
#             latest = df.iloc[-1]
#             return {
#                 "current_price": round(float(latest['Close']), 2),
#                 "rsi_14": round(float(latest['rsi_14']), 2),
#                 "macd_histogram": round(float(latest['macd_hist']), 4),
#                 "atr": round(float(latest['atr_14']), 2)
#             }
#         except Exception as e:
#             print(f"Error fetching data for {ticker}: {e}")
#             return {}

#     def manage_active_positions(self):
#         """Monitors active positions using LLM reasoning."""
#         print("\n[Risk Manager Agent] 🛡️ Evaluating Active Portfolio Context...")
#         active_trades = self.db.query(Trade).filter(Trade.status == "ACTIVE").all()
        
#         if not active_trades:
#             print(" -> No active positions found in database.")
#             return

#         for trade in active_trades:
#             context = self.fetch_live_technical_context(trade.ticker)
#             if not context:
#                 continue
                
#             current_price = context['current_price']
            
#             # Calculate current Unrealized P&L
#             if "SHORT" in trade.action:
#                 pnl_per_share = trade.entry_price - current_price
#             else:
#                 pnl_per_share = current_price - trade.entry_price
            
#             total_pnl = round(pnl_per_share * trade.sizing, 2)
            
#             print(f"\n -> Analyzing {trade.ticker} | {trade.action} | Entry: ₹{trade.entry_price} | Live: ₹{current_price} | PnL: ₹{total_pnl}")

#             # --- LLM COGNITIVE EVALUATION ---
#             system_instruction = (
#                 "You are an elite quantitative Risk Manager monitoring an open position.\n"
#                 "You will receive the trade details and live technical indicators.\n\n"
#                 "MANAGEMENT RULES:\n"
#                 "1. HARD EXITS: If the price has hit or crossed the Take Profit -> 'TAKE_PROFIT'. If it hit the Stop Loss -> 'CUT_LOSS'.\n"
#                 "2. PROTECT PROFITS: If the trade is highly profitable but momentum is reversing against us (e.g., RSI diverging, MACD flipping) -> 'FORCE_CLOSE'.\n"
#                 "3. TRAIL STOPS: If the trade is in profit and the trend is strong, update the Stop Loss closer to the current price to lock in profits -> 'TRAIL_STOP_LOSS'.\n"
#                 "4. PATIENCE: If the trade is hovering near entry and indicators are normal -> 'HOLD'.\n\n"
#                 "Your reasoning must be extremely brief and cite the specific indicators or PnL driving your decision."
#             )
            
#             payload = {
#                 "trade_details": {
#                     "action": trade.action,
#                     "entry_price": trade.entry_price,
#                     "take_profit": trade.take_profit,
#                     "current_stop_loss": trade.stop_loss,
#                     "unrealized_pnl_inr": total_pnl
#                 },
#                 "live_market_context": context
#             }
            
#             # Ask Gemini what to do
#             decision = self.structured_llm.invoke([
#                 {"role": "system", "content": system_instruction},
#                 {"role": "user", "content": f"Evaluate this position:\n{payload}"}
#             ])

#             # Apply the Decision to the Database
#             print(f"   🤖 ACTION: {decision.decision}")
#             print(f"   💬 {decision.reasoning}")

#             if decision.decision in ["TAKE_PROFIT", "CUT_LOSS", "FORCE_CLOSE"]:
#                 trade.status = f"CLOSED_{decision.decision}"
#                 print(f"   🔒 Trade Closed. Status updated in ledger.")
            
#             elif decision.decision == "TRAIL_STOP_LOSS":
#                 print(f"   🛡️ Stop Loss updated from ₹{trade.stop_loss} to ₹{decision.new_stop_loss}")
#                 trade.stop_loss = decision.new_stop_loss

#         # Save all changes to Postgres
#         self.db.commit()

#     def close(self):
#         self.db.close()

# if __name__ == "__main__":
#     rm = RiskManagerAgent()
#     rm.manage_active_positions()
#     rm.close()

import os
import yfinance as yf
import pandas as pd
import ta
import requests
from datetime import datetime
from pydantic import BaseModel, Field

# Database Imports
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
from sqlalchemy.orm import sessionmaker, declarative_base

# LangChain Imports
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv

import time
import pytz

# --- Configuration & Database Setup ---
load_dotenv()
DB_PASSWORD = os.getenv('DB_PASSWORD', 'root')
DATABASE_URL = f"postgresql://postgres:{DB_PASSWORD}@localhost:5432/nifty_intraday_db"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Trade(Base):
    __tablename__ = "trade_ledger"
    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String, index=True)
    action = Column(String)
    entry_price = Column(Float)
    take_profit = Column(Float)
    stop_loss = Column(Float)
    sizing = Column(Integer)
    status = Column(String, default="PENDING")
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # --- THE NEW COLUMNS WE ADDED IN PGADMIN ---
    live_price = Column(Float, nullable=True)
    live_rsi = Column(Float, nullable=True)
    live_macd = Column(Float, nullable=True)
    current_pnl = Column(Float, nullable=True)
    risk_reasoning = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    activated_at = Column(DateTime, nullable=True)

# --- Pydantic Schema for LLM Output ---
class RiskDecision(BaseModel):
    decision: str = Field(description="'HOLD', 'TRAIL_STOP_LOSS', 'FORCE_CLOSE', 'TAKE_PROFIT', or 'CUT_LOSS'")
    new_stop_loss: float = Field(description="The updated Stop Loss. If HOLD, FORCE_CLOSE, TAKE_PROFIT, or CUT_LOSS, keep it the same as the current stop loss.")
    reasoning: str = Field(description="A 1-sentence explanation citing the live indicators (RSI/MACD) and the current profit/loss.")

# --- The Cognitive Agent ---
class RiskManagerAgent:
    def __init__(self):
        self.db = SessionLocal()
        # Initialize Gemini with 0.0 temperature for strict logic
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash-lite",
            google_api_key=os.getenv("GOOGLE_API_KEY"),
            temperature=0.0
        )
        self.structured_llm = self.llm.with_structured_output(RiskDecision)

    def fetch_live_technical_context(self, ticker: str) -> dict:
        """Fetches live price and calculates basic intraday indicators for context."""
        try:
            session = requests.Session()
            session.headers.update({'User-Agent': 'Mozilla/5.0'})
            stock = yf.Ticker(f"{ticker}.NS", session=session)
            
            # Fetch 5 days of 15m data to get enough candles for indicators
            df = stock.history(period="5d", interval="15m")
            if df.empty: return {}

            # Calculate basic momentum indicators
            df['rsi_14'] = ta.momentum.rsi(df['Close'], window=14)
            macd = ta.trend.MACD(df['Close'])
            df['macd_hist'] = macd.macd_diff()
            df['atr_14'] = ta.volatility.average_true_range(df['High'], df['Low'], df['Close'], window=14)
            
            # Grab the very last candle
            latest = df.iloc[-1]
            return {
                "current_price": round(float(latest['Close']), 2),
                "rsi_14": round(float(latest['rsi_14']), 2),
                "macd_histogram": round(float(latest['macd_hist']), 4),
                "atr": round(float(latest['atr_14']), 2)
            }
        except Exception as e:
            print(f"Error fetching data for {ticker}: {e}")
            return {}

    def manage_active_positions(self):
        """Monitors active positions using LLM reasoning."""
        print("\n[Risk Manager Agent] 🛡️ Evaluating Active Portfolio Context...")
        active_trades = self.db.query(Trade).filter(Trade.status == "ACTIVE").all()
        
        if not active_trades:
            print(" -> No active positions found in database.")
            return

        # for trade in active_trades:
        #     context = self.fetch_live_technical_context(trade.ticker)
        #     if not context:
        #         continue
                
        #     current_price = context['current_price']
            
        #     # Calculate current Unrealized P&L
        #     if "SHORT" in trade.action:
        #         pnl_per_share = trade.entry_price - current_price
        #     else:
        #         pnl_per_share = current_price - trade.entry_price
            
        #     total_pnl = round(pnl_per_share * trade.sizing, 2)
            
        #     print(f"\n -> Analyzing {trade.ticker} | {trade.action} | Entry: ₹{trade.entry_price} | Live: ₹{current_price} | PnL: ₹{total_pnl}")

        #     # --- LLM COGNITIVE EVALUATION ---
        #     system_instruction = (
        #         "You are an elite quantitative Risk Manager monitoring an open position.\n"
        #         "You will receive the trade details and live technical indicators.\n\n"
        #         "MANAGEMENT RULES:\n"
        #         "1. HARD EXITS: If the price has hit or crossed the Take Profit -> 'TAKE_PROFIT'. If it hit the Stop Loss -> 'CUT_LOSS'.\n"
        #         "2. PROTECT PROFITS: If the trade is highly profitable but momentum is reversing against us (e.g., RSI diverging, MACD flipping) -> 'FORCE_CLOSE'.\n"
        #         "3. TRAIL STOPS: If the trade is in profit and the trend is strong, update the Stop Loss closer to the current price to lock in profits -> 'TRAIL_STOP_LOSS'.\n"
        #         "4. PATIENCE: If the trade is hovering near entry and indicators are normal -> 'HOLD'.\n\n"
        #         "Your reasoning must be extremely brief and cite the specific indicators or PnL driving your decision."
        #     )
            
        #     payload = {
        #         "trade_details": {
        #             "action": trade.action,
        #             "entry_price": trade.entry_price,
        #             "take_profit": trade.take_profit,
        #             "current_stop_loss": trade.stop_loss,
        #             "unrealized_pnl_inr": total_pnl
        #         },
        #         "live_market_context": context
        #     }
            
        #     # Ask Gemini what to do
        #     decision = self.structured_llm.invoke([
        #         {"role": "system", "content": system_instruction},
        #         {"role": "user", "content": f"Evaluate this position:\n{payload}"}
        #     ])

        #     print(f"   🤖 ACTION: {decision.decision}")
        #     print(f"   💬 {decision.reasoning}")

        #     # --- THIS IS THE NEW PART THAT SAVES DATA TO PGADMIN ---
        #     trade.live_price = current_price
        #     trade.live_rsi = context['rsi_14']
        #     trade.live_macd = context['macd_histogram']
        #     trade.current_pnl = total_pnl
        #     trade.risk_reasoning = decision.reasoning

        #     # Apply the decision limits
        #     if decision.decision in ["TAKE_PROFIT", "CUT_LOSS", "FORCE_CLOSE"]:
        #         trade.status = f"CLOSED_{decision.decision}"
        #         print(f"   🔒 Trade Closed. Status updated in ledger.")
        #     elif decision.decision == "TRAIL_STOP_LOSS":
        #         print(f"   🛡️ Stop Loss updated from ₹{trade.stop_loss} to ₹{decision.new_stop_loss}")
        #         trade.stop_loss = decision.new_stop_loss

        #         time.sleep(4)

        # # Save all changes to Postgres
        # self.db.commit()
        for trade in active_trades:
            context = self.fetch_live_technical_context(trade.ticker)
            if not context:
                continue
                
            current_price = context['current_price']
            
            # --- TIME AWARENESS CALCULATION ---
            ist = pytz.timezone('Asia/Kolkata')
            current_ist_time = datetime.now(ist)
            
            # Calculate how many minutes the trade has been active
            if trade.activated_at:
                # activated_at is in UTC. We compare it to current UTC time.
                minutes_held = int((datetime.utcnow() - trade.activated_at).total_seconds() / 60)
            else:
                minutes_held = 0

            # Calculate current Unrealized P&L
            if "SHORT" in trade.action:
                pnl_per_share = trade.entry_price - current_price
            else:
                pnl_per_share = current_price - trade.entry_price
            total_pnl = round(pnl_per_share * trade.sizing, 2)
            
            print(f"\n -> Analyzing {trade.ticker} | Held for: {minutes_held} mins | Live: ₹{current_price} | PnL: ₹{total_pnl}")

            # --- LLM COGNITIVE EVALUATION WITH TIME AWARENESS ---
            system_instruction = (
                "You are an elite quantitative Risk Manager monitoring an open position.\n"
                "You receive trade details, live indicators, and critical TIME data.\n\n"
                "MANAGEMENT RULES:\n"
                "1. HARD EXITS: If the price has hit or crossed the Take Profit -> 'TAKE_PROFIT'. If it hit the Stop Loss -> 'CUT_LOSS'.\n"
                "2. END OF DAY SQUARING: Indian markets close at 15:30. Brokers auto-square off at 15:15. If the 'current_time' is 15:15 or later, you MUST output 'FORCE_CLOSE' to flatten the book, regardless of PnL.\n"
                "3. TIME DECAY / CONSOLIDATION: If 'minutes_held' is greater than 90 minutes, and the PnL is hovering near 0, and the MACD histogram is flat (meaning zero momentum), output 'FORCE_CLOSE' to free up capital.\n"
                "4. PROTECT PROFITS: If highly profitable but momentum is reversing -> 'FORCE_CLOSE'.\n"
                "5. TRAIL STOPS: If in profit and trend is strong -> 'TRAIL_STOP_LOSS'.\n"
                "6. PATIENCE: If recently opened and indicators are normal -> 'HOLD'.\n\n"
                "Your reasoning must be extremely brief. If closing due to time decay or EOD, state that explicitly."
            )
            
            payload = {
                "time_data": {
                    "current_market_time_ist": current_ist_time.strftime("%H:%M"),
                    "minutes_held": minutes_held
                },
                "trade_details": {
                    "action": trade.action,
                    "entry_price": trade.entry_price,
                    "take_profit": trade.take_profit,
                    "current_stop_loss": trade.stop_loss,
                    "unrealized_pnl_inr": total_pnl
                },
                "live_market_context": context
            }
            
            # Rate Limit Retry Loop
            decision = None
            for attempt in range(3):
                try:
                    decision = self.structured_llm.invoke([
                        {"role": "system", "content": system_instruction},
                        {"role": "user", "content": f"Evaluate this position:\n{payload}"}
                    ])
                    break 
                except Exception as e:
                    if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                        print(f"   ⏳ API Rate Limit Hit (Attempt {attempt + 1}/3). Sleeping 35s...")
                        import time
                        time.sleep(35)
                    else:
                        print(f"   ❌ Unhandled LLM Error: {e}")
                        break
            
            if not decision:
                continue

            print(f"   🤖 ACTION: {decision.decision}")
            print(f"   💬 {decision.reasoning}")

            # --- SAVE DATA TO PGADMIN ---
            trade.live_price = current_price
            trade.live_rsi = context['rsi_14']
            trade.live_macd = context['macd_histogram']
            trade.current_pnl = total_pnl
            trade.risk_reasoning = decision.reasoning

            # Apply the decision limits
            if decision.decision in ["TAKE_PROFIT", "CUT_LOSS", "FORCE_CLOSE"]:
                trade.status = f"CLOSED_{decision.decision}"
                print(f"   🔒 Trade Closed. Status updated in ledger.")
            elif decision.decision == "TRAIL_STOP_LOSS":
                print(f"   🛡️ Stop Loss updated from ₹{trade.stop_loss} to ₹{decision.new_stop_loss}")
                trade.stop_loss = decision.new_stop_loss

            time.sleep(4) # Throttle to protect API limits

        self.db.commit()

    def close(self):
        self.db.close()

if __name__ == "__main__":
    rm = RiskManagerAgent()
    rm.manage_active_positions()
    rm.close()