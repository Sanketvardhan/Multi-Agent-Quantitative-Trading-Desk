import os
from dotenv import load_dotenv

load_dotenv() # This loads the variables from the .env file

import pandas as pd
from sqlalchemy import create_engine

# Format: postgresql://username:password@host:port/database_name
DB_USER = 'postgres'
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_HOST = 'localhost'
DB_PORT = '5432'
DB_NAME = 'nifty_lstm_db'

# Database Connection
engine = create_engine(f'postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}')

def merge_with_database():
    print("Reading existing features and macro data from PostgreSQL...")
    existing_df = pd.read_sql("SELECT * FROM processed_features_l2_l6", engine)
    macro_df = pd.read_sql("SELECT * FROM raw_macro_context", engine)
    
    # Ensure pure midnight dates for a perfect SQL-style merge
    existing_df['date'] = pd.to_datetime(existing_df['date']).dt.normalize()
    macro_df['date'] = pd.to_datetime(macro_df['date']).dt.normalize()
    
    print("Merging Market Context (Layer 7)...")
    final_df = pd.merge(existing_df, macro_df, on='date', how='left')
    
    print("Patching holiday gaps and missing early data...")
    final_df.ffill(inplace=True)
    final_df.bfill(inplace=True)
    
    # Drop any remaining unfixable errors
    final_df.dropna(inplace=True)
    
    table_name = 'master_features_l2_l7'
    print(f"Saving final master table to PostgreSQL: '{table_name}'...")
    final_df.to_sql(table_name, engine, if_exists='replace', index=False)
    print(f"Success! {len(final_df)} master rows saved.")

if __name__ == "__main__":
    merge_with_database()