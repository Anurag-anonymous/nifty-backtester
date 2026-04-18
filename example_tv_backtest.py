#!/usr/bin/env python3
"""
Example: Using TradingView Data with Your Backtester

This script shows how to fetch NIFTY 50 data from TradingView
and use it with your backtesting engine.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import pandas as pd
from tv_api import fetch_and_save_tv_data, fetch_nifty_data_from_tv


def example_1_basic_fetch():
    """Example 1: Fetch data and save to CSV."""
    print("\n" + "=" * 70)
    print("EXAMPLE 1: Basic Fetch and Save")
    print("=" * 70)
    
    # Fetch last 500 bars (about 2-3 days of 5-minute data)
    csv_path = fetch_and_save_tv_data(
        n_bars=500,
        output_path="data/nifty_example_500bars.csv",
        interval_minutes=5
    )
    
    print(f"\n✅ Data saved to: {csv_path}")
    
    # Load the file
    df = pd.read_csv(csv_path, parse_dates=['Datetime'])
    print(f"\nData summary:")
    print(f"  Total candles: {len(df)}")
    print(f"  Date range: {df['Datetime'].min()} to {df['Datetime'].max()}")
    print(f"  NIFTY range: {df['Close'].min():.2f} to {df['Close'].max():.2f}")
    
    return df


def example_2_load_for_backtest():
    """Example 2: Load data and prepare for backtesting."""
    print("\n" + "=" * 70)
    print("EXAMPLE 2: Load Data and Prepare for Backtesting")
    print("=" * 70)
    
    # Fetch fresh data
    df = fetch_nifty_data_from_tv(n_bars=1000, interval_minutes=5)
    
    print(f"\n✅ Loaded {len(df)} candles for backtesting")
    print(f"   Columns: {list(df.columns)}")
    print(f"   Trading days: {df['date'].nunique()}")
    
    # Display sample
    print(f"\nFirst 5 candles:")
    print(df.head().to_string())
    
    # You can now pass this DataFrame to your backtester
    # results = run_backtest(df, strategy_params={...})
    
    return df


def example_3_different_intervals():
    """Example 3: Fetch different timeframes."""
    print("\n" + "=" * 70)
    print("EXAMPLE 3: Different Intervals")
    print("=" * 70)
    
    # 15-minute data (300 bars = ~3 days)
    print("\n📊 Fetching 15-minute data (300 bars)...")
    df_15m = fetch_nifty_data_from_tv(n_bars=300, interval_minutes=15)
    print(f"   ✓ {len(df_15m)} bars")
    print(f"   Date range: {df_15m['Datetime'].min()} to {df_15m['Datetime'].max()}")
    
    # 1-hour data (100 bars = ~4-5 days)
    print("\n📊 Fetching 1-hour data (100 bars)...")
    df_1h = fetch_nifty_data_from_tv(n_bars=100, interval_minutes=60)
    print(f"   ✓ {len(df_1h)} bars")
    print(f"   Date range: {df_1h['Datetime'].min()} to {df_1h['Datetime'].max()}")
    
    return df_15m, df_1h


def example_4_multiple_fetches():
    """Example 4: Fetch multiple times for comparison."""
    print("\n" + "=" * 70)
    print("EXAMPLE 4: Compare Data from Multiple Fetches")
    print("=" * 70)
    
    # First fetch
    print("\n📥 First fetch...")
    df1 = fetch_nifty_data_from_tv(n_bars=100, interval_minutes=5)
    print(f"   Fetched {len(df1)} bars, last close: {df1['Close'].iloc[-1]:.2f}")
    
    # You could do other work here...
    print("\n[Doing other work...]")
    
    # Second fetch
    print("\n📥 Second fetch...")
    df2 = fetch_nifty_data_from_tv(n_bars=100, interval_minutes=5)
    print(f"   Fetched {len(df2)} bars, last close: {df2['Close'].iloc[-1]:.2f}")
    
    # Compare
    print(f"\n📊 Comparison:")
    print(f"   Same data? {df1['Close'].iloc[-1] == df2['Close'].iloc[-1]}")


def main():
    """Run all examples."""
    print("\n" + "=" * 70)
    print("🔷 TRADINGVIEW INTEGRATION - USAGE EXAMPLES")
    print("=" * 70)
    
    try:
        # Run examples
        df1 = example_1_basic_fetch()
        df2 = example_2_load_for_backtest()
        df3_15m, df3_1h = example_3_different_intervals()
        example_4_multiple_fetches()
        
        # Summary
        print("\n" + "=" * 70)
        print("✅ ALL EXAMPLES COMPLETED SUCCESSFULLY!")
        print("=" * 70)
        print("\nYou can now:")
        print("1. Use fetch_and_save_tv_data() to get fresh data")
        print("2. Pass DataFrames to run_backtest() to test strategies")
        print("3. Schedule daily fetches to keep data updated")
        print("\nExample workflow:")
        print("   from tv_api import fetch_and_save_tv_data")
        print("   csv = fetch_and_save_tv_data(n_bars=2000)")
        print("   from backtest import run_backtest")
        print("   df = pd.read_csv(csv, parse_dates=['Datetime'])")
        print("   results = run_backtest(df, entries=[...], exits=[...])")
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
