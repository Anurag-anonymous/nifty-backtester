"""
Groww API Integration - Fetch 5-minute Nifty 50 data

This module fetches historical 5-minute OHLCV data from Groww API
and converts it to the format needed for backtesting.

API Reference: https://groww.in/trade-api/docs/curl/historical-data
"""

import requests
import pandas as pd
from datetime import datetime, timedelta
import json
import os


# ============================================================================
# CONFIGURATION - GROWW API DETAILS
# ============================================================================

GROWW_API_ENDPOINT = "https://api.groww.in/v1/historical/candle/range"
GROWW_API_KEY = os.getenv("GROWW_API_KEY", "")  # Set via environment variable
GROWW_API_VERSION = "1.0"

# For Nifty 50
GROWW_EXCHANGE = "NSE"
GROWW_SEGMENT = "CASH"  # or "CASH" - change based on your needs
GROWW_NIFTY_SYMBOL = "NIFTY50"  # Trading symbol for Nifty 50

# API request headers
def get_groww_headers():
    """Get headers with authorization token."""
    return {
        "Accept": "application/json",
        "X-API-VERSION": GROWW_API_VERSION,
        "Authorization": f"Bearer {GROWW_API_KEY}" if GROWW_API_KEY else "",
    }


# ============================================================================
# GROWW API FUNCTIONS
# ============================================================================

def fetch_nifty_data_from_groww(start_date=None, end_date=None, interval_minutes=5):
    """
    Fetch 5-minute Nifty 50 data from Groww API.
    
    Parameters:
    -----------
    start_date : str (YYYY-MM-DD or YYYY-MM-DD HH:MM:SS)
        Start date/time for data fetch
    end_date : str (YYYY-MM-DD or YYYY-MM-DD HH:MM:SS)
        End date/time for data fetch
    interval_minutes : int
        Candle interval in minutes (default: 5)
    
    Returns:
    --------
    pd.DataFrame
        DataFrame with columns: Datetime, Open, High, Low, Close, Volume, date
    
    Raises:
    -------
    ValueError
        If API request fails, no API key set, or data format is unexpected
    """
    
    if not GROWW_API_KEY:
        raise ValueError(
            "Groww API key not found. Please set the GROWW_API_KEY environment variable.\n"
            "Usage: $env:GROWW_API_KEY='your_api_key' (PowerShell)\n"
            "       export GROWW_API_KEY='your_api_key' (Bash)"
        )
    
    # Ensure timestamps include time component (market operates 09:15-15:30)
    if start_date and len(start_date) == 10:  # YYYY-MM-DD format
        start_date = f"{start_date} 09:15:00"
    if end_date and len(end_date) == 10:
        end_date = f"{end_date} 15:30:00"
    
    print(f"Fetching Nifty 50 data from Groww API...")
    print(f"  Symbol: {GROWW_NIFTY_SYMBOL}")
    print(f"  Interval: {interval_minutes} minutes")
    print(f"  Date range: {start_date} to {end_date}")
    
    try:
        # Prepare request parameters
        params = {
            "exchange": GROWW_EXCHANGE,
            "segment": GROWW_SEGMENT,
            "trading_symbol": GROWW_NIFTY_SYMBOL,
            "start_time": start_date,
            "end_time": end_date,
            "interval_in_minutes": str(interval_minutes),
        }
        
        print(f"\n  Making API request...")
        
        # Make API request
        response = requests.get(
            GROWW_API_ENDPOINT,
            params=params,
            headers=get_groww_headers(),
            timeout=30
        )
        response.raise_for_status()
        
        # Parse response
        data = response.json()
        
        if data.get("status") != "SUCCESS":
            error_msg = data.get("payload", {}).get("message", "Unknown error")
            raise ValueError(f"Groww API error: {error_msg}")
        
        print(f"  ✓ Received response from Groww API")
        
        # Convert to DataFrame
        df = normalize_groww_response(data["payload"])
        
        print(f"  ✓ Fetched {len(df)} candles")
        print(f"  ✓ Date range: {df['date'].min()} to {df['date'].max()}")
        
        return df
        
    except requests.exceptions.ConnectionError as e:
        raise ValueError(f"Groww API connection failed: Check your internet connection. {str(e)}")
    except requests.exceptions.Timeout as e:
        raise ValueError(f"Groww API request timed out: {str(e)}")
    except requests.exceptions.HTTPError as e:
        raise ValueError(f"Groww API HTTP error: {response.status_code} - {str(e)}")
    except requests.exceptions.RequestException as e:
        raise ValueError(f"Groww API request failed: {str(e)}")
    except Exception as e:
        raise ValueError(f"Error fetching Groww data: {str(e)}")


def normalize_groww_response(payload):
    """
    Convert Groww API response to DataFrame.
    
    Response structure:
    {
        "candles": [
            [timestamp_epoch, open, high, low, close, volume],
            ...
        ],
        "start_time": "2025-01-01 15:30:00",
        "end_time": "2025-01-01 15:30:00",
        "interval_in_minutes": 5
    }
    
    Parameters:
    -----------
    payload : dict
        Payload from Groww API response
    
    Returns:
    --------
    pd.DataFrame
        Normalized OHLCV data with Datetime, Open, High, Low, Close, Volume, date
    
    Raises:
    -------
    ValueError
        If payload format is unexpected
    """
    
    try:
        # Extract candle data from response
        candles = payload.get("candles", [])
        if not candles:
            print("Warning: No candles received from API")
            return pd.DataFrame(columns=['Datetime', 'Open', 'High', 'Low', 'Close', 'Volume', 'date'])
        
        # Convert list of lists to list of dicts with standard column names
        rows = []
        for candle in candles:
            if len(candle) < 6:
                print(f"Warning: Skipping malformed candle: {candle}")
                continue
            
            try:
                # Groww format: [timestamp_epoch, open, high, low, close, volume]
                timestamp, open_price, high_price, low_price, close_price, volume = candle[:6]
                
                row = {
                    "Datetime": pd.to_datetime(int(timestamp), unit='s'),
                    "Open": float(open_price),
                    "High": float(high_price),
                    "Low": float(low_price),
                    "Close": float(close_price),
                    "Volume": int(volume)
                }
                rows.append(row)
            except (ValueError, TypeError) as e:
                print(f"Warning: Error parsing candle {candle}: {e}")
                continue
        
        if not rows:
            raise ValueError("No valid candles could be parsed from response")
        
        # Create DataFrame
        df = pd.DataFrame(rows)
        
        # Ensure timezone is naive (remove if present)
        if df['Datetime'].dt.tz is not None:
            df['Datetime'] = df['Datetime'].dt.tz_localize(None)
        
        # Add date column for grouping
        df['date'] = df['Datetime'].dt.date
        
        # Sort by datetime
        df = df.sort_values('Datetime').reset_index(drop=True)
        
        return df
        
    except Exception as e:
        raise ValueError(f"Error normalizing Groww response: {str(e)}")


def get_date_range(days_back=365):
    """
    Calculate date range for historical data fetch.
    
    Groww API limitations for 5-minute data:
    - Last 15 days available (max 15 days)
    - Data available for last 3 months with restrictions
    
    Parameters:
    -----------
    days_back : int
        Number of days to go back from today (max 15 for 5m data)
    
    Returns:
    --------
    tuple
        (start_date, end_date) in YYYY-MM-DD format
    """
    
    # For 5-minute data, Groww limits to last 15 days
    if days_back > 15:
        print(f"⚠️  Warning: Groww API limits 5-minute data to last 15 days")
        print(f"   Reducing from {days_back} days to 15 days")
        days_back = 15
    
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=days_back)
    
    return str(start_date), str(end_date)


def fetch_and_save_groww_data(days_back=15, output_path=None):
    """
    Fetch data from Groww API and save as CSV.
    
    Important: Groww API limits 5-minute Nifty 50 data to the last 15 days.
    
    Parameters:
    -----------
    days_back : int
        Number of days to fetch (max 15 for 5m data)
    output_path : str
        Path to save CSV file (default: data/nifty_groww_5m.csv)
    
    Returns:
    --------
    str
        Path to saved CSV file
    
    Raises:
    -------
    ValueError
        If API key not set or API request fails
    """
    
    if output_path is None:
        output_path = "data/nifty_groww_5m.csv"
    
    print("\n" + "=" * 70)
    print("Groww API - Nifty 50 5-Minute Data Fetch")
    print("=" * 70)
    
    try:
        # Get date range
        start_date, end_date = get_date_range(days_back)
        print(f"\n📊 Fetch Parameters:")
        print(f"   Symbol: {GROWW_NIFTY_SYMBOL}")
        print(f"   Exchange: {GROWW_EXCHANGE} | Segment: {GROWW_SEGMENT}")
        print(f"   Interval: 5 minutes")
        print(f"   Date range: {start_date} to {end_date}")
        print()
        
        # Fetch data
        df = fetch_nifty_data_from_groww(
            start_date=start_date,
            end_date=end_date,
            interval_minutes=5
        )
        
        # Validate data
        if len(df) == 0:
            raise ValueError("No data received from Groww API")
        
        print(f"\n📋 Data Summary:")
        print(f"   Total candles: {len(df)}")
        print(f"   Unique trading days: {df['date'].nunique()}")
        print(f"   Date range: {df['date'].min()} to {df['date'].max()}")
        print(f"   Columns: {list(df.columns)}")
        print(f"   Price range: ₹{df['Close'].min():.2f} - ₹{df['Close'].max():.2f}")
        print(f"   Volume: {df['Volume'].sum():,} shares")
        
        # Save to CSV
        os.makedirs(os.path.dirname(output_path) or 'data', exist_ok=True)
        df.to_csv(output_path, index=False)
        
        print(f"\n✅ Data saved to: {output_path}")
        print("=" * 70 + "\n")
        
        return output_path
        
    except ValueError as e:
        print(f"\n❌ Error: {str(e)}")
        print("=" * 70 + "\n")
        raise
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")
        print("=" * 70 + "\n")
        raise


if __name__ == "__main__":
    # Example usage
    print("Groww API Direct Usage Example:")
    print("=" * 70)
    print("\nBefore running, set your API key:")
    print("  PowerShell: $env:GROWW_API_KEY = 'your_api_key_here'")
    print("  Bash:       export GROWW_API_KEY='your_api_key_here'")
    print("\nThen run this script to fetch and save data.")
    print("=" * 70)
    
    try:
        # Fetch last 15 days of 5-minute data
        csv_path = fetch_and_save_groww_data(
            days_back=15,
            output_path="data/nifty_groww_5m_latest.csv"
        )
        print(f"\n✅ Success! Data saved to: {csv_path}")
        
    except ValueError as e:
        if "API key not found" in str(e):
            print("\n⚠️  API Key Error:")
            print("   1. Get your API key from: https://groww.in/trade-api")
            print("   2. Set it as environment variable GROWW_API_KEY")
        else:
            print(f"\n❌ Error: {e}")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
