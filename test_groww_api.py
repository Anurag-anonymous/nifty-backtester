#!/usr/bin/env python3
"""
Groww API Test and Integration Script

This script tests the Groww API integration and provides examples
of how to use it with your Nifty 50 backtester.
"""

import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(__file__))

from groww_api import (
    fetch_nifty_data_from_groww,
    get_date_range,
    GROWW_API_KEY,
    GROWW_NIFTY_SYMBOL,
    GROWW_EXCHANGE,
    GROWW_SEGMENT
)


def check_api_key():
    """Check if API key is set."""
    print("\n" + "=" * 70)
    print("1️⃣  CHECK API KEY")
    print("=" * 70)
    
    if GROWW_API_KEY:
        print(f"✅ API Key Found!")
        print(f"   Key: {GROWW_API_KEY[:20]}...{GROWW_API_KEY[-10:]}")
        return True
    else:
        print("❌ API Key Not Found!")
        print("\n   To set your API key, run one of:")
        print("\n   PowerShell (Windows):")
        print("     $env:GROWW_API_KEY = 'your_api_key_here'")
        print("\n   Command Prompt (Windows):")
        print("     setx GROWW_API_KEY your_api_key_here")
        print("\n   Bash (Linux/Mac):")
        print("     export GROWW_API_KEY='your_api_key_here'")
        print("\n   Get your key from: https://groww.in/trade-api")
        return False


def check_settings():
    """Display current settings."""
    print("\n" + "=" * 70)
    print("2️⃣  CURRENT SETTINGS")
    print("=" * 70)
    
    print(f"   Symbol: {GROWW_NIFTY_SYMBOL}")
    print(f"   Exchange: {GROWW_EXCHANGE}")
    print(f"   Segment: {GROWW_SEGMENT}")
    print(f"   Interval: 5 minutes")
    print(f"\n   ⚠️  Limitation: 5-min data available for last 15 days only")
    print(f"   ⚠️  For longer history: Use daily data (3+ years available)")


def show_date_range():
    """Show date range for last 15 days."""
    print("\n" + "=" * 70)
    print("3️⃣  AVAILABLE DATE RANGE")
    print("=" * 70)
    
    start_date, end_date = get_date_range(15)
    print(f"\n   Last 15 days (max available):")
    print(f"   Start: {start_date}")
    print(f"   End:   {end_date}")


def show_usage_examples():
    """Show usage examples."""
    print("\n" + "=" * 70)
    print("4️⃣  USAGE EXAMPLES")
    print("=" * 70)
    
    print("\n   Example 1: Direct fetch in Python")
    print("   " + "-" * 66)
    print("""
   from groww_api import fetch_nifty_data_from_groww
   
   df = fetch_nifty_data_from_groww(
       start_date='2026-03-15',
       end_date='2026-04-02',
       interval_minutes=5
   )
   print(df.head())
   print(f"Total candles: {len(df)}")
    """)
    
    print("\n   Example 2: Save to CSV")
    print("   " + "-" * 66)
    print("""
   from groww_api import fetch_and_save_groww_data
   
   csv_path = fetch_and_save_groww_data(
       days_back=15,
       output_path="data/nifty_groww_latest.csv"
   )
   print(f"Saved to: {csv_path}")
    """)
    
    print("\n   Example 3: Use with backtester")
    print("   " + "-" * 66)
    print("""
   from groww_api import fetch_and_save_groww_data
   from data_loader import load_csv_upload
   from indicators import prepare_data
   from backtest import run_backtest
   
   # 1. Fetch data from Groww
   csv_path = fetch_and_save_groww_data(days_back=15)
   
   # 2. Load into backtester format
   df = load_csv_upload(csv_path)
   
   # 3. Prepare indicators
   df_prepared = prepare_data(df)
   
   # 4. Run backtest
   trades_df, daily_summary = run_backtest(df_prepared, **params)
    """)


def show_next_steps():
    """Show next steps."""
    print("\n" + "=" * 70)
    print("5️⃣  NEXT STEPS")
    print("=" * 70)
    
    print("\n   Step 1: Set your API key (see above)")
    print("\n   Step 2: Run this script to verify connection")
    print("           (It will fetch actual data if key is set)")
    print("\n   Step 3: Use groww_api functions in your code")
    print("\n   Step 4: Save data as CSV for training")
    print("\n   Step 5: Load into backtester (data_loader.py)")
    print("\n   Step 6: Run backtests with real Groww data")


def test_connection():
    """Test actual API connection (if key is available)."""
    if not GROWW_API_KEY:
        return
    
    print("\n" + "=" * 70)
    print("6️⃣  TESTING API CONNECTION")
    print("=" * 70)
    
    print("\n   Fetching sample data from Groww API...")
    print("   (This may take 10-30 seconds)")
    
    try:
        start_date, end_date = get_date_range(3)  # Try last 3 days
        
        df = fetch_nifty_data_from_groww(
            start_date=start_date,
            end_date=end_date,
            interval_minutes=5
        )
        
        print(f"\n   ✅ Connection successful!")
        print(f"\n   📊 Sample Data:")
        print(f"      Total candles: {len(df)}")
        print(f"      Trading days: {df['date'].nunique()}")
        print(f"      Date range: {df['date'].min()} to {df['date'].max()}")
        print(f"      Price: ₹{df['Close'].min():.2f} - ₹{df['Close'].max():.2f}")
        print(f"      Volume: {df['Volume'].sum():,} shares")
        
        # Show sample candles
        print(f"\n   📈 First 5 candles:")
        print(f"      {df[['Datetime', 'Open', 'Close', 'Volume']].head().to_string()}")
        
        return True
        
    except ValueError as e:
        print(f"\n   ❌ Connection failed: {e}")
        return False
    except Exception as e:
        print(f"\n   ❌ Error: {e}")
        return False


def main():
    """Run all checks and tests."""
    print("\n")
    print("╔" + "=" * 68 + "╗")
    print("║" + " " * 68 + "║")
    print("║" + "  Groww API Integration Test & Setup Guide".center(68) + "║")
    print("║" + "  Nifty 50 5-Minute Data Fetcher".center(68) + "║")
    print("║" + " " * 68 + "║")
    print("╚" + "=" * 68 + "╝")
    
    # Run checks
    has_key = check_api_key()
    check_settings()
    show_date_range()
    show_usage_examples()
    
    # Test API if key exists
    if has_key:
        test_connection()
    
    show_next_steps()
    
    print("\n" + "=" * 70)
    print("📚 Documentation: GROWW_API_SETUP.md")
    print("📖 API Docs: https://groww.in/trade-api/docs/curl/historical-data")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
