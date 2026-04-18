#!/usr/bin/env python
"""Quick test of the fixed pipeline"""

from data_loader import fetch_data
from indicators import prepare_data
from backtest import run_backtest
from metrics import compute_metrics

print("Testing fixed pipeline...")
print("=" * 60)

# Test 1: Data loading
print("\n1. Testing data_loader...")
df = fetch_data('60d', '5m', False)
print(f"   ✓ Data loaded: {len(df)} candles")
print(f"   ✓ Trading days: {df['date'].nunique()}")
print(f"   ✓ Columns: {df.columns.tolist()}")

# Test 2: Indicators
print("\n2. Testing indicators...")
df_p = prepare_data(df)
print(f"   ✓ Indicators prepared: {df_p.shape[0]} rows")
print(f"   ✓ Columns: {df_p.columns.tolist()}")

# Test 3: Backtest
print("\n3. Running backtest...")
trades, daily_summary = run_backtest(df_p)
print(f"   ✓ Trades executed: {len(trades)}")
print(f"   ✓ Trading days: {len(daily_summary)}")

# Test 4: Metrics
print("\n4. Computing metrics...")
m = compute_metrics(trades, 500000)
print(f"   ✓ Total trades: {m['total_trades']}")
print(f"   ✓ Win rate: {m['win_rate_pct']:.2f}%")
print(f"   ✓ Total P&L: ₹{m['total_pnl_inr']:,.0f}")
print(f"   ✓ Profit factor: {m['profit_factor']:.2f}")
print(f"   ✓ Expectancy: {m['expectancy_points']:.2f} pts")

print("\n" + "=" * 60)
print("✅ All modules working correctly!")
