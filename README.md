# Mixed Workload Serving Benchmark

Lightweight benchmark harness for **mixed streaming + agentic workloads**.

This project is designed for fast, reproducible experiments on scheduling behavior under realistic stressors:
- workload mix shifts (90:10, 50:50, 10:90)
- tool stalls and timeout behavior
- queue contention in shared worker pools

## What You Get

- deterministic workload generator (seeded)
- discrete-event simulator for serving policies
- built-in metrics:
  - throughput
  - p95/p99 latency
  - SLA violation rate
  - cost per successful task
- one-command sweep for policy comparison

## Quick Start

```bash
uv venv .venv
source .venv/bin/activate
uv pip install -e .

# Run one config
uv run mws-bench run --config configs/default.json --output results/default_run.json

# Run matrix sweep (mix x policy)
uv run mws-bench sweep --output results/sweep.csv
```

## Project Layout

- `src/mws_bench/config.py`: typed experiment config and JSON loader
- `src/mws_bench/workload.py`: arrival and job-shape generation
- `src/mws_bench/simulator.py`: event-loop simulation engine
- `src/mws_bench/metrics.py`: aggregate metrics and class-level stats
- `src/mws_bench/runner.py`: replicate runner + sweep matrix
- `src/mws_bench/cli.py`: `run` and `sweep` commands
- `configs/default.json`: baseline experiment config
- `tests/`: smoke tests for generation, simulation, and metrics

## Notes

- This scaffold intentionally uses standard library only.
- You can extend it to real serving backends (Ray Serve, vLLM, SGLang) after validating synthetic policy trends.
