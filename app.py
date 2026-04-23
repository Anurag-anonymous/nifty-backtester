"""
Flask Web Application - Nifty 50 VWAP + EMA Scalp Backtester

Serves a web dashboard for configuring and running backtests on the
VWAP + EMA scalping strategy. Provides API endpoints for data status,
running backtests, and refreshing cached data.

Usage:
    python app.py
    
Then open http://localhost:5000 in your browser.
"""

from flask import Flask, render_template, jsonify, request
import traceback
import json
from io import StringIO
import csv
import os
from datetime import datetime

from data_loader import fetch_data, get_data_status, ensure_data_directory, fetch_data_from_tradingview, load_latest_data
from indicators import prepare_data
from backtest import run_backtest, DEFAULT_PARAMS
from metrics import compute_metrics, get_equity_curve, get_monthly_pnl, get_trade_log

app = Flask(__name__, template_folder='templates', static_folder='static')

# Ensure writable data directory exists on startup
ensure_data_directory()

# Global cache for last backtest results (to support CSV download)
last_backtest_trades = None


@app.route('/')
def index():
    """Serve the main dashboard HTML."""
    return render_template('index.html')


@app.route('/api/config', methods=['GET'])
def api_config():
    """Return service URLs for cross-navigation between backtester and options UI."""
    return jsonify({
        'backtester_url': os.environ.get('BACKTESTER_URL', request.host_url.rstrip('/')),
        'options_url': os.environ.get('OPTIONS_URL', 'http://localhost:5001')
    })


@app.route('/api/data-status', methods=['GET'])
def api_data_status():
    """
    Get cached data status without running a backtest.
    
    Returns JSON:
    {
        'data_exists': bool,
        'date_range': [start_date, end_date] or null,
        'trading_days': int,
        'default_params': dict
    }
    """
    try:
        status = get_data_status()
        
        # Convert tuple to list for JSON serialization
        if status['date_range']:
            status['date_range'] = list(status['date_range'])
        
        # Include default parameters for frontend
        status['default_params'] = {
            'stop_loss_points': DEFAULT_PARAMS['stop_loss_points'],
            'rr_ratio': DEFAULT_PARAMS['rr_ratio'],
            'ema_pullback_pct': DEFAULT_PARAMS['ema_pullback_pct'],
            'max_trades_per_day': DEFAULT_PARAMS['max_trades_per_day'],
            'daily_loss_limit_pct': DEFAULT_PARAMS['daily_loss_limit_pct'],
            'initial_capital': DEFAULT_PARAMS['initial_capital'],
            'lot_size': DEFAULT_PARAMS['lot_size'],
            'brokerage_per_trade': DEFAULT_PARAMS['brokerage_per_trade']
        }
        
        return jsonify(status), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/run-backtest', methods=['POST'])
def api_run_backtest():
    """
    Run a backtest with the provided parameters.
    
    Expected JSON body:
    {
        'stop_loss_points': float,
        'rr_ratio': float,
        'ema_pullback_pct': float,
        'max_trades_per_day': int,
        'daily_loss_limit_pct': float,
        'initial_capital': float,
        'lot_size': int,
        'brokerage_per_trade': float,
        'regime_sma_period': int,
        'end_date': str (optional) - format: 'YYYY-MM-DD'
    }
    
    Returns JSON:
    {
        'metrics': {...},
        'equity_curve': [[timestamp, capital], ...],
        'trades': [...],
        'daily_summary': [...],
        'monthly_pnl': {...}
    }
    """
    global last_backtest_trades
    
    try:
        # Parse request parameters
        params = request.get_json()
        
        # Validate required keys exist
        required_keys = [
            'stop_loss_points', 'rr_ratio', 'ema_pullback_pct',
            'max_trades_per_day', 'daily_loss_limit_pct', 'initial_capital',
            'lot_size', 'brokerage_per_trade', 'regime_sma_period'
        ]
        for key in required_keys:
            if key not in params:
                return jsonify({'error': f'Missing parameter: {key}'}), 400
        
        # Extract optional end_date for custom date range
        end_date = params.get('end_date', None)
        if end_date and end_date.strip() == '':
            end_date = None
        
        # Try to load latest available data (TradingView first, then yfinance)
        try:
            print(f"\nLoading latest available data...")
            df = load_latest_data()
        except ValueError:
            # If no TradingView data, try fetching from yfinance
            print(f"\nNo TradingView data found. Fetching from yfinance...")
            if end_date:
                print(f"Fetching data for custom date range ending {end_date}...")
                df = fetch_data(period="60d", interval="5m", force_refresh=False, end_date=end_date)
            else:
                print(f"Fetching data (last 60 days from today)...")
                df = fetch_data(period="60d", interval="5m", force_refresh=False)
        
        if len(df) == 0:
            return jsonify({'error': 'No data available. Please try refreshing data.'}), 400
        
        # Prepare with indicators
        print(f"Preparing indicators...")
        df_prepared = prepare_data(df)
        
        # Run backtest
        print(f"Running backtest...")
        trades_df, daily_summary_df = run_backtest(df_prepared, **params)
        
        # Compute metrics
        print(f"Computing metrics...")
        metrics = compute_metrics(trades_df, params['initial_capital'])
        
        # Get visualizations data
        equity_curve = get_equity_curve(trades_df, params['initial_capital'])
        monthly_pnl = get_monthly_pnl(trades_df)
        trade_log = get_trade_log(trades_df)
        
        # Cache trades for CSV download
        last_backtest_trades = trades_df
        
        # Convert DataFrames to JSON-serializable format
        daily_summary = daily_summary_df.to_dict('records') if len(daily_summary_df) > 0 else []
        for record in daily_summary:
            record['date'] = str(record['date'])
        
        response = {
            'metrics': metrics,
            'equity_curve': equity_curve,
            'trades': trade_log,
            'daily_summary': daily_summary,
            'monthly_pnl': monthly_pnl
        }
        
        print(f"Backtest completed successfully")
        return jsonify(response), 200
        
    except Exception as e:
        print(f"Error in backtest: {str(e)}")
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500


@app.route('/api/refresh-data', methods=['POST'])
def api_refresh_data():
    """
    Force re-download of data from yfinance.
    
    Expected JSON body (optional):
    {
        'end_date': str (optional) - format: 'YYYY-MM-DD'
    }
    
    Returns JSON:
    {
        'success': bool,
        'data_exists': bool,
        'date_range': [start_date, end_date],
        'trading_days': int
    }
    """
    try:
        # Extract optional end_date
        request_data = request.get_json() or {}
        end_date = request_data.get('end_date', None)
        if end_date and end_date.strip() == '':
            end_date = None
        
        if end_date:
            print(f"\nForcing data refresh for custom date range ending {end_date}...")
            df = fetch_data(period="60d", interval="5m", force_refresh=True, end_date=end_date)
        else:
            print(f"\nForcing data refresh (last 60 days from today)...")
            df = fetch_data(period="60d", interval="5m", force_refresh=True)
        
        status = get_data_status()
        if status['date_range']:
            status['date_range'] = list(status['date_range'])
        
        status['success'] = True
        return jsonify(status), 200
        
    except Exception as e:
        print(f"Error refreshing data: {str(e)}")
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500


@app.route('/api/download-trades', methods=['GET'])
def api_download_trades():
    """
    Download last backtest trades as CSV.
    
    This endpoint returns the trades from the last run as CSV file.
    """
    global last_backtest_trades
    
    try:
        if last_backtest_trades is None or len(last_backtest_trades) == 0:
            return jsonify({'error': 'No trades to download. Run a backtest first.'}), 400
        
        # Create CSV content
        output = StringIO()
        trades = last_backtest_trades.copy()
        
        # Format columns for export
        trades['date'] = trades['date'].astype(str)
        trades['entry_time'] = trades['entry_time'].astype(str)
        trades['exit_time'] = trades['exit_time'].astype(str)
        
        trades.to_csv(output, index=False)
        
        csv_content = output.getvalue()
        
        return csv_content, 200, {
            'Content-Type': 'text/csv',
            'Content-Disposition': 'attachment; filename=nifty_backtest_trades.csv'
        }
        
    except Exception as e:
        print(f"Error downloading trades: {str(e)}")
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500


@app.route('/api/fetch-tradingview-data', methods=['POST'])
def api_fetch_tradingview_data():
    """
    Fetch data from TradingView using tvdatafeed.
    
    Expected JSON body:
    {
        'username': str (optional),
        'password': str (optional), 
        'n_bars': int (default: 500),
        'interval_minutes': int (default: 5)
    }
    
    Returns JSON:
    {
        'success': bool,
        'candles_count': int,
        'date_range': str,
        'file_path': str
    }
    """
    try:
        # Parse request parameters
        params = request.get_json()
        
        username = params.get('username')
        password = params.get('password')
        n_bars = params.get('n_bars', 500)
        interval_minutes = params.get('interval_minutes', 5)
        
        # Set environment variables if provided
        if username:
            os.environ['TV_USERNAME'] = username
        if password:
            os.environ['TV_PASSWORD'] = password
        
        # Fetch data using the data_loader function
        df = fetch_data_from_tradingview(
            n_bars=n_bars,
            interval_minutes=interval_minutes
        )
        
        if len(df) == 0:
            return jsonify({'error': 'No data received from TradingView'}), 400
        
        # Get data info
        candles_count = len(df)
        date_range = f"{df['date'].min()} to {df['date'].max()}"
        file_path = f"data/nifty_tv_{interval_minutes}m_{n_bars}bars.csv"
        
        response = {
            'success': True,
            'candles_count': candles_count,
            'date_range': date_range,
            'file_path': file_path
        }
        
        print(f"TradingView data fetch completed: {candles_count} candles")
        return jsonify(response), 200
        
    except Exception as e:
        print(f"Error fetching TradingView data: {str(e)}")
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500


@app.route('/api/upload-csv', methods=['POST'])
def api_upload_csv():
    """
    Upload custom CSV data (future feature).
    
    Expected CSV format:
    Datetime,Open,High,Low,Close,Volume
    2024-01-02 09:15:00,21500.5,21520.0,21490.0,21510.0,150000
    
    This is a placeholder for CSV upload functionality.
    """
    # TODO: Implement CSV upload parsing and validation
    return jsonify({'error': 'CSV upload not yet implemented'}), 501


@app.route('/api/live-signal', methods=['POST'])
def get_live_signal():
    """
    Fetch live Nifty data from Groww, compute indicators, and return
    the current strategy signal.
    
    Request body:
    {
      "api_token": "your_groww_api_token",
      "stop_loss_points": 65,
      "rr_ratio": 2.5,
      "ema_pullback_pct": 0.20
    }
    
    Response:
    {
      "signal": "LONG" | "SHORT" | "WAIT" | "OFF",
      "reason": "explanation string",
      "candle_time": "2026-04-06 10:35:00",
      "entry_price": 23150.5,
      "stop_loss": 23085.5,
      "target": 23280.5,
      "regime": "downtrend",
      "live_price": 23148.2,
      "market_open": true,
      "indicators": { "close": ..., "vwap": ..., "ema9": ..., ... },
      "conditions": { "Below VWAP": true, "EMA9 < EMA21": true, ... },
      "last_updated": "2026-04-06 10:37:22"
    }
    """
    try:
        from growwapi import GrowwAPI
        from live_engine import (
            get_nifty_candles, get_live_price, prepare_live_indicators,
            get_daily_regime, evaluate_signal, is_market_open
        )
        
        data = request.get_json()
        api_token = data.get('api_token', '').strip()
        
        if not api_token:
            return jsonify({'error': 'Groww API token is required'}), 400
        
        params = {
            'stop_loss_points': float(data.get('stop_loss_points', 65)),
            'rr_ratio':         float(data.get('rr_ratio', 2.5)),
            'ema_pullback_pct': float(data.get('ema_pullback_pct', 0.20)),
        }
        
        groww = GrowwAPI(api_token)
        
        # Fetch all data in parallel conceptually (sequentially here)
        df      = get_nifty_candles(groww, lookback_days=10)
        regime  = get_daily_regime(groww)
        ltp     = get_live_price(groww)
        
        if df.empty:
            return jsonify({'error': 'No candle data received from Groww'}), 500
        
        df_with_indicators = prepare_live_indicators(df)
        result = evaluate_signal(df_with_indicators, params, regime)
        
        # Format candle_time as string for JSON
        if result.get('candle_time') is not None:
            result['candle_time'] = str(result['candle_time'])
        
        result['regime']       = regime
        result['live_price']   = ltp
        result['market_open']  = is_market_open()
        result['last_updated'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        return jsonify(result)
    
    except Exception as e:
        print(f"Error in live signal: {str(e)}")
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500


@app.route('/api/live-status', methods=['GET'])
def get_live_status():
    """Simple health check — returns whether market is currently open."""
    from live_engine import is_market_open
    return jsonify({
        'market_open': is_market_open(),
        'server_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    })


if __name__ == '__main__':
    # Ensure data directory exists
    ensure_data_directory()
    
    print("=" * 60)
    print("Nifty 50 VWAP + EMA Scalp Backtester")
    print("=" * 60)
    print(f"\nStarting Flask server...")
    print(f"Open your browser to: http://localhost:5000")
    print(f"\nPress Ctrl+C to stop the server.")
    print("=" * 60)
    
    app.run(debug=True, host='127.0.0.1', port=5000)
