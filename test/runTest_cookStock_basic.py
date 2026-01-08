#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Jan  9 00:10:18 2021

@author: sxu
"""
from importlib import reload # python 2.7 does not require this
import sys
import os

def find_path():
        """Find the 'cookstock' project root quickly.

        Strategy (fast):
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
                return os.path.abspath(p)

        # 2) search upward from this file (or cwd)
        try:
            start = os.path.dirname(__file__)
        except NameError:
            start = os.getcwd()
        p = os.path.abspath(start)
        while True:
            if os.path.basename(p).lower() == 'cookstock':
                return p
            parent = os.path.dirname(p)
            if parent == p:
                break
            p = parent

        # 3) try git root
        try:
            git_root = subprocess.check_output(['git', 'rev-parse', '--show-toplevel'], stderr=subprocess.DEVNULL).decode().strip()
            if os.path.basename(git_root).lower() == 'cookstock':
                return git_root
        except Exception:
            pass

        # 4) common locations
        common = ['~/Sources/cookstock', '~/cookstock', '~/Projects/cookstock']
        for c in common:
            cpath = os.path.expanduser(c)
            if os.path.isdir(cpath):
                return os.path.abspath(cpath)

        return None

#set cookstock path
print("Finding cookstock path...")
basePath = find_path()
if not basePath:
    print("Error: 'cookstock' folder not found. Please set COOKSTOCK_PATH env var or run from inside the repo.")
    sys.exit(1)
#src path
print("Base path found:", basePath)
srcPath = os.path.join(basePath, 'src')

#how to get the path right
#where I am running the code from
print("Adding to sys.path:", srcPath)
sys.path.insert(0, srcPath)

print("Importing cookStock...")

import cookStock
reload(cookStock)
from cookStock import *
import pandas as pd

print("Creating cookFinancials object...")

x = cookFinancials('AAPL')

print('Ticker:',x.ticker)

print(x.get_balanceSheetHistory_quarter())

print(x.get_incomeStatementHistory_quarter())

print(x.get_cashflowStatementHistory_quarter())

print(x.get_BV_quarter())

print(x.get_summary_data())

bv = x.get_BV_quarter()
print(x.get_GR_median(bv))
print(x.get_earningsperShare())

bv = x.get_BV()
print(x.get_GR_median(bv))

bv = x.get_BV(20)
bv.insert(0, x.get_book_value())
print(x.ticker,'book value',bv)
bvgr = x.get_BV_GR_median(bv)
print(bvgr)
growth = bvgr[1]
cEPS = x.get_earnings_per_share()
years = 3;
rRate = 0.25;
safty = 0.5
PE = x.get_PE()
price=x.get_suggest_price(cEPS, growth, years, rRate, PE, safty)                
print(price)
stickerPrice = x.get_current_price()
decision = x.get_decision(price[1],stickerPrice)
print(decision)