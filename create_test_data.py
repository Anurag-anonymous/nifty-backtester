#!/usr/bin/env python
"""Create sample test data for backtesting"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta

print("Creating sample Nifty 50 test data...")

# Create date range (past 7 trading days)
dates = pd.date_range(end=datetime.now(), periods=40, freq='1D')  # 40 trading days
dates = dates[dates.weekday < 5]  # Remove weekends

data = []
base_price = 21500

for day_offset, day in enumerate(dates):
    # Create 5-minute candles (78 per day: 9:15 AM to 3:30 PM IST = 6h 15min = 375 min / 5)
    
    for candle in range(78):
        time = day.replace(hour=9, minute=15) + timedelta(minutes=candle * 5)
        
        # Skip opening range (first 3 candles: 9:15-9:30)
        if candle < 3:
            continue
        
        #Generate realistic OHLC
        open_price = base_price + np.random.randn() * 10
        high_price = open_price + abs(np.random.randn() * 15)
        low_price = open_price - abs(np.random.randn() * 15)
        close_price = np.random.uniform(low_price, high_price)
        volume = int(np.random.uniform(100000, 500000))
        
        data.append({
            'Datetime': time,
            'Open': round(open_price, 2),
            'High': round(max(open_price, high_price), 2),
            'Low': round(min(open_price, low_price), 2),
            'Close': round(close_price, 2),
            'Volume': volume
        })
    
    # Trend adjustment for next day
    base_price += np.random.randn() * 50

df = pd.DataFrame(data)
df['date'] = df['Datetime'].dt.date

print(f"Created {len(df)} candles across {df['date'].nunique()} trading days")
print(f"Date range: {df['Datetime'].min()} to {df['Datetime'].max()}")

# Save to cache
import os
os.makedirs('data', exist_ok=True)
df.to_csv('data/nifty_5m_60d.csv', index=False)
print(f"Saved to data/nifty_5m_60d.csv")

# Display sample
print(f"\nSample data:")
print(df.head(10))
