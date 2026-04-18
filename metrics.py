"""
Metrics Module - Performance statistics computation for backtest results.

Computes comprehensive trading metrics from the trades DataFrame:
- Win rate, profit factor, expectancy
- Drawdown, Sharpe ratio
- P&L in points and INR
- Consecutive wins/losses
"""

import pandas as pd
import numpy as np
from datetime import datetime


def compute_metrics(trades_df, initial_capital):
    """
    Compute comprehensive performance metrics from trades DataFrame.
    
    Parameters:
    -----------
    trades_df : pd.DataFrame
        DataFrame of trades from backtest.run_backtest(), with columns:
        - date, entry_time, exit_time, direction, entry_price, stop_loss, target,
        - exit_price, exit_reason, pnl_points, pnl_inr, trade_number_today,
        - running_capital
    initial_capital : float
        Starting capital in INR (for return % calculations)
    
    Returns:
    --------
    dict
        Dictionary with keys:
        - total_trades, winning_trades, losing_trades, scratch_trades
        - win_rate_pct, win_rate_by_direction
        - avg_win_points, avg_loss_points, total_pnl_points
        - total_pnl_inr, avg_pnl_per_trade_inr
        - profit_factor, expectancy_points
        - max_drawdown_inr, max_drawdown_pct
        - max_consecutive_losses, max_consecutive_wins
        - sharpe_ratio
        - total_return_pct, avg_daily_pnl_inr
        - equity_curve_data (for external plotting)
    """
    
    if len(trades_df) == 0:
        # No trades
        return {
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'scratch_trades': 0,
            'win_rate_pct': 0,
            'avg_win_points': 0,
            'avg_loss_points': 0,
            'total_pnl_points': 0,
            'total_pnl_inr': 0,
            'avg_pnl_per_trade_inr': 0,
            'profit_factor': 0,
            'expectancy_points': 0,
            'max_drawdown_inr': 0,
            'max_drawdown_pct': 0,
            'max_consecutive_losses': 0,
            'max_consecutive_wins': 0,
            'sharpe_ratio': 0,
            'total_return_pct': 0,
            'avg_daily_pnl_inr': 0
        }
    
    trades = trades_df.copy()
    
    # Basic counts
    total_trades = len(trades)
    winning_trades = len(trades[trades['pnl_inr'] > 0])
    losing_trades = len(trades[trades['pnl_inr'] < 0])
    scratch_trades = len(trades[trades['pnl_inr'] == 0])
    
    # Win rate
    win_rate_pct = (winning_trades / total_trades * 100) if total_trades > 0 else 0
    
    # Points metrics
    total_pnl_points = trades['pnl_points'].sum()
    avg_win_points = trades[trades['pnl_points'] > 0]['pnl_points'].mean() if winning_trades > 0 else 0
    avg_loss_points = trades[trades['pnl_points'] < 0]['pnl_points'].mean() if losing_trades > 0 else 0
    
    # INR metrics
    total_pnl_inr = trades['pnl_inr'].sum()
    avg_pnl_per_trade_inr = total_pnl_inr / total_trades if total_trades > 0 else 0
    
    # Profit factor = gross_profit / gross_loss
    gross_profit = trades[trades['pnl_inr'] > 0]['pnl_inr'].sum()
    gross_loss = abs(trades[trades['pnl_inr'] < 0]['pnl_inr'].sum())
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else (1 if gross_profit > 0 else 0)
    
    # Expectancy = (win_rate * avg_win) + (loss_rate * avg_loss)
    loss_rate = (1 - win_rate_pct / 100)
    expectancy_points = (win_rate_pct / 100 * avg_win_points) + (loss_rate * avg_loss_points)
    
    # Consecutive wins/losses
    trades['pnl_sign'] = np.sign(trades['pnl_inr'])
    trades['pnl_sign'] = trades['pnl_sign'].replace(0, np.nan)  # Scratch trades excluded
    
    max_consecutive_wins = 0
    max_consecutive_losses = 0
    current_wins = 0
    current_losses = 0
    
    for pnl_sign in trades['pnl_sign']:
        if pnl_sign == 1:
            current_wins += 1
            current_losses = 0
            max_consecutive_wins = max(max_consecutive_wins, current_wins)
        elif pnl_sign == -1:
            current_losses += 1
            current_wins = 0
            max_consecutive_losses = max(max_consecutive_losses, current_losses)
    
    # Drawdown analysis
    equity_curve = trades['running_capital'].values
    peak_value = np.maximum.accumulate(equity_curve)
    drawdown = peak_value - equity_curve
    max_drawdown_inr = drawdown.max()
    max_drawdown_pct = (max_drawdown_inr / initial_capital * 100) if initial_capital > 0 else 0
    
    # Sharpe ratio (annualized, using daily returns)
    daily_pnl = trades.groupby('date')['pnl_inr'].sum()
    daily_returns = daily_pnl / initial_capital
    
    if len(daily_returns) > 1:
        daily_std = daily_returns.std()
        sharpe_ratio = (daily_returns.mean() / daily_std * np.sqrt(252)) if daily_std > 0 else 0
    else:
        sharpe_ratio = 0
    
    # Total return
    total_return_pct = (total_pnl_inr / initial_capital * 100) if initial_capital > 0 else 0
    
    # Average daily P&L
    num_trading_days = trades['date'].nunique()
    avg_daily_pnl_inr = daily_pnl.mean() if num_trading_days > 0 else 0
    
    # Win rate by direction
    long_trades = trades[trades['direction'] == 'long']
    short_trades = trades[trades['direction'] == 'short']
    
    long_win_rate = (len(long_trades[long_trades['pnl_inr'] > 0]) / len(long_trades) * 100) if len(long_trades) > 0 else 0
    short_win_rate = (len(short_trades[short_trades['pnl_inr'] > 0]) / len(short_trades) * 100) if len(short_trades) > 0 else 0
    
    return {
        'total_trades': int(total_trades),
        'winning_trades': int(winning_trades),
        'losing_trades': int(losing_trades),
        'scratch_trades': int(scratch_trades),
        'long_trades': int(len(long_trades)),
        'short_trades': int(len(short_trades)),
        'win_rate_pct': round(win_rate_pct, 2),
        'long_win_rate': round(long_win_rate, 2),
        'short_win_rate': round(short_win_rate, 2),
        'avg_win_points': round(avg_win_points, 2),
        'avg_loss_points': round(avg_loss_points, 2),
        'total_pnl_points': round(total_pnl_points, 2),
        'total_pnl_inr': round(total_pnl_inr, 2),
        'avg_pnl_per_trade_inr': round(avg_pnl_per_trade_inr, 2),
        'gross_profit': round(gross_profit, 2),
        'gross_loss': round(gross_loss, 2),
        'profit_factor': round(profit_factor, 2),
        'expectancy_points': round(expectancy_points, 2),
        'max_drawdown_inr': round(max_drawdown_inr, 2),
        'max_drawdown_pct': round(max_drawdown_pct, 2),
        'max_consecutive_losses': int(max_consecutive_losses),
        'max_consecutive_wins': int(max_consecutive_wins),
        'sharpe_ratio': round(sharpe_ratio, 2),
        'total_return_pct': round(total_return_pct, 2),
        'avg_daily_pnl_inr': round(avg_daily_pnl_inr, 2),
        'num_trading_days': int(num_trading_days)
    }


def get_equity_curve(trades_df, initial_capital):
    """
    Get equity curve (running capital) for plotting.
    
    Parameters:
    -----------
    trades_df : pd.DataFrame
        DataFrame of trades from backtest
    initial_capital : float
        Starting capital
    
    Returns:
    --------
    list
        List of [timestamp_unix, capital] pairs for Plotly time-series plotting
    """
    if len(trades_df) == 0:
        return []
    
    curve = []
    for idx, row in trades_df.iterrows():
        # Convert datetime to unix timestamp (milliseconds for Plotly)
        timestamp = int(row['exit_time'].timestamp() * 1000)
        capital = row['running_capital']
        curve.append([timestamp, capital])
    
    return curve


def get_monthly_pnl(trades_df):
    """
    Get month-wise P&L summary.
    
    Parameters:
    -----------
    trades_df : pd.DataFrame
        DataFrame of trades from backtest
    
    Returns:
    --------
    dict
        Dictionary with keys in format "YYYY-MM" and values as dicts:
        {
            'pnl_inr': float,
            'num_trades': int,
            'num_days': int,
            'win_rate': float
        }
    """
    if len(trades_df) == 0:
        return {}
    
    trades = trades_df.copy()
    trades['exit_date'] = trades['exit_time'].dt.date
    trades['month'] = trades['exit_time'].dt.to_period('M')
    
    monthly = trades.groupby('month').agg({
        'pnl_inr': 'sum',
        'date': 'nunique',
        'exit_date': 'nunique'
    }).reset_index()
    
    # Count wins per month
    monthly_wins = trades[trades['pnl_inr'] > 0].groupby('month').size()
    monthly_total = trades.groupby('month').size()
    
    result = {}
    for idx, row in monthly.iterrows():
        month_str = str(row['month'])
        wins = monthly_wins.get(row['month'], 0)
        total = monthly_total.get(row['month'], 0)
        win_rate = (wins / total * 100) if total > 0 else 0
        
        result[month_str] = {
            'pnl_inr': round(row['pnl_inr'], 2),
            'num_trades': int(total),
            'num_days': int(row['date']),
            'win_rate': round(win_rate, 2)
        }
    
    return result


def get_trade_log(trades_df):
    """
    Format trades for tabular display (for HTML table).
    
    Parameters:
    -----------
    trades_df : pd.DataFrame
        DataFrame of trades from backtest
    
    Returns:
    --------
    list
        List of dicts suitable for rendering as table rows
    """
    if len(trades_df) == 0:
        return []
    
    trades = trades_df.copy()
    
    result = []
    for idx, row in trades.iterrows():
        date_val = row['date']
        if isinstance(date_val, str):
            date_val = pd.to_datetime(date_val).date()

        entry_time = row['entry_time']
        if isinstance(entry_time, str):
            entry_time = pd.to_datetime(entry_time)

        result.append({
            'date': date_val.strftime('%Y-%m-%d'),
            'time': entry_time.strftime('%H:%M'),
            'direction': row['direction'].upper(),
            'entry_price': round(row['entry_price'], 2),
            'sl': round(row['stop_loss'], 2),
            'target': round(row['target'], 2),
            'exit_price': round(row['exit_price'], 2),
            'reason': row['exit_reason'],
            'pnl_points': round(row['pnl_points'], 2),
            'pnl_inr': round(row['pnl_inr'], 2),
            'trade_number': row['trade_number_today']
        })
    
    return result


if __name__ == "__main__":
    # Standalone testing
    from data_loader import fetch_data
    from indicators import prepare_data
    from backtest import run_backtest
    
    print("=" * 60)
    print("Metrics Module - Standalone Test")
    print("=" * 60)
    
    # Fetch, prepare, and backtest
    df = fetch_data(period="60d", interval="5m", force_refresh=False)
    df_prepared = prepare_data(df)
    trades_df, daily_summary_df = run_backtest(df_prepared, initial_capital=500000)
    
    # Compute metrics
    initial_capital = 500000
    metrics = compute_metrics(trades_df, initial_capital)
    
    print(f"\n\nMetrics:")
    for key, value in metrics.items():
        if key != 'num_trading_days':
            print(f"  {key}: {value}")
    
    # Get equity curve
    equity_curve = get_equity_curve(trades_df, initial_capital)
    print(f"\n\nEquity curve points: {len(equity_curve)}")
    if equity_curve:
        print(f"  First: {equity_curve[0]}")
        print(f"  Last: {equity_curve[-1]}")
    
    # Get monthly P&L
    monthly_pnl = get_monthly_pnl(trades_df)
    print(f"\n\nMonthly P&L:")
    for month, data in monthly_pnl.items():
        print(f"  {month}: ₹{data['pnl_inr']} ({data['num_trades']} trades, {data['win_rate']:.1f}% WR)")
    
    # Get trade log
    trade_log = get_trade_log(trades_df)
    print(f"\n\nTrade log ({len(trade_log)} trades):")
    for trade in trade_log[:5]:
        print(f"  {trade}")
