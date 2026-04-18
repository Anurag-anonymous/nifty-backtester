"""
Start Both Apps Simultaneously

This script runs both the backtester (port 5000) and the options tool (port 5001)
in separate processes. Run with: python start_all.py

Press Ctrl+C to stop both apps.
"""

import subprocess
import sys
import time

print("=" * 70)
print("🚀 Starting Nifty Backtester + Options Tool")
print("=" * 70)
print("\n📊 Backtester:    http://localhost:5000")
print("🎯 Options Tool:  http://localhost:5001\n")
print("Press Ctrl+C to stop both apps.\n")
print("=" * 70 + "\n")

# Start both apps
p1 = None
p2 = None

try:
    print("Starting Backtester (port 5000)...")
    p1 = subprocess.Popen([sys.executable, 'app.py'])
    
    time.sleep(2)  # Give first app time to start
    
    print("Starting Options Tool (port 5001)...\n")
    p2 = subprocess.Popen([sys.executable, 'options_app.py'])
    
    # Wait for both to complete
    p1.wait()
    p2.wait()

except KeyboardInterrupt:
    print("\n\nShutting down both apps...")
    if p1:
        p1.terminate()
        try:
            p1.wait(timeout=3)
        except subprocess.TimeoutExpired:
            p1.kill()
    
    if p2:
        p2.terminate()
        try:
            p2.wait(timeout=3)
        except subprocess.TimeoutExpired:
            p2.kill()
    
    print("✓ Both apps stopped.")
    sys.exit(0)

except Exception as e:
    print(f"Error: {e}")
    if p1:
        p1.terminate()
    if p2:
        p2.terminate()
    sys.exit(1)
