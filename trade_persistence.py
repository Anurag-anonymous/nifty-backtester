"""
Trade Entry Persistence - Save live signal trade entries for backtesting & monitoring.

Stores entry details (entry price, target, stop loss) when long/short conditions are met,
even when the user is not actively watching the tool. Enables automatic trade tracking.
"""

import json
import os
from datetime import datetime
import pytz

IST = pytz.timezone('Asia/Kolkata')


def get_trades_dir():
    """
    Get or create the directory for storing trade entry files.
    
    Returns:
    --------
    str
        Path to trades directory (uses /tmp on cloud, ./data/trades locally)
    """
    # Check if running on Render (cloud)
    if os.getenv('RENDER'):
        trades_dir = '/tmp/trades'
    else:
        trades_dir = os.path.join(os.path.dirname(__file__), 'data', 'trades')
    
    os.makedirs(trades_dir, exist_ok=True)
    return trades_dir


def save_trade_entry(entry_type, entry_price, target_price, stop_loss_price, 
                     nifty_price=None, ema9=None, ema21=None, vwap=None):
    """
    Save a trade entry when long/short conditions are met.
    
    Parameters:
    -----------
    entry_type : str
        "LONG" or "SHORT"
    entry_price : float
        Entry price for the trade
    target_price : float
        Target/profit price
    stop_loss_price : float
        Stop loss price
    nifty_price : float, optional
        Current Nifty price
    ema9 : float, optional
        EMA9 value at entry
    ema21 : float, optional
        EMA21 value at entry
    vwap : float, optional
        VWAP value at entry
    
    Returns:
    --------
    dict
        The saved trade entry
    """
    trades_dir = get_trades_dir()
    
    trade_entry = {
        "timestamp": datetime.now(IST).isoformat(),
        "type": entry_type,
        "entry_price": float(entry_price),
        "target_price": float(target_price),
        "stop_loss_price": float(stop_loss_price),
        "status": "ACTIVE",
        "nifty_price": float(nifty_price) if nifty_price else None,
        "ema9": float(ema9) if ema9 else None,
        "ema21": float(ema21) if ema21 else None,
        "vwap": float(vwap) if vwap else None,
        "risk_reward_ratio": (float(target_price) - float(entry_price)) / (float(entry_price) - float(stop_loss_price))
    }
    
    # Load existing trades
    trades_file = os.path.join(trades_dir, 'active_trades.json')
    trades = []
    if os.path.exists(trades_file):
        try:
            with open(trades_file, 'r') as f:
                trades = json.load(f)
        except Exception as e:
            print(f"Failed to load existing trades: {e}")
    
    # Append new trade
    trades.append(trade_entry)
    
    # Save updated trades
    try:
        with open(trades_file, 'w') as f:
            json.dump(trades, f, indent=2)
        print(f"✅ Trade entry saved: {entry_type} @ ₹{entry_price}")
        return trade_entry
    except Exception as e:
        print(f"❌ Failed to save trade entry: {e}")
        return None


def load_active_trades():
    """
    Load all active trade entries.
    
    Returns:
    --------
    list
        List of active trade entries
    """
    trades_dir = get_trades_dir()
    trades_file = os.path.join(trades_dir, 'active_trades.json')
    
    if not os.path.exists(trades_file):
        return []
    
    try:
        with open(trades_file, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Failed to load active trades: {e}")
        return []


def update_trade_status(trade_index, status, exit_price=None, exit_reason=None):
    """
    Update the status of an active trade (e.g., mark as closed).
    
    Parameters:
    -----------
    trade_index : int
        Index of the trade in active_trades.json
    status : str
        New status: "CLOSED_TARGET", "CLOSED_STOPLOSS", "CLOSED_MANUAL"
    exit_price : float, optional
        Price at which trade was closed
    exit_reason : str, optional
        Reason for closing the trade
    """
    trades_dir = get_trades_dir()
    trades_file = os.path.join(trades_dir, 'active_trades.json')
    
    try:
        with open(trades_file, 'r') as f:
            trades = json.load(f)
        
        if 0 <= trade_index < len(trades):
            trades[trade_index]['status'] = status
            if exit_price:
                trades[trade_index]['exit_price'] = float(exit_price)
            if exit_reason:
                trades[trade_index]['exit_reason'] = exit_reason
            trades[trade_index]['exit_time'] = datetime.now(IST).isoformat()
            
            with open(trades_file, 'w') as f:
                json.dump(trades, f, indent=2)
            print(f"✅ Trade {trade_index} updated: {status}")
    except Exception as e:
        print(f"❌ Failed to update trade: {e}")


def get_pending_trades():
    """
    Get all trades with ACTIVE status that need monitoring.
    
    Returns:
    --------
    list
        List of active trades
    """
    trades = load_active_trades()
    return [t for t in trades if t.get('status') == 'ACTIVE']


def export_trades_csv(filename=None):
    """
    Export all trades to a CSV file for analysis.
    
    Parameters:
    -----------
    filename : str, optional
        Output filename (default: trades_export_TIMESTAMP.csv)
    
    Returns:
    --------
    str
        Path to exported CSV file
    """
    import csv
    
    trades = load_active_trades()
    if not trades:
        print("No trades to export")
        return None
    
    if not filename:
        timestamp = datetime.now(IST).strftime("%Y%m%d_%H%M%S")
        filename = f"trades_export_{timestamp}.csv"
    
    trades_dir = get_trades_dir()
    filepath = os.path.join(trades_dir, filename)
    
    try:
        with open(filepath, 'w', newline='') as f:
            fieldnames = ['timestamp', 'type', 'entry_price', 'target_price', 'stop_loss_price', 
                         'exit_price', 'status', 'exit_reason', 'pnl_points', 'pnl_pct']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            
            writer.writeheader()
            for trade in trades:
                row = {
                    'timestamp': trade.get('timestamp'),
                    'type': trade.get('type'),
                    'entry_price': trade.get('entry_price'),
                    'target_price': trade.get('target_price'),
                    'stop_loss_price': trade.get('stop_loss_price'),
                    'exit_price': trade.get('exit_price'),
                    'status': trade.get('status'),
                    'exit_reason': trade.get('exit_reason')
                }
                
                # Calculate P&L if trade is closed
                if trade.get('exit_price'):
                    if trade.get('type') == 'LONG':
                        pnl_pts = trade.get('exit_price') - trade.get('entry_price')
                    else:  # SHORT
                        pnl_pts = trade.get('entry_price') - trade.get('exit_price')
                    
                    row['pnl_points'] = round(pnl_pts, 2)
                    row['pnl_pct'] = round((pnl_pts / trade.get('entry_price')) * 100, 2)
                
                writer.writerow(row)
        
        print(f"✅ Trades exported to {filepath}")
        return filepath
    except Exception as e:
        print(f"❌ Failed to export trades: {e}")
        return None


if __name__ == "__main__":
    print("Trade persistence module loaded")
    print(f"Trades directory: {get_trades_dir()}")
