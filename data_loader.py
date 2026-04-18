"""
Data Loader Module - Fetches and caches Nifty 50 data from yfinance.

This module handles downloading intraday OHLCV data for Nifty 50 (^NSEI) from
yfinance and caching it locally as CSV to avoid repeated downloads.

Supports custom date ranges: specify an end_date and it will download 60 days
of data ending on that date. If no end_date is provided, uses current date.

Important: yfinance only provides 60 days of intraday data (interval <= 1 hour).
For longer history, users should use broker APIs (e.g., Zerodha Kite) and upload
CSV files directly to the app.
"""

import glob
import os
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))


def get_data_dir():
    """Return a writable data directory path for local and cloud deployment."""
    if os.environ.get('RENDER') or os.environ.get('FLASK_ENV') == 'production':
        data_dir = os.path.join('/tmp', 'data')
    else:
        data_dir = os.path.join(BASE_DIR, 'data')
    os.makedirs(data_dir, exist_ok=True)
    return data_dir


DATA_DIR = get_data_dir()


def ensure_data_directory():
    """Create the data directory if it doesn't exist."""
    os.makedirs(DATA_DIR, exist_ok=True)


def get_cache_path(interval="5m", period="60d", end_date=None):
    """
    Generate the cache file path for the given period and interval.
    
    Parameters:
    -----------
    interval : str
        Candle interval (default: "5m")
    period : str
        Time period (default: "60d")
    end_date : str or None
        End date for custom range (format: 'YYYY-MM-DD').
        If provided, cache path includes this date to distinguish custom ranges.
    
    Returns:
    --------
    str
        Path to cache file
    """
    ensure_data_directory()
    if end_date:
        return os.path.join(DATA_DIR, f"nifty_{interval}_{period}_to_{end_date}.csv")
    return os.path.join(DATA_DIR, f"nifty_{interval}_{period}.csv")


def get_yfinance_cache_paths(interval="5m", period="60d"):
    """Return all matching yfinance cache file paths for the given interval and period."""
    ensure_data_directory()
    pattern = os.path.join(DATA_DIR, f"nifty_{interval}_{period}*.csv")
    return sorted(glob.glob(pattern), key=os.path.getmtime, reverse=True)


def get_latest_yfinance_cache_path(interval="5m", period="60d"):
    """Return the newest yfinance cache file path, including custom date files."""
    paths = get_yfinance_cache_paths(interval, period)
    return paths[0] if paths else None


def get_custom_csv_paths():
    """Return all CSV files in the data directory sorted by newest modification time."""
    ensure_data_directory()
    pattern = os.path.join(DATA_DIR, '*.csv')
    return sorted(glob.glob(pattern), key=os.path.getmtime, reverse=True)


def validate_data_file(path):
    """Return True if the CSV has the required trading data columns."""
    try:
        df = pd.read_csv(path, nrows=2)
        if 'Datetime' not in df.columns:
            return False
        required = {'Open', 'High', 'Low', 'Close', 'Volume'}
        return required.issubset(set(df.columns))
    except Exception:
        return False


def get_latest_custom_data_path():
    """Return the newest valid CSV file from data/ that can be used by the backtester."""
    for path in get_custom_csv_paths():
        if validate_data_file(path):
            return path
    return None


def fetch_data(period="60d", interval="5m", force_refresh=False, end_date=None):
    """
    Fetch Nifty 50 data from yfinance with local CSV caching.
    
    Supports custom date ranges: specify end_date to download 60 days of data
    ending on that date. If end_date is None, uses current date.
    
    Critical note on yfinance MultiIndex:
    yfinance now returns a MultiIndex DataFrame where columns look like
    ('Close', '^NSEI') instead of just 'Close'. We flatten this immediately
    after download so the rest of the pipeline works with simple column names.
    
    Parameters:
    -----------
    period : str
        Time period for data (default: "60d"). For custom date ranges, this is ignored
        and period is inferred from end_date.
    interval : str
        Candle interval (default: "5m"). Supported: 1m, 2m, 5m, 15m, 30m, 60m
    force_refresh : bool
        If True, re-download data from yfinance. Otherwise, use cached CSV.
    end_date : str or None
        End date for custom date range (format: 'YYYY-MM-DD').
        If provided, downloads 60 days ending on this date.
        If None, downloads 60 days ending on current date.
    
    Returns:
    --------
    pd.DataFrame
        DataFrame with columns: Datetime, Open, High, Low, Close, Volume, date
        - Datetime is timezone-naive
        - date is a Python date object for daily grouping
        - Rows with Volume == 0 are dropped
        - NaN rows in OHLC are dropped
    
    Examples:
    ---------
    # Download last 60 days from today
    df = fetch_data()
    
    # Download 60 days ending on 2026-03-01
    df = fetch_data(end_date='2026-03-01')
    """
    cache_path = get_cache_path(interval, period, end_date)
    
    # Determine actual period to use for yfinance download
    if end_date:
        # Parse end_date and calculate start_date (60 days before)
        try:
            end_dt = pd.to_datetime(end_date)
            start_dt = end_dt - timedelta(days=60)
            actual_period = None  # We'll use start/end dates instead
        except Exception as e:
            print(f"Error parsing end_date '{end_date}': {e}")
            print("Falling back to default 60d from today")
            end_date = None
            actual_period = period
    else:
        actual_period = period
    
    if not force_refresh and os.path.exists(cache_path):
        print(f"Loading cached data from {cache_path}")
        df = pd.read_csv(cache_path, parse_dates=['Datetime'])
        df['date'] = pd.to_datetime(df['date']).dt.date
        print(f"Loaded {len(df)} candles ({df['date'].min()} to {df['date'].max()})")
        return df
    
    if end_date:
        print(f"Downloading fresh data: ^NSEI from {start_dt.date()} to {end_dt.date()}, interval={interval}")
    else:
        print(f"Downloading fresh data: ^NSEI, period={actual_period}, interval={interval}")
    
    # Download data from yfinance
    if end_date:
        # Use start and end date parameters
        raw = yf.download(
            "^NSEI",
            start=start_dt.date(),
            end=end_dt.date(),
            interval=interval,
            progress=False
        )
    else:
        # Use period parameter
        raw = yf.download(
            "^NSEI",
            period=actual_period,
            interval=interval,
            progress=False
        )
    
    # ── THE CRITICAL FIX ──────────────────────────────────────────────────────
    # yfinance returns MultiIndex columns like ('Close', '^NSEI').
    # We drop the second level (the ticker name) to get simple column names.
    if isinstance(raw.columns, pd.MultiIndex):
        print("MultiIndex detected — flattening columns...")
        raw.columns = raw.columns.droplevel(1)  # Drop the ticker level
    # ─────────────────────────────────────────────────────────────────────────
    
    # Reset index so Datetime becomes a regular column (not the index)
    raw = raw.reset_index()
    
    # Standardize the datetime column name — yfinance uses 'Datetime' for
    # intraday data but 'Date' for daily data. We normalize to 'Datetime'.
    if 'Date' in raw.columns and 'Datetime' not in raw.columns:
        raw = raw.rename(columns={'Date': 'Datetime'})
    
    # Strip timezone info — yfinance returns IST as UTC+5:30 which causes
    # comparison issues. We strip it since we only care about the time value.
    raw['Datetime'] = pd.to_datetime(raw['Datetime']).dt.tz_localize(None)
    
    # Add a plain date column for daily grouping (used by VWAP, OR, etc.)
    raw['date'] = raw['Datetime'].dt.date
    
    # Remove zero-volume candles — these are artifacts from pre/post market
    # data leaking in, not real trading candles
    raw = raw[raw['Volume'] > 0].copy()
    
    # Remove any rows where OHLC data is missing
    raw = raw.dropna(subset=['Open', 'High', 'Low', 'Close'])
    
    # Save to cache
    ensure_data_directory()
    raw.to_csv(cache_path, index=False)
    print(f"Data saved to {cache_path} — {len(raw)} candles, "
          f"{raw['date'].nunique()} trading days")
    
    return raw


def get_latest_tv_file():
    """
    Find the latest TradingView data file.
    
    Returns:
    --------
    str or None
        Path to the most recent TradingView CSV file, or None if not found
    """
    ensure_data_directory()
    
    # Look for TradingView data files (pattern: nifty_tv_*m_*.csv)
    tv_files = []
    try:
        for file in os.listdir(DATA_DIR):
            if file.startswith('nifty_tv_') and file.endswith('.csv'):
                file_path = os.path.join(DATA_DIR, file)
                # Get modification time
                mtime = os.path.getmtime(file_path)
                tv_files.append((mtime, file_path))
        
        if tv_files:
            # Sort by modification time (newest first)
            tv_files.sort(reverse=True)
            return tv_files[0][1]  # Return path of most recent file
    except Exception as e:
        print(f"Error finding TradingView file: {e}")
    
    return None


def get_data_status():
    """
    Check cached data status.
    
    Checks TradingView data first, then falls back to yfinance data.
    
    Returns:
    --------
    dict
        {
            'data_exists': bool,
            'date_range': (start_date, end_date) or None,
            'trading_days': int,
            'cache_path': str,
            'data_source': str ('tradingview' or 'yfinance')
        }
    """
    # Check for TradingView data first
    tv_file = get_latest_tv_file()
    if tv_file and os.path.exists(tv_file):
        try:
            df = pd.read_csv(tv_file, parse_dates=['Datetime'])
            df['date'] = pd.to_datetime(df['date']).dt.date
            
            trading_days = df['date'].nunique()
            date_range = (str(df['date'].min()), str(df['date'].max()))
            
            return {
                'data_exists': True,
                'date_range': date_range,
                'trading_days': trading_days,
                'cache_path': tv_file,
                'data_source': 'tradingview'
            }
        except Exception as e:
            print(f"Error reading TradingView file: {e}")
    
    # Fall back to yfinance data
    cache_path = get_latest_yfinance_cache_path()
    if cache_path is None or not os.path.exists(cache_path):
        # If no yfinance cache exists, try any valid CSV in data/
        cache_path = get_latest_custom_data_path()
        if cache_path is None:
            return {
                'data_exists': False,
                'date_range': None,
                'trading_days': 0,
                'cache_path': None,
                'data_source': None
            }

    try:
        df = pd.read_csv(cache_path)
        df['Datetime'] = pd.to_datetime(df['Datetime'])
        df['date'] = df['Datetime'].dt.date
        
        trading_days = df['date'].nunique()
        date_range = (str(df['date'].min()), str(df['date'].max()))
        
        source = 'yfinance' if cache_path == get_latest_yfinance_cache_path() else 'custom'
        return {
            'data_exists': True,
            'date_range': date_range,
            'trading_days': trading_days,
            'cache_path': cache_path,
            'data_source': source
        }
    except Exception as e:
        return {
            'data_exists': False,
            'date_range': None,
            'trading_days': 0,
            'cache_path': cache_path,
            'data_source': None,
            'error': str(e)
        }


def load_latest_data():
    """
    Load the latest available data (TradingView first, then yfinance).
    
    Returns:
    --------
    pd.DataFrame
        DataFrame with columns: Datetime, Open, High, Low, Close, Volume, date
    """
    # Try TradingView first
    tv_file = get_latest_tv_file()
    if tv_file and os.path.exists(tv_file):
        try:
            df = pd.read_csv(tv_file, parse_dates=['Datetime'])
            df['date'] = pd.to_datetime(df['date']).dt.date
            print(f"Loaded TradingView data from: {tv_file}")
            return df
        except Exception as e:
            print(f"Error loading TradingView data: {e}")
    
    # Fall back to yfinance
    cache_path = get_latest_yfinance_cache_path()
    if cache_path and os.path.exists(cache_path):
        try:
            df = pd.read_csv(cache_path, parse_dates=['Datetime'])
            df['date'] = pd.to_datetime(df['date']).dt.date
            print(f"Loaded yfinance data from: {cache_path}")
            return df
        except Exception as e:
            print(f"Error loading yfinance data: {e}")

    # Fall back to any valid CSV in data/
    cache_path = get_latest_custom_data_path()
    if cache_path and os.path.exists(cache_path):
        try:
            df = pd.read_csv(cache_path, parse_dates=['Datetime'])
            if 'date' in df.columns:
                df['date'] = pd.to_datetime(df['date']).dt.date
            else:
                df['date'] = pd.to_datetime(df['Datetime']).dt.date
            print(f"Loaded custom CSV data from: {cache_path}")
            return df
        except Exception as e:
            print(f"Error loading custom CSV data: {e}")
    
    # No data available
    raise ValueError("No data available. Please fetch data first.")


def fetch_data_from_tradingview(n_bars=500, interval_minutes=5, output_path=None):
    """
    Fetch Nifty 50 data from TradingView using tvdatafeed.
    
    This is an alternative to yfinance for better data quality and extended history.
    TradingView data can go back much further than yfinance's 60-day limit.
    
    Parameters:
    -----------
    n_bars : int
        Number of bars to fetch (default: 500 ≈ 2-3 days for 5m data)
    interval_minutes : int
        Candle interval in minutes (default: 5)
    output_path : str
        Path to save CSV file (default: data/nifty_tv_5m_latest.csv)
    
    Returns:
    --------
    pd.DataFrame
        DataFrame with columns: Datetime, Open, High, Low, Close, Volume, date
    
    Requires:
    ---------
    - tvdatafeed library installed: pip install git+https://github.com/rongardF/tvdatafeed.git
    - Optional: TV_USERNAME and TV_PASSWORD environment variables for full access
    """
    try:
        from tv_api import fetch_and_save_tv_data
        
        if output_path is None:
            output_path = os.path.join(DATA_DIR, f"nifty_tv_{interval_minutes}m_{n_bars}bars.csv")
        
        # Fetch from TradingView and save
        csv_path = fetch_and_save_tv_data(
            n_bars=n_bars,
            output_path=output_path,
            interval_minutes=interval_minutes
        )
        
        # Load and return
        df = pd.read_csv(csv_path, parse_dates=['Datetime'])
        df['date'] = pd.to_datetime(df['date']).dt.date
        df['Volume'] = df['Volume'].astype(int)
        
        return df
        
    except ImportError:
        print("ERROR: tvdatafeed not installed!")
        print("Install with: pip install git+https://github.com/rongardF/tvdatafeed.git")
        raise
    except Exception as e:
        print(f"Error fetching from TradingView: {str(e)}")
        raise


if __name__ == "__main__":
    # Standalone testing
    print("=" * 60)
    print("Data Loader - Standalone Test")
    print("=" * 60)
    
    # Fetch data (5-minute interval - yfinance compatible)
    df = fetch_data(period="7d", interval="5m", force_refresh=False)
    print(f"\nDataFrame shape: {df.shape}")
    print(f"Columns: {df.columns.tolist()}")
    print(f"\nFirst 5 rows:")
    print(df.head())
    print(f"\nData status:")
    print(get_data_status())
