#!/usr/bin/env python3
"""
Complete Example: Using Groww API with Nifty 50 Backtester

This script demonstrates the complete workflow:
1. Fetch 5-minute Nifty 50 data from Groww API
2. Prepare data with indicators
3. Run backtest
4. Display results

Before running:
1. Get API key from https://groww.in/trade-api
2. Set environment variable: $env:GROWW_API_KEY = 'your_key'
"""

import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(__file__))

from groww_api import fetch_and_save_groww_data, GROWW_API_KEY
from data_loader import load_csv_upload, ensure_data_directory
from indicators import prepare_data
from backtest import run_backtest, DEFAULT_PARAMS
from metrics import compute_metrics, get_equity_curve


def main():
    print("\n" + "=" * 80)
    print("Complete Example: Groww API + Nifty 50 5-Minute Backtester")
    print("=" * 80)
    
    # Check API key
    if not GROWW_API_KEY:
        print("\n❌ Error: GROWW_API_KEY environment variable not set")
        print("\n   To set it on Windows (PowerShell):")
        print("   $env:GROWW_API_KEY = 'your_api_key_here'")
        print("\n   Get your API key from: https://groww.in/trade-api")
        return
    
    print(f"\n✅ API Key found: {GROWW_API_KEY[:20]}...{GROWW_API_KEY[-10:]}")
    
    # Step 1: Fetch data from Groww API
    print("\n" + "-" * 80)
    print("STEP 1: Fetch 5-Minute Data from Groww API")
    print("-" * 80)
    
    try:
        csv_path = fetch_and_save_groww_data(
            days_back=15,
            output_path="data/nifty_groww_5m.csv"
        )
    except Exception as e:
        print(f"\n❌ Failed to fetch data: {e}")
        return
    
    # Step 2: Load CSV data
    print("\n" + "-" * 80)
    print("STEP 2: Load CSV Data")
    print("-" * 80)
    
    try:
        print(f"\nLoading data from: {csv_path}")
        df = load_csv_upload(csv_path)
        print(f"✅ Loaded {len(df)} candles")
        print(f"   Date range: {df['date'].min()} to {df['date'].max()}")
    except Exception as e:
        print(f"❌ Failed to load CSV: {e}")
        return
    
    # Step 3: Prepare data with indicators
    print("\n" + "-" * 80)
    print("STEP 3: Prepare Data with VWAP, EMA, and Opening Range")
    print("-" * 80)
    
    try:
        print(f"\nPreparing indicators...")
        df_prepared = prepare_data(df)
        
        print(f"✅ Indicators calculated")
        print(f"   Columns: {list(df_prepared.columns)}")
        print(f"   Sample candle with indicators:")
        sample = df_prepared.iloc[0]
        print(f"   - Close: ₹{sample['Close']:.2f}")
        print(f"   - EMA9: ₹{sample['EMA9']:.2f}")
        print(f"   - EMA21: ₹{sample['EMA21']:.2f}")
        print(f"   - VWAP: ₹{sample['VWAP']:.2f}")
    except Exception as e:
        print(f"❌ Failed to prepare data: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Step 4: Run backtest with default parameters
    print("\n" + "-" * 80)
    print("STEP 4: Run Backtest with Default Strategy Parameters")
    print("-" * 80)
    
    print(f"\nStrategy Parameters:")
    print(f"  Stop Loss: {DEFAULT_PARAMS['stop_loss_points']} points")
    print(f"  R:R Ratio: {DEFAULT_PARAMS['rr_ratio']}")
    print(f"  EMA Pullback %: {DEFAULT_PARAMS['ema_pullback_pct']}")
    print(f"  Max Trades/Day: {DEFAULT_PARAMS['max_trades_per_day']}")
    print(f"  Daily Loss Limit %: {DEFAULT_PARAMS['daily_loss_limit_pct']}")
    print(f"  Initial Capital: ₹{DEFAULT_PARAMS['initial_capital']:,.0f}")
    
    try:
        print(f"\nRunning backtest...")
        trades_df, daily_summary_df = run_backtest(df_prepared, **DEFAULT_PARAMS)
        
        print(f"✅ Backtest completed")
    except Exception as e:
        print(f"❌ Backtest failed: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Step 5: Compute metrics
    print("\n" + "-" * 80)
    print("STEP 5: Compute Performance Metrics")
    print("-" * 80)
    
    try:
        metrics = compute_metrics(trades_df, DEFAULT_PARAMS['initial_capital'])
        
        print(f"\n📊 Performance Metrics:")
        print(f"  Total Trades: {metrics['total_trades']}")
        print(f"  Win Rate: {metrics['win_rate_pct']:.2f}%")
        print(f"  Profit Factor: {metrics['profit_factor']:.2f}")
        print(f"  Expectancy: {metrics['expectancy_points']:.2f} points")
        print(f"  Max Drawdown: ₹{metrics['max_drawdown_inr']:,.0f} ({metrics['max_drawdown_pct']:.2f}%)")
        print(f"  Total Return: {metrics['total_return_pct']:.2f}%")
        print(f"  Total P&L: ₹{metrics['total_pnl_inr']:,.0f}")
        print(f"  Sharpe Ratio: {metrics['sharpe_ratio']:.2f}")
        print(f"  Avg Daily P&L: ₹{metrics['avg_daily_pnl_inr']:,.0f}")
        
    except Exception as e:
        print(f"❌ Failed to compute metrics: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Step 6: Summary
    print("\n" + "=" * 80)
    print("✅ BACKTEST COMPLETED SUCCESSFULLY")
    print("=" * 80)
    
    print(f"\n📈 Summary:")
    print(f"   Data source: Groww API (5-minute Nifty 50)")
    print(f"   Period: {df['date'].min()} to {df['date'].max()}")
    print(f"   Candles analyzed: {len(df_prepared)}")
    print(f"   Trades generated: {metrics['total_trades']}")
    print(f"   Net P&L: ₹{metrics['total_pnl_inr']:,.0f}")
    print(f"   Return on capital: {metrics['total_return_pct']:.2f}%")
    
    print(f"\n💾 Files saved:")
    print(f"   Raw data: {csv_path}")
    
    if metrics['total_trades'] > 0:
        print(f"\n📊 Sample trades:")
        print(trades_df[['date', 'entry_price', 'exit_price', 'direction', 'pnl_inr']].head(3).to_string())
    
    print("\n" + "=" * 80 + "\n")


if __name__ == "__main__":
    main()
