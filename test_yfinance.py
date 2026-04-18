#!/usr/bin/env python
"""Quick test to see what yfinance returns"""

import yfinance as yf
import pandas as pd

print("Testing yfinance data structure...")
print("=" * 60)

# Try downloading a small sample
df = yf.download("^NSEI", period="1d", interval="5m", progress=False)

print(f"Type: {type(df)}")
print(f"Shape: {df.shape}")
print(f"Columns: {df.columns}")
print(f"Columns type: {type(df.columns)}")
print(f"\nFirst few rows:")
print(df.head())
print(f"\nData types:")
print(df.dtypes)

# Check if it has MultiIndex
if isinstance(df.columns, pd.MultiIndex):
    print("\n⚠️ MultiIndex detected!")
    print(f"Column levels: {df.columns.nlevels}")
    print(f"Columns: {df.columns.tolist()}")
    df_clean = df.copy()
    df_clean.columns = df_clean.columns.droplevel(1)
    print(f"After dropping level: {df_clean.columns}")
