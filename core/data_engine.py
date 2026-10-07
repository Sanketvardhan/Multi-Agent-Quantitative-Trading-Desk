import os
import sys
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple
import pandas as pd
import numpy as np
import requests
import yfinance as yf
import ta

# Import central configuration
from core.config import DATA_PROVIDER, DATA_CACHE_TTL_SECONDS, ATR_PERIOD

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("DataEngine")

def format_ticker_for_yf(ticker: str) -> str:
    """Standardizes symbols for Yahoo Finance across equities, indices, and commodities."""
    clean = str(ticker).strip().upper()
    if clean in ["NIFTY", "NIFTY 50", "NIFTY50", "^NSEI"]:
        return "^NSEI"
    if clean in ["BANKNIFTY", "NIFTY BANK", "^NSEBANK"]:
        return "^NSEBANK"
    if clean in ["INDIAVIX", "INDIA VIX", "^INDIAVIX"]:
        return "^INDIAVIX"
    if clean.startswith("^") or clean.endswith("=X") or clean.endswith("=F") or clean.endswith(".NS") or clean.endswith(".BO"):
        return clean
    return f"{clean}.NS"

class NSEDirectClient:
    """
    Direct NSE India HTTP client that fetches live market data directly from
    nseindia.com using an active session cookie. Provides real-time quotes at 0 cost.
    """
    def __init__(self):
        self.session = requests.Session()
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive'
        }
        self.session.headers.update(self.headers)
        self.last_cookie_refresh = 0
        self.cookie_refresh_interval = 300 # Refresh cookies every 5 minutes

    def _refresh_cookies(self):
        now = time.time()
        if now - self.last_cookie_refresh > self.cookie_refresh_interval:
            try:
                self.session.get("https://www.nseindia.com", timeout=6)
                self.last_cookie_refresh = now
            except Exception as e:
                logger.debug(f"NSE cookie refresh notice: {e}")

    def get_live_quote(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Fetches live LTP, Open, High, Low directly from NSE."""
        clean_symbol = symbol.replace(".NS", "").replace("^", "").upper()
        if clean_symbol in ["NSEI", "NIFTY 50", "NIFTY50"]:
            clean_symbol = "NIFTY 50"
            
        self._refresh_cookies()
        url = f"https://www.nseindia.com/api/quote-equity?symbol={clean_symbol}"
        
        try:
            req_headers = dict(self.headers)
            req_headers['Referer'] = f"https://www.nseindia.com/get-quotes/equity?symbol={clean_symbol}"
            response = self.session.get(url, headers=req_headers, timeout=4)
            
            if response.status_code == 200:
                data = response.json()
                price_info = data.get('priceInfo', {})
                last_price = price_info.get('lastPrice')
                if last_price:
                    return {
                        'symbol': clean_symbol,
                        'current_price': float(last_price),
                        'open': float(price_info.get('open', last_price)),
                        'high': float(price_info.get('intraDayHighLow', {}).get('max', last_price)),
                        'low': float(price_info.get('intraDayHighLow', {}).get('min', last_price)),
                        'previous_close': float(price_info.get('previousClose', last_price)),
                        'change_pct': float(price_info.get('pChange', 0.0)),
                        'source': 'NSE_DIRECT'
                    }
        except Exception as e:
            logger.debug(f"NSE direct quote failed for {symbol}: {e}")
        return None


class UniversalDataEngine:
    """
    Unified Data Ingestion Engine for both Swing and Intraday models.
    Provides multi-tier fallbacks: NSE Direct -> Yahoo Finance Session -> Cached Ticks.
    """
    def __init__(self):
        self.nse_client = NSEDirectClient()
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.yf_session = requests.Session()
        self.yf_session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
        })

    def get_realtime_price(self, ticker: str) -> Optional[float]:
        """
        Gets instant LTP (Last Traded Price) with caching and multi-tier fallback.
        """
        clean_ticker = ticker.replace(".NS", "").upper()
        now = time.time()
        
        # 1. Check in-memory cache
        if clean_ticker in self.cache:
            entry = self.cache[clean_ticker]
            if now - entry['timestamp'] < DATA_CACHE_TTL_SECONDS:
                return entry['price']

        # 2. Tier 1: Try Direct NSE (only for standard equity tickers)
        if not clean_ticker.startswith("^"):
            quote = self.nse_client.get_live_quote(clean_ticker)
            if quote and quote.get('current_price'):
                price = quote['current_price']
                self.cache[clean_ticker] = {'price': price, 'timestamp': now, 'source': 'NSE'}
                return price

        # 3. Tier 2: Fallback to Yahoo Finance fast_info
        try:
            yf_ticker = format_ticker_for_yf(ticker)
            stock = yf.Ticker(yf_ticker, session=self.yf_session)
            fast_info = stock.fast_info
            if 'last_price' in fast_info and fast_info['last_price'] is not None:
                price = round(float(fast_info['last_price']), 2)
                self.cache[clean_ticker] = {'price': price, 'timestamp': now, 'source': 'YF_FAST'}
                return price
        except Exception as e:
            logger.debug(f"YFinance fast_info failed for {ticker}: {e}")

        # 4. Tier 3: Try history fallback
        try:
            yf_ticker = format_ticker_for_yf(ticker)
            stock = yf.Ticker(yf_ticker, session=self.yf_session)
            hist = stock.history(period="1d", interval="1m")
            if not hist.empty:
                price = round(float(hist['Close'].iloc[-1]), 2)
                self.cache[clean_ticker] = {'price': price, 'timestamp': now, 'source': 'YF_1M'}
                return price
        except Exception:
            pass

        # 5. Return stale cache if available
        if clean_ticker in self.cache:
            return self.cache[clean_ticker]['price']

        return None

    def fetch_historical_bars(self, ticker: str, interval: str = "15m", period: str = "10d") -> pd.DataFrame:
        """
        Fetches clean OHLCV historical dataframe with proper ticker formatting.
        """
        yf_ticker = format_ticker_for_yf(ticker)
        try:
            stock = yf.Ticker(yf_ticker, session=self.yf_session)
            df = stock.history(period=period, interval=interval)
            
            if df.empty or len(df) < 5:
                # Secondary attempt without custom session in case of cookie issues
                stock_alt = yf.Ticker(yf_ticker)
                df = stock_alt.history(period=period, interval=interval)

            if df.empty:
                raise ValueError(f"Empty dataframe returned for {ticker} ({yf_ticker})")

            df.reset_index(inplace=True)
            date_col = 'Datetime' if 'Datetime' in df.columns else 'Date'
            df.rename(columns={
                date_col: 'date_time',
                'Open': 'open',
                'High': 'high',
                'Low': 'low',
                'Close': 'close',
                'Volume': 'volume'
            }, inplace=True)
            df['date_time'] = pd.to_datetime(df['date_time']).dt.tz_localize(None)
            return df
        except Exception as e:
            logger.warning(f"Error fetching historical bars for {ticker} ({yf_ticker}): {e}")
            return pd.DataFrame()

    def calculate_technical_context(self, ticker: str) -> Dict[str, Any]:
        """
        Calculates live ATR, RSI, MACD, and LTP for risk management and sizing.
        """
        df = self.fetch_historical_bars(ticker, interval="15m", period="5d")
        if df.empty:
            price = self.get_realtime_price(ticker)
            return {
                "ticker": ticker,
                "current_price": price or 0.0,
                "atr": 0.0,
                "rsi_14": 50.0,
                "macd_hist": 0.0,
                "high": price or 0.0,
                "low": price or 0.0,
                "status": "partial" if price else "error"
            }

        df['atr_14'] = ta.volatility.average_true_range(df['high'], df['low'], df['close'], window=ATR_PERIOD)
        df['rsi_14'] = ta.momentum.rsi(df['close'], window=14)
        macd = ta.trend.MACD(df['close'])
        df['macd_hist'] = macd.macd_diff()

        latest = df.iloc[-1]
        live_price = self.get_realtime_price(ticker) or float(latest['close'])
        atr = float(latest['atr_14']) if not pd.isna(latest['atr_14']) else float(latest['close']) * 0.015

        return {
            "ticker": ticker,
            "current_price": round(live_price, 2),
            "atr": round(atr, 2),
            "rsi_14": round(float(latest['rsi_14']), 2) if not pd.isna(latest['rsi_14']) else 50.0,
            "macd_hist": round(float(latest['macd_hist']), 4) if not pd.isna(latest['macd_hist']) else 0.0,
            "high": round(float(latest['high']), 2),
            "low": round(float(latest['low']), 2),
            "status": "success"
        }

# Global singleton instance
data_engine = UniversalDataEngine()
