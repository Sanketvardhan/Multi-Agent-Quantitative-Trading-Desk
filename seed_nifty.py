import os
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, Column, String, Integer
from sqlalchemy.orm import sessionmaker, declarative_base

# 1. Load Environment & Database Connection
load_dotenv()
DB_PASSWORD = os.getenv('DB_PASSWORD', 'root')
DATABASE_URL = f"postgresql://postgres:{DB_PASSWORD}@localhost:5432/converse_db"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# 2. Define the Table Schema (With proper primary key)
class NiftyConstituent(Base):
    __tablename__ = "nifty_constituents"
    __table_args__ = {'extend_existing': True} 
    
    # We use the ticker itself as the Primary Key so we don't even need an 'id' column!
    ticker = Column(String, primary_key=True, index=True)

# 3. Clean and Reset the Table Automatically
print("🧼 Resetting table schema to ensure perfect alignment...")
# This safely wipes out your empty manual table structure
Base.metadata.drop_all(bind=engine, tables=[NiftyConstituent.__table__])
# This builds a pristine new table optimized for our ORM code
Base.metadata.create_all(bind=engine)

# 4. Scrape the Clean Symbols from Wikipedia
print("🌍 Scraping Nifty 50 tickers from Wikipedia...")
url = 'https://en.wikipedia.org/wiki/NIFTY_50'
headers = {'User-Agent': 'Mozilla/5.0'}

try:
    tables = pd.read_html(url, storage_options=headers)
    nifty_table = None
    for table in tables:
        if 'Symbol' in table.columns:
            nifty_table = table
            break
            
    if nifty_table is None:
        raise ValueError("Could not find the Symbol column on Wikipedia.")
        
    tickers = nifty_table['Symbol'].astype(str).tolist()
    print(f"✅ Found {len(tickers)} tickers to insert.")

    # 5. Push them into your PostgreSQL table
    db = SessionLocal()
    print("💾 Writing tickers to PostgreSQL...")
    
    for symbol in tickers:
        new_stock = NiftyConstituent(ticker=symbol)
        db.add(new_stock)
            
    db.commit()
    print("🚀 Seed Complete! Your database table is officially populated and perfectly aligned.")

except Exception as e:
    print(f"❌ Seeding Failed: {e}")
finally:
    db.close()