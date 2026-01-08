###a high level script to run the whole pipeline
# runBatch_cookStock_stage2template.py
# get super stocks
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tuesday 11/12/2024

@author: sxu
"""
from importlib import reload # python 2.7 does not require this
import os
import sys
#set cookstock path
def find_path():
    """Find the 'cookstock' project root quickly.

    Strategy:
    - honor COOKSTOCK_PATH environment variable if set
    - walk upward from this file's directory (or cwd) and look for a parent named 'cookstock'
    - try to use git to find the repo root if available
    - check a few common locations
    Returns absolute path or None.
    """
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

# set cookstock path
basePath = find_path()
if not basePath:
    print("Error: 'cookstock' folder not found. Please set COOKSTOCK_PATH or run from inside the repo.")
    sys.exit(1)
#src path
srcPath = os.path.join(basePath, 'src')
print("Adding to sys.path:", srcPath)
sys.path.insert(0, srcPath)

import matplotlib.pyplot as plt
import cookStock
reload(cookStock)
from cookStock import *


from importlib import reload # python 2.7 does not require this
import get_tickers
reload(get_tickers)
from get_tickers import *

        
#filtered_by_sector = ['VNRX', 'INFU']
#get name of the file from the sector and date automatically
current_date = dt.date.today().strftime("%m_%d_%Y")

#set sector names to be run
# sectorCollection = [SectorConstants.TECH, SectorConstants.HEALTH_CARE, SectorConstants.BASICS, SectorConstants.SERVICES, SectorConstants.FINANCE, SectorConstants.ENERGY, SectorConstants.NON_DURABLE_GOODS, SectorConstants.DURABLE_GOODS]

sectorCollection = [SectorConstants.TECH, SectorConstants.HEALTH_CARE,SectorConstants.FINANCE, SectorConstants.ENERGY]

# sectorCollection = [SectorConstants.TECH]

sectorName = []
selected = [] 
for sector in sectorCollection:
    filtered_by_sector = get_tickers_filtered(sectors=sector)
    #remove underscore in sector name
    sector = sector.replace(" ", "")
    sectorName.append(sector)
    for i in filtered_by_sector: 
        if i not in selected: 
            selected.append(i) 

#convert sectorCollection to a file name
sectorNameStr = '_'.join(sectorName)

# selected = ['DSP']

# ============================================================================
# OPTION 1: Use sector-filtered tickers (original approach)
# ============================================================================
y = batch_process(selected, sectorNameStr)
y.batch_pipeline_full()

# ============================================================================
# OPTION 2: Use custom ticker lists by market
# ============================================================================
# Uncomment one of the following to use custom ticker lists:

# For US market only:
# y_us = batch_process(None, 'CustomUS', market='US')
# y_us.batch_pipeline_full()

# For UK market only:
# y_uk = batch_process(None, 'CustomUK', market='UK')
# y_uk.batch_pipeline_full()

# For both US and UK markets:
# y_both = batch_process(None, 'CustomUS_UK', market='BOTH')
# y_both.batch_pipeline_full()


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

def setup_result_file(basePath, file_prefix, current_date):
    filepath = os.path.join(basePath, 'results', f"{file_prefix}_vcp_study_{current_date}.json")
    save_json(filepath, {"data": []})
    return filepath