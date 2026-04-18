"""
Live Signal Engine - Real-time strategy signal generator using Groww API.

Connects to Groww's historical candle API to fetch the most recent 5-minute
Nifty candles, computes VWAP proxy, EMA9, EMA21, EMA50, and evaluates the
VWAP + EMA confluence pullback strategy conditions to generate a live signal.

Signal outputs:
- LONG:  All long entry conditions met — consider buying Nifty calls or futures
- SHORT: All short entry conditions met — consider buying Nifty puts or shorting
- WAIT:  Conditions not met or outside trading window — do nothing
- OFF:   Daily regime filter is neutral — strategy is inactive today
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta, time as dtime
import pytz

IST = pytz.timezone('Asia/Kolkata')


def get_nifty_candles(groww_client, lookback_days=10):
    """
    Fetch recent 5-minute Nifty candles from Groww historical API.
    
    We fetch 10 days of data (well within the 15-day limit per request)
    to ensure EMA50 has enough candles to stabilize. EMA50 needs at least
    50 candles — 10 days of 5-minute data gives roughly 750 candles, more
    than sufficient.
    
    Parameters:
    -----------
    groww_client : GrowwAPI
        Authenticated Groww API client instance
    lookback_days : int
        Number of calendar days to look back (default 10, max 15 for 5m)
    
    Returns:
    --------
    pd.DataFrame
        DataFrame with columns: Datetime, Open, High, Low, Close, Volume, date
        Sorted ascending by Datetime (oldest first).
    """
    now_ist = datetime.now(IST)
    end_time = now_ist.strftime("%Y-%m-%d %H:%M:%S")
    start_time = (now_ist - timedelta(days=lookback_days)).strftime("%Y-%m-%d %H:%M:%S")
    
    print(f"Fetching Nifty 5-min candles: {start_time} → {end_time}")
    
    response = groww_client.get_historical_candle_data(
        trading_symbol="NIFTY",
        exchange=groww_client.EXCHANGE_NSE,
        segment=groww_client.SEGMENT_CASH,
        start_time=start_time,
        end_time=end_time,
        interval_in_minutes=5
    )
    
    # Parse the candle array format: [timestamp_epoch, open, high, low, close, volume]
    candles = response.get('candles', [])
    if not candles:
        print("WARNING: No candles returned from Groww API")
        return pd.DataFrame()
    
    df = pd.DataFrame(candles, columns=['timestamp', 'Open', 'High', 'Low', 'Close', 'Volume'])
    
    # Convert epoch seconds to IST datetime
    df['Datetime'] = pd.to_datetime(df['timestamp'], unit='s', utc=True).dt.tz_convert(IST).dt.tz_localize(None)
    df['date'] = df['Datetime'].dt.date
    df = df.drop(columns=['timestamp'])
    df = df.sort_values('Datetime').reset_index(drop=True)
    
    # Filter to only market hours (9:15 AM to 3:30 PM IST)
    df = df[df['Datetime'].dt.time >= dtime(9, 15)]
    df = df[df['Datetime'].dt.time <= dtime(15, 30)]
    
    print(f"Fetched {len(df)} candles across {df['date'].nunique()} trading days")
    return df


def get_live_price(groww_client):
    """
    Fetch the current live last traded price of Nifty 50.
    Used to display real-time price on the dashboard between candle refreshes.
    
    Returns:
    --------
    float or None
        Current LTP of Nifty, or None if fetch failed
    """
    try:
        response = groww_client.get_ltp(
            segment=groww_client.SEGMENT_CASH,
            exchange_trading_symbols="NSE_NIFTY"
        )
        return response.get("NSE_NIFTY")
    except Exception as e:
        print(f"LTP fetch failed: {e}")
        return None


def prepare_live_indicators(df):
    """
    Compute all strategy indicators on the live candle DataFrame.
    
    This reuses the exact same logic as the backtester's indicators.py
    to ensure live signals are computed identically to backtest signals.
    No lookahead bias is possible here since we're processing real data
    that has already occurred candle by candle.
    
    Indicators computed:
    - EMA9, EMA21, EMA50 (exponential moving averages of Close)
    - VWAP proxy (cumulative typical price average, resets each day)
    - prev_close (previous candle's close, within same day only)
    
    Returns:
    --------
    pd.DataFrame
        Input DataFrame with indicator columns added
    """
    df = df.copy()
    
    # EMA calculations (cross-day — EMAs don't reset daily, they carry over)
    df['ema9']  = df['Close'].ewm(span=9,  adjust=False).mean()
    df['ema21'] = df['Close'].ewm(span=21, adjust=False).mean()
    df['ema50'] = df['Close'].ewm(span=50, adjust=False).mean()
    
    # VWAP proxy (resets each day)
    df['typical_price'] = (df['High'] + df['Low'] + df['Close']) / 3
    df['vwap'] = (
        df.groupby('date')['typical_price']
        .expanding()
        .mean()
        .reset_index(level=0, drop=True)
    )
    
    # prev_close within same day (no cross-day contamination)
    df['prev_close'] = df.groupby('date')['Close'].shift(1)
    
    return df


def get_daily_regime(groww_client):
    """
    Fetch daily Nifty closing prices and compute the 5-day SMA regime filter.
    
    Uses Groww's historical API at 1-day interval (full history available)
    to compute the same daily regime filter used in the backtest.
    
    Returns:
    --------
    str
        'uptrend'   → long signals allowed today
        'downtrend' → short signals allowed today  
        'neutral'   → no trading today (choppy market)
    """
    try:
        now_ist = datetime.now(IST)
        end_time = now_ist.strftime("%Y-%m-%d %H:%M:%S")
        # Fetch last 30 days of daily data — plenty for a 5-day SMA
        start_time = (now_ist - timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")
        
        response = groww_client.get_historical_candle_data(
            trading_symbol="NIFTY",
            exchange=groww_client.EXCHANGE_NSE,
            segment=groww_client.SEGMENT_CASH,
            start_time=start_time,
            end_time=end_time,
            interval_in_minutes=1440  # 1440 minutes = 1 day
        )
        
        candles = response.get('candles', [])
        if len(candles) < 7:
            return 'neutral'  # Insufficient data
        
        closes = [c[4] for c in candles]  # Close price is index 4
        
        # Compute 5-day SMA for last few days
        if len(closes) < 5:
            return 'neutral'
        
        sma_today     = sum(closes[-5:]) / 5
        sma_two_ago   = sum(closes[-7:-2]) / 5
        
        slope_pct = (sma_today - sma_two_ago) / sma_two_ago * 100
        
        if slope_pct > 0.05:
            return 'uptrend'
        elif slope_pct < -0.05:
            return 'downtrend'
        else:
            return 'neutral'
    
    except Exception as e:
        print(f"Regime computation failed: {e}")
        return 'neutral'


def is_trading_window(hour, minute):
    """Check if current time is within one of the trading windows."""
    current_time = dtime(hour, minute)
    morning_start = dtime(9, 30)
    morning_end = dtime(11, 30)
    afternoon_start = dtime(14, 0)
    afternoon_end = dtime(15, 10)
    
    return (morning_start <= current_time <= morning_end) or \
           (afternoon_start <= current_time <= afternoon_end)


def evaluate_signal(df, params, regime):
    """
    Evaluate the strategy conditions on the most recent completed candle
    and return the current signal.
    
    We evaluate on the LAST COMPLETED candle (second-to-last row if market
    is open, last row if market just closed). The current live candle is
    still forming and should not be used for entry decisions.
    
    Parameters:
    -----------
    df : pd.DataFrame
        Prepared DataFrame with all indicators
    params : dict
        Strategy parameters (same as backtest params)
    regime : str
        Current daily regime ('uptrend', 'downtrend', 'neutral')
    
    Returns:
    --------
    dict
        {
          'signal':       'LONG' | 'SHORT' | 'WAIT' | 'OFF',
          'reason':       str explaining why this signal was generated,
          'candle_time':  datetime of the evaluated candle,
          'entry_price':  float (suggested entry = last candle's close),
          'stop_loss':    float,
          'target':       float,
          'indicators':   dict of current indicator values for display
        }
    """
    if df.empty or len(df) < 51:
        return {
            'signal': 'WAIT',
            'reason': 'Insufficient candle data for indicator computation',
            'candle_time': None,
            'entry_price': None,
            'stop_loss': None,
            'target': None,
            'indicators': {}
        }
    
    # Use the last COMPLETED candle
    row = df.iloc[-1]
    candle_time = row['Datetime']
    
    # Build indicator snapshot for display
    indicators = {
        'close':    round(row['Close'], 2),
        'vwap':     round(row['vwap'], 2),
        'ema9':     round(row['ema9'], 2),
        'ema21':    round(row['ema21'], 2),
        'ema50':    round(row['ema50'], 2),
        'prev_close': round(row['prev_close'], 2) if not pd.isna(row['prev_close']) else None
    }
    
    # Check regime first
    if regime == 'neutral':
        return {
            'signal': 'OFF',
            'reason': 'Daily regime filter: market is in neutral/choppy mode. Strategy inactive today.',
            'candle_time': candle_time,
            'entry_price': row['Close'],
            'stop_loss': None,
            'target': None,
            'indicators': indicators,
            'conditions': {}
        }
    
    # Check trading window
    hour   = candle_time.hour
    minute = candle_time.minute
    if not is_trading_window(hour, minute):
        return {
            'signal': 'WAIT',
            'reason': f'Outside trading window. Valid windows: 9:30–11:30 AM and 2:00–3:10 PM IST.',
            'candle_time': candle_time,
            'entry_price': row['Close'],
            'stop_loss': None,
            'target': None,
            'indicators': indicators,
            'conditions': {}
        }
    
    # Check for NaN indicators
    if any(pd.isna([row['vwap'], row['ema9'], row['ema21'], row['ema50']])):
        return {
            'signal': 'WAIT',
            'reason': 'Indicator values not yet stable (NaN). Wait for more candles.',
            'candle_time': candle_time,
            'entry_price': row['Close'],
            'stop_loss': None,
            'target': None,
            'indicators': indicators,
            'conditions': {}
        }
    
    sl  = params['stop_loss_points']
    rr  = params['rr_ratio']
    pct = params['ema_pullback_pct']
    
    upper_band = row['ema21'] * (1 + pct / 100)
    lower_band = row['ema21'] * (1 - pct / 100)
    in_band    = lower_band <= row['Close'] <= upper_band
    
    prev_close_valid = not pd.isna(row['prev_close'])
    
    def normalize_bool_conditions(cond_dict):
        return {k: bool(v) for k, v in cond_dict.items()}
    
    # ── LONG SIGNAL CHECK ────────────────────────────────────────────────────
    if regime == 'uptrend':
        long_conditions = normalize_bool_conditions({
            'Above VWAP':        row['Close'] > row['vwap'],
            'EMA9 > EMA21':      row['ema9']  > row['ema21'],
            'Above EMA50':       row['Close'] > row['ema50'],
            'In EMA21 band':     in_band,
            'Candle bouncing':   prev_close_valid and row['Close'] >= row['prev_close'],
        })
        
        if all(long_conditions.values()):
            entry = row['Close']
            return {
                'signal': 'LONG',
                'reason': 'All long conditions met: price above VWAP, EMA9>EMA21, above EMA50, pulled back to EMA21, candle bouncing up.',
                'candle_time': candle_time,
                'entry_price': round(entry, 2),
                'stop_loss':   round(entry - sl, 2),
                'target':      round(entry + sl * rr, 2),
                'indicators':  indicators,
                'conditions':  long_conditions
            }
        else:
            failed = [k for k, v in long_conditions.items() if not v]
            return {
                'signal': 'WAIT',
                'reason': f'Uptrend regime but long conditions not met. Failing: {", ".join(failed)}',
                'candle_time': candle_time,
                'entry_price': row['Close'],
                'stop_loss': None,
                'target': None,
                'indicators': indicators,
                'conditions': long_conditions
            }
    
    # ── SHORT SIGNAL CHECK ───────────────────────────────────────────────────
    if regime == 'downtrend':
        short_conditions = normalize_bool_conditions({
            'Below VWAP':        row['Close'] < row['vwap'],
            'EMA9 < EMA21':      row['ema9']  < row['ema21'],
            'Below EMA50':       row['Close'] < row['ema50'],
            'In EMA21 band':     in_band,
            'Candle dropping':   prev_close_valid and row['Close'] <= row['prev_close'],
        })
        
        if all(short_conditions.values()):
            entry = row['Close']
            return {
                'signal': 'SHORT',
                'reason': 'All short conditions met: price below VWAP, EMA9<EMA21, below EMA50, pulled back to EMA21, candle dropping.',
                'candle_time': candle_time,
                'entry_price': round(entry, 2),
                'stop_loss':   round(entry + sl, 2),
                'target':      round(entry - sl * rr, 2),
                'indicators':  indicators,
                'conditions':  short_conditions
            }
        else:
            failed = [k for k, v in short_conditions.items() if not v]
            return {
                'signal': 'WAIT',
                'reason': f'Downtrend regime but short conditions not met. Failing: {", ".join(failed)}',
                'candle_time': candle_time,
                'entry_price': row['Close'],
                'stop_loss': None,
                'target': None,
                'indicators': indicators,
                'conditions': short_conditions
            }
    
    return {
        'signal': 'WAIT',
        'reason': 'No conditions matched.',
        'candle_time': candle_time,
        'entry_price': row['Close'],
        'stop_loss': None,
        'target': None,
        'indicators': indicators,
        'conditions': {}
    }


def is_market_open():
    """
    Check if NSE is currently open for trading.
    Market hours: Monday–Friday, 9:15 AM – 3:30 PM IST.
    Does not account for exchange holidays (add holiday list if needed).
    """
    now = datetime.now(IST)
    if now.weekday() >= 5:  # Saturday=5, Sunday=6
        return False
    market_open  = now.replace(hour=9,  minute=15, second=0, microsecond=0)
    market_close = now.replace(hour=15, minute=30, second=0, microsecond=0)
    return market_open <= now <= market_close
