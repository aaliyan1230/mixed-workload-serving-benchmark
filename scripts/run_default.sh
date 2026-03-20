#!/usr/bin/env bash
set -euo pipefail

uv run mws-bench run --config configs/default.json --output results/default_run.json
uv run mws-bench sweep --config configs/default.json --output results/sweep.csv

echo "Wrote results/default_run.json and results/sweep.csv"
