#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Example script demonstrating how to use custom ticker lists
for US and UK markets.

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
# EXAMPLE 1: Using custom US tickers
# ============================================================================
print("\n" + "="*70)
print("EXAMPLE 1: Using Custom US Tickers")
print("="*70)

# Get custom US tickers
us_tickers = get_custom_tickers('US')
print(f"Processing {len(us_tickers)} US stocks")
print(f"First 5 tickers: {us_tickers[:5]}")

# Create batch processor with custom US tickers
y_us = batch_process(us_tickers, 'CustomUS')
y_us.batch_pipeline_full()  # Uncomment to run

# ============================================================================
# EXAMPLE 2: Using custom UK tickers
# ============================================================================
print("\n" + "="*70)
print("EXAMPLE 2: Using Custom UK Tickers")
print("="*70)

# Get custom UK tickers
uk_tickers = get_custom_tickers('UK')
print(f"Processing {len(uk_tickers)} UK stocks")
print(f"First 5 tickers: {uk_tickers[:5]}")

# Create batch processor with custom UK tickers
y_uk = batch_process(uk_tickers, 'CustomUK')
y_uk.batch_pipeline_full()  # Uncomment to run

# ============================================================================
# EXAMPLE 3: Using ALL markets (US + UK + HK)
# ============================================================================
print("\n" + "="*70)
print("EXAMPLE 3: Using ALL Markets (US + UK + HK)")
print("="*70)

# Get all tickers from US, UK, and HK markets
all_tickers = get_custom_tickers('ALL')
print(f"Processing {len(all_tickers)} stocks (US + UK + HK)")
print(f"First 5 tickers: {all_tickers[:5]}")
print(f"Last 5 tickers: {all_tickers[-5:]}")

# Create batch processor with all market tickers
y_all = batch_process(all_tickers, 'CustomALL')
y_all.batch_pipeline_full()  # Uncomment to run

# ============================================================================
# EXAMPLE 4: Using market parameter directly in batch_process
# ============================================================================
# NOTE: This example is commented out because it duplicates Examples 1-3 above.
# It demonstrates an alternative syntax using the market= parameter, but produces
# identical results. Uncomment only if you want to see this alternative approach.
#
# print("\n" + "="*70)
# print("EXAMPLE 4: Using Market Parameter in batch_process")
# print("="*70)
#
# # Create batch processor using market parameter (no need to call get_custom_tickers)
# # This will automatically use the custom US ticker list
# y_market_us = batch_process(None, 'CustomUS_Direct', market='US')
# print(f"Initialized with {len(y_market_us.tickers)} US tickers via market parameter")
#
# # For UK market
# y_market_uk = batch_process(None, 'CustomUK_Direct', market='UK')
# print(f"Initialized with {len(y_market_uk.tickers)} UK tickers via market parameter")
#
# # For both markets
# y_market_both = batch_process(None, 'CustomBoth_Direct', market='BOTH')
# print(f"Initialized with {len(y_market_both.tickers)} tickers (US+UK) via market parameter")
#
# # Uncomment below to run the pipeline
# y_market_us.batch_pipeline_full()

print("\n" + "="*70)
print("All examples completed. Uncomment the .batch_pipeline_full() lines to run.")
print("="*70)
