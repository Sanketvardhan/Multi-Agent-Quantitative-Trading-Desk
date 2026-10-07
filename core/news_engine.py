import os
import time
import logging
import urllib.request
import xml.etree.ElementTree as ET
from typing import Dict, Any, List, Optional
from datetime import datetime

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("NewsEngine")

# Keywords for Financial Sentiment & Red-Flag Catalyst Detection
POSITIVE_KEYWORDS = {
    "surge", "surges", "jump", "jumps", "rally", "rallies", "profit jumps", "beats estimates",
    "record high", "upgrade", "upgrades", "buy rating", "strong growth", "deal win", "contract",
    "order win", "revenue up", "soars", "gains", "bullish", "outperform", "dividend", "acquisition"
}

NEGATIVE_KEYWORDS = {
    "plunge", "plunges", "fall", "falls", "drop", "drops", "crash", "losses", "misses estimates",
    "slump", "slumps", "downgrade", "downgrades", "sell rating", "fraud", "investigation", "probe",
    "raid", "penalty", "sebi notice", "ed raid", "tax raid", "resigns", "strike", "deficit", "subpoena",
    "warning", "lawsuit", "default", "scam", "top loser", "underperform", "layoffs", "plant shutdown"
}

RED_FLAG_KEYWORDS = {
    "fraud", "investigation", "probe", "raid", "penalty", "sebi notice", "ed raid", "tax raid",
    "scam", "lawsuit", "default", "plant shutdown", "cfo resigns", "ceo resigns"
}

SECTOR_KEYWORD_MAP = {
    "IT": "IT sector stocks TCS Infosys Wipro India",
    "Banking": "Nifty Bank Indian Banking stocks HDFC ICICI SBI",
    "Auto": "Indian Auto sector stocks Maruti Tata Motors",
    "Metals": "Nifty Metal Tata Steel JSW Steel mining",
    "Pharma": "Nifty Pharma Sun Pharma Dr Reddys Indian healthcare",
    "Energy": "Nifty Energy Reliance ONGC crude oil India",
    "FMCG": "Nifty FMCG ITC Hindustan Unilever India consumption",
    "Realty": "Nifty Realty real estate stocks India"
}

class IndianMarketNewsEngine:
    """
    Real-Time Indian Financial Media Aggregator & Sentiment Classifier.
    - Zero external paid API dependencies (Uses Google News Financial RSS for Indian markets).
    - In-memory 15-minute TTL caching to avoid redundant HTTP requests.
    - Financial Sentiment Scoring (-1.0 to +1.0) and Breaking Red-Flag Catalyst Detector.
    """
    def __init__(self, cache_ttl_seconds: int = 900): # 15 minutes default TTL
        self.cache_ttl = cache_ttl_seconds
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

    def _fetch_rss(self, query: str, max_items: int = 5) -> List[Dict[str, str]]:
        encoded_query = urllib.parse.quote(query)
        url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-IN&gl=IN&ceid=IN:en"
        
        try:
            req = urllib.request.Request(url, headers=self.headers)
            with urllib.request.urlopen(req, timeout=4) as response:
                xml_data = response.read()
                
            tree = ET.fromstring(xml_data)
            items = tree.findall('.//item')[:max_items]
            
            results = []
            for item in items:
                title = item.find('title').text if item.find('title') is not None else ""
                pub_date = item.find('pubDate').text if item.find('pubDate') is not None else ""
                source = item.find('source').text if item.find('source') is not None else "News"
                
                # Clean up title (remove publisher suffix if present)
                clean_title = title.rsplit(' - ', 1)[0] if ' - ' in title else title
                results.append({
                    "title": clean_title,
                    "source": source,
                    "pub_date": pub_date
                })
            return results
        except Exception as e:
            logger.debug(f"RSS fetch failed for query '{query}': {e}")
            return []

    def _analyze_sentiment(self, headlines: List[Dict[str, str]]) -> Dict[str, Any]:
        if not headlines:
            return {"score": 0.0, "label": "NEUTRAL", "has_red_flag": False, "red_flags": []}
            
        pos_count = 0
        neg_count = 0
        red_flags = []
        
        for item in headlines:
            text = item["title"].lower()
            
            # Check Red Flags
            for rf in RED_FLAG_KEYWORDS:
                if rf in text:
                    red_flags.append(item["title"])
                    break
                    
            # Positive & Negative counts
            for p in POSITIVE_KEYWORDS:
                if p in text:
                    pos_count += 1
            for n in NEGATIVE_KEYWORDS:
                if n in text:
                    neg_count += 1

        total = pos_count + neg_count
        if total == 0:
            score = 0.0
            label = "NEUTRAL"
        else:
            score = round((pos_count - neg_count) / total, 2)
            if score >= 0.25:
                label = "BULLISH"
            elif score <= -0.25:
                label = "BEARISH"
            else:
                label = "NEUTRAL"
                
        return {
            "score": score,
            "label": label,
            "has_red_flag": len(red_flags) > 0,
            "red_flags": red_flags
        }

    def fetch_market_news(self) -> Dict[str, Any]:
        """Fetches top Indian market-wide headlines (Nifty, Sensex, Global cues)."""
        cache_key = "general_market"
        now = time.time()
        
        if cache_key in self.cache:
            entry = self.cache[cache_key]
            if now - entry["timestamp"] < self.cache_ttl:
                return entry["data"]
                
        headlines = self._fetch_rss("NIFTY 50 Indian Stock Market Sensex", max_items=5)
        sentiment = self._analyze_sentiment(headlines)
        
        data = {
            "headlines": headlines,
            "sentiment": sentiment,
            "updated_at": datetime.utcnow().isoformat()
        }
        self.cache[cache_key] = {"timestamp": now, "data": data}
        return data

    def fetch_sector_news(self, sector: str) -> Dict[str, Any]:
        """Fetches news and sentiment for a specific sector."""
        cache_key = f"sector_{sector}"
        now = time.time()
        
        if cache_key in self.cache:
            entry = self.cache[cache_key]
            if now - entry["timestamp"] < self.cache_ttl:
                return entry["data"]
                
        query = SECTOR_KEYWORD_MAP.get(sector, f"{sector} sector stocks India")
        headlines = self._fetch_rss(query, max_items=4)
        sentiment = self._analyze_sentiment(headlines)
        
        data = {
            "sector": sector,
            "headlines": headlines,
            "sentiment": sentiment,
            "updated_at": datetime.utcnow().isoformat()
        }
        self.cache[cache_key] = {"timestamp": now, "data": data}
        return data

    def fetch_ticker_news(self, ticker: str) -> Dict[str, Any]:
        """Fetches news and checks for breaking red-flag catalysts for a specific stock."""
        cache_key = f"ticker_{ticker}"
        now = time.time()
        
        if cache_key in self.cache:
            entry = self.cache[cache_key]
            if now - entry["timestamp"] < self.cache_ttl:
                return entry["data"]
                
        headlines = self._fetch_rss(f"{ticker} share price news NSE", max_items=3)
        sentiment = self._analyze_sentiment(headlines)
        
        data = {
            "ticker": ticker,
            "headlines": headlines,
            "sentiment": sentiment,
            "has_breaking_negative": sentiment["has_red_flag"] or sentiment["label"] == "BEARISH",
            "has_breaking_positive": sentiment["label"] == "BULLISH",
            "updated_at": datetime.utcnow().isoformat()
        }
        self.cache[cache_key] = {"timestamp": now, "data": data}
        return data

# Singleton Instance
news_engine = IndianMarketNewsEngine()

if __name__ == "__main__":
    import urllib.parse
    m = news_engine.fetch_market_news()
    print("Market Sentiment:", m["sentiment"])
    for h in m["headlines"]:
        print("-", h["title"])
        
    t = news_engine.fetch_ticker_news("MARUTI")
    print("\nMARUTI Ticker News:", t["sentiment"])
    for h in t["headlines"]:
        print("-", h["title"])
