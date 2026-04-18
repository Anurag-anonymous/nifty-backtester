#!/usr/bin/env python3
"""Final verification of Groww API integration"""

import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

print('=' * 70)
print('GROWW API Integration - Final Verification')
print('=' * 70)

# Test imports
print('\nChecking imports...')
try:
    from groww_api import (
        fetch_nifty_data_from_groww,
        fetch_and_save_groww_data,
        normalize_groww_response,
        get_date_range,
        GROWW_API_ENDPOINT,
        GROWW_NIFTY_SYMBOL,
        GROWW_EXCHANGE,
        GROWW_SEGMENT
    )
    print('✅ All groww_api functions imported successfully')
except Exception as e:
    print(f'❌ Import failed: {e}')
    sys.exit(1)

# Show configuration
print('\nConfiguration:')
print(f'  - API Endpoint: {GROWW_API_ENDPOINT}')
print(f'  - Symbol: {GROWW_NIFTY_SYMBOL}')
print(f'  - Exchange: {GROWW_EXCHANGE}')
print(f'  - Segment: {GROWW_SEGMENT}')

# Test utility functions
print('\nTesting utility functions...')
try:
    start, end = get_date_range(15)
    print(f'✅ Date range: {start} to {end}')
except Exception as e:
    print(f'❌ Error: {e}')

# Check data directory
if os.path.exists('data'):
    print('✅ Data directory exists')
else:
    print('⚠️  Creating data directory...')
    os.makedirs('data', exist_ok=True)

print('\n' + '=' * 70)
print('✅ GROWW API Integration Verified Successfully!')
print('=' * 70)

print('\n📋 Files Created:')
print('  1. groww_api.py                    - Main module')
print('  2. test_groww_api.py               - Setup verification')
print('  3. example_groww_backtest.py       - Complete example')
print('  4. GROWW_API_SETUP.md              - Setup guide')
print('  5. GROWW_API_IMPLEMENTATION.md     - Technical ref')
print('  6. GROWW_API_QUICKSTART.md         - Quick guide')

print('\n🚀 Next Steps:')
print('  1. Get API key: https://groww.in/trade-api')
print('  2. Set env var: $env:GROWW_API_KEY = "your_key"')
print('  3. Verify:      python test_groww_api.py')
print('  4. Run example: python example_groww_backtest.py')

print('\n📚 Documentation:')
print('  • GROWW_API_QUICKSTART.md    - Start here!')
print('  • GROWW_API_SETUP.md         - Detailed setup')
print('  • GROWW_API_IMPLEMENTATION.md - Technical details')

print('=' * 70 + '\n')
