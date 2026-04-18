#!/usr/bin/env python3
"""
TradingView Credentials Setup Script

This script helps you set up your TradingView username and password
for accessing premium data with increased candle limits (up to 5000).
"""

import os
import getpass
from pathlib import Path


def setup_tradingview_credentials():
    """Set up TradingView credentials for premium access."""
    print("\n" + "=" * 60)
    print("TRADINGVIEW CREDENTIALS SETUP")
    print("=" * 60)
    print("\nThis will set your TradingView username and password.")
    print("This enables:")
    print("  ✅ Access to premium symbols")
    print("  ✅ Higher rate limits")
    print("  ✅ Extended data history")
    print("  ✅ Up to 5000 candles (vs 500 in no-login mode)")
    print("\nYour credentials are stored locally and never sent anywhere.")
    print("You can change them anytime by running this script again.")
    
    # Get current values
    current_username = os.getenv('TV_USERNAME', '')
    current_password = os.getenv('TV_PASSWORD', '')
    
    if current_username:
        print(f"\nCurrent username: {current_username}")
        change = input("Change username? (y/N): ").lower().strip()
        if change == 'y':
            username = input("Enter TradingView username: ").strip()
        else:
            username = current_username
    else:
        username = input("Enter TradingView username: ").strip()
    
    if current_password:
        print("Current password: [HIDDEN]")
        change = input("Change password? (y/N): ").lower().strip()
        if change == 'y':
            password = getpass.getpass("Enter TradingView password: ")
        else:
            password = current_password
    else:
        password = getpass.getpass("Enter TradingView password: ")
    
    # Validate inputs
    if not username:
        print("\n❌ Username cannot be empty")
        return False
    
    if not password:
        print("\n❌ Password cannot be empty")
        return False
    
    # Set environment variables
    os.environ['TV_USERNAME'] = username
    os.environ['TV_PASSWORD'] = password
    
    # Also set permanently in user environment (Windows)
    try:
        import winreg
        
        # Set username
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, 'Environment', 0, winreg.KEY_SET_VALUE)
        winreg.SetValueEx(key, 'TV_USERNAME', 0, winreg.REG_SZ, username)
        winreg.CloseKey(key)
        
        # Set password
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, 'Environment', 0, winreg.KEY_SET_VALUE)
        winreg.SetValueEx(key, 'TV_PASSWORD', 0, winreg.REG_SZ, password)
        winreg.CloseKey(key)
        
        print("\n✅ Credentials set permanently in Windows environment")
        print("   They will persist across PowerShell sessions and IDE restarts")
        
    except ImportError:
        print("\n⚠️  Not on Windows - credentials set for current session only")
        print("   Run this script each time you start a new terminal")
    except Exception as e:
        print(f"\n⚠️  Could not set permanent credentials: {e}")
        print("   Credentials set for current session only")
    
    # Test the credentials
    print("\n🔍 Testing credentials...")
    try:
        from tv_api import get_tv_connection
        tv = get_tv_connection()
        print("✅ Connection successful!")
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        print("   Check your credentials and internet connection")
        return False
    
    print("\n" + "=" * 60)
    print("SETUP COMPLETE!")
    print("=" * 60)
    print("\nYour TradingView credentials are now configured.")
    print("\nNext steps:")
    print("1. Open the web dashboard: python app.py")
    print("2. Go to 'TradingView Data Fetching' section")
    print("3. Set number of bars to 5000")
    print("4. Click 'Fetch from TradingView'")
    print("5. Run backtests with extended data!")
    
    return True


def clear_credentials():
    """Clear stored TradingView credentials."""
    print("\nClearing TradingView credentials...")
    
    # Remove from current environment
    if 'TV_USERNAME' in os.environ:
        del os.environ['TV_USERNAME']
    if 'TV_PASSWORD' in os.environ:
        del os.environ['TV_PASSWORD']
    
    # Remove from Windows registry
    try:
        import winreg
        
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, 'Environment', 0, winreg.KEY_SET_VALUE)
            winreg.DeleteValue(key, 'TV_USERNAME')
            winreg.DeleteValue(key, 'TV_PASSWORD')
            winreg.CloseKey(key)
            print("✅ Credentials cleared from Windows environment")
        except FileNotFoundError:
            print("ℹ️  No credentials found in Windows environment")
            
    except ImportError:
        print("ℹ️  Not on Windows - credentials were session-only")
    
    print("✅ Credentials cleared")


def show_current_status():
    """Show current credential status."""
    print("\n" + "=" * 60)
    print("TRADINGVIEW CREDENTIALS STATUS")
    print("=" * 60)
    
    username = os.getenv('TV_USERNAME', '')
    password = os.getenv('TV_PASSWORD', '')
    
    if username and password:
        print("✅ Credentials configured")
        print(f"   Username: {username}")
        print("   Password: [HIDDEN]")
        print("\n   Access level: Premium (up to 5000 candles)")
    else:
        print("⚠️  No credentials configured")
        print("   Access level: Free (up to 500 candles)")
    
    print("\nTo change credentials, run this script again.")


def main():
    """Main menu."""
    while True:
        print("\n" + "=" * 60)
        print("TRADINGVIEW CREDENTIALS MANAGER")
        print("=" * 60)
        print("1. Setup credentials")
        print("2. Show current status")
        print("3. Clear credentials")
        print("4. Exit")
        
        choice = input("\nChoose an option (1-4): ").strip()
        
        if choice == '1':
            setup_tradingview_credentials()
        elif choice == '2':
            show_current_status()
        elif choice == '3':
            clear_credentials()
        elif choice == '4':
            print("\nGoodbye!")
            break
        else:
            print("❌ Invalid choice. Please try again.")
        
        input("\nPress Enter to continue...")


if __name__ == "__main__":
    main()
