# Custom Ticker Lists - Usage Guide

## Overview
The codebase now supports custom ticker lists for US and UK markets. You can easily switch between sector-based filtering and predefined custom ticker lists.

## Changes Made

### 1. Updated `get_tickers.py`
Added two static arrays:
- **`CUSTOM_TICKERS_US`**: 50 major US stocks (AAPL, MSFT, GOOGL, etc.)
- **`CUSTOM_TICKERS_UK`**: 50 major UK stocks (AZN.L, SHEL.L, HSBA.L, etc.)

Added new function:
```python
get_custom_tickers(market='US')
```
- **Parameters**: `market` - Options: 'US', 'UK', or 'BOTH'
- **Returns**: List of ticker symbols

### 2. Updated `batch_process` class in `cookStock.py`
Enhanced the `__init__` method with a new `market` parameter:
```python
batch_process(tickers, sectors, market=None)
```
- **tickers**: List of ticker symbols (can be None if using market parameter)
- **sectors**: Sector name for results file naming
- **market**: Optional - 'US', 'UK', or 'BOTH' to use custom tickers

## Usage Examples

### Method 1: Using `get_custom_tickers()` function

```python
from get_tickers import get_custom_tickers
from cookStock import batch_process

# Get US tickers
us_tickers = get_custom_tickers('US')
y = batch_process(us_tickers, 'CustomUS')
y.batch_pipeline_full()

# Get UK tickers
uk_tickers = get_custom_tickers('UK')
y = batch_process(uk_tickers, 'CustomUK')
y.batch_pipeline_full()

# Get both US and UK tickers
both_tickers = get_custom_tickers('BOTH')
y = batch_process(both_tickers, 'CustomUS_UK')
y.batch_pipeline_full()
```

### Method 2: Using `market` parameter directly

```python
from cookStock import batch_process

# For US market (simpler approach)
y = batch_process(None, 'CustomUS', market='US')
y.batch_pipeline_full()

# For UK market
y = batch_process(None, 'CustomUK', market='UK')
y.batch_pipeline_full()

# For both markets
y = batch_process(None, 'CustomBoth', market='BOTH')
y.batch_pipeline_full()
```

### Method 3: Mix custom tickers with your own list

```python
from get_tickers import get_custom_tickers
from cookStock import batch_process

# Start with US custom tickers and add your own
my_tickers = get_custom_tickers('US')
my_tickers.extend(['TSLA', 'COIN', 'SHOP'])  # Add additional tickers

y = batch_process(my_tickers, 'Custom_Mixed')
y.batch_pipeline_full()
```

## Example Scripts

### Quick Start Script
Run the example script to see all usage patterns:
```bash
python batch/runBatch_customTickers.py
```

### Updated Pipeline Script
The main pipeline script (`cookStockPipeline.py`) has been updated with commented examples showing how to use custom tickers.

## Customizing Ticker Lists

To customize the ticker lists, edit the arrays in `src/get_tickers.py`:

```python
# Add or remove tickers as needed
CUSTOM_TICKERS_US = [
    'AAPL', 'MSFT', 'GOOGL',  # Tech
    'JPM', 'BAC', 'WFC',      # Finance
    # ... add more
]

CUSTOM_TICKERS_UK = [
    'AZN.L', 'SHEL.L', 'HSBA.L',  # Major UK stocks
    # ... add more
]
```

**Note**: UK stocks use the `.L` suffix for London Stock Exchange listings.

## Benefits

1. **Predefined Lists**: No need to filter by sector every time
2. **Flexibility**: Easy to switch between US, UK, or combined markets
3. **Customizable**: Simple to modify the static arrays for your needs
4. **Backward Compatible**: Original sector-based filtering still works

## Files Modified

1. **`src/get_tickers.py`**
   - Added `CUSTOM_TICKERS_US` array
   - Added `CUSTOM_TICKERS_UK` array
   - Added `get_custom_tickers()` function

2. **`src/cookStock.py`**
   - Updated `batch_process.__init__()` with `market` parameter

3. **`batch/cookStockPipeline.py`**
   - Added examples showing how to use custom tickers

4. **`batch/runBatch_customTickers.py`** (NEW)
   - Complete example script demonstrating all usage patterns

## Notes

- The custom ticker lists contain ~50 major stocks each
- UK tickers use the `.L` suffix for London Stock Exchange
- You can easily modify the lists to include your preferred stocks
- The market parameter is optional - if not provided, the original behavior is preserved
