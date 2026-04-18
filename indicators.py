"""
Indicators Module - Technical indicators for the VWAP + EMA scalp strategy.

Computes VWAP, EMA (9 and 21), and Opening Range for each trading day.
All functions take a DataFrame and return it with new columns added.
"""

import pandas as pd
import numpy as np


def add_ema(df, span):
    """
    Add Exponential Moving Average (EMA) to DataFrame.
    
    Parameters:
    -----------
    df : pd.DataFrame
        DataFrame with OHLCV data. Must have 'Close' column.
    span : int
        EMA period (e.g., 9, 21)
    
    Returns:
    --------
    pd.DataFrame
        DataFrame with new column f"ema{span}" added.
        EMA is calculated using pandas.ewm with adjust=False (recursive formula).
    """
    df = df.copy()
    column_name = f"ema{span}"
    df[column_name] = df['Close'].ewm(span=span, adjust=False).mean()
    return df


def add_vwap(df):
    """
    Compute a price-action VWAP proxy since yfinance index volume is unreliable.
    
    Instead of true VWAP (which needs accurate volume), we compute a cumulative
    typical price average that resets each day. This captures the same conceptual
    meaning — the 'fair value' price around which the day is anchored — without
    depending on volume data.
    
    This is sometimes called the 'unweighted VWAP' or 'pivot VWAP' in retail
    trading circles. Institutions use true VWAP, but for strategy testing purposes
    this is a much more honest proxy given our data constraints.
    """
    df['typical_price'] = (df['High'] + df['Low'] + df['Close']) / 3
    
    # Cumulative average of typical price, resetting each day
    # This is honest about what we're computing — not true VWAP
    df['vwap'] = df.groupby('date')['typical_price'].expanding().mean().reset_index(level=0, drop=True)
    
    return df


def add_opening_range(df):
    """
    Add Opening Range (OR) high and low to DataFrame.
    
    The opening range is the High and Low of the first 15 minutes of each
    trading day (first 5 candles on a 3-minute chart, i.e., 9:15–9:30 IST).
    
    Parameters:
    -----------
    df : pd.DataFrame
        DataFrame with OHLCV data and 'date' column for daily grouping.
        Must have columns: 'High', 'Low', 'date', 'Datetime'
    
    Returns:
    --------
    pd.DataFrame
        DataFrame with 'or_high' and 'or_low' columns added.
        OR values are the same for all candles within a single trading day.
    
    Notes:
    ------
    - The strategy does NOT trade during the opening range window
    - OR values are used as context/reference for the strategy
    - The opening range is determined by the first 5 candles only
    """
    df = df.copy()
    
    # Extract hour and minute from Datetime
    df['hour'] = df['Datetime'].dt.hour
    df['minute'] = df['Datetime'].dt.minute
    
    # Identify opening range candles (first 5 candles of each day)
    # For IST (UTC+5:30), trading starts at 9:15 AM
    # First 5 candles of 3m = 9:15, 9:18, 9:21, 9:24, 9:27
    # So OR ends before 9:30
    df['is_opening_range'] = (df['hour'] == 9) & (df['minute'] <= 27)
    
    # Get OR high and low for each day
    or_data = df[df['is_opening_range']].groupby('date').agg({
        'High': 'max',
        'Low': 'min'
    }).reset_index()
    or_data.columns = ['date', 'or_high', 'or_low']
    
    # Merge OR values back to main dataframe
    # All candles in a day get the same OR high/low
    df = df.merge(or_data, on='date', how='left')
    
    # If no opening range candles exist for a day, use NaN or previous day's value
    # Forward fill to handle gaps
    df['or_high'] = df.groupby('date')['or_high'].transform(lambda x: x.iloc[0] if len(x) > 0 else np.nan)
    df['or_low'] = df.groupby('date')['or_low'].transform(lambda x: x.iloc[0] if len(x) > 0 else np.nan)
    
    # Drop helper columns
    df = df.drop(columns=['hour', 'minute', 'is_opening_range'])
    
    return df


def prepare_data(df):
    """
    Prepare DataFrame with all required indicators for backtesting.
    
    This is the main pipeline: takes raw OHLCV data and computes all indicators.
    
    Parameters:
    -----------
    df : pd.DataFrame
        Raw OHLCV DataFrame from data_loader.fetch_data()
    
    Returns:
    --------
    pd.DataFrame
        DataFrame with all columns: OHLCV + date + EMA9 + EMA21 + VWAP + OR_high/low
    """
    df = df.copy()
    
    # Add indicators
    df = add_ema(df, span=9)
    df = add_ema(df, span=21)
    df = add_ema(df, 50) 
    df = add_vwap(df)
    df = add_opening_range(df)
    
    return df


if __name__ == "__main__":
    # Standalone testing
    from data_loader import fetch_data
    
    print("=" * 60)
    print("Indicators - Standalone Test")
    print("=" * 60)
    
    # Fetch sample data
    df = fetch_data(period="60d", interval="5m", force_refresh=False)
    print(f"\nRaw data shape: {df.shape}")
    print(f"Columns: {df.columns.tolist()}")
    
    # Prepare with indicators
    df_prepared = prepare_data(df)
    print(f"\nPrepared data shape: {df_prepared.shape}")
    print(f"Columns: {df_prepared.columns.tolist()}")
    
    # Show sample
    print(f"\nSample rows with indicators:")
    print(df_prepared[['Datetime', 'Close', 'ema9', 'ema21', 'vwap', 'or_high', 'or_low']].head(20))
    
    # Check for NaN values
    print(f"\nNaN values per column:")
    print(df_prepared.isnull().sum())
