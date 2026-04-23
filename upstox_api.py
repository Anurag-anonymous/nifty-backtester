"""
Upstox API Integration - Real-time Nifty 50 market data via WebSocket.

This module connects to Upstox's WebSocket feed to get live market data
for Nifty 50, replacing the Groww API for cloud deployment.

API Reference: https://upstox.com/developer/api-documentation/v3/get-market-data-feed
Instrument Key for Nifty 50: NSE_INDEX|Nifty 50
"""

import requests
import json
import os
from datetime import datetime
import time


# ============================================================================
# CONFIGURATION - UPSTOX API DETAILS
# ============================================================================

UPSTOX_API_BASE = "https://api.upstox.com"
UPSTOX_API_KEY = os.getenv("UPSTOX_API_KEY", "")
UPSTOX_API_SECRET = os.getenv("UPSTOX_API_SECRET", "")
UPSTOX_REDIRECT_URI = os.getenv("UPSTOX_REDIRECT_URI", "http://localhost:5000/upstox-callback")

# Nifty 50 instrument key
NIFTY_INSTRUMENT_KEY = "NSE_INDEX|Nifty 50"


def get_upstox_auth_url():
    """
    Generate the OAuth2 authorization URL for Upstox.
    
    User must open this URL in browser and authorize the app to access their account.
    After authorization, user will be redirected with an auth code.
    
    Returns:
    --------
    str
        Authorization URL to open in browser
    """
    params = {
        "client_id": UPSTOX_API_KEY,
        "redirect_uri": UPSTOX_REDIRECT_URI,
        "response_type": "code",
        "scope": "full_access"
    }
    
    auth_url = f"{UPSTOX_API_BASE}/v2/login/authorization/dialog"
    query_string = "&".join([f"{k}={v}" for k, v in params.items()])
    return f"{auth_url}?{query_string}"


def exchange_auth_code_for_token(auth_code):
    """
    Exchange authorization code for access token.
    
    Parameters:
    -----------
    auth_code : str
        Authorization code received after user authorizes the app
    
    Returns:
    --------
    dict
        Response with 'access_token' key
    
    Raises:
    -------
    ValueError
        If token exchange fails
    """
    url = f"{UPSTOX_API_BASE}/v2/login/authorization/token"
    
    payload = {
        "code": auth_code,
        "client_id": UPSTOX_API_KEY,
        "client_secret": UPSTOX_API_SECRET,
        "redirect_uri": UPSTOX_REDIRECT_URI,
        "grant_type": "authorization_code"
    }
    
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        data = response.json()
        
        if "data" in data:
            return data["data"].get("access_token")
        return data.get("access_token")
    except Exception as e:
        raise ValueError(f"Failed to exchange auth code for token: {e}")


def get_market_feed_url(access_token):
    """
    Get the WebSocket feed URL by authenticating with access token.
    
    This makes an HTTP request to get the WebSocket URL that will
    accept the authenticated WebSocket connection.
    
    Parameters:
    -----------
    access_token : str
        Bearer token from Upstox authentication
    
    Returns:
    --------
    str
        WebSocket URL to connect to (wss://...)
    
    Raises:
    -------
    ValueError
        If feed URL fetch fails
    """
    url = f"{UPSTOX_API_BASE}/v3/feed/market-data-feed"
    
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "*/*"
    }
    
    try:
        response = requests.get(url, headers=headers, allow_redirects=False)
        
        # Upstox returns a 302 redirect to the WebSocket URL
        if response.status_code == 302:
            return response.headers.get("location")
        
        # If not a redirect, try parsing JSON response
        if response.status_code == 200:
            data = response.json()
            if "data" in data and "authorizedRedirectUrl" in data["data"]:
                return data["data"]["authorizedRedirectUrl"]
        
        raise ValueError(f"Unexpected response: {response.status_code}")
    except Exception as e:
        raise ValueError(f"Failed to get market feed URL: {e}")


def format_subscribe_message(instrument_keys, mode="ltpc"):
    """
    Format a WebSocket subscription message for Upstox.
    
    Parameters:
    -----------
    instrument_keys : list
        List of instrument keys (e.g., ["NSE_INDEX|Nifty 50"])
    mode : str
        Data mode: "ltpc" (latest trade price + close), "full", "full_d30", "option_greeks"
    
    Returns:
    --------
    dict
        Message to send via WebSocket
    """
    import uuid
    
    return {
        "guid": str(uuid.uuid4()),
        "method": "sub",
        "data": {
            "mode": mode,
            "instrumentKeys": instrument_keys
        }
    }


def parse_market_feed(message):
    """
    Parse incoming WebSocket feed message from Upstox.
    
    Messages are JSON-encoded and may contain:
    - market_info: Status of market segments
    - live_feed: Price updates for subscribed instruments
    
    Parameters:
    -----------
    message : str or bytes
        WebSocket message (JSON text)
    
    Returns:
    --------
    dict
        Parsed message, or empty dict if parse fails
    """
    try:
        if isinstance(message, bytes):
            message = message.decode('utf-8')
        
        data = json.loads(message)
        return data
    except Exception as e:
        print(f"Failed to parse market feed: {e}")
        return {}


def extract_ltp(feed_message):
    """
    Extract Nifty LTP (Last Traded Price) from a live feed message.
    
    Parameters:
    -----------
    feed_message : dict
        Parsed message from Upstox WebSocket
    
    Returns:
    --------
    float or None
        Latest trading price of Nifty, or None if not in message
    """
    try:
        if feed_message.get("type") == "live_feed":
            feeds = feed_message.get("feeds", {})
            nifty_data = feeds.get(NIFTY_INSTRUMENT_KEY, {})
            ltpc = nifty_data.get("ltpc", {})
            return float(ltpc.get("ltp"))
    except Exception as e:
        print(f"Failed to extract LTP: {e}")
    
    return None


# ============================================================================
# TEST/HELPER FUNCTIONS
# ============================================================================

def test_upstox_connection(access_token):
    """
    Test if Upstox connection is working with provided token.
    
    Parameters:
    -----------
    access_token : str
        Bearer token for Upstox API
    
    Returns:
    --------
    bool
        True if connection successful, False otherwise
    """
    try:
        url = f"{UPSTOX_API_BASE}/v3/feed/market-data-feed"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "*/*"
        }
        
        response = requests.get(url, headers=headers, timeout=5, allow_redirects=False)
        return response.status_code in [200, 302]
    except Exception as e:
        print(f"Upstox connection test failed: {e}")
        return False


if __name__ == "__main__":
    # Quick test
    print("Upstox API module loaded successfully")
    print(f"Nifty instrument key: {NIFTY_INSTRUMENT_KEY}")
    print(f"API Base URL: {UPSTOX_API_BASE}")
