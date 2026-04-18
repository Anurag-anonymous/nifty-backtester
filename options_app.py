"""
Options Tool - Nifty Weekly Options Paper Trading Assistant.
Runs on http://localhost:5001

Start with: python options_app.py

This is a separate Flask app from the main backtester (port 5000).
Both can run simultaneously in different terminal windows.
"""

from flask import Flask, render_template, request, jsonify
import traceback
import os
from datetime import datetime

app = Flask(__name__, template_folder='templates', static_folder='static')

# Ensure writable paper trade directory exists on startup
if os.environ.get('RENDER') or os.environ.get('FLASK_ENV') == 'production':
    os.makedirs(os.path.join('/tmp', 'data'), exist_ok=True)
else:
    os.makedirs(os.path.join(os.path.dirname(__file__), 'data'), exist_ok=True)


@app.route('/')
def index():
    """Serve the options dashboard UI."""
    return render_template('options.html')


@app.route('/api/config', methods=['GET'])
def api_config():
    """Return service URLs for cross-navigation between backtester and options UI."""
    return jsonify({
        'backtester_url': os.environ.get('BACKTESTER_URL', 'http://localhost:5000'),
        'options_url': os.environ.get('OPTIONS_URL', request.host_url.rstrip('/'))
    })


@app.route('/api/options-signal', methods=['POST'])
def get_options_signal():
    """
    Fetch live Nifty signal + identify the best option to buy.
    
    Request body:
    {
      "api_token": str,
      "budget_min": 3000,   (optional, default 3000)
      "budget_max": 7500    (optional, default 7500)
    }
    
    Response:
    {
      "underlying_signal": "LONG" | "SHORT" | "WAIT" | "OFF",
      "regime": str,
      "nifty_price": float,
      "signal_reason": str,
      "recommended_option": { ...option details... } or null,
      "has_open_trade": bool,
      "last_updated": str
    }
    """
    try:
        from growwapi import GrowwAPI
        from live_engine import (
            get_nifty_candles, prepare_live_indicators,
            get_daily_regime, evaluate_signal, get_live_price
        )
        from options_engine import select_option
        from options_tracker import get_open_trade
        from backtest import DEFAULT_PARAMS

        data      = request.get_json()
        api_token = data.get('api_token', '').strip()

        if not api_token:
            return jsonify({'error': 'Groww API token required'}), 400

        budget_min = float(data.get('budget_min', 3000))
        budget_max = float(data.get('budget_max', 7500))

        groww  = GrowwAPI(api_token)
        df     = get_nifty_candles(groww, lookback_days=10)
        regime = get_daily_regime(groww)
        ltp    = get_live_price(groww)

        if df.empty:
            return jsonify({'error': 'No candle data received'}), 500

        df_ind = prepare_live_indicators(df)

        params = {
            'stop_loss_points': DEFAULT_PARAMS['stop_loss_points'],
            'rr_ratio':         DEFAULT_PARAMS['rr_ratio'],
            'ema_pullback_pct': DEFAULT_PARAMS['ema_pullback_pct'],
        }

        signal_result = evaluate_signal(df_ind, params, regime)
        signal        = signal_result['signal']

        # Find recommended option only for actionable signals
        recommended = None
        if signal in ('LONG', 'SHORT') and ltp:
            recommended = select_option(
                groww, signal, ltp, budget_min, budget_max
            )

        return jsonify({
            'underlying_signal':  signal,
            'regime':             regime,
            'nifty_price':        ltp,
            'signal_reason':      signal_result.get('reason', ''),
            'candle_time':        str(signal_result.get('candle_time', '')),
            'indicators':         signal_result.get('indicators', {}),
            'conditions':         signal_result.get('conditions', {}),
            'recommended_option': recommended,
            'has_open_trade':     get_open_trade() is not None,
            'last_updated':       datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })

    except Exception as e:
        print(f"Error in options-signal: {str(e)}")
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500


@app.route('/api/paper-trade/open', methods=['POST'])
def open_paper_trade():
    """
    Log a paper trade entry.
    
    Request body:
    {
      "option_details": { ...from recommended_option... },
      "signal_direction": "LONG" | "SHORT",
      "nifty_price": float
    }
    """
    try:
        from options_tracker import add_trade
        data = request.get_json()
        trade_id = add_trade(
            data['option_details'],
            data['signal_direction'],
            data['nifty_price']
        )
        if trade_id:
            return jsonify({'success': True, 'trade_id': trade_id})
        return jsonify({'success': False, 'error': 'Open trade already exists'}), 400
    except Exception as e:
        print(f"Error opening paper trade: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/paper-trade/close', methods=['POST'])
def close_paper_trade():
    """
    Close an open paper trade with exit details.
    
    Request body:
    {
      "trade_id": str,
      "exit_premium": float,
      "exit_reason": str
    }
    """
    try:
        from options_tracker import close_trade
        data   = request.get_json()
        result = close_trade(
            data['trade_id'],
            float(data['exit_premium']),
            data['exit_reason']
        )
        return jsonify(result)
    except Exception as e:
        print(f"Error closing paper trade: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/paper-trade/status', methods=['POST'])
def paper_trade_status():
    """
    Get current status of open trade including live P&L.
    
    Request body: { "api_token": str }
    """
    try:
        from growwapi import GrowwAPI
        from options_engine import get_option_live_price, check_exit_conditions
        from options_tracker import get_open_trade

        data      = request.get_json()
        api_token = data.get('api_token', '').strip()
        trade     = get_open_trade()

        if not trade:
            return jsonify({'has_open_trade': False})

        current_premium = None
        exit_check      = None

        if api_token:
            try:
                groww           = GrowwAPI(api_token)
                current_premium = get_option_live_price(groww, trade['trading_symbol'])
                if current_premium:
                    exit_check = check_exit_conditions(
                        float(trade['entry_premium']),
                        current_premium,
                        float(trade['target_premium']),
                        float(trade['stop_premium'])
                    )
            except Exception as e:
                print(f"Live price fetch failed: {e}")

        return jsonify({
            'has_open_trade':   True,
            'trade':            trade,
            'current_premium':  current_premium,
            'exit_check':       exit_check
        })

    except Exception as e:
        print(f"Error checking paper trade status: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/paper-trade/summary', methods=['GET'])
def paper_trade_summary():
    """Get summary stats and full trade log."""
    try:
        from options_tracker import get_trade_summary, load_trades
        summary = get_trade_summary()
        trades  = load_trades().to_dict(orient='records')
        return jsonify({'summary': summary, 'trades': trades})
    except Exception as e:
        print(f"Error getting trade summary: {str(e)}")
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    print("=" * 60)
    print("🎯 Nifty Options Paper Trading Tool")
    print("=" * 60)
    print(f"Options Tool: http://localhost:5001")
    print(f"Backtester:  http://localhost:5000 (run in separate terminal)")
    print(f"Start both:  python start_all.py")
    print("=" * 60)
    print("\nPress Ctrl+C to stop.\n")
    
    app.run(debug=True, port=5001, host='127.0.0.1')
