# Nifty 50 VWAP + EMA Scalping Backtester

A purpose-built Python + web dashboard application for backtesting a specific intraday scalping strategy on Nifty 50 3-minute data.

## ⚡ Quick Start

### 1. Installation

```bash
# Navigate to project directory
cd nifty_backtester

# Install dependencies
pip install yfinance pandas numpy flask plotly

# Run the app
python app.py
```

### 2. Open Dashboard

Once the server starts, open your browser to:
```
http://localhost:5000
```

You should see:
- A configuration panel at the top
- Data status banner showing available data
- Configure parameters and click "Run Backtest"
- View results in metrics cards and interactive charts

## 📊 Strategy Overview

### VWAP + 9/21 EMA Confluence Scalping

This backtester is designed for **one specific strategy only**:
- **Timeframe**: 3-minute candles on Nifty 50 (^NSEI)
- **Confluence**: VWAP + EMA(9) + EMA(21)
- **Trade times**: Morning (9:30–11:30 AM) and Afternoon (2:00–3:10 PM) IST
- **Goal**: Intraday scalping with stops at 20 points, 2:1 risk:reward

### Entry Rules

#### LONG Entry (when all below are true):
1. Within trading window (9:30–11:30 AM OR 2:00–3:10 PM IST)
2. Close price **ABOVE** VWAP
3. EMA9 **ABOVE** EMA21 (uptrend)
4. Close within 0.15% of EMA21 (pullback to EMA21)
5. No open trade for the day yet

#### SHORT Entry (when all below are true):
1. Within trading window (9:30–11:30 AM OR 2:00–3:10 PM IST)
2. Close price **BELOW** VWAP
3. EMA9 **BELOW** EMA21 (downtrend)
4. Close within 0.15% of EMA21 (pullback to EMA21)
5. No open trade for the day yet

### Exit Rules

- **Target**: Exit when price moves 2x the stop loss distance (2:1 RR)
- **Stop Loss**: Exit when stop level is hit (default: 20 points)
- **End of Day**: Close all trades at 3:15 PM at that candle's close price
- **Daily Loss Limit**: Stop trading if cumulative loss exceeds 2% of capital

## 🎮 Configuration Parameters

All parameters are adjustable in the dashboard:

| Parameter | Default | Description |
|-----------|---------|-------------|
| **Stop Loss (pts)** | 20 | Stop loss distance in index points |
| **R:R Ratio** | 2.0 | Reward:Risk ratio; target = SL × RR |
| **EMA Pullback %** | 0.15 | Proximity to EMA21 to qualify as pullback |
| **Max Trades/Day** | 3 | Maximum trades to allow per day |
| **Daily Loss Limit %** | 2.0 | Stop trading if day loss exceeds this % |
| **Initial Capital (₹)** | 500,000 | Starting capital for return calculations |
| **Lot Size** | 50 | Nifty lot size (for INR calculations) |
| **Brokerage/Trade (₹)** | 40 | Flat brokerage per trade (entry + exit) |

## 📈 Metrics Explained

Once backtest completes, you'll see:

### Performance Metrics

- **Win Rate %**: Percentage of profitable trades
  - *Target*: 50%+ for scalping strategies
  - *Good performance*: 55%–65%

- **Total Trades**: Number of trades executed in the test period
  
- **Profit Factor**: Gross Profit / Gross Loss
  - *Acceptable*: > 1.5
  - *Excellent*: > 2.0

- **Expectancy (pts)**: Average points per trade
  - Formula: (Win% × Avg Win) + (Loss% × Avg Loss)
  - *Positive expectancy* = profitable edge

- **Max Drawdown**: Worst peak-to-trough decline in capital
  - Expressed in both ₹ and %
  - *Lower is better*: Indicates strategy resilience

- **Total Return %**: Total profit as % of initial capital
  
- **Total P&L (₹)**: Total profit or loss in rupees
  
- **Sharpe Ratio**: Risk-adjusted return (annualized)
  - *> 1.0* = decent risk-adjusted performance
  - *> 2.0* = excellent

- **Avg Daily P&L**: Average daily profit/loss

## 📊 Dashboard Sections

### 1. Configuration Panel
At the top—adjust all strategy parameters and click **Run Backtest**.

### 2. Metrics Summary
Grid of metric cards showing key performance numbers. Color-coded:
- 🟢 Green = Positive values (good)
- 🔴 Red = Negative values (unfavorable)

### 3. Charts (4 Tabs)

#### Tab 1: Equity Curve
Line chart of running capital over all trades.
- Shaded green area = profit above initial capital
- Shaded red area = drawdown below peak
- Shows trend of strategy performance

#### Tab 2: Trade P&L Distribution
Histogram showing frequency of win/loss sizes.
- Green bars = winning trades
- Red bars = losing trades
- Helps identify consistency

#### Tab 3: Monthly P&L
Bar chart of total P&L per month.
- Green bars = profitable months
- Red bars = losing months
- Shows seasonal or consistency patterns

#### Tab 4: Trade Log
Detailed table of every trade executed:
- Entry time, direction, entry price
- Stop loss and target
- Exit price and exit reason
- P&L in points and rupees
- **Download as CSV** button for further analysis

## 💾 Data Management

### Automatic Caching
- Data is automatically downloaded from yfinance and cached as CSV
- Subsequent backtests load from cache (fast)
- Saves bandwidth and speeds up testing

### Data Limitations
**Important**: yfinance only provides **60 days of intraday data** (interval ≤ 1 hour).
- Current backtest: Uses last 60 days
- For longer history: Use broker APIs (e.g., Zerodha Kite) and upload CSV
- CSV upload feature coming soon

### Refresh Data
Click the **"🔄 Refresh Data"** button in the status banner to force a re-download from yfinance.

## 🛠️ Project Structure

```
nifty_backtester/
│
├── app.py                  # Flask web server
├── backtest.py             # Core backtesting engine (strategy logic)
├── data_loader.py          # Fetch & cache Nifty data from yfinance
├── indicators.py           # VWAP, EMA, Opening Range calculations
├── metrics.py              # Performance statistics
│
├── templates/
│   └── index.html          # Web dashboard UI
│
├── static/
│   └── style.css           # Dashboard styles
│
├── data/
│   └── (auto-created)      # CSV cache files stored here
│
└── README.md               # This file
```

## 🔧 Module Reference

### `data_loader.py`
Fetches Nifty 50 data from yfinance, caches locally as CSV.
- `fetch_data()` — Download or load cached data
- `get_data_status()` — Check cached data info
- Key: Handles timezone, zero-volume rows, daily grouping

### `indicators.py`
Computes technical indicators on the data.
- `add_ema()` — Exponential moving averages
- `add_vwap()` — VWAP (resets daily)
- `add_opening_range()` — Opening range high/low
- `prepare_data()` — Pipeline to compute all indicators

### `backtest.py`
Core backtesting loop; applies strategy rules and tracks trades.
- `run_backtest()` — Main function; iterates candles, executes trades
- `check_long_entry()` — Long entry condition checks
- `check_short_entry()` — Short entry condition checks
- `check_exit_conditions()` — Exit logic (target, stop, EOD)
- Returns: trades_df, daily_summary_df

### `metrics.py`
Computes performance stats from trade results.
- `compute_metrics()` — Returns dict with all metrics
- `get_equity_curve()` — Running capital for plotting
- `get_monthly_pnl()` — Monthly summary for visualization
- `get_trade_log()` — Formatted trades for table display

### `app.py`
Flask web server; serves dashboard and API endpoints.
- `GET /` — Serve dashboard HTML
- `GET /api/data-status` — Check cached data
- `POST /api/run-backtest` — Execute backtest with params
- `POST /api/refresh-data` — Re-download data
- `GET /api/download-trades` — CSV export

### `templates/index.html`
Single-page web dashboard.
- Configuration form
- Metrics cards
- Interactive Plotly charts
- Trade log table

### `static/style.css`
Dark theme styling for dashboard.
- Responsive design (mobile-friendly)
- Color-coded metrics (green = good, red = bad)
- Smooth animations and interactions

## 🎯 Tips for Using the Backtester

### 1. Start with Default Parameters
Run a backtest with default values first to understand baseline performance.

### 2. Adjust One Parameter at a Time
Change stop loss OR EMA pullback, observe impact. Understand cause-effect.

### 3. Focus on Profit Factor
Profit factor (> 1.5) is more reliable than win rate for strategy quality.

### 4. Check the Trade Log
Look at actual trades to understand when entry/exits happen.
- Are entries near support/resistance?
- Does EOD happen often (suggests tight stops)?

### 5. Monthly Breakdown
Look for consistency. Avoid strategies that win only in certain months.

### 6. Equity Curve Shape
- Smooth upward curve = good and consistent
- Jagged or declining curve = high variance or poor fit

## ⚠️ Important Notes

### Not for Live Trading
This backtester is **educational and testing only**. Do not use live with real money without:
1. Paper trading validation
2. Slippage and liquidity checks
3. Broker API integration
4. Risk management and position sizing review

### Backtesting Limitations
- **No slippage modeling** — Assumes entry/exit at exact prices
- **No liquidity checks** — Assumes enough volume to fill any size
- **No gaps** — Assumes you can enter/exit within 3-minute candle
- **Historical bias** — Past performance ≠ future results

### Data Quality
- Missing data days (market holidays) are skipped
- Zero-volume candles are dropped
- Ensure yfinance data accuracy (validate against your broker)

## 🚀 Future Enhancements

- [ ] CSV upload for custom data (beyond 60 days)
- [ ] Multiple timeframe analysis (1m, 5m, 15m)
- [ ] Strategy parameter optimization (grid search)
- [ ] Walk-forward analysis
- [ ] Monte Carlo simulation
- [ ] P&L by entry/exit time heatmap

## 📝 License

Educational use only. Use at your own risk. No guarantees on profitability.

## 💬 Questions?

Refer to the code comments—they explain the WHY behind each decision, especially in the strategy logic (`backtest.py`).

---

**Happy Backtesting! 📈**
