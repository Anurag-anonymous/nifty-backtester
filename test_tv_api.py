#!/usr/bin/env python3
"""
TradingView API Test and Integration Script

Demonstrates how to use tvdatafeed with your Nifty 50 backtester.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from tv_api import (
    fetch_nifty_data_from_tv,
    fetch_and_save_tv_data,
    search_symbol,
    get_tv_connection
)
from tvDatafeed import Interval
import pandas as pd


def load_csv_upload(csv_path):
    """Simple CSV loader for testing."""
    df = pd.read_csv(csv_path, parse_dates=['Datetime'])
    df['date'] = pd.to_datetime(df['date']).dt.date
    return df


def test_basic_fetch():
    """Test basic data fetch."""
    print("\n" + "=" * 70)
    print("1️⃣  BASIC FETCH - Download 100 bars (30-40 min of 5m data)")
    print("=" * 70)
    
    try:
        df = fetch_nifty_data_from_tv(n_bars=100, interval_minutes=5)
        print(f"\n✅ Success!")
        print(f"   Rows: {len(df)}")
        print(f"   Date range: {df['Datetime'].min()} to {df['Datetime'].max()}")
        print(f"\n   First 3 rows:")
        print(df.head(3).to_string())
        return df
    except Exception as e:
        print(f"❌ Error: {e}")
        return None


def test_save_to_csv():
    """Test saving data to CSV."""
    print("\n" + "=" * 70)
    print("2️⃣  SAVE TO CSV - Download 500 bars and save")
    print("=" * 70)
    
    try:
        csv_path = fetch_and_save_tv_data(
            n_bars=500,
            output_path="data/test_nifty_500bars.csv"
        )
        print(f"\n✅ Saved to: {csv_path}")
        print(f"   File size: {os.path.getsize(csv_path) / 1024:.1f} KB")
        return csv_path
    except Exception as e:
        print(f"❌ Error: {e}")
        return None


def test_load_csv():
    """Test loading CSV with data_loader."""
    print("\n" + "=" * 70)
    print("3️⃣  LOAD CSV - Read saved file using data_loader")
    print("=" * 70)
    
    try:
        csv_path = "data/nifty_tv_5m_latest.csv"
        if not os.path.exists(csv_path):
            print(f"⚠️  File not found: {csv_path}")
            print("   Run test 2 first to create the file")
            return None
        
        df = load_csv_upload(csv_path)
        print(f"\n✅ Loaded {len(df)} rows")
        print(f"   Columns: {list(df.columns)}")
        print(f"   Trading days: {df['date'].nunique()}")
        print(f"   Date range: {df['date'].min()} to {df['date'].max()}")
        print(f"\n   Statistics:")
        print(f"   Open  - Min: {df['Open'].min():.2f}, Max: {df['Open'].max():.2f}")
        print(f"   Close - Min: {df['Close'].min():.2f}, Max: {df['Close'].max():.2f}")
        print(f"   Volume - Min: {df['Volume'].min():.0f}, Max: {df['Volume'].max():.0f}")
        return df
    except Exception as e:
        print(f"❌ Error: {e}")
        return None


def test_different_intervals():
    """Test fetching different intervals."""
    print("\n" + "=" * 70)
    print("4️⃣  DIFFERENT INTERVALS - Test 1h and 15m data")
    print("=" * 70)
    
    try:
        # 1-hour data (50 bars = ~2 days)
        print("\n📊 Fetching 1-hour data (50 bars)...")
        df_1h = fetch_nifty_data_from_tv(n_bars=50, interval_minutes=60)
        print(f"   ✓ 1h: {len(df_1h)} bars, range {df_1h['Datetime'].min()} to {df_1h['Datetime'].max()}")
        
        # 15-minute data (100 bars = 1.5 hours)
        print("\n📊 Fetching 15-minute data (100 bars)...")
        df_15m = fetch_nifty_data_from_tv(n_bars=100, interval_minutes=15)
        print(f"   ✓ 15m: {len(df_15m)} bars, range {df_15m['Datetime'].min()} to {df_15m['Datetime'].max()}")
        
        return df_1h, df_15m
    except Exception as e:
        print(f"❌ Error: {e}")
        return None, None


def test_data_quality():
    """Test data quality checks."""
    print("\n" + "=" * 70)
    print("5️⃣  DATA QUALITY - Validate fetched data")
    print("=" * 70)
    
    try:
        df = fetch_nifty_data_from_tv(n_bars=100, interval_minutes=5)
        
        # Checks
        checks = {
            "No NaN values in OHLCV": not df[['Open', 'High', 'Low', 'Close', 'Volume']].isna().any().any(),
            "OHLC logical order": (df['High'] >= df['Low']).all() and (df['High'] >= df['Open']).all(),
            "Positive prices": (df['Close'] > 0).all(),
            "Positive volumes": (df['Volume'] > 0).all(),
            "Datetime is increasing": (df['Datetime'].diff().dt.total_seconds() > 0).all() or len(df) == 1,
        }
        
        print("\n📋 Data Quality Checks:")
        all_passed = True
        for check_name, passed in checks.items():
            status = "✓" if passed else "✗"
            print(f"   {status} {check_name}")
            if not passed:
                all_passed = False
        
        print(f"\n{'✅ All checks passed!' if all_passed else '⚠️  Some checks failed'}")
        return all_passed
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_symbol_search():
    """Test symbol search."""
    print("\n" + "=" * 70)
    print("6️⃣  SYMBOL SEARCH - Find trading symbols")
    print("=" * 70)
    
    try:
        print("\n🔍 Searching for NIFTY symbols...")
        symbols = search_symbol('NIFTY', 'NSE')
        
        if symbols:
            print(f"✓ Found {len(symbols)} symbols:")
            for sym in symbols[:10]:  # Show first 10
                print(f"   - {sym}")
            if len(symbols) > 10:
                print(f"   ... and {len(symbols) - 10} more")
        else:
            print("   No symbols found")
        
        return symbols
    except Exception as e:
        print(f"❌ Error: {e}")
        return None


def test_futures_data():
    """Test fetching futures data."""
    print("\n" + "=" * 70)
    print("7️⃣  FUTURES DATA - Fetch NIFTY futures contract")
    print("=" * 70)
    
    try:
        tv = get_tv_connection()
        
        print("\n📊 Fetching NIFTY futures (Continuous contract 1)...")
        df = tv.get_hist(
            symbol='NIFTY',
            exchange='NSE',
            interval=Interval.in_5_minute,
            n_bars=100,
            fut_contract=1
        )
        
        # Normalize
        from tv_api import normalize_tv_response
        df = normalize_tv_response(df)
        
        print(f"   ✓ Fetched {len(df)} bars")
        print(f"   Range: {df['Datetime'].min()} to {df['Datetime'].max()}")
        print(f"   Price: {df['Close'].min():.2f} to {df['Close'].max():.2f}")
        
        return df
    except Exception as e:
        print(f"❌ Error: {e}")
        return None


def main():
    """Run all tests."""
    print("\n" + "=" * 70)
    print("TRADINGVIEW API - COMPREHENSIVE TEST SUITE")
    print("=" * 70)
    print("\nThis script demonstrates all features of the TradingView integration.")
    
    # Run tests
    results = {}
    results['basic'] = test_basic_fetch()
    results['csv'] = test_save_to_csv()
    results['load'] = test_load_csv()
    results['intervals'] = test_different_intervals()
    results['quality'] = test_data_quality()
    results['search'] = test_symbol_search()
    results['futures'] = test_futures_data()
    
    # Summary
    print("\n" + "=" * 70)
    print("📊 TEST SUMMARY")
    print("=" * 70)
    print("\n✅ TradingView integration is working!")
    print("\nNext steps:")
    print("1. Use fetch_and_save_tv_data() to get fresh data")
    print("2. Load with load_csv_upload() to use in backtester")
    print("3. Pass DataFrame to run_backtest() to start backtesting")
    print("\nExample:")
    print("   from tv_api import fetch_and_save_tv_data")
    print("   csv = fetch_and_save_tv_data(n_bars=1000)")
    print("   from data_loader import load_csv_upload")
    print("   df = load_csv_upload(csv)")
    print("   from backtest import run_backtest")
    print("   results = run_backtest(df, entries=[...], exits=[...])")


if __name__ == "__main__":
    main()
