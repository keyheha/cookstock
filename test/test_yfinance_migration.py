#!/usr/bin/env python3
"""Test script for yfinance migration.

Run: python test/test_yfinance_migration.py
Exits with code 0 on PASS, 1 on FAIL.
"""
import os
import sys
import json
import argparse
import datetime as dt

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import yfinance as yf


def main(argv=None):
    parser = argparse.ArgumentParser(description='Test yfinance historical data fetching')
    parser.add_argument('--ticker', default='AAPL', help='Ticker symbol to fetch')
    parser.add_argument('--days', type=int, default=120, help='Number of days to fetch. Default: 120')

    args = parser.parse_args(argv)

    # Determine date range
    today = dt.date.today()
    start_date = today - dt.timedelta(days=args.days - 1)

    print(f'Fetching historical data for {args.ticker} from {start_date} to {today}')
    
    try:
        ticker = yf.Ticker(args.ticker)
        hist = ticker.history(start=start_date, end=today)
        
        if hist.empty:
            print(f'FAIL: No data returned for {args.ticker}')
            return 1
        
        print(f'Successfully fetched {len(hist)} days of historical data')
        print(f'Date range: {hist.index[0].date()} to {hist.index[-1].date()}')
        print(f'\nSample data (last 5 days):')
        print(hist.tail())
        
        # Verify we have the expected columns
        required_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
        missing = [col for col in required_cols if col not in hist.columns]
        if missing:
            print(f'FAIL: Missing columns: {missing}')
            return 1
        
        print('\nPASS: yfinance is working correctly')
        return 0
        
    except Exception as e:
        print(f'FAIL: Exception occurred: {e}')
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
