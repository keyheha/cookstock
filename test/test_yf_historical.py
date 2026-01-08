#!/usr/bin/env python3
"""Simple runnable smoke test for YahooFinancials.get_historical_price_data.

Run: python test/test_yf_historical.py
Exits with code 0 on PASS/SKIP, 1 on FAIL.
"""
import os
import sys
import types
import importlib.util
import json
import argparse
import datetime as dt
import time


def _to_epoch_seconds(val):
    """Convert YYYY-MM-DD or numeric string/int/float to epoch seconds (int)."""
    if isinstance(val, (int, float)):
        return int(val)
    if isinstance(val, str):
        if val.isdigit():
            return int(val)
        try:
            dtobj = dt.datetime.strptime(val, '%Y-%m-%d')
            return int(time.mktime(dtobj.timetuple()))
        except Exception:
            return int(float(val))
    if isinstance(val, dt.date):
        dtobj = dt.datetime(val.year, val.month, val.day)
        return int(time.mktime(dtobj.timetuple()))
    if isinstance(val, dt.datetime):
        return int(time.mktime(val.timetuple()))
    raise ValueError(f"Cannot convert {val!r} to epoch seconds")


def _load_yahoo_from_package():
    try:
        from yahoofinancials.yf import YahooFinancials
        return YahooFinancials
    except Exception:
        return None


def _load_yahoo_from_repo():
    # Attempt to load the vendored yf.py from the repository tree
    repo_root = os.path.dirname(os.path.dirname(__file__))
    yf_path = os.path.join(repo_root, 'yahoofinancials', 'yahoofinancials', 'yf.py')
    if not os.path.exists(yf_path):
        return None
    spec = importlib.util.spec_from_file_location('yahoofinancials.yf', yf_path)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return getattr(mod, 'YahooFinancials', None)


def main(argv=None):
    parser = argparse.ArgumentParser(description='Smoke-test YahooFinancials.get_historical_price_data')
    parser.add_argument('--live', action='store_true', help='Perform a live fetch (requires network and deps)')
    parser.add_argument('--ticker', default='AAPL', help='Ticker symbol to fetch')
    parser.add_argument('--start', help='Start date YYYY-MM-DD')
    parser.add_argument('--end', help='End date YYYY-MM-DD')
    parser.add_argument('--days', type=int, default=120, help='Number of days to fetch (used when --start/--end not provided). Default: 120')

    args = parser.parse_args(argv)

    YahooFinancials = _load_yahoo_from_package() or _load_yahoo_from_repo()
    if YahooFinancials is None:
        print('SKIP: yahoofinancials not available; activate venv or install dependencies')
        return 0

    # Determine date range
    if args.start and args.end:
        # Normalize provided args (accept YYYY-MM-DD or numeric epoch)
        start = _to_epoch_seconds(args.start)
        end = _to_epoch_seconds(args.end)
    else:
        today = dt.date.today()
        end = _to_epoch_seconds(today)
        start_date = today - dt.timedelta(days=args.days - 1)
        start = _to_epoch_seconds(start_date)

    y = YahooFinancials(args.ticker)

    if args.live:
        try:
            res = y.get_historical_price_data(start, end, 'daily')
            print(f'Live fetch for {args.ticker} {start}..{end} returned:')
            try:
                print(json.dumps(res, indent=2, default=str))
            except Exception:
                print(repr(res))
            # also print number of price points when available
            try:
                n = len(res[args.ticker]['prices'])
                print(f'Number of price points: {n}')
            except Exception:
                pass
            print('PASS (live)')
            return 0
        except Exception as e:
            print('FAIL: live fetch raised:', e)
            return 1

    # Non-live (mocked) mode for quick checks
    # Replace get_stock_data with a fake that captures inputs and returns controlled output
    captured = {}

    def fake_get_stock_data(self, arg_type, hist_obj=None):
        captured['arg_type'] = arg_type
        captured['hist_obj'] = hist_obj

        def _to_date(val):
            # Handles 'YYYY-MM-DD', integer/float epoch seconds, or numeric strings
            if isinstance(val, (int, float)):
                try:
                    return dt.date.fromtimestamp(int(val))
                except Exception:
                    return None
            if isinstance(val, str):
                if val.isdigit():
                    try:
                        return dt.date.fromtimestamp(int(val))
                    except Exception:
                        pass
                try:
                    return dt.datetime.strptime(val, '%Y-%m-%d').date()
                except Exception:
                    try:
                        return dt.date.fromtimestamp(float(val))
                    except Exception:
                        return None
            return None

        start_raw = hist_obj.get('start') if hist_obj else None
        end_raw = hist_obj.get('end') if hist_obj else None
        s = _to_date(start_raw)
        e = _to_date(end_raw)

        if s is None or e is None:
            # Fallback: echo the provided start value as a single point
            return {args.ticker: {'prices': [{'formatted_date': start_raw, 'close': 100}]}}

        days = (e - s).days + 1
        prices = []
        for i in range(max(days, 1)):
            d = s + dt.timedelta(days=i)
            prices.append({'formatted_date': d.isoformat(), 'close': 100 + i})
        return {args.ticker: {'prices': prices}}

    y.get_stock_data = types.MethodType(fake_get_stock_data, y)

    try:
        print(f'Performing mocked fetch for {args.ticker} from {start} to {end}...')
        res = y.get_historical_price_data(start, end, 'daily')
        print("Fetched (mock) historical price data.")
    except Exception as e:
        print('FAIL: get_historical_price_data raised:', e)
        return 1

    # Basic validations
    if captured.get('arg_type') != 'history':
        print('FAIL: expected arg_type "history", got', captured.get('arg_type'))
        return 1
    hist_obj = captured.get('hist_obj')
    if not isinstance(hist_obj, dict) or not all(k in hist_obj for k in ('start', 'end', 'interval')):
        print('FAIL: hist_obj missing keys or invalid:', hist_obj)
        return 1

    # Print captured request and returned data for inspection
    print('Captured request (hist_obj):')
    try:
        print(json.dumps(hist_obj, indent=2, default=str))
    except Exception:
        print(repr(hist_obj))
    print('Returned result (res):')
    try:
        print(json.dumps(res, indent=2, default=str))
    except Exception:
        print(repr(res))

    try:
        n = len(res[args.ticker]['prices'])
        print(f'Number of price points (mock): {n}')
    except Exception:
        pass

    print('PASS')
    return 0


if __name__ == '__main__':
    sys.exit(main())