"""
TradingView Data Integration - Fetch 5-minute Nifty 50 data

This module fetches historical 5-minute OHLCV data from TradingView
and converts it to the format needed for backtesting.

Uses tvdatafeed library: https://github.com/rongardF/tvdatafeed
"""

import pandas as pd
from datetime import datetime, timedelta
import os
from pathlib import Path

try:
    from tvDatafeed import TvDatafeed, Interval
    TVDATAFEED_AVAILABLE = True
except ImportError:
    TVDATAFEED_AVAILABLE = False


# ============================================================================
# CONFIGURATION - TRADINGVIEW CREDENTIALS
# ============================================================================

# TradingView login credentials (optional for limited free access)
TV_USERNAME = os.getenv("TV_USERNAME", "")  # Leave empty for no-login mode (limited data)
TV_PASSWORD = os.getenv("TV_PASSWORD", "")

# For Nifty 50
TV_EXCHANGE = "NSE"
TV_NIFTY_SYMBOL = "NIFTY"  # Trading symbol for Nifty 50 index

# Default output path for fetched data
DEFAULT_OUTPUT_PATH = "data/nifty_tv_5m_latest.csv"


# ============================================================================
# TRADINGVIEW API FUNCTIONS
# ============================================================================

def get_tv_connection():
    """
    Get TradingView connection.
    
    Returns:
    --------
    TvDatafeed
        TradingView data feed object
    """
    if not TVDATAFEED_AVAILABLE:
        raise ImportError("tvdatafeed library is not available")
    
    if TV_USERNAME and TV_PASSWORD:
        print("📡 Connecting to TradingView with login credentials...")
        tv = TvDatafeed(username=TV_USERNAME, password=TV_PASSWORD)
        return tv
    else:
        print("📡 Connecting to TradingView (no-login mode - limited data access)...")
        tv = TvDatafeed()
        return tv


def fetch_nifty_data_from_tv(start_date=None, end_date=None, n_bars=500, interval_minutes=5):
    """
    Fetch 5-minute Nifty 50 data from TradingView.
    
    Parameters:
    -----------
    start_date : str (YYYY-MM-DD) - OPTIONAL
        Start date for data fetch (not used with n_bars approach)
    end_date : str (YYYY-MM-DD) - OPTIONAL
        End date for data fetch (not used with n_bars approach)
    n_bars : int
        Number of bars to fetch (default: 500 = ~2-3 days of 5m data)
        Maximum: 5000 bars
    interval_minutes : int
        Candle interval in minutes (default: 5)
        Supported: 1, 3, 5, 15, 30, 45, 60, 120, 180, 240, 1D, 1W, 1M
    
    Returns:
    --------
    pd.DataFrame
        DataFrame with columns: Datetime, Open, High, Low, Close, Volume, date
    
    Raises:
    -------
    ValueError
        If fetch fails or data format is unexpected
    """
    
    if not TVDATAFEED_AVAILABLE:
        raise ValueError("TradingView data fetching is only available when running locally. "
                         "On cloud: use the CSV upload feature or click Refresh Data to use yfinance.")
    
    # Map interval minutes to TvDatafeed Interval enum
    interval_map = {
        1: Interval.in_1_minute,
        3: Interval.in_3_minute,
        5: Interval.in_5_minute,
        15: Interval.in_15_minute,
        30: Interval.in_30_minute,
        45: Interval.in_45_minute,
        60: Interval.in_1_hour,
        120: Interval.in_2_hour,
        180: Interval.in_3_hour,
        240: Interval.in_4_hour,
    }
    
    if interval_minutes not in interval_map:
        raise ValueError(f"Unsupported interval: {interval_minutes}. Supported: {list(interval_map.keys())}")
    
    tv_interval = interval_map[interval_minutes]
    
    print(f"Fetching Nifty 50 data from TradingView...")
    print(f"  Symbol: {TV_NIFTY_SYMBOL}")
    print(f"  Exchange: {TV_EXCHANGE}")
    print(f"  Interval: {interval_minutes} minutes")
    print(f"  Bars to fetch: {n_bars}")
    
    if start_date or end_date:
        print(f"  Date range: {start_date or 'N/A'} to {end_date or 'N/A'}")
    
    try:
        tv = get_tv_connection()
        
        print(f"\n  Making API request to TradingView...")
        
        # Fetch historical data
        df = tv.get_hist(
            symbol=TV_NIFTY_SYMBOL,
            exchange=TV_EXCHANGE,
            interval=tv_interval,
            n_bars=min(n_bars, 5000)  # Cap at 5000 bars max
        )
        
        print(f"  ✓ Received response from TradingView")
        
        # Normalize the response
        df = normalize_tv_response(df)
        
        print(f"  ✓ Fetched {len(df)} candles")
        if len(df) > 0:
            print(f"  ✓ Date range: {df['date'].min()} to {df['date'].max()}")
        
        return df
        
    except Exception as e:
        raise ValueError(f"Error fetching TradingView data: {str(e)}")


def normalize_tv_response(df):
    """
    Convert TradingView response to standard backtester format.
    
    TradingView returns:
    - Index: datetime
    - Columns: open, high, low, close, volume
    
    Convert to:
    - Columns: Datetime, Open, High, Low, Close, Volume, date
    
    Parameters:
    -----------
    df : pd.DataFrame
        Raw TradingView response
    
    Returns:
    --------
    pd.DataFrame
        Normalized OHLCV data
    """
    
    try:
        if df.empty:
            print("Warning: No candles received from TradingView")
            return pd.DataFrame(columns=['Datetime', 'Open', 'High', 'Low', 'Close', 'Volume', 'date'])
        
        # Rename columns to match backtester format
        df = df.copy()
        df = df.reset_index()  # Convert index to column
        
        # Standardize column names (case-insensitive mapping)
        column_mapping = {
            'time': 'Datetime',
            'datetime': 'Datetime',
            'open': 'Open',
            'high': 'High',
            'low': 'Low',
            'close': 'Close',
            'volume': 'Volume'
        }
        
        # Rename columns
        df.rename(columns={k: v for k, v in column_mapping.items() if k in df.columns}, inplace=True)
        
        # Ensure Datetime column exists and is datetime type
        if 'Datetime' not in df.columns:
            if len(df.columns) > 0:
                # Assume first column is datetime
                df.rename(columns={df.columns[0]: 'Datetime'}, inplace=True)
            else:
                raise ValueError("No datetime column found in TradingView response")
        
        df['Datetime'] = pd.to_datetime(df['Datetime'])
        
        # Create 'date' column (date only, without time)
        df['date'] = df['Datetime'].dt.date
        
        # Ensure numeric columns
        for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # Select and order columns
        df = df[['Datetime', 'Open', 'High', 'Low', 'Close', 'Volume', 'date']]
        
        # Sort by datetime
        df = df.sort_values('Datetime').reset_index(drop=True)
        
        return df
        
    except Exception as e:
        raise ValueError(f"Error normalizing TradingView response: {str(e)}")


def fetch_and_save_tv_data(n_bars=500, output_path=None, interval_minutes=5):
    """
    Fetch Nifty 50 data from TradingView and save to CSV.
    
    Parameters:
    -----------
    n_bars : int
        Number of bars to fetch (default: 500)
    output_path : str
        Path to save CSV file (default: data/nifty_tv_5m_latest.csv)
    interval_minutes : int
        Candle interval in minutes (default: 5)
    
    Returns:
    --------
    str
        Path to saved CSV file
    """
    
    if output_path is None:
        output_path = DEFAULT_OUTPUT_PATH
    
    print("\n" + "=" * 70)
    print("FETCHING NIFTY 50 DATA FROM TRADINGVIEW")
    print("=" * 70)
    
    try:
        # Fetch data
        df = fetch_nifty_data_from_tv(n_bars=n_bars, interval_minutes=interval_minutes)
        
        # Create output directory if it doesn't exist
        output_dir = os.path.dirname(output_path)
        if output_dir:
            Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        # Save to CSV
        df.to_csv(output_path, index=False)
        
        print(f"\n✅ Data saved to: {output_path}")
        print(f"   Records: {len(df)}")
        print(f"   File size: {os.path.getsize(output_path) / 1024:.1f} KB")
        
        return output_path
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        raise


def search_symbol(search_text, exchange="NSE"):
    """
    Search for trading symbols on TradingView.
    
    Parameters:
    -----------
    search_text : str
        Symbol to search for (e.g., 'NIFTY', 'BANK', 'INFY')
    exchange : str
        Exchange to search in (default: 'NSE')
    
    Returns:
    --------
    list
        List of matching symbols
    """
    try:
        tv = get_tv_connection()
        symbols = tv.search_symbol(search_text, exchange)
        return symbols
    except Exception as e:
        print(f"Error searching symbols: {str(e)}")
        return []


# ============================================================================
# CLI - Direct script execution
# ============================================================================

if __name__ == "__main__":
    try:
        # Fetch last 500 bars (approximately 2-3 days of 5-minute data)
        csv_path = fetch_and_save_tv_data(
            n_bars=500,
            output_path="data/nifty_tv_5m_latest.csv",
            interval_minutes=5
        )
        
        print("\n" + "=" * 70)
        print("✅ SUCCESS - Data ready for backtesting!")
        print("=" * 70)
        print(f"\nNext steps:")
        print(f"1. Load data in backtester:")
        print(f"   from data_loader import load_csv_upload")
        print(f"   df = load_csv_upload('{csv_path}')")
        print(f"\n2. Or use in web dashboard:")
        print(f"   Upload the CSV file through the UI")
        
    except Exception as e:
        print(f"\n❌ FAILED: {str(e)}")
        exit(1)
