import yfinance as yf
import pandas as pd

# Define the stock ticker (e.g., Apple)
ticker_symbol = "AAPL"
stock = yf.Ticker(ticker_symbol)

# Fetch recent news articles
news = stock.news

# Convert to a clean Pandas DataFrame
df = pd.DataFrame(news)

# Display just the titles and links
if not df.empty:
    print(df[['title', 'link', 'publisher']])
else:
    print("No news found for this ticker.")
