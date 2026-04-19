"""
Backtest Module - VWAP + EMA Confluence Scalping Strategy

Implements the specific intraday scalping strategy for Nifty 50:
- VWAP + EMA(9/21) confluence entries
- 2:1 risk:reward targets
- Daily loss limits and trade count limits
"""

import pandas as pd
import numpy as np
from datetime import datetime, time


# Default strategy parameters
DEFAULT_PARAMS = {
    'stop_loss_points': 20,           # Stop loss distance in points
    'rr_ratio': 2.0,                  # Risk:Reward ratio
    'ema_pullback_pct': 0.15,         # Max % deviation from EMA21 for pullback
    'max_trades_per_day': 3,          # Max trades allowed per day
    'daily_loss_limit_pct': 2.0,      # Stop trading if daily loss > this %
    'initial_capital': 500000,        # Starting capital in INR
    'lot_size': 50,                   # Nifty lot size
    'brokerage_per_trade': 40         # Brokerage per trade (entry + exit)
}


def run_backtest(df, stop_loss_points=20, rr_ratio=2.0, ema_pullback_pct=0.15,
                 max_trades_per_day=3, daily_loss_limit_pct=2.0, initial_capital=500000,
                 lot_size=50, brokerage_per_trade=40):
    """
    Run backtest on VWAP + EMA confluence scalping strategy.

    Parameters:
    -----------
    df : pd.DataFrame
        DataFrame with OHLCV + indicators from indicators.prepare_data()
    stop_loss_points : float
        Stop loss distance in index points
    rr_ratio : float
        Risk:Reward ratio (target = stop_loss * rr_ratio)
    ema_pullback_pct : float
        Max % deviation from EMA21 to qualify as pullback (0.15 = 0.15%)
    max_trades_per_day : int
        Maximum trades to allow per day
    daily_loss_limit_pct : float
        Stop trading if cumulative daily loss exceeds this % of capital
    initial_capital : float
        Starting capital in INR
    lot_size : int
        Nifty lot size for P&L calculations
    brokerage_per_trade : float
        Brokerage cost per trade (entry + exit)

    Returns:
    --------
    trades_df : pd.DataFrame
        DataFrame with all executed trades and their details
    daily_summary_df : pd.DataFrame
        Daily P&L summary
    """

    # Input validation
    required_cols = ['date', 'timestamp', 'Open', 'High', 'Low', 'Close', 'ema9', 'ema21', 'vwap']
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        raise ValueError(f"Missing required columns: {missing_cols}")

    # Make copy and sort
    df = df.copy().sort_values(['date', 'timestamp']).reset_index(drop=True)

    # Trading windows (IST)
    MORNING_START = time(9, 30)
    MORNING_END = time(11, 30)
    AFTERNOON_START = time(14, 0)  # 2:00 PM
    AFTERNOON_END = time(15, 10)   # 3:10 PM
    MARKET_CLOSE = time(15, 15)    # 3:15 PM

    def is_trading_window(ts):
        """Check if timestamp is within trading windows."""
        t = ts.time()
        return ((MORNING_START <= t <= MORNING_END) or
                (AFTERNOON_START <= t <= AFTERNOON_END))

    # Initialize tracking variables
    trades = []
    daily_trades_count = {}
    daily_pnl = {}
    running_capital = initial_capital
    trade_counter = 0

    # Process each candle
    for idx, row in df.iterrows():
        current_date = row['date']
        current_time = row['timestamp']

        # Initialize daily counters if new day
        if current_date not in daily_trades_count:
            daily_trades_count[current_date] = 0
            daily_pnl[current_date] = 0

        # Check daily loss limit
        if daily_pnl[current_date] < -(initial_capital * daily_loss_limit_pct / 100):
            continue  # Skip this candle, daily loss limit hit

        # Check max trades per day
        if daily_trades_count[current_date] >= max_trades_per_day:
            continue  # Skip this candle, max trades reached

        # Check if we're in trading window
        if not is_trading_window(current_time):
            continue

        # Check for open trades (only allow one trade per day)
        open_trades_today = [t for t in trades if t['date'] == current_date and t.get('exit_time') is None]
        if open_trades_today:
            # Manage open trade
            trade = open_trades_today[0]

            # Check stop loss
            if trade['direction'] == 'LONG':
                if row['Low'] <= trade['stop_loss']:
                    # Stop loss hit
                    exit_price = trade['stop_loss']
                    exit_reason = 'stop_loss'
                elif row['High'] >= trade['target']:
                    # Target hit
                    exit_price = trade['target']
                    exit_reason = 'target'
                elif current_time.time() >= MARKET_CLOSE:
                    # End of day
                    exit_price = row['Close']
                    exit_reason = 'end_of_day'
                else:
                    continue  # Trade still open
            else:  # SHORT
                if row['High'] >= trade['stop_loss']:
                    # Stop loss hit
                    exit_price = trade['stop_loss']
                    exit_reason = 'stop_loss'
                elif row['Low'] <= trade['target']:
                    # Target hit
                    exit_price = trade['target']
                    exit_reason = 'target'
                elif current_time.time() >= MARKET_CLOSE:
                    # End of day
                    exit_price = row['Close']
                    exit_reason = 'end_of_day'
                else:
                    continue  # Trade still open

            # Close the trade
            trade['exit_time'] = current_time
            trade['exit_price'] = exit_price
            trade['exit_reason'] = exit_reason

            # Calculate P&L
            if trade['direction'] == 'LONG':
                pnl_points = exit_price - trade['entry_price']
            else:
                pnl_points = trade['entry_price'] - exit_price

            trade['pnl_points'] = pnl_points
            trade['pnl_inr'] = pnl_points * lot_size
            trade['pnl_inr'] -= brokerage_per_trade  # Subtract brokerage

            # Update daily P&L
            daily_pnl[current_date] += trade['pnl_inr']

            continue  # Don't look for new entries on same candle

        # Look for new entries
        close_price = row['Close']
        ema21 = row['ema21']
        ema9 = row['ema9']
        vwap = row['vwap']

        # Calculate pullback percentage from EMA21
        pullback_pct = abs(close_price - ema21) / ema21 * 100

        # LONG entry conditions
        long_conditions = [
            close_price > vwap,                                    # Above VWAP
            ema9 > ema21,                                          # Uptrend
            pullback_pct <= ema_pullback_pct,                      # Close to EMA21
            daily_trades_count[current_date] == 0                 # No trades today yet
        ]

        # SHORT entry conditions
        short_conditions = [
            close_price < vwap,                                    # Below VWAP
            ema9 < ema21,                                          # Downtrend
            pullback_pct <= ema_pullback_pct,                      # Close to EMA21
            daily_trades_count[current_date] == 0                 # No trades today yet
        ]

        if all(long_conditions):
            # Enter LONG
            entry_price = close_price
            stop_loss = entry_price - stop_loss_points
            target = entry_price + (stop_loss_points * rr_ratio)

            trade = {
                'date': current_date,
                'entry_time': current_time,
                'direction': 'LONG',
                'entry_price': entry_price,
                'stop_loss': stop_loss,
                'target': target,
                'exit_time': None,
                'exit_price': None,
                'exit_reason': None,
                'pnl_points': None,
                'pnl_inr': None,
                'trade_number_today': daily_trades_count[current_date] + 1,
                'running_capital': running_capital
            }

            trades.append(trade)
            daily_trades_count[current_date] += 1
            trade_counter += 1

        elif all(short_conditions):
            # Enter SHORT
            entry_price = close_price
            stop_loss = entry_price + stop_loss_points
            target = entry_price - (stop_loss_points * rr_ratio)

            trade = {
                'date': current_date,
                'entry_time': current_time,
                'direction': 'SHORT',
                'entry_price': entry_price,
                'stop_loss': stop_loss,
                'target': target,
                'exit_time': None,
                'exit_price': None,
                'exit_reason': None,
                'pnl_points': None,
                'pnl_inr': None,
                'trade_number_today': daily_trades_count[current_date] + 1,
                'running_capital': running_capital
            }

            trades.append(trade)
            daily_trades_count[current_date] += 1
            trade_counter += 1

    # Convert to DataFrames
    trades_df = pd.DataFrame(trades)

    # Create daily summary
    daily_summary = []
    for date in df['date'].unique():
        day_trades = trades_df[trades_df['date'] == date]
        if len(day_trades) > 0:
            day_pnl = day_trades['pnl_inr'].sum()
            daily_summary.append({
                'date': date,
                'trades': len(day_trades),
                'pnl_inr': day_pnl,
                'pnl_points': day_pnl / lot_size if lot_size > 0 else 0
            })

    daily_summary_df = pd.DataFrame(daily_summary)

    return trades_df, daily_summary_df