#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Example script demonstrating how to use custom ticker lists
for US and UK markets.

Usage:
    python runBatch_customTickers.py [market]
    
    market: hk | us | uk | all (default: all)

Created on Wednesday 01/08/2026
@author: GitHub Copilot
"""
from importlib import reload
import os
import sys

# Set cookstock path
def find_path():
    """Find the 'cookstock' project root quickly."""
    import subprocess

    # 1) env var override
    env_path = os.environ.get('COOKSTOCK_PATH')
    if env_path:
        p = os.path.expanduser(env_path)
        if os.path.isdir(p):
            print(f"Using COOKSTOCK_PATH={p}")
            return os.path.abspath(p)

    # 2) search upward from this file (or cwd)
    try:
        start = os.path.dirname(__file__)
    except NameError:
        start = os.getcwd()
    p = os.path.abspath(start)
    while True:
        if os.path.basename(p).lower() == 'cookstock':
            print(f"Found cookstock by upward search: {p}")
            return p
        parent = os.path.dirname(p)
        if parent == p:
            break
        p = parent

    # 3) try git root
    try:
        git_root = subprocess.check_output(['git', 'rev-parse', '--show-toplevel'], stderr=subprocess.DEVNULL).decode().strip()
        if os.path.basename(git_root).lower() == 'cookstock':
            print(f"Found cookstock via git root: {git_root}")
            return git_root
    except Exception:
        pass

    # 4) common locations
    common = ['~/Sources/cookstock', '~/cookstock', '~/Projects/cookstock']
    for c in common:
        cpath = os.path.expanduser(c)
        if os.path.isdir(cpath):
            print(f"Found cookstock in common path: {cpath}")
            return os.path.abspath(cpath)

    print("Could not find 'cookstock' project root. Set COOKSTOCK_PATH env var to override.")
    return None

# Set cookstock path
basePath = find_path()
if not basePath:
    print("Error: 'cookstock' folder not found. Please set COOKSTOCK_PATH or run from inside the repo.")
    sys.exit(1)

# src path
srcPath = os.path.join(basePath, 'src')
print("Adding to sys.path:", srcPath)
sys.path.insert(0, srcPath)

import cookStock
reload(cookStock)
from cookStock import batch_process

import get_tickers
reload(get_tickers)
from get_tickers import get_custom_tickers

# ============================================================================
# Parse command line arguments
# ============================================================================
# Get market parameter from command line (default: 'all')
market_param = sys.argv[1].lower() if len(sys.argv) > 1 else 'all'

# Validate market parameter
valid_markets = ['hk', 'us', 'uk', 'all']
if market_param not in valid_markets:
    print(f"Error: Invalid market parameter '{market_param}'")
    print(f"Valid options: {', '.join(valid_markets)}")
    sys.exit(1)

print("\n" + "="*70)
print(f"Running Custom Tickers Analysis - Market: {market_param.upper()}")
print("="*70)

# ============================================================================
# Process based on market parameter
# ============================================================================
if market_param == 'us':
    # Process US market only
    print("\nProcessing US Market")
    us_tickers = get_custom_tickers('US')
    print(f"Processing {len(us_tickers)} US stocks")
    print(f"First 5 tickers: {us_tickers[:5]}")
    
    y_us = batch_process(us_tickers, 'CustomUS')
    y_us.batch_pipeline_full()

elif market_param == 'uk':
    # Process UK market only
    print("\nProcessing UK Market")
    uk_tickers = get_custom_tickers('UK')
    print(f"Processing {len(uk_tickers)} UK stocks")
    print(f"First 5 tickers: {uk_tickers[:5]}")
    
    y_uk = batch_process(uk_tickers, 'CustomUK')
    y_uk.batch_pipeline_full()

elif market_param == 'hk':
    # Process HK market only
    print("\nProcessing HK Market")
    hk_tickers = get_custom_tickers('HK')
    print(f"Processing {len(hk_tickers)} HK stocks")
    print(f"First 5 tickers: {hk_tickers[:5]}")
    
    y_hk = batch_process(hk_tickers, 'CustomHK')
    y_hk.batch_pipeline_full()

else:  # market_param == 'all'
    # Process all markets
    print("\nProcessing ALL Markets (US + UK + HK)")
    all_tickers = get_custom_tickers('ALL')
    print(f"Processing {len(all_tickers)} stocks (US + UK + HK)")
    print(f"First 5 tickers: {all_tickers[:5]}")
    print(f"Last 5 tickers: {all_tickers[-5:]}")
    
    y_all = batch_process(all_tickers, 'CustomALL')
    y_all.batch_pipeline_full()

print("\n" + "="*70)
print("Processing completed!")
print("="*70)

