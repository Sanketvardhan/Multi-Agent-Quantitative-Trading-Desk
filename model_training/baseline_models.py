import pandas as pd
import numpy as np
from sqlalchemy import create_engine
import os
from dotenv import load_dotenv

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error

# Load environment variables
load_dotenv()
DB_PASSWORD = os.getenv('DB_PASSWORD', 'root')
engine = create_engine(f'postgresql://postgres:{DB_PASSWORD}@localhost:5432/nifty_lstm_db')

def run_baseline_pipeline():
    print("1. Loading Model-Ready Data from PostgreSQL...")
    df = pd.read_sql("SELECT * FROM model_ready_data", engine)
    df['date'] = pd.to_datetime(df['date'])
    
    # Drop any lingering NaNs just to be safe
    df.dropna(inplace=True)
    
    print("2. Performing Chronological Split...")
    # Define our cutoffs based on your Phase 2 plan
    # Train: 2015 to end of 2022
    # Val: 2023
    # Test: 2024 to Present
    train_df = df[df['date'].dt.year <= 2022].copy()
    val_df = df[df['date'].dt.year == 2023].copy()
    test_df = df[df['date'].dt.year >= 2024].copy()
    
    print(f"   Train rows: {len(train_df)} | Val rows: {len(val_df)} | Test rows: {len(test_df)}")

    # Separate Features (X) and Target (y)
    # We must drop 'date' and 'Ticker' because models can't read strings/timestamps directly
    drop_cols = ['date', 'Ticker', 'target_return']
    
    X_train = train_df.drop(columns=drop_cols)
    y_train = train_df['target_return']
    
    X_val = val_df.drop(columns=drop_cols)
    y_val = val_df['target_return']
    
    X_test = test_df.drop(columns=drop_cols)
    y_test = test_df['target_return']
    
    print("3. Scaling Features (Preventing Data Leakage)...")
    scaler = StandardScaler()
    
    # CRITICAL: We FIT only on the training data to learn the historical distribution
    X_train_scaled = scaler.fit_transform(X_train)
    
    # We TRANSFORM the val and test data blindly based on the training rules
    X_val_scaled = scaler.transform(X_val)
    X_test_scaled = scaler.transform(X_test)
    
    print("4. Training Random Forest Baseline (This may take a minute)...")
    # We use 100 trees, with a max depth of 10 to prevent overfitting to noise
    rf_model = RandomForestRegressor(n_estimators=100, max_depth=10, random_state=42, n_jobs=-1)
    rf_model.fit(X_train_scaled, y_train)
    
    print("5. Evaluating Model Performance...")
    
    def evaluate(model, X, y_true, dataset_name):
        y_pred = model.predict(X)
        
        # Standard regression metrics
        mae = mean_absolute_error(y_true, y_pred)
        rmse = np.sqrt(mean_squared_error(y_true, y_pred))
        
        # Directional Accuracy: Did we correctly guess if it would go UP or DOWN?
        # If true and pred are both positive, or both negative, multiplying them gives a positive number.
        correct_direction = ((y_true * y_pred) > 0).mean() * 100
        
        print(f"\n--- {dataset_name} Metrics ---")
        print(f"MAE: {mae:.5f} (Average error in percentage return)")
        print(f"RMSE: {rmse:.5f}")
        print(f"Directional Accuracy: {correct_direction:.2f}%")
        
    evaluate(rf_model, X_train_scaled, y_train, "Training")
    evaluate(rf_model, X_val_scaled, y_val, "Validation")
    evaluate(rf_model, X_test_scaled, y_test, "Testing")

if __name__ == "__main__":
    run_baseline_pipeline()