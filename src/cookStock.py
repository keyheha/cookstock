#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Jan  9 00:10:18 2021

@author: sxu
"""
import numpy as np
import pandas as pd
import json as js
import datetime as dt
import os.path
from time import sleep
import sys

import matplotlib.pyplot as plt
import logging
import time
import threading
import functools
import subprocess

# Basic logger setup for pipeline progress
logger = logging.getLogger(__name__)
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(name)s: %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    # Allow overriding via environment variable LOG_LEVEL (e.g., DEBUG, INFO, WARNING)
    log_level = os.getenv("LOG_LEVEL")
    if log_level:
        try:
            logger.setLevel(getattr(logging, log_level.upper()))
        except Exception:
            logger.warning("Invalid LOG_LEVEL '%s'; using INFO", log_level)

# Helper to emit periodic heartbeat logs while a single ticker is being processed
# Use a background thread that logs every `interval` seconds until stopped.
def _start_heartbeat(ticker, interval=30):
    stop = threading.Event()
    start = time.time()
    def _hb():
        while not stop.is_set():
            elapsed = time.time() - start
            logger.info("Ticker %s still processing (elapsed %.0fs)", ticker, elapsed)
            stop.wait(interval)
    t = threading.Thread(target=_hb, daemon=True)
    t.start()
    return stop

# Reusable decorator to log function entry/exit and duration. Use as @_log_step() above methods.
def _log_step(level='info', show_args=False):
    """Decorator to log entry/exit and execution time for functions.
    - level: 'info' or 'debug'
    - show_args: if True, will attempt to log args and kwargs (may trim `self` for methods)
    """
    def _decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            name = f"{func.__qualname__}"
            if show_args:
                try:
                    arg_preview = args[1:] if len(args) > 0 else args
                    if level == 'debug':
                        logger.info("Entering %s args=%s kwargs=%s", name, arg_preview, kwargs)
                    else:
                        logger.info("Entering %s", name)
                except Exception:
                    logger.info("Entering %s (args omitted due to formatting error)", name)
            else:
                if level == 'debug':
                    logger.info("Starting %s", name)
                else:
                    logger.info("Starting %s", name)
            t0 = time.time()
            try:
                result = func(*args, **kwargs)
                elapsed = time.time() - t0
                if level == 'debug':
                    logger.info("Finished %s in %.2fs", name, elapsed)
                else:
                    logger.info("Finished %s in %.2fs", name, elapsed)
                return result
            except Exception:
                logger.exception("Error in %s", name)
                raise
        return wrapper
    return _decorator

def find_path():
    """Find the 'cookstock' project root quickly.

    Strategy (fast):
    - honor COOKSTOCK_PATH environment variable if set
    - walk upward from this file's directory (or cwd) and look for a parent named 'cookstock'
    - try to use git to find the repo root if available
    - check a few common locations
    Returns absolute path or None.
    """
    # 1) env var override
    env_path = os.environ.get('COOKSTOCK_PATH')
    if env_path:
        p = os.path.expanduser(env_path)
        if os.path.isdir(p):
            logger.info("Using cookstock path from COOKSTOCK_PATH: %s", p)
            return os.path.abspath(p)

    # 2) search upward from this file (or cwd)
    try:
        start = os.path.dirname(__file__)
    except NameError:
        start = os.getcwd()
    p = os.path.abspath(start)
    while True:
        if os.path.basename(p).lower() == 'cookstock':
            logger.info("Found cookstock by upward search: %s", p)
            return p
        parent = os.path.dirname(p)
        if parent == p:
            break
        p = parent

    # 3) try git root
    try:
        git_root = subprocess.check_output(['git', 'rev-parse', '--show-toplevel'], stderr=subprocess.DEVNULL).decode().strip()
        if os.path.basename(git_root).lower() == 'cookstock':
            logger.info("Found cookstock via git root: %s", git_root)
            return git_root
    except Exception:
        logger.debug("git root lookup failed", exc_info=True)

    # 4) common locations
    common = ['~/Sources/cookstock', '~/cookstock', '~/Projects/cookstock']
    for c in common:
        cpath = os.path.expanduser(c)
        if os.path.isdir(cpath):
            logger.info("Found cookstock in common path: %s", cpath)
            return os.path.abspath(cpath)

    logger.warning("Could not find 'cookstock' project root; returning None. Set COOKSTOCK_PATH env var to override.")
    return None

basePath = find_path()
if not basePath:
    logger.error("'cookstock' root not found; please set COOKSTOCK_PATH env var or run from inside the repo.")
    raise RuntimeError("'cookstock' root not found; set COOKSTOCK_PATH or run from inside repo")

# Import yfinance
import yfinance as yf

# Configurable defaults (can be overridden with environment variables)
HISTORICAL_DAYS_DEFAULT = int(os.getenv("HISTORICAL_DAYS", "120"))
CACHE_TTL_HOURS = int(os.getenv("CACHE_TTL_HOURS", "24"))
PREFETCH_ENABLED = os.getenv("PREFETCH", "false").lower() in ("1", "true", "yes")
PREFETCH_WORKERS = int(os.getenv("PREFETCH_WORKERS", "8"))

# Cache directory for historical price data
CACHE_DIR = os.path.join(basePath, 'results', 'cache', 'prices')
try:
    os.makedirs(CACHE_DIR, exist_ok=True)
except Exception:
    logger.debug("Unable to create cache directory %s", CACHE_DIR)


def _to_epoch_seconds(val):
    """Convert a date/datetime/ISO date string or numeric value to epoch seconds (int).

    Accepts:
    - int/float (assumed epoch seconds)
    - numeric strings (digits or floats)
    - 'YYYY-MM-DD' strings
    - datetime.date or datetime.datetime objects
    Raises ValueError on unrecognized inputs.
    """
    try:
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
    except Exception as e:
        logger.debug("Failed to convert %r to epoch seconds: %s", val, e)
        raise
    raise ValueError(f"Cannot convert {val!r} to epoch seconds")


def _cache_file(ticker, days):
    safe_t = str(ticker).upper()
    return os.path.join(CACHE_DIR, f"{safe_t}_{days}.json")


def _cache_load(ticker, days, ttl_hours=CACHE_TTL_HOURS):
    filepath = _cache_file(ticker, days)
    try:
        if not os.path.exists(filepath):
            return None
        mtime = os.path.getmtime(filepath)
        age_hours = (time.time() - mtime) / 3600.0
        if age_hours > ttl_hours:
            return None
        with open(filepath, 'r') as f:
            return js.load(f)
    except Exception:
        logger.debug("Cache load failed for %s", filepath, exc_info=True)
        return None


def _cache_save(ticker, days, data):
    filepath = _cache_file(ticker, days)
    try:
        with open(filepath, 'w') as f:
            js.dump(data, f)
    except Exception:
        logger.debug("Cache save failed for %s", filepath, exc_info=True)
# yfinance is now imported at module level
logger.info("yfinance successfully loaded.")

#define some constants
class algoParas:   
    PIVOT_PRICE_PERC = 0.15  # Minervini: 15% max correction for valid pivots
    VOLUME_DROP_THRESHOLD_HIGH = 0.8
    VOLUME_DROP_THRESHOLD_LOW = 0.4
    REGRESSION_DAYS = 100
    PEAK_VOL_RATIO = 1.3
    PRICE_POSITION_LOW = 0.75  # Minervini: price within top 25% of 52-week high
    VOLUME_THRESHOLD = 100000
    
    

class cookFinancials:
    ticker = ''
    bshData = []
    bshData_quarter = []
    ish = []
    ish_quarter = []
    cfsh = []
    cfsh_quarter = []
    summaryData = []
    priceData = []
    m_recordVCP = []
    m_footPrint = []
    current_stickerPrice = []
    #define some parameters
    
    def __init__(self, ticker, priceData=None, fetch_days=None):
        if isinstance(ticker, str):
            self.ticker = ticker.upper()
            self.yf_ticker = yf.Ticker(self.ticker)
        else:
            self.ticker = [t.upper() for t in ticker]
            self.yf_ticker = None  # Multiple tickers handled differently
        self._cache = {}

        # Determine how many days of history to fetch
        days = fetch_days if fetch_days is not None else HISTORICAL_DAYS_DEFAULT

        date = dt.date.today()

        # If priceData is provided (e.g., from prefetch), use it
        if priceData:
            logger.info("Using pre-fetched priceData for %s", self.ticker)
            # priceData may be a dict mapping tickers to their data
            if isinstance(priceData, dict) and self.ticker in priceData:
                self.priceData = {self.ticker: priceData[self.ticker]}
            else:
                self.priceData = priceData
        else:
            # try load cache
            cached = _cache_load(self.ticker, days)
            if cached is not None:
                logger.info("Loaded cached historical price data for %s (last %d days)", self.ticker, days)
                self.priceData = cached
            else:
                logger.info("Fetching last %d days historical price data for %s", days, self.ticker)
                try:
                    # log the input dates (use date strings for yfinance)
                    start_date = date - dt.timedelta(days=days)
                    logger.info("Fetching data from %s to %s", str(start_date), str(date))
                    
                    # Use yfinance to fetch historical data
                    hist = self.yf_ticker.history(start=start_date, end=date)
                    
                    # Convert yfinance format to expected format
                    prices = []
                    for idx, row in hist.iterrows():
                        prices.append({
                            'formatted_date': idx.strftime('%Y-%m-%d'),
                            'date': int(idx.timestamp()),
                            'open': row['Open'],
                            'high': row['High'],
                            'low': row['Low'],
                            'close': row['Close'],
                            'volume': row['Volume'],
                            'adjclose': row['Close']
                        })
                    
                    self.priceData = {self.ticker: {'prices': prices}}
                    logger.info("Fetched %d price points", len(prices))
                    _cache_save(self.ticker, days, self.priceData)
                except Exception:
                    logger.exception("Failed to fetch historical price data for %s", self.ticker)
                    self.priceData = {self.ticker: {'prices': []}}

        logger.info("Initialized cookFinancials for ticker: %s", self.ticker)
        # Get fresh current price from yfinance instead of cached historical close
        # This ensures we have the latest market price
        try:
            self.current_stickerPrice = self.get_current_price()
            if not self.current_stickerPrice:
                # Fallback to last cached price if live price unavailable
                if self.priceData.get(self.ticker, {}).get('prices'):
                    self.current_stickerPrice = self.priceData[self.ticker]['prices'][-1]['close']
                    logger.debug("Using cached close price for %s", self.ticker)
                else:
                    self.current_stickerPrice = None
        except Exception:
            logger.debug("Could not set current_stickerPrice for %s", self.ticker)
            self.current_stickerPrice = None
        
    def get_balanceSheetHistory(self):
        # yfinance uses different attribute names
        bs = self.yf_ticker.balance_sheet  # Annual by default
        self.bshData = {self.ticker: self._convert_financials_to_old_format(bs)}
        return self.bshData
    
    def get_balanceSheetHistory_quarter(self):
        bs_q = self.yf_ticker.quarterly_balance_sheet
        self.bshData_quarter = {self.ticker: self._convert_financials_to_old_format(bs_q)}
        return self.bshData_quarter
    
    def get_incomeStatementHistory(self):
        income = self.yf_ticker.income_stmt
        self.ish = {self.ticker: self._convert_financials_to_old_format(income)}
        return self.ish
    
    def get_incomeStatementHistory_quarter(self):
        income_q = self.yf_ticker.quarterly_income_stmt
        self.ish_quarter = {self.ticker: self._convert_financials_to_old_format(income_q)}
        return self.ish_quarter
    
    def get_cashflowStatementHistory(self):
        cf = self.yf_ticker.cashflow
        self.cfsh = {self.ticker: self._convert_financials_to_old_format(cf)}
        return self.cfsh
        
    def get_cashflowStatementHistory_quarter(self):
        cf_q = self.yf_ticker.quarterly_cashflow
        self.cfsh_quarter = {self.ticker: self._convert_financials_to_old_format(cf_q)}
        return self.cfsh_quarter
    
    def _convert_financials_to_old_format(self, df):
        """Convert yfinance DataFrame format to old yahoofinancials dict format."""
        if df is None or df.empty:
            return []
        result = []
        for col in df.columns:
            date_str = col.strftime('%Y-%m-%d')
            data_dict = {date_str: {}}
            for idx in df.index:
                # Convert pandas index to snake_case key
                key = idx.replace(' ', '')
                # Common mapping for financial statement keys
                key_map = {
                    'StockholdersEquity': 'stockholdersEquity',
                    'TotalEquityGrossMinorityInterest': 'stockholdersEquity',
                    'ShortLongTermDebt': 'shortLongTermDebt',
                    'CurrentDebt': 'shortLongTermDebt',
                    'LongTermDebt': 'longTermDebt',
                    'NetIncome': 'netIncome',
                    'OperatingCashFlow': 'operatingCashFlow'
                }
                value = df.loc[idx, col]
                # Use mapped key if available, otherwise use camelCase version
                mapped_key = key_map.get(key, key[0].lower() + key[1:] if key else key)
                if pd.notna(value):
                    data_dict[date_str][mapped_key] = int(value) if isinstance(value, (int, float)) else value
            result.append(data_dict)
        return result
    
    def get_book_value(self):
        """Get current book value (stockholders equity) from yfinance."""
        try:
            info = self.yf_ticker.info
            # Try to get book value from info
            book_value = info.get('bookValue')
            if book_value:
                # bookValue in info is per share, multiply by shares outstanding
                shares = info.get('sharesOutstanding')
                if shares:
                    return book_value * shares
            
            # Fallback: get from most recent balance sheet
            if not self.bshData:
                self.get_balanceSheetHistory()
            if self.bshData and self.bshData.get(self.ticker):
                date_key = list(self.bshData[self.ticker][0].keys())[0]
                return self.bshData[self.ticker][0][date_key].get('stockholdersEquity')
            
            return None
        except Exception:
            logger.exception("Failed to get book value for %s", self.ticker)
            return None
    
    @_log_step()
    def get_BV(self, numofYears=20):
        bv = []
        if not(self.bshData):
            self.get_balanceSheetHistory()
        for i in range(min(np.size(self.bshData[self.ticker]), numofYears)):
            date_key = list(self.bshData[self.ticker][i].keys())[0]
            if not(self.bshData[self.ticker][i][date_key]):    
                break
            #check if the key is in the dictionary
            if not(self.bshData[self.ticker][i][date_key].get('stockholdersEquity')):
                #warning
                print('stockholdersEquity is not in the dictionary')
                break
            bv.append(self.bshData[self.ticker][i][date_key]['stockholdersEquity'])
        return bv
    
    @_log_step()
    def get_BV_quarter(self, numofQuarter=20):
        bv = []
        if not(self.bshData_quarter):
            self.get_balanceSheetHistory_quarter()
        for i in range(min(np.size(self.bshData_quarter[self.ticker]), numofQuarter)):
            date_key = list(self.bshData_quarter[self.ticker][i].keys())[0]
            if not(self.bshData_quarter[self.ticker][i][date_key]):    
                break
            if not(self.bshData_quarter[self.ticker][i][date_key].get('stockholdersEquity')):
                #warning
                logger.warning("stockholdersEquity is not in the dictionary for %s (quarter)", self.ticker)
                break
            bv.append(self.bshData_quarter[self.ticker][i][date_key]['stockholdersEquity'])
        return bv   
    
    def get_ROIC(self, numofYears=20):
        roic = []
        if not(self.cfsh):
            self.get_cashflowStatementHistory()
        if not(self.bshData):
            self.get_balanceSheetHistory()
        for i in range(min(np.size(self.bshData[self.ticker]), numofYears)):
            date_key = list(self.bshData[self.ticker][i].keys())[0]
            if not(self.bshData[self.ticker][i][date_key]):    
                break
            #check if the key is in the dictionary
            if not(self.bshData[self.ticker][i][date_key].get('stockholdersEquity')):
                #warning
                print('stockholdersEquity is not in the dictionary')
                break
            equity = self.bshData[self.ticker][i][date_key]['stockholdersEquity']
            if self.bshData[self.ticker][i][date_key].get('shortLongTermDebt') is None or not(self.bshData[self.ticker][i][date_key]['shortLongTermDebt']):
                debt_short = 0
            else:
                debt_short = self.bshData[self.ticker][i][date_key].get('shortLongTermDebt')
            if self.bshData[self.ticker][i][date_key].get('longTermDebt') is None or not(self.bshData[self.ticker][i][date_key]['longTermDebt']) :
                debt_long = 0
            else:
                debt_long = self.bshData[self.ticker][i][date_key]['longTermDebt']
            debt = debt_short + debt_long
            date_key = list(self.cfsh[self.ticker][i].keys())[0]
            if not(self.cfsh[self.ticker][i][date_key]):    
                break
            netincome = self.cfsh[self.ticker][i][date_key]['netIncome']
            roic_year = netincome/(equity + debt)
            roic.append(roic_year)
        return roic 
    
    @_log_step()
    def get_totalCashFromOperatingActivities(self, numofYears=20):
        totalCash = []
        if not(self.cfsh):
            self.get_cashflowStatementHistory()        
        for i in range(min(np.size(self.cfsh[self.ticker]), numofYears)):
            date_key = list(self.cfsh[self.ticker][i].keys())[0]
            if not(self.cfsh[self.ticker][i][date_key]):    
                break
            #check if the key is in the dictionary
            if not(self.cfsh[self.ticker][i][date_key].get('operatingCashFlow')):
                #warning
                logger.warning("operatingCashFlow is not in the dictionary for %s", self.ticker)
                break
            totalCash.append(self.cfsh[self.ticker][i][date_key]['operatingCashFlow'])  
        return totalCash
    
    def get_summary_data(self):
        """Get summary data using yfinance info."""
        if not self.summaryData:
            try:
                info = self.yf_ticker.info
                self.summaryData = {self.ticker: info}
            except Exception:
                logger.exception("Failed to get summary data for %s", self.ticker)
                self.summaryData = {self.ticker: {}}
        return self.summaryData
    
    def get_pricetoSales(self):
        if not(self.summaryData):
            self.summaryData = self.get_summary_data()
        if not(self.summaryData[self.ticker]):
            return 'na'
        return self.summaryData[self.ticker].get('priceToSalesTrailing12Months', 'na')
    
    def get_marketCap_B(self):
        if not(self.summaryData):
            self.summaryData = self.get_summary_data()
        if not(self.summaryData[self.ticker]):
            return 'na'
        market_cap = self.summaryData[self.ticker].get('marketCap')
        return market_cap/1000000000 if market_cap else 'na'
    
    def get_CF_GR_median(self, totalCash):
        gr = []
        for v in range(np.size(totalCash)-1):
            gr.append((totalCash[v]-totalCash[v+1])/abs(totalCash[v+1]))
        #print(gr)
        return np.size(totalCash)-1, np.median(gr) 
    
    #use mean of each year    
    def get_BV_GR_median(self, bv):
        # Filter out None values from bv
        bv_filtered = [value for value in bv if value is not None]
        
        gr = []
        for v in range(np.size(bv_filtered) - 1):
            # Calculate growth rate between consecutive years
            gr.append((bv_filtered[v] - bv_filtered[v + 1]) / abs(bv_filtered[v + 1]))

        return np.size(bv_filtered) - 1, np.median(gr) if gr else None
    
    def get_GR_median(self, bv):
        gr = []
        for v in range(np.size(bv)-1):
            gr.append((bv[v]-bv[v+1])/abs(bv[v+1]))
        #print(gr)
        return np.size(bv)-1, np.median(gr)
    
    #use mean of each year    
    def get_ROIC_median(self, roic):
        return np.size(roic), np.median(roic)
    
    def get_BV_GR_max(self, bv):
        gr = []
        for v in range(np.size(bv)-1):
            gr.append((bv[v]-bv[v+1])/abs(bv[v+1]))
        #print(gr)
        if not gr:
            return np.size(bv)-1, 0
        return np.size(bv)-1, np.max(gr)
    
    def growthRate(self, cur,init, years):
        if cur <=0 or init<=0:
            return -1
        return (cur/init)**(1/years)-1
    
    def get_BV_GR_mean(self, bv):
        gr = []
        BV_GR = self.growthRate(bv[0], bv[np.size(bv)-1], np.size(bv)-1)
        if BV_GR==-1:
            for v in range(np.size(bv)-1):
                gr.append((bv[v]-bv[v+1])/abs(bv[v+1]))
            BV_GR = np.mean(gr) if gr else -1
        return np.size(bv)-1, BV_GR
    
    def get_suggest_price(self, cEPS, growth, years, rRate, PE, safty):
        if not(cEPS) or not(growth) or not(PE):
            return 'NA'
        fEPS = cEPS*(1+growth)**years
        fPrice = fEPS*PE;
        stickerPrice = fPrice/(1+rRate)**years
        return stickerPrice, stickerPrice*safty
    
    def payBackTime(self, price, cEPS, growth):
        tmp = 0
        i = 0
        if cEPS < 0:
            return 0
        while(growth>0):
            i+=1
            tmp = tmp + cEPS*(1+growth)**i
            if (tmp>price):
                break
        return i
    
    def get_earningsperShare(self):
        try:
            info = self.yf_ticker.info
            eps = info.get('trailingEps')
            if not eps:
                # Try getting from financials
                income = self.yf_ticker.income_stmt
                if not income.empty and 'Basic EPS' in income.index:
                    eps = income.loc['Basic EPS'].iloc[0]
            logger.info("eps: %s", eps)
            return eps
        except Exception:
            logger.exception("Failed to get EPS for %s", self.ticker)
            return None
    
    def get_earnings_per_share(self):
        """Alias for get_earningsperShare for consistency with naming conventions."""
        return self.get_earningsperShare()
    
    def get_PE(self):
        try:
            info = self.yf_ticker.info
            trailing_pe = info.get('trailingPE')
            forward_pe = info.get('forwardPE')
            
            if not trailing_pe:
                return forward_pe
            if not forward_pe:
                return trailing_pe
            return (trailing_pe + forward_pe) / 2
        except Exception:
            logger.exception("Failed to get PE for %s", self.ticker)
            return None
    
    def get_current_price(self):
        """Get current stock price from yfinance."""
        try:
            info = self.yf_ticker.info
            return info.get('currentPrice') or info.get('regularMarketPrice')
        except Exception:
            logger.exception("Failed to get current price for %s", self.ticker)
            return None
    
    def get_decision(self,suggestPrice, stockprice):
        #print('suggested price:', suggestPrice)
        #print('stock price:', stockprice)
        if isinstance(suggestPrice, str):
            return 'skip due to negative eps'
        elif suggestPrice>stockprice:
            return 'strong buy' 
        else:
            return 'do not buy'   
    def get_ma_ref(self, date_from, date_to):
        start_ts = _to_epoch_seconds(date_from)
        end_ts = _to_epoch_seconds(date_to)
        data = self.get_historical_price_data(start_ts, end_ts, 'daily')
        tmp = 0
        if not(data[self.ticker]['prices']):
            return -1
        for i in range(len(data[self.ticker]['prices'])):
            #print(data[self.ticker]['prices'][i]['formatted_date'])
            if not(data[self.ticker]['prices'][i]['close']):
                if i > 0:
                    data[self.ticker]['prices'][i]['close'] = data[self.ticker]['prices'][i-1]['close']
                else:
                    # Skip first element if no close price
                    continue
            tmp = tmp + data[self.ticker]['prices'][i]['close']
        return tmp/(i+1) if i >= 0 else -1
    
    def get_ma(self, date_from, date_to):
        if not(self.priceData):
            date = dt.date.today()
            start_date = date - dt.timedelta(days=365)
            start_ts = _to_epoch_seconds(start_date)
            end_ts = _to_epoch_seconds(date)
            self.priceData = self.get_historical_price_data(start_ts, end_ts, 'daily')
        #don't need to pull data from remote, use local
        priceDataStruct = self.priceData[self.ticker]['prices']
        selectedPriceDataStruct = self.get_price_from_buffer_start_end(priceDataStruct, date_from, date_to)
        #data = self.get_historical_price_data(date_from,date_to, 'daily')
        tmp = 0
        if not(selectedPriceDataStruct):
            return -1
        for i in range(len(selectedPriceDataStruct)):
            #print(data[self.ticker]['prices'][i]['formatted_date'])
            if not(selectedPriceDataStruct[i]['close']):
                selectedPriceDataStruct[i]['close'] = selectedPriceDataStruct[i-1]['close']
            tmp = tmp + selectedPriceDataStruct[i]['close']
        return tmp/(i+1)
    
    def get_ma_50(self, date):
        date_from = (date - dt.timedelta(days=50))
        date_to = (date)
        return self.get_ma(date_from, date_to)
    def get_ma_200(self, date):
        date_from = (date - dt.timedelta(days=200))
        date_to = (date)
        return self.get_ma(date_from, date_to)
    def get_ma_150(self, date):
        date_from = (date - dt.timedelta(days=150))
        date_to = (date)
        return self.get_ma(date_from, date_to)
    
    def get_ema(self, date, period):
        """Calculate Exponential Moving Average (EMA) for a given period.
        
        Args:
            date: The end date for EMA calculation
            period: The number of periods for EMA (e.g., 8, 20, 50)
        
        Returns:
            EMA value or -1 if insufficient data
        """
        if not(self.priceData):
            date_now = dt.date.today()
            start_date = date_now - dt.timedelta(days=365)
            start_ts = _to_epoch_seconds(start_date)
            end_ts = _to_epoch_seconds(date_now)
            self.priceData = self.get_historical_price_data(start_ts, end_ts, 'daily')
        
        # Get price data up to the specified date
        date_from = date - dt.timedelta(days=period * 3)  # Get extra data for EMA calculation
        priceDataStruct = self.priceData[self.ticker]['prices']
        selectedPriceDataStruct = self.get_price_from_buffer_start_end(priceDataStruct, date_from, date)
        
        if not selectedPriceDataStruct or len(selectedPriceDataStruct) < period:
            logger.warning("get_ema: Insufficient data for %s (period=%d)", self.ticker, period)
            return -1
        
        # Extract close prices
        close_prices = []
        for item in selectedPriceDataStruct:
            if item['close']:
                close_prices.append(item['close'])
            elif close_prices:  # Use last valid price if current is missing
                close_prices.append(close_prices[-1])
        
        if len(close_prices) < period:
            return -1
        
        # Calculate EMA using pandas
        prices_series = pd.Series(close_prices)
        ema = prices_series.ewm(span=period, adjust=False).mean()
        
        return ema.iloc[-1] if len(ema) > 0 else -1
    
    def get_ema_8(self, date):
        """Get 8-period EMA."""
        return self.get_ema(date, 8)
    
    def is_swing_trade_entry(self):
        """Check for swing trade entry signal.
        
        Criteria:
        - Current price is above 8 EMA (Exponential Moving Average)
        - Current price is above 200 SMA (Simple Moving Average)
        
        Returns:
            Tuple (bool, dict): (True/False, details dict with prices and EMAs)
        """
        try:
            date = dt.date.today()
            
            # Get current price
            if not self.current_stickerPrice:
                self.current_stickerPrice = self.get_current_price()
            current_price = self.current_stickerPrice
            
            if current_price is None:
                logger.warning("is_swing_trade_entry: No current price for %s", self.ticker)
                return False, {}
            
            # Get 8 EMA
            ema_8 = self.get_ema_8(date)
            if ema_8 == -1:
                logger.warning("is_swing_trade_entry: Could not calculate 8 EMA for %s", self.ticker)
                return False, {}
            
            # Get 200 SMA
            sma_200 = self.get_ma_200(date)
            if sma_200 == -1:
                logger.warning("is_swing_trade_entry: Could not calculate 200 SMA for %s", self.ticker)
                return False, {}
            
            # Check conditions: price > 8 EMA AND price > 200 SMA
            is_above_ema8 = current_price > ema_8
            is_above_sma200 = current_price > sma_200
            is_entry_signal = is_above_ema8 and is_above_sma200
            
            details = {
                'current_price': current_price,
                'ema_8': ema_8,
                'sma_200': sma_200,
                'above_ema8': is_above_ema8,
                'above_sma200': is_above_sma200,
                'swing_entry_signal': is_entry_signal
            }
            
            logger.info("Swing trade entry check for %s: signal=%s (price=%.2f, ema8=%.2f, sma200=%.2f)",
                       self.ticker, is_entry_signal, current_price, ema_8, sma_200)
            
            return is_entry_signal, details
            
        except Exception as e:
            logger.exception("Error in is_swing_trade_entry for %s: %s", self.ticker, e)
            return False, {}
    
    def get_30day_trend_ma200(self):
        """Check if 200 SMA is trending up over the last 30 days (Minervini criteria).
        Returns 1 if trending up, -1 otherwise.
        """
        current = self.get_ma_200((dt.date.today()))
        if current == -1:
            return -1
        mid = self.get_ma_200((dt.date.today()-dt.timedelta(days=15)))
        if mid == -1:
            return -1
        last = self.get_ma_200((dt.date.today()-dt.timedelta(days=30)))
        if last == -1:
            return -1
        # All three points must show uptrend
        if current > mid and mid > last:
            return 1
        return -1
    def check_ma_alignment(self):
        """Check if moving averages are aligned per Minervini's Trend Template.
        Required: 150 SMA > 200 SMA (price above both)
        Preferred: 50 SMA > 150 SMA > 200 SMA
        Returns: (meets_required, meets_preferred)
        """
        try:
            date = dt.date.today()
            
            # Get all moving averages
            ma_50 = self.get_ma_50(date)
            ma_150 = self.get_ma_150(date)
            ma_200 = self.get_ma_200(date)
            
            if ma_150 == -1 or ma_200 == -1:
                return False, False
            
            # Required: 150 > 200
            meets_required = ma_150 > ma_200
            
            # Preferred: 50 > 150 > 200
            meets_preferred = False
            if ma_50 != -1:
                meets_preferred = ma_50 > ma_150 and ma_150 > ma_200
            
            logger.info("MA alignment for %s: 50=%.2f, 150=%.2f, 200=%.2f, required=%s, preferred=%s",
                       self.ticker, ma_50 if ma_50 != -1 else 0, ma_150, ma_200, meets_required, meets_preferred)
            
            return meets_required, meets_preferred
            
        except Exception:
            logger.exception("Error checking MA alignment for %s", self.ticker)
            return False, False
    
    def get_30day_trend(self):
        if not(self.priceData):
            date = dt.date.today()
            start_date = date - dt.timedelta(days=365)
            start_ts = _to_epoch_seconds(start_date)
            end_ts = _to_epoch_seconds(date)
            self.priceData = self.get_historical_price_data(start_ts, end_ts, 'daily')
        length = len(self.priceData[self.ticker]['prices'])
        #get 30 days data
        price30Structure = self.get_price_from_buffer(self.priceData[self.ticker]['prices'], dt.date.today()-dt.timedelta(days=30), 30)
        price30 = [item['close'] for item in price30Structure]
        #find the trend
        trend, _ = self._calculate_volume_trend(price30)
        flag = 1 if trend > 0 else -1
        return flag
    
    def mv_strategy(self):
        """Minervini's Trend Template criteria:
        - Price > 150 SMA and 200 SMA
        - Price > 50 SMA (preferred)
        - 150 SMA > 200 SMA (required)
        - 50 SMA > 150 SMA > 200 SMA (preferred)
        - 200 SMA trending up for at least 1 month
        """
        if not(self.priceData):
            date = dt.date.today()
            start_date = date - dt.timedelta(days=365)
            start_ts = _to_epoch_seconds(start_date)
            end_ts = _to_epoch_seconds(date)
            self.priceData = self.get_historical_price_data(start_ts, end_ts, 'daily')
        if not self.current_stickerPrice:
            self.current_stickerPrice = self.get_current_price()
        currentPrice = self.current_stickerPrice
        
        if currentPrice is None:
            logger.warning("mv_strategy: No current price for %s", self.ticker)
            return -1
        
        date = dt.date.today()
        price50 = self.get_ma_50(date)
        price150 = self.get_ma_150(date)
        price200 = self.get_ma_200(date)
        
        # Check for invalid data
        if price150 == -1 or price200 == -1:
            logger.warning("mv_strategy: Invalid MA data for %s", self.ticker)
            return -1
        
        # Minervini Criteria:
        # 1. Price above 150 and 200 SMA
        if not (currentPrice > price150 and currentPrice > price200):
            logger.info("mv_strategy %s: Price not above both 150 & 200 SMA", self.ticker)
            return -1
        
        # 2. Check MA alignment (150 > 200 required)
        meets_required, meets_preferred = self.check_ma_alignment()
        if not meets_required:
            logger.info("mv_strategy %s: 150 SMA not above 200 SMA", self.ticker)
            return -1
        
        # 3. 200 SMA trending up for at least 1 month
        if self.get_30day_trend_ma200() != 1:
            logger.info("mv_strategy %s: 200 SMA not trending up", self.ticker)
            return -1
        
        # 4. Price above 50 SMA (preferred, not required)
        if price50 != -1 and currentPrice > price50:
            logger.info("mv_strategy %s: All Minervini criteria met (including 50 SMA)", self.ticker)
        else:
            logger.info("mv_strategy %s: Core Minervini criteria met", self.ticker)
        
        return 1  
        
    def get_vol(self, checkDays, avrgDays):
        date = dt.date.today()
        vol3day = []
        vol50day = []
        if not self.priceData:
            start_date = date - dt.timedelta(days=365)
            start_ts = _to_epoch_seconds(start_date)
            end_ts = _to_epoch_seconds(date)
            self.priceData = self.get_historical_price_data(start_ts, end_ts, 'daily')
        length = len(self.priceData[self.ticker]['prices'])
        
        # Check if we have enough data
        if length < checkDays:
            logger.warning("get_vol: Insufficient data for %s (length=%d, checkDays=%d)", self.ticker, length, checkDays)
            return [], 0, [], 0
        
        for i in range(checkDays):
            idx = length - 1 - i
            if idx < 0 or idx >= length:
                logger.warning("get_vol: Index out of bounds for %s (idx=%d, length=%d)", self.ticker, idx, length)
                break
            if not(self.priceData[self.ticker]['prices'][idx]['volume']):
                # Use previous day's volume if current is missing (but avoid going out of bounds)
                if idx + 1 < length:
                    self.priceData[self.ticker]['prices'][idx]['volume'] = self.priceData[self.ticker]['prices'][idx+1]['volume']
                else:
                    self.priceData[self.ticker]['prices'][idx]['volume'] = 0
            vol3day.append(self.priceData[self.ticker]['prices'][idx]['volume'])
        #print(vol3day)
        
        # Check if we have enough data for the second loop
        if length < checkDays + 1:
            logger.warning("get_vol: Insufficient data for avgDays calculation for %s (length=%d, checkDays=%d)", self.ticker, length, checkDays)
            return vol3day, np.sum(vol3day)/checkDays if vol3day else 0, [], 0
        
        for i in range(np.min([avrgDays, length - checkDays])):
            idx = length - 1 - checkDays - i
            if idx < 0 or idx >= length:
                logger.warning("get_vol: Index out of bounds for avgDays for %s (idx=%d, length=%d)", self.ticker, idx, length)
                break
            if not(self.priceData[self.ticker]['prices'][idx]['volume']):
                # Use previous day's volume if current is missing (but avoid going out of bounds)
                if idx + 1 < length:
                    self.priceData[self.ticker]['prices'][idx]['volume'] = self.priceData[self.ticker]['prices'][idx+1]['volume']
                else:
                    self.priceData[self.ticker]['prices'][idx]['volume'] = 0
        #    print(self.priceData[self.ticker]['prices'][idx]['volume'])
            vol50day.append(self.priceData[self.ticker]['prices'][idx]['volume'])
        
        # Calculate averages safely
        avgVol3day = np.sum(vol3day) / len(vol3day) if vol3day else 0
        avgVol50day = np.sum(vol50day) / len(vol50day) if vol50day else 0
        
        return vol3day, avgVol3day, vol50day, avgVol50day
    
    @_log_step()
    def vol_strategy(self):
        # Fetch the 3-day and 50-day volume averages
        vol3day, avgVol3day, vol50day, avgVol50day = self.get_vol(3, 200)
        
        # Check if we got valid data
        if avgVol3day == 0 and avgVol50day == 0:
            logger.warning("vol_strategy: No volume data available for %s", self.ticker)
            return -1

        # Check if 3-day average volume is at least 1.5x the 50-day average volume
        if avgVol3day >= algoParas.PEAK_VOL_RATIO* avgVol50day and avgVol50day >= algoParas.VOLUME_THRESHOLD:
            return 1  # Volume condition met based on recent surge
        
        # # Check if 50-day average volume is above a minimum threshold (e.g., 800,000 shares)
        # if avgVol50day >= 800000:
        #     print("Consistent trading interest with 50-day average volume above 800,000 shares.")
        #     return 1  # Volume condition met based on sustained interest

        # If neither condition is met, the strategy fails
        return -1
        
    @_log_step()
    def price_strategy(self):
        closePrice = []
        if not(self.priceData):
            date = dt.date.today()
            start_date = date - dt.timedelta(days=365)
            start_ts = _to_epoch_seconds(start_date)
            end_ts = _to_epoch_seconds(date)
            self.priceData = self.get_historical_price_data(start_ts, end_ts, 'daily')
        length = len(self.priceData[self.ticker]['prices'])
        
        # Check if we have any price data
        if length == 0:
            logger.warning("price_strategy: No price data available for %s", self.ticker)
            return -1
        
        for i in range(length):
            if not(self.priceData[self.ticker]['prices'][i]['close']):
                if i > 0:
                    self.priceData[self.ticker]['prices'][i]['close'] = self.priceData[self.ticker]['prices'][i-1]['close']
                else:
                    # First element has no close price, skip it
                    continue
            closePrice.append(self.priceData[self.ticker]['prices'][i]['close'])
        
        # Check if we collected any close prices
        if not closePrice:
            logger.warning("price_strategy: No valid close prices for %s", self.ticker)
            return -1
        
        lowestPrice = np.min(closePrice)
        if not self.current_stickerPrice:
            self.current_stickerPrice = self.get_current_price()
        currentPrice = self.current_stickerPrice
        
        # Check if currentPrice is valid
        if currentPrice is None:
            logger.warning("price_strategy: No current price available for %s", self.ticker)
            return -1
        
        highestPrice = np.max(closePrice)
    # Calculate range position as a percentage
        if highestPrice == lowestPrice:
            logger.warning("price_strategy: No price variation for %s (highestPrice=%s, lowestPrice=%s)", self.ticker, highestPrice, lowestPrice)
            return -1
        
        range_position = (currentPrice - lowestPrice) / (highestPrice - lowestPrice)

        # Minervini: price within top 25% of 52-week high (range_position >= 0.75)
        if range_position >= algoParas.PRICE_POSITION_LOW:
            logger.info("price_strategy %s: Within top 25%% of 52-week high (%.1f%%)", 
                       self.ticker, range_position * 100)
            return 1  # Passes Minervini price positioning criteria
        
        logger.info("price_strategy %s: Not in top 25%% (at %.1f%%)", self.ticker, range_position * 100)
        return -1  # Fails price strategy
        
    @_log_step()
    def get_price_from_buffer(self, priceDataStruct, startDate, frame):
        selectedPriceDataStruct = []
        ##for each date
        currentDate = dt.date.today()
        dateList = []
        i = 0
        while(True):
            dateList.append(startDate + dt.timedelta(i))
            i = i + 1
            if dateList[-1] == currentDate:
                break
        for dd in dateList:
            for item in priceDataStruct:
                if item['formatted_date'] == str(dd):
                    selectedPriceDataStruct.append(item)
                    frame = frame - 1
                if frame <= 0:
                    break
        return selectedPriceDataStruct
    
    def get_price_from_buffer_start_end(self, priceDataStruct, startDate, endDate):
        selectedPriceDataStruct = []
        ##for each date
        currentDate = dt.date.today()
        dateList = []
        i = 0
        while(True):
            dateList.append(startDate + dt.timedelta(i))
            i = i + 1
            if dateList[-1] == endDate:
                break
        for dd in dateList:
            for item in priceDataStruct:
                if item['formatted_date'] == str(dd):
                    selectedPriceDataStruct.append(item)
        return selectedPriceDataStruct
        
#given start date and a time frame, if no price on that day, just move to next day
    def get_price(self, startDate, frame):
        to_date = startDate + dt.timedelta(frame)
        if not(self.priceData):
            date = dt.date.today()
            start_date = date - dt.timedelta(days=365)
            start_ts = _to_epoch_seconds(start_date)
            end_ts = _to_epoch_seconds(date)
            self.priceData = self.get_historical_price_data(start_ts, end_ts, 'daily')
        #don't need to pull data from remote, use local
        priceDataStruct = self.priceData[self.ticker]['prices']
        selectedPriceDataStruct = self.get_price_from_buffer(priceDataStruct, startDate, frame)
        
                
        return selectedPriceDataStruct
    
    def get_price_ref(self, startDate, frame):
        to_date = startDate + dt.timedelta(frame)
        if not(self.priceData):
            date = dt.date.today()
            start_date = date - dt.timedelta(days=365)
            start_ts = _to_epoch_seconds(start_date)
            end_ts = _to_epoch_seconds(date)
            self.priceData = self.get_historical_price_data(start_ts, end_ts, 'daily')
        #don't need to pull data from remote, use local
        start_ts = _to_epoch_seconds(startDate)
        end_ts = _to_epoch_seconds(to_date)
        priceData = self.get_historical_price_data(start_ts, end_ts, 'daily')
        priceDataStruct = priceData[self.ticker]['prices']    
        return priceDataStruct
    
    def get_highest_in5days(self, startDate):
        priceData = []
        priceDataStruct = self.get_price(startDate, 5)
        tmpLen = len(priceDataStruct)
        for i in range(tmpLen):
            priceData.append(priceDataStruct[i]['close'])
        if not(priceData):
            return [-1, -1]
        else:
            highestPrice = np.max(priceData)
            ind = np.argmax(priceData)
        return highestPrice, priceDataStruct[ind]['formatted_date']
    
    def get_lowest_in5days(self, startDate):
        priceData = []
        priceDataStruct = self.get_price(startDate, 5)
        tmpLen = len(priceDataStruct)
        for i in range(tmpLen):
            priceData.append(priceDataStruct[i]['close'])
        if not(priceData):
            return [-1, -1]
        else:
            lowestPrice = np.min(priceData)
            ind = np.argmin(priceData)
        return lowestPrice, priceDataStruct[ind]['formatted_date']
        
    def find_one_contraction(self, startDate):
        print('start searching date')
        print(startDate)
        date = dt.date.today()
        tmp = date - startDate
        numOfDate = tmp.days
        localHighestPrice = -float('inf')
        localHighestDate = -1
        counter = 0
        counterThr = 5
        flag = True
        for i in range(numOfDate):
            movingDate = startDate + dt.timedelta(i)
            #print(movingDate)
            price, priceDate = self.get_highest_in5days(movingDate)
            if price == -1 and priceDate == -1:
                flag = False
                return flag, -1, -1, -1, -1
            if price > localHighestPrice:
                localHighestPrice = price
                localHighestDate = priceDate
                counter = 0
            else:
                counter = counter + 1
                print('start lock the date')
                print(priceDate)
            if counter >= counterThr or i == numOfDate-1:
                #get local high
                print('find the local highest price')
                print(localHighestPrice)
                print('date is')
                print(localHighestDate)
                break
        if counter < counterThr:
            flag = False
            return flag, -1, -1, -1, -1
            
        #search for local low
        if counter >= counterThr:
            print('start search for lowest price')
            tmp_dt = dt.datetime.strptime(localHighestDate, "%Y-%m-%d")
            localHighestDate_dt = tmp_dt.date()
            tmp = date - localHighestDate_dt
            numOfDate2 = tmp.days
            startDate2 = localHighestDate_dt
            localLowestPrice = float('inf')
            localLowestDate = -1
            counter2 = 0
            for j in range(numOfDate2):
                movingDate2 = startDate2 + dt.timedelta(j)
                price, priceDate = self.get_lowest_in5days(movingDate2)
                if price == -1 and priceDate == -1:
                    break
                if price < localLowestPrice:
                    localLowestPrice = price
                    localLowestDate = priceDate
                    counter2 = 0
                else:
                    counter2 = counter2 + 1
                    logger.info('start lock the date for %s', priceDate)
                if counter2 >= counterThr or j == numOfDate2-1:
                    #get local high
                    logger.info('find the local lowest price: %s', localLowestPrice)
                    logger.info('date is %s', localLowestDate)
                    break
                
        #
        if localHighestPrice == localLowestPrice:
            return False, -1, -1, -1, -1
        return flag, localHighestDate, localHighestPrice, localLowestDate, localLowestPrice
                
    @_log_step()
    def find_volatility_contraction_pattern(self, startDate):
        """
        Finds all contraction patterns starting from the given date.
        Returns a tuple: (count, recordVCP).
        """
        MAX_ITERATIONS = 1000
        recordVCP = []
        self.m_recordVCP = []
        counterForVCP = 0

        while counterForVCP < MAX_ITERATIONS:
            flagForOneContraction, hD, hP, lD, lP = self.find_one_contraction(startDate)

            if not flagForOneContraction:
                break

            recordVCP.append([hD, hP, lD, lP])
            counterForVCP += 1
            startDate = dt.datetime.strptime(lD, "%Y-%m-%d").date()

        self.m_recordVCP = recordVCP
        return counterForVCP, recordVCP
            
    
    @_log_step()
    def get_footPrint(self):
        flag = False
        if not(self.m_recordVCP):
            date_from = (dt.date.today() - dt.timedelta(days=60))
            self.find_volatility_contraction_pattern(date_from)
        length = len(self.m_recordVCP)
        self.m_footPrint=[]
        for i in range(length):            
            self.m_footPrint.append([self.m_recordVCP[i][0], self.m_recordVCP[i][2], (self.m_recordVCP[i][1]-self.m_recordVCP[i][3])/self.m_recordVCP[i][1]])
        return self.m_footPrint
    
    @_log_step()
    def is_pivot_good(self):
        flag = False
        if not(self.m_footPrint):
            self.get_footPrint()
        
        # Check if we have valid footprint and VCP records
        if not self.m_footPrint or not self.m_recordVCP:
            logger.warning("is_pivot_good: No footprint or VCP records for %s", self.ticker)
            return False, None, None, None
        
        #correction within 10% of max price and current price higher then lower boundary
        if not self.current_stickerPrice:
            current = self.get_current_price()
        else:
            current = self.current_stickerPrice
        
        # Check if current price is valid
        if current is None:
            logger.warning("is_pivot_good: No current price available for %s", self.ticker)
            return False, None, None, None
        
        flag = (self.m_footPrint[-1][2] <= algoParas.PIVOT_PRICE_PERC) and (current> self.m_recordVCP[-1][3])
        #report support and pressure
        logger.info("%s current price: %s", self.ticker, current)
        logger.info("%s support price: %s", self.ticker, self.m_recordVCP[-1][3])
        logger.info("%s pressure price: %s", self.ticker, self.m_recordVCP[-1][1])
        return flag, current, self.m_recordVCP[-1][3], self.m_recordVCP[-1][1]
    
    @_log_step()
    def is_correction_deep(self):
        flag = False
        if not(self.m_footPrint):
            self.get_footPrint()
        
        # Check if we have valid footprint data after trying to get it
        if not self.m_footPrint:
            logger.warning("is_correction_deep: No footprint data for %s", self.ticker)
            return False
        
        tmp = np.asarray(self.m_footPrint)
        tmpcorrection = tmp[:,2]
        correction = tmpcorrection.astype(float)
        return correction.max() >= 0.5
    #check the last contraction, is the demand dry

    @_log_step()
    def is_demand_dry(self):
        if not self.m_footPrint:
            self.get_footPrint()
        
        # Check if we have valid footprint data
        if not self.m_footPrint:
            logger.warning("is_demand_dry: No footprint data for %s", self.ticker)
            return False, None, None, [], 0, 0, None, None, [], 0, 0

        # Get the date range from the last footprint entry
        startDate = self.m_footPrint[-1][0]
        endDate = self.m_footPrint[-1][1]
        startDate_dt = dt.datetime.strptime(startDate, "%Y-%m-%d")
        endDate_dt = dt.datetime.strptime(endDate, "%Y-%m-%d")

        # Load price data if not already loaded
        if not self.priceData:
            date = dt.date.today()
            start_date = date - dt.timedelta(days=365)
            start_ts = _to_epoch_seconds(start_date)
            end_ts = _to_epoch_seconds(date)
            self.priceData = self.get_historical_price_data(start_ts, end_ts, 'daily')

        # Fetch volumes for the specific period in the footprint
        priceDataStruct = self.priceData[self.ticker]['prices']
        footprintVolume = self._extract_volume_for_period(priceDataStruct, startDate_dt.date(), endDate_dt.date())

        # Calculate the volume trend using linear regression
        slope, intercept = self._calculate_volume_trend(footprintVolume)
        
        #get past 4 days volume
        recentData = priceDataStruct[-4:]
        if not recentData or len(recentData) == 0:
            logger.warning("is_demand_dry: No recent data for %s", self.ticker)
            return False, startDate, endDate, footprintVolume, slope, intercept, None, None, [], 0, 0
        
        recentStartDate = recentData[0]['formatted_date']
        recentEndDate = recentData[-1]['formatted_date']
        recentVolume = [item['volume'] for item in recentData]
        slopeRecent, interceptRecent = self._calculate_volume_trend(recentVolume)
        slopeRecentPrice, _ = self._calculate_volume_trend([item['close'] for item in recentData])

        # Determine if demand is dry based on slope and volume comparison
        isDry = (slope <= 0) or slopeRecent <= 0
        # exclude the case that the volume is going up slopeRecent is going up and price is going down, which means selling pressure is increasing
        if slopeRecent > 0 and slopeRecentPrice < 0:
            isDry = False
        return isDry, startDate, endDate, footprintVolume, slope, intercept, recentStartDate, recentEndDate, recentVolume, slopeRecent, interceptRecent

    def _extract_volume_for_period(self, priceDataStruct, start_date, end_date):
        """Extracts volume data for a specified period from price data."""
        selected_data = self.get_price_from_buffer_start_end(priceDataStruct, start_date, end_date)
        return [item['volume'] for item in selected_data]

    def _calculate_volume_trend(self, volume_list):
        """Performs linear regression to determine volume trend."""
        x = np.arange(len(volume_list))
        y = np.array(volume_list)
        slope, intercept = np.polyfit(x, y, 1)
        return slope, intercept

    def _calculate_historical_average_volume(self, priceDataStruct, days):
        """Calculates the average volume over the last 'days' period."""
        end_date = dt.date.today()
        start_date = end_date - dt.timedelta(days=days)
        historical_data = self.get_price_from_buffer_start_end(priceDataStruct, start_date, end_date)
        volume_list = [item['volume'] for item in historical_data]
        return np.mean(volume_list) if volume_list else 0
    
    
    @_log_step()
    def combined_best_strategy(self):
        # Check moving average strategy
        s = True
        if self.mv_strategy() != 1:
            s = s and False
        
        # Check volume strategy
        if self.vol_strategy() != 1:
            s = s and False
        
        # Check price strategy
        if self.price_strategy() != 1:
            s = s and False
        
        # Check if the stock is near a good pivot point
        isGoodPivot, currentPrice, supportPrice, resistancePrice = self.is_pivot_good()
        if not isGoodPivot:
            s = s and False
        
        # Check if recent correction is not too deep
        if self.is_correction_deep():
            s = s and False
        
        # Check if demand is drying up (selling pressure has decreased)
        isDemandDry, startDate, endDate, volume_ls, slope, intercept, _, _, _, _, _ = self.is_demand_dry()
        if not isDemandDry:
            s = s and False
        
        # All criteria met, return True for a strong buy signal
        return s



class batch_process:
    tickers = []
    resultsPath = ''
    result_file = ''
    
    def __init__(self, tickers, sectors, market=None):
        """
        Initialize batch processing.
        
        Args:
            tickers (list): List of ticker symbols, or None to use custom market tickers
            sectors (str): Sector name for results file naming
            market (str): Optional market to use custom tickers ('US', 'UK', 'BOTH'). 
                         If provided, tickers parameter will be overridden
        """
        # Import here to avoid circular imports
        from get_tickers import get_custom_tickers
        
        # Use custom tickers if market is specified
        if market:
            self.tickers = get_custom_tickers(market)
            logger.info("Using custom ticker list for market: %s", market)
        else:
            self.tickers = tickers
        
        basePath = find_path()
        current_date = dt.date.today().strftime('%Y-%m-%d')
        self.resultsPath = os.path.join(basePath, 'results', current_date)
        file = sectors + '.json'
        self.result_file = setup_result_file(self.resultsPath, file)
        # Setup market-specific CSV files with __ prefix to sort at top
        self.csv_files = {
            'US': os.path.join(self.resultsPath, '__result_US.csv'),
            'UK': os.path.join(self.resultsPath, '__result_UK.csv'),
            'HK': os.path.join(self.resultsPath, '__result_HK.csv')
        }
        # Setup market-specific image folders
        self.image_folders = {
            'US': os.path.join(self.resultsPath, 'charts_US'),
            'UK': os.path.join(self.resultsPath, 'charts_UK'),
            'HK': os.path.join(self.resultsPath, 'charts_HK')
        }
        for market, csv_file in self.csv_files.items():
            setup_csv_file(csv_file)
        for market, img_folder in self.image_folders.items():
            os.makedirs(img_folder, exist_ok=True)
            logger.info("Created image folder: %s", img_folder)
        logger.info("Initialized batch_process for %d tickers; results -> %s, csv -> %s", len(self.tickers), self.result_file, list(self.csv_files.values())) 
            
    def batch_strategy(self):
        superStock=[]
        total = np.size(self.tickers)
        start_time = time.time()
        logger.info("Starting batch_strategy for %d tickers", total)
        for i in range(total):
            try:
                ticker = self.tickers[i]
                logger.info("Processing %d/%d: %s", i+1, total, ticker)
                x = cookFinancials(ticker)
                s1=0
                s2=0
                s3=0
                if x.mv_strategy()==1:
                    s1 = 1
                    logger.info("passing moving average strategy for %s", ticker)
                if x.vol_strategy() == 1: #not from original book, not working
                    s2 = 1
                    logger.info("passing 3 day volume strategy for %s", ticker)
                if x.price_strategy() == 1:
                    s3 = 1
                    logger.info("passing price strategy for %s", ticker)
                #if s1==1 and s2==1 and s3==1:
                if s1==1 and s3==1 and s2:
                    logger.info("congrats, %s passes strategies", ticker)
                    superStock.append(ticker)    
                append_to_json(self.result_file, ticker)
            except Exception:
                logger.exception("Error processing ticker %s", self.tickers[i])
                pass
        logger.info("batch_strategy finished; candidates=%d, elapsed=%.2fs", len(superStock), time.time()-start_time)
        
            
    def batch_pipeline_full(self):
        superStock=[]
        total = np.size(self.tickers)
        date_from = (dt.date.today() - dt.timedelta(days=100))
        date_to = (dt.date.today())
        start_time = time.time()
        logger.info("Starting batch_pipeline_full for %d tickers", total)

        # Optionally prefetch historical price data for the entire batch (concurrent)
        price_map = None
        if PREFETCH_ENABLED and total > 1:
            try:
                days = HISTORICAL_DAYS_DEFAULT
                logger.info("Prefetching last %d days of historical price data concurrently for %d tickers", days, total)
                try:
                    start_date = dt.date.today() - dt.timedelta(days=days)
                    end_date = dt.date.today()
                    
                    # Use yfinance download for multiple tickers
                    hist_data = yf.download(self.tickers, start=start_date, end=end_date, group_by='ticker', progress=False)
                    
                    # Convert to expected format
                    price_map = {}
                    for ticker in self.tickers:
                        try:
                            if len(self.tickers) > 1:
                                ticker_data = hist_data[ticker]
                            else:
                                ticker_data = hist_data
                            
                            prices = []
                            for idx, row in ticker_data.iterrows():
                                if pd.notna(row['Close']):
                                    prices.append({
                                        'formatted_date': idx.strftime('%Y-%m-%d'),
                                        'date': int(idx.timestamp()),
                                        'open': row['Open'],
                                        'high': row['High'],
                                        'low': row['Low'],
                                        'close': row['Close'],
                                        'volume': row['Volume'],
                                        'adjclose': row['Close']
                                    })
                            price_map[ticker] = {'prices': prices}
                            _cache_save(ticker, days, {ticker: {'prices': prices}})
                        except Exception:
                            logger.debug("Failed to process prefetch for %s", ticker, exc_info=True)
                    
                    logger.info("Prefetch complete")
                except Exception:
                    logger.exception("Prefetch failed; continuing without prefetch")
                    price_map = None
            except Exception:
                logger.debug("Prefetch decision failed", exc_info=True)

        for idx in range(total):
            try:
                ticker = self.tickers[idx]
                logger.info("Processing %d/%d: %s", idx+1, total, ticker)
                # start a heartbeat thread so we get periodic "still processing" logs
                start_t = time.time()
                heartbeat = _start_heartbeat(ticker, interval=30)
                try:
                    logger.info("Starting pipeline for %s", ticker)
                    t0 = time.time()
                    # If we have a prefetch price_map, pass it in to avoid per-ticker downloads
                    if price_map:
                        x = cookFinancials(ticker, priceData=price_map, fetch_days=HISTORICAL_DAYS_DEFAULT)
                    else:
                        x = cookFinancials(ticker)
                    
                    # Get current price first for CSV output (needed for all tickers)
                    if not x.current_stickerPrice:
                        x.current_stickerPrice = x.get_current_price()
                    currentPrice = x.current_stickerPrice
                    
                    # Check for swing trade entry signal (for all tickers)
                    isSwingEntry, swingDetails = x.is_swing_trade_entry()
                    logger.info("swing_trade_entry=%s for %s", isSwingEntry, ticker)
                    
                    # Try to get basic pivot data (for all tickers)
                    try:
                        # Run VCP analysis to get pivot data
                        counter, record = x.find_volatility_contraction_pattern(date_from)
                        footprint = x.get_footPrint()
                        isGoodPivot, currentPrice, supportPrice, pressurePrice = x.is_pivot_good()
                        
                        if currentPrice is None or supportPrice is None or pressurePrice is None:
                            # Use fallback values if pivot analysis fails
                            supportPrice = currentPrice if currentPrice else 0
                            pressurePrice = currentPrice if currentPrice else 0
                            isGoodPivot = False
                        
                        isDeepCor = x.is_correction_deep()
                        isDemandDry, startDate, endDate, volume_ls, slope, interY, recentStart, recentEnd, volume_re, slopeRecet, interYRecent = x.is_demand_dry()
                    except Exception:
                        logger.exception("Error in analysis for %s, using defaults", ticker)
                        supportPrice = currentPrice if currentPrice else 0
                        pressurePrice = currentPrice if currentPrice else 0
                        isGoodPivot = False
                        isDeepCor = False
                        isDemandDry = False
                        counter = 0
                        volume_ls = []
                        volume_re = []
                    
                    # Initialize figName
                    figName = ''
                    
                    # Create charts for all tickers (moved outside combined_best_strategy check)
                    t1 = time.time()
                    sp = x.get_price(date_from, 100)
                    logger.info("get_price for %s finished in %.2fs", ticker, time.time()-t1)
                    tmpLen = len(sp)
                    date = []
                    price = []
                    volume = []
                    for i in range(tmpLen):
                        date.append(sp[i]['formatted_date'])
                        price.append(sp[i]['close'])
                        volume.append(sp[i]['volume'])
                    
                    # create figure and axis objects with subplots()
                    fig,ax = plt.subplots(2)
                    fig.suptitle(x.ticker)
                    # make a plot
                    ax[0].plot(date, price, color="blue", marker="o")
                    # set x-axis label
                    ax[0].set_xlabel("date",fontsize=14)
                    # set y-axis label
                    ax[0].set_ylabel("stock price",color="blue",fontsize=14)
                    
                    # twin object for two different y-axis on the sample plot
                    # make a plot with different y-axis using second axis object
                    ax[1].bar(date, np.asarray(volume)/10**6 ,color="green")
                    ax[1].set_ylabel("volume (m)",color="green",fontsize=14)
                    
                    # Set x-ticks to display every 10th date and include the last date
                    xticks = np.arange(0, len(date), 10).tolist()
                    if len(date) - 1 not in xticks:  # Check if the last date is already included
                        xticks.append(len(date) - 1)  # Add the last date index to x-ticks

                    ax[0].set_xticks(xticks)
                    ax[1].set_xticks(xticks)

                    # Format date labels for readability
                    fig.autofmt_xdate(rotation=45)
                    
                    logger.info("Highest in 5 days for %s: %s", ticker, x.get_highest_in5days(date_from))
                    
                    # Create ticker data for JSON
                    ticker_data = {ticker:{'current price':str(currentPrice), 'support price':str(supportPrice), 'pressure price':str(pressurePrice), \
                                'is_good_pivot':str(isGoodPivot), 'is_deep_correction':str(isDeepCor), 'is_demand_dry': str(isDemandDry), \
                                'swing_trade_entry': str(isSwingEntry), 'ema_8': str(swingDetails.get('ema_8', 'N/A')), 'sma_200': str(swingDetails.get('sma_200', 'N/A'))}}
                    
                    # Plot VCP patterns if found
                    if counter > 0:
                        logger.info("Found %d VCP pattern(s) for %s", counter, ticker)
                        for i in range(counter):
                            ax[0].plot([record[i][0], record[i][2]], [record[i][1], record[i][3]], 'r')
                        
                        # Plot volume trend lines if we have the data
                        if volume_ls:
                            for ind, item in enumerate(date):
                                if item == startDate:
                                    logger.info("start index for demand dry for %s: %d", ticker, ind)
                                    break
                            
                            x_axis = []
                            for i in range(len(volume_ls)):
                                x_axis.append(ind+i)
                            x_axis = np.array(x_axis)
                            
                            y = slope*x_axis-slope*ind + volume_ls[0]
                            ax[1].plot(np.asarray(date)[x_axis], y/10**6, color="red",linewidth=4)
                            
                            if volume_re:
                                for ind, item in enumerate(date):
                                    if item == recentStart:
                                        logger.info("recent start index for %s: %d", ticker, ind)
                                        break
                                
                                x_axis = []
                                for i in range(len(volume_re)):
                                    x_axis.append(ind+i)
                                x_axis = np.array(x_axis)
                                yRecent = slopeRecet*x_axis-slopeRecet*ind + volume_re[0]
                                ax[1].plot(np.asarray(date)[x_axis], yRecent/10**6, color="red",linewidth=4)
                    
                    fig.show()
                    
                    # Determine market and use market-specific image folder
                    market = get_ticker_market(ticker)
                    img_folder = self.image_folders.get(market, self.image_folders['US'])
                    figName = os.path.join(img_folder, ticker+'.jpg')
                    # Save chart for all stocks with VCP patterns OR meeting buy criteria
                    if counter > 0 or (isGoodPivot and not(isDeepCor) and isDemandDry):
                        fig.savefig(figName,
                                    format='jpeg',
                                    dpi=100,
                                    bbox_inches='tight')
                        logger.info("Saved figure %s", figName)
                        ticker_data[ticker]['fig'] = figName
                    else:
                        figName = ''  # No chart saved if no VCP and doesn't meet criteria
                    
                    # Add to JSON for all tickers
                    append_to_json(self.result_file, ticker_data)
                    
                    # Check combined strategy for superStock tracking
                    flag = x.combined_best_strategy()
                    logger.info("combined_best_strategy for %s: %s (finished in %.2fs)", ticker, flag, time.time()-t0)
                    if flag == True:
                        logger.info("%s passes combined strategy", ticker)
                        superStock.append(ticker)
                    
                    # Write to CSV for ALL tickers (after chart generation for passing stocks)
                    market = get_ticker_market(ticker)
                    csv_file = self.csv_files.get(market, self.csv_files['US'])
                    append_to_csv(csv_file, ticker, currentPrice if currentPrice else 0, 
                                 supportPrice, pressurePrice, 
                                 isGoodPivot, isDeepCor, isDemandDry, isSwingEntry)
                finally:
                    # stop heartbeat and log per-ticker total elapsed
                    heartbeat.set()
                    logger.info("Processing complete for %s; elapsed=%.2fs", ticker, time.time()-start_t)
            except Exception:
                logger.exception("Error processing ticker %s", ticker)
                pass
        logger.info("batch_pipeline_full finished; candidates=%d, elapsed=%.2fs", len(superStock), time.time()-start_time)
        
        # Sort all CSV files by Buy Signal
        for market, csv_file in self.csv_files.items():
            sort_csv_by_buy_signal(csv_file)
        logger.info("CSV files sorted by Buy Signal")

            
    def batch_financial(self):       
        for i in range(np.size(self.tickers)):
            try:
                print(self.tickers[i])
                x = cookFinancials(self.tickers[i])
                bv = x.get_BV(20)
                bv.insert(0, x.get_book_value())
                print(bv)
                bvgr = x.get_BV_GR_median(bv)
                print(bvgr)
                growth = bvgr[1]
                cEPS = x.get_earnings_per_share()
                print(cEPS)
                years = 3;
                rRate = 0.25;
                safty = 0.5
                PE = x.get_PE()
                price=x.get_suggest_price(cEPS, growth, years, rRate, PE, safty)
                print(price)
                stickerPrice = x.current_stickerPrice
                decision = x.get_decision(price[1],stickerPrice)
                print(decision)
                y2pb = 0
                roic = 0
                mcap = 0
                cashflow = 0
                priceSales = 0
                if decision == 'strong buy':
                    y2pb = x.payBackTime(stickerPrice, cEPS, growth)
                    roic = x.get_ROIC()
                    mcap = x.get_marketCap_B()
                    cashflow = (x.get_totalCashFromOperatingActivities())
                    priceSales = x.get_pricetoSales()               
                s = {
                    self.tickers[i]:{
                        "decision":decision,
                        "suggested price":price[1],
                        "stock price":stickerPrice,                     
                        "Payback years": y2pb,
                        "Book Value": bv,
                        "ROIC": roic,
                        "market cap (b)": mcap,
                        "cashflow": cashflow,
                        "priceSalesRatio":priceSales,
                        "PE": PE
                    }
                }
                print(s)
                with open(self.jsfile, "r") as f:
                    data = js.load(f)
                    cont = data['data']
                    cont.append(s)
                with open(self.jsfile, "w") as f:
                    js.dump(data, f, indent=4) 
                print('=====================================')
            except Exception:
                print("error!")
                pass
            
def load_json(filepath):
    with open(filepath, "r") as f:
        return js.load(f)

def save_json(filepath, data):
    with open(filepath, "w") as f:
        js.dump(data, f, indent=4)

def append_to_json(filepath, ticker_data):
    data = load_json(filepath)
    data['data'].append(ticker_data)
    save_json(filepath, data)

def setup_result_file(basePath, file):
    # check if each level directory exists
    if not os.path.exists(basePath):
        os.makedirs(basePath)
    filepath = os.path.join(basePath, file)
    save_json(filepath, {"data": []})
    return filepath

def setup_csv_file(filepath):
    """Initialize CSV file with headers, replacing any existing file."""
    import csv
    basedir = os.path.dirname(filepath)
    if not os.path.exists(basedir):
        os.makedirs(basedir)
    # Always create fresh CSV file with headers (overwrite if exists)
    with open(filepath, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Ticker', 'Buy Signal', 'Sell Signal', 'Swing Trade Entry', 'Current Price', 'Support Price', 'Pressure Price', 
                        'Price to Support %', 'Good Pivot', 'Deep Correction', 'Demand Dry'])
    logger.info("Created/reset CSV file: %s", filepath)

def append_to_csv(filepath, ticker, current_price, support_price, pressure_price,
                 is_good_pivot, is_deep_correction, is_demand_dry, is_swing_trade_entry):
    """Append a row to the CSV file."""
    import csv
    # Calculate buy signal: True if all conditions met
    buy_signal = 'YES' if (is_good_pivot and not is_deep_correction and is_demand_dry) else 'NO'
    
    # Calculate sell signal: 
    # - Deep correction (>50% drop) = breakdown
    # - Price below support AND not good pivot = broken support
    # - Demand NOT dry AND deep correction = distribution phase
    sell_signal = 'YES' if (is_deep_correction or 
                           (not is_good_pivot and current_price < support_price) or
                           (is_deep_correction and not is_demand_dry)) else 'NO'
    
    # Swing trade entry signal
    swing_entry = 'YES' if is_swing_trade_entry else 'NO'
    
    # Calculate price to support as percentage: ((current_price - support_price) / support_price) * 100
    try:
        support_val = float(support_price)
        if support_val != 0:
            price_to_support = round(((float(current_price) - support_val) / support_val) * 100, 2)
        else:
            price_to_support = 0
    except (ValueError, TypeError):
        price_to_support = 0
    
    with open(filepath, 'a', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([ticker, buy_signal, sell_signal, swing_entry, current_price, support_price, pressure_price,
                        price_to_support, is_good_pivot, is_deep_correction, is_demand_dry])

def get_ticker_market(ticker):
    """Determine the market from ticker suffix.
    
    Returns:
        'US', 'UK', or 'HK' based on ticker suffix
    """
    ticker_upper = ticker.upper()
    if '.L' in ticker_upper:  # London Stock Exchange
        return 'UK'
    elif '.HK' in ticker_upper:  # Hong Kong Stock Exchange
        return 'HK'
    else:  # Default to US (no suffix or other suffixes)
        return 'US'

def sort_csv_by_buy_signal(filepath):
    """Sort CSV file by Buy Signal (YES first), then by Price to Support % (smallest percentage first), then Sell Signal (YES last)."""
    import csv
    try:
        # Read all rows
        with open(filepath, 'r', newline='') as f:
            reader = csv.reader(f)
            header = next(reader)
            rows = list(reader)
        
        # Skip if no data rows
        if not rows:
            return
        
        # Sort by: Buy Signal (YES first), then Price to Support % (smallest percentage first for buy signals), then Sell Signal (NO first)
        # Using tuple sort: (not buy_yes, price_to_support_pct if buy_yes else large_number, sell_yes)
        def sort_key(row):
            buy_yes = row[1] == 'YES'
            sell_yes = row[2] == 'YES'
            try:
                # Price to Support % is at index 7 (after Pressure Price)
                price_to_support_pct = float(row[7]) if buy_yes else float('inf')
            except (ValueError, IndexError):
                price_to_support_pct = float('inf')
            return (not buy_yes, price_to_support_pct, sell_yes)
        
        rows.sort(key=sort_key)
        
        # Write back sorted data
        with open(filepath, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(header)
            writer.writerows(rows)
        
        logger.info("Sorted CSV file: %s", filepath)
    except Exception:
        logger.exception("Failed to sort CSV file: %s", filepath)