# Render Deployment Guide

This guide explains how to deploy the Nifty 50 VWAP + EMA Scalping Backtester to Render.com for permanent public URLs accessible from any device.

## 🚀 Quick Deploy

### 1. Fork/Clone Repository
```bash
git clone https://github.com/Anurag-anonymous/nifty-backtester.git
cd nifty-backtester
```

### 2. Create Render Account
- Go to [render.com](https://render.com) and sign up for a free account
- Connect your GitHub account

### 3. Deploy Services

#### Option A: Manual Deployment (Recommended for first time)
1. **Backtester Service**:
   - Click "New" → "Web Service"
   - Connect your GitHub repo
   - Set service name: `nifty-backtester`
   - Runtime: `Python 3`
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `gunicorn --bind 0.0.0.0:$PORT app_cloud:app`
   - Environment: `Free` tier
   - Click "Create Web Service"

2. **Options Tool Service**:
   - Click "New" → "Web Service"
   - Connect the same GitHub repo
   - Set service name: `nifty-options`
   - Runtime: `Python 3`
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `gunicorn --bind 0.0.0.0:$PORT options_app:app`
   - Environment: `Free` tier
   - Click "Create Web Service"

#### Option B: Blueprint Deployment (Automated)
1. Click "New" → "Blueprint"
2. Connect your GitHub repo
3. Render will automatically detect `render.yaml` and create both services
4. Set environment variables if needed

### 4. Configure Environment Variables
For each service, add these environment variables:
- `BACKTESTER_URL`: URL of the backtester service (e.g., `https://nifty-backtester.onrender.com`)
- `OPTIONS_URL`: URL of the options service (e.g., `https://nifty-options.onrender.com`)

### 5. Access Your Apps
- **Backtester**: `https://nifty-backtester.onrender.com`
- **Options Tool**: `https://nifty-options.onrender.com`

## 📱 Mobile Access

The apps are now mobile-responsive! Access them from:
- **Android**: Chrome/Samsung Internet browsers
- **iPhone**: Safari/Chrome browsers
- **PC**: Any modern browser

## ⚠️ Important Notes

### Ephemeral Storage
- Render's free tier has **ephemeral storage** - data resets on redeploy
- Paper trades and cached data will be lost on app restarts
- Use "Export Trades" feature to save your trading history locally

### TradingView Data
- TradingView data fetching requires `tvdatafeed` library (not available on Render)
- On cloud: Use CSV upload or "Refresh Data" (uses yfinance)
- Locally: Full TradingView integration available

### Free Tier Limitations
- 750 hours/month free
- Sleeps after 15 minutes of inactivity
- Cold starts may take 10-30 seconds

## 🔧 Troubleshooting

### App Won't Start
- Check Render logs for Python errors
- Verify all dependencies in `requirements.txt`
- Ensure `app_cloud.py` and `options_app.py` exist

### Data Not Loading
- Use "Refresh Data" button (uses yfinance)
- Upload CSV files for historical data
- Check browser console for errors

### Mobile Issues
- Ensure viewport meta tag is present
- Test on different browsers
- Check for touch event conflicts

## 📊 Features

✅ **Cloud-Ready**: Works on Render's free tier
✅ **Mobile-Responsive**: Optimized for phones/tablets
✅ **Cross-App Navigation**: Easy switching between tools
✅ **Ephemeral Storage Warnings**: Clear user notifications
✅ **Optional Dependencies**: Graceful fallback when libraries unavailable
✅ **Production-Ready**: Gunicorn WSGI server, pinned dependencies

## 🎯 Next Steps

1. Test both apps on Render
2. Verify mobile access from your phone
3. Export paper trades regularly (data resets on redeploy)
4. Consider upgrading to paid tier for persistent storage

## 📞 Support

If you encounter issues:
1. Check Render service logs
2. Verify GitHub repository is up to date
3. Test locally first: `python app_cloud.py`
4. Check browser developer console for errors

---

**Happy Trading! 📈**