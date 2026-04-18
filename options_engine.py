"""
Options Engine - Nifty weekly options selection and signal generation.

This module takes a directional signal (LONG/SHORT) from the VWAP + EMA
strategy and identifies the optimal Nifty weekly option to buy within
the ₹5,000–₹8,000 budget constraint.
"""

import pandas as pd
from datetime import datetime, timedelta, date
import pytz

IST = pytz.timezone('Asia/Kolkata')


def get_weekly_expiry():
    """
    Find the nearest upcoming Nifty weekly expiry (Thursday).
    
    Nifty weekly options expire every Thursday. If today is Thursday
    and it's past 3 PM, return next Thursday.
    
    Returns:
    --------
    str
        Expiry date in 'YYYY-MM-DD' format
    """
    today = datetime.now(IST).date()
    days_until_thursday = (3 - today.weekday()) % 7  # Thursday = weekday 3
    
    if days_until_thursday == 0:
        # Today is Thursday — check if market has closed
        now_ist = datetime.now(IST)
        if now_ist.hour >= 15 and now_ist.minute >= 30:
            days_until_thursday = 7  # Use next Thursday
    
    expiry = today + timedelta(days=days_until_thursday)
    return expiry.strftime('%Y-%m-%d')


def get_atm_strike(current_price):
    """
    Find the At-The-Money (ATM) strike for Nifty.
    Nifty strikes are in multiples of 50.
    
    Parameters:
    -----------
    current_price : float
        Current Nifty price
    
    Returns:
    --------
    int
        Nearest strike price (multiple of 50)
    """
    return round(current_price / 50) * 50


def select_option(groww_client, signal, current_nifty_price,
                  budget_min=3000, budget_max=7500):
    """
    Select the optimal Nifty weekly option within budget.
    
    Fetches the option chain from Groww, finds the best affordable
    strike for the given signal direction, and returns full trade details.
    
    Parameters:
    -----------
    groww_client : GrowwAPI
        Authenticated Groww API client
    signal : str
        'LONG' → buy Call, 'SHORT' → buy Put
    current_nifty_price : float
        Current Nifty spot price (LTP)
    budget_min : float
        Minimum acceptable lot cost in ₹ (default ₹3,000)
    budget_max : float
        Maximum acceptable lot cost in ₹ (default ₹7,500)
    
    Returns:
    --------
    dict or None
        {
          'trading_symbol': str,      # e.g. 'NIFTY25APR2323150CE'
          'strike': int,              # e.g. 23150
          'option_type': str,         # 'CE' or 'PE'
          'expiry': str,              # '2026-04-10'
          'premium': float,           # current LTP of the option
          'lot_cost': float,          # premium × 50
          'max_loss': float,          # same as lot_cost (full premium)
          'target_premium': float,    # premium × 1.80 (80% gain target)
          'stop_premium': float,      # premium × 0.60 (40% loss stop)
          'target_pnl': float,        # (target_premium - premium) × 50
          'stop_pnl': float,          # (stop_premium - premium) × 50 (negative)
          'delta': float,             # option delta from Greeks
          'iv': float,                # implied volatility
          'moneyness': str,           # 'ATM', 'OTM+50', 'OTM+100' etc.
          'days_to_expiry': int,
        }
        Returns None if no suitable option found within budget.
    """
    expiry = get_weekly_expiry()
    atm = get_atm_strike(current_nifty_price)
    option_type = 'CE' if signal == 'LONG' else 'PE'
    
    try:
        chain = groww_client.get_option_chain(
            exchange=groww_client.EXCHANGE_NSE,
            underlying="NIFTY",
            expiry_date=expiry
        )
    except Exception as e:
        print(f"Option chain fetch failed: {e}")
        return None
    
    strikes_data = chain.get('strikes', {})
    if not strikes_data:
        return None
    
    # Get sorted list of available strikes
    available_strikes = sorted([int(k) for k in strikes_data.keys()])
    
    # For CALL: scan from ATM upward (slightly OTM calls are cheaper)
    # For PUT:  scan from ATM downward (slightly OTM puts are cheaper)
    if option_type == 'CE':
        # Start at ATM, go up
        candidate_strikes = [s for s in available_strikes if s >= atm]
    else:
        # Start at ATM, go down
        candidate_strikes = [s for s in reversed(available_strikes) if s <= atm]
    
    # Find the first strike within budget
    selected = None
    for strike in candidate_strikes:
        strike_str = str(strike)
        if strike_str not in strikes_data:
            continue
        
        option_data = strikes_data[strike_str].get(option_type, {})
        if not option_data:
            continue
        
        premium = option_data.get('ltp', 0)
        if premium <= 0:
            continue
        
        lot_cost = premium * 50  # Nifty lot size = 50
        
        if budget_min <= lot_cost <= budget_max:
            greeks = option_data.get('greeks', {})
            
            # Calculate moneyness label
            diff = strike - atm
            if diff == 0:
                moneyness = 'ATM'
            elif option_type == 'CE':
                moneyness = f'OTM+{diff}' if diff > 0 else f'ITM{diff}'
            else:
                moneyness = f'OTM{diff}' if diff < 0 else f'ITM+{diff}'
            
            # Days to expiry
            expiry_date = datetime.strptime(expiry, '%Y-%m-%d').date()
            days_to_expiry = (expiry_date - datetime.now(IST).date()).days
            
            selected = {
                'trading_symbol': option_data.get('trading_symbol', ''),
                'strike':          strike,
                'option_type':     option_type,
                'expiry':          expiry,
                'premium':         round(premium, 2),
                'lot_cost':        round(lot_cost, 2),
                'max_loss':        round(lot_cost, 2),
                'target_premium':  round(premium * 1.80, 2),
                'stop_premium':    round(premium * 0.60, 2),
                'target_pnl':      round((premium * 1.80 - premium) * 50, 2),
                'stop_pnl':        round((premium * 0.60 - premium) * 50, 2),
                'delta':           round(greeks.get('delta', 0), 4),
                'iv':              round(greeks.get('iv', 0), 2),
                'moneyness':       moneyness,
                'days_to_expiry':  days_to_expiry,
            }
            break
    
    if not selected:
        print(f"No {option_type} option found within ₹{budget_min}–₹{budget_max} budget")
    
    return selected


def get_option_live_price(groww_client, trading_symbol):
    """
    Fetch the current live premium of a specific option contract.
    Used to track open paper trades in real time.
    
    Returns:
    --------
    float or None
    """
    try:
        response = groww_client.get_quote(
            exchange=groww_client.EXCHANGE_NSE,
            segment=groww_client.SEGMENT_FNO,
            trading_symbol=trading_symbol
        )
        return response.get('last_price')
    except Exception as e:
        print(f"Option price fetch failed for {trading_symbol}: {e}")
        return None


def check_exit_conditions(entry_premium, current_premium,
                           target_premium, stop_premium):
    """
    Check whether an open options position should be exited.
    
    Parameters:
    -----------
    entry_premium : float
        Premium at which option was bought
    current_premium : float
        Current option premium (live price)
    target_premium : float
        Premium at which to take profit (entry × 1.80)
    stop_premium : float
        Premium at which to cut loss (entry × 0.60)
    
    Returns:
    --------
    dict
        {
          'should_exit': bool,
          'reason': str,
          'pnl_per_lot': float,
          'pnl_pct': float
        }
    """
    pnl_per_lot = (current_premium - entry_premium) * 50
    pnl_pct     = ((current_premium - entry_premium) / entry_premium) * 100
    
    if current_premium >= target_premium:
        return {
            'should_exit': True,
            'reason':      f'TARGET HIT: Premium {current_premium:.2f} ≥ target {target_premium:.2f}',
            'pnl_per_lot': round(pnl_per_lot, 2),
            'pnl_pct':     round(pnl_pct, 2)
        }
    
    if current_premium <= stop_premium:
        return {
            'should_exit': True,
            'reason':      f'STOP HIT: Premium {current_premium:.2f} ≤ stop {stop_premium:.2f}',
            'pnl_per_lot': round(pnl_per_lot, 2),
            'pnl_pct':     round(pnl_pct, 2)
        }
    
    return {
        'should_exit': False,
        'reason':      'Trade still open — within range',
        'pnl_per_lot': round(pnl_per_lot, 2),
        'pnl_pct':     round(pnl_pct, 2)
    }
