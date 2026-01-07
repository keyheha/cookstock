# Logging

The pipeline emits structured progress logs to the console (INFO level by default).

To see more verbose output set the `LOG_LEVEL` environment variable (e.g., `LOG_LEVEL=DEBUG`).

Example:

```bash
LOG_LEVEL=DEBUG python batch/cookStockPipeline.py
```

Log messages include per-ticker progress, detected patterns, saved figures, and error traces when exceptions occur.