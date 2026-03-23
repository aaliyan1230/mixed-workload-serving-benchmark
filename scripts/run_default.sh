#!/usr/bin/env bash
set -euo pipefail

uv run mws-bench run --config configs/default.json --output results/default_run.json
uv run mws-bench sweep --config configs/default.json --output results/sweep.csv
uv run mws-bench sweep --config configs/high_contention.json --output results/high_contention_sweep.csv

if uv run python -c "import matplotlib" >/dev/null 2>&1; then
  uv run python scripts/plot_sweep.py --input results/sweep.csv --output-dir results/plots/default
  uv run python scripts/plot_sweep.py --input results/high_contention_sweep.csv --output-dir results/plots/high_contention
fi

echo "Wrote baseline + high-contention results in results/"
