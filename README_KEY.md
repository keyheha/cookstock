# Getting Started

```bash
/opt/homebrew/bin/python3.9 -m venv venv
source venv/bin/activate

conda env create -f env_mac.yml
conda activate cookStock
```

```bash
python batch/cookStockPipeline.py

python test/runTest_cookStock_basic.py
python test/test_yf_historical.py
```

```bash
pip freeze > requirements.txt
pip install -r requirements.txt
```