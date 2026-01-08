# Getting Started

```bash
python3.10 -m venv venv
source venv/bin/activate
```

```bash
python batch/cookStockPipeline.py
python batch/runBatch_customTickers.py

python test/runTest_cookStock_basic.py
python test/test_yfinance_migration.py
```

```bash
pip freeze > requirements.txt
pip install -r requirements.txt
```