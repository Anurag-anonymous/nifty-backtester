"""
Paper Trade Tracker - Logs and tracks options paper trades to CSV.

Every paper trade (simulated buy/sell of a Nifty option) is recorded here.
On startup, the tracker loads existing trades from CSV. Ongoing trades
have their current P&L updated in real time via the options engine.
"""

import pandas as pd
import os
from datetime import datetime


BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))


def get_data_dir():
    if os.environ.get('RENDER') or os.environ.get('FLASK_ENV') == 'production':
        data_dir = os.path.join('/tmp', 'data')
    else:
        data_dir = os.path.join(BASE_DIR, 'data')
    os.makedirs(data_dir, exist_ok=True)
    return data_dir


PAPER_TRADES_CSV = os.path.join(get_data_dir(), 'paper_trades.csv')

COLUMNS = [
    'trade_id', 'entry_time', 'signal_direction', 'trading_symbol',
    'strike', 'option_type', 'expiry', 'entry_premium', 'lot_cost',
    'target_premium', 'stop_premium', 'exit_time', 'exit_premium',
    'exit_reason', 'pnl_per_lot', 'pnl_pct', 'status',
    'nifty_at_entry', 'iv_at_entry', 'delta_at_entry', 'days_to_expiry'
]


def load_trades():
    """Load all paper trades from CSV. Returns empty DataFrame if file missing."""
    if not os.path.exists(PAPER_TRADES_CSV):
        return pd.DataFrame(columns=COLUMNS)
    return pd.read_csv(PAPER_TRADES_CSV)


def save_trades(df):
    """Save trades DataFrame to CSV."""
    os.makedirs(os.path.dirname(PAPER_TRADES_CSV), exist_ok=True)
    df.to_csv(PAPER_TRADES_CSV, index=False)


def add_trade(option_details, signal_direction, nifty_price):
    """
    Record a new paper trade entry.
    
    Parameters:
    -----------
    option_details : dict
        Output from options_engine.select_option()
    signal_direction : str
        'LONG' or 'SHORT'
    nifty_price : float
        Nifty spot price at entry time
    
    Returns:
    --------
    str
        trade_id of the new trade
    """
    df = load_trades()
    
    # Check if there's already an open trade — only one at a time
    open_trades = df[df['status'] == 'OPEN']
    if not open_trades.empty:
        print("WARNING: There is already an open paper trade. Close it first.")
        return None
    
    trade_id = f"PT{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    new_trade = {
        'trade_id':          trade_id,
        'entry_time':        datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'signal_direction':  signal_direction,
        'trading_symbol':    option_details['trading_symbol'],
        'strike':            option_details['strike'],
        'option_type':       option_details['option_type'],
        'expiry':            option_details['expiry'],
        'entry_premium':     option_details['premium'],
        'lot_cost':          option_details['lot_cost'],
        'target_premium':    option_details['target_premium'],
        'stop_premium':      option_details['stop_premium'],
        'exit_time':         None,
        'exit_premium':      None,
        'exit_reason':       None,
        'pnl_per_lot':       None,
        'pnl_pct':           None,
        'status':            'OPEN',
        'nifty_at_entry':    round(nifty_price, 2),
        'iv_at_entry':       option_details.get('iv', None),
        'delta_at_entry':    option_details.get('delta', None),
        'days_to_expiry':    option_details.get('days_to_expiry', None),
    }
    
    df = pd.concat([df, pd.DataFrame([new_trade])], ignore_index=True)
    save_trades(df)
    print(f"Paper trade logged: {trade_id} — {option_details['trading_symbol']} @ ₹{option_details['premium']}")
    return trade_id


def close_trade(trade_id, exit_premium, exit_reason):
    """
    Mark an open paper trade as closed with final P&L.
    
    Parameters:
    -----------
    trade_id : str
    exit_premium : float
        Premium at which the option was exited
    exit_reason : str
        'TARGET', 'STOP', 'MANUAL', 'TIME_STOP', 'SIGNAL_REVERSAL'
    
    Returns:
    --------
    dict
        Final P&L summary
    """
    df = load_trades()
    mask = df['trade_id'] == trade_id
    
    if not mask.any():
        return {'error': f'Trade {trade_id} not found'}
    
    entry_premium = float(df.loc[mask, 'entry_premium'].values[0])
    pnl_per_lot   = (exit_premium - entry_premium) * 50
    pnl_pct       = ((exit_premium - entry_premium) / entry_premium) * 100
    
    df.loc[mask, 'exit_time']    = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    df.loc[mask, 'exit_premium'] = round(exit_premium, 2)
    df.loc[mask, 'exit_reason']  = exit_reason
    df.loc[mask, 'pnl_per_lot']  = round(pnl_per_lot, 2)
    df.loc[mask, 'pnl_pct']      = round(pnl_pct, 2)
    df.loc[mask, 'status']       = 'CLOSED'
    
    save_trades(df)
    
    return {
        'trade_id':    trade_id,
        'exit_premium': round(exit_premium, 2),
        'exit_reason':  exit_reason,
        'pnl_per_lot':  round(pnl_per_lot, 2),
        'pnl_pct':      round(pnl_pct, 2),
        'result':       'WIN' if pnl_per_lot > 0 else 'LOSS'
    }


def get_open_trade():
    """Return the currently open paper trade, or None if no open trade."""
    df = load_trades()
    open_trades = df[df['status'] == 'OPEN']
    if open_trades.empty:
        return None
    return open_trades.iloc[-1].to_dict()


def get_trade_summary():
    """
    Compute performance summary across all closed paper trades.
    
    Returns:
    --------
    dict
        {
          'total_trades': int,
          'wins': int, 'losses': int,
          'win_rate_pct': float,
          'total_pnl': float,
          'avg_win': float,
          'avg_loss': float,
          'best_trade': float,
          'worst_trade': float,
          'open_trade': dict or None
        }
    """
    df = load_trades()
    closed = df[df['status'] == 'CLOSED'].copy()
    
    if closed.empty:
        return {
            'total_trades': 0, 'wins': 0, 'losses': 0,
            'win_rate_pct': 0, 'total_pnl': 0,
            'avg_win': 0, 'avg_loss': 0,
            'best_trade': 0, 'worst_trade': 0,
            'open_trade': get_open_trade()
        }
    
    closed['pnl_per_lot'] = pd.to_numeric(closed['pnl_per_lot'], errors='coerce')
    wins   = closed[closed['pnl_per_lot'] > 0]
    losses = closed[closed['pnl_per_lot'] <= 0]
    
    return {
        'total_trades': len(closed),
        'wins':         len(wins),
        'losses':       len(losses),
        'win_rate_pct': round(len(wins) / len(closed) * 100, 1) if len(closed) > 0 else 0,
        'total_pnl':    round(closed['pnl_per_lot'].sum(), 2),
        'avg_win':      round(wins['pnl_per_lot'].mean(), 2) if not wins.empty else 0,
        'avg_loss':     round(losses['pnl_per_lot'].mean(), 2) if not losses.empty else 0,
        'best_trade':   round(closed['pnl_per_lot'].max(), 2),
        'worst_trade':  round(closed['pnl_per_lot'].min(), 2),
        'open_trade':   get_open_trade()
    }
