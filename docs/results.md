# Mixed Workload Benchmark Results

Data sources used in this report:

- `results/sweep.csv` (baseline simulator sweep)
- `results/high_contention_sweep.csv` (high-contention simulator sweep)
- `results/live_ollama_run.json` (live local-model run)
- `results/live_ollama_trace.jsonl` (request-level live trace)
- `results/live_ollama_sweep.csv` (live local-model sweep)
- `results/traces/live_ollama/*.jsonl` (per-scenario live traces)

## Executive Summary

- Under baseline conditions, the 0.9:0.1 mix (streaming:agentic) dominates all other mixes for both throughput and SLA reliability.
- Under high contention, `shortest-job-first` is clearly superior across all tracked metrics, especially throughput and SLA violation.
- Live Ollama smoke run validates end-to-end trace instrumentation and exposes queueing effects (no hard timeouts, but rising queue wait/latency for later requests).
- Live Ollama sweep is now available and shows consistent ordering: at each mix, `agentic-priority` narrowly leads throughput with zero timeouts in this short-duration setup.

## Baseline Simulator Sweep

### Best policy per metric

- Throughput: `fifo` at 0.9:0.1 (7.7209 +- 0.3700 rps)
- P95 latency: `shortest-job-first` at 0.9:0.1 (3892.1 +- 262.7 ms)
- SLA violation: `shortest-job-first` at 0.9:0.1 (0.0272 +- 0.0068)
- Cost per success: `fifo` at 0.9:0.1 (0.0015 +- 0.0000)

### Pareto frontier (throughput up, SLA violation down)

- `shortest-job-first` 0.9:0.1 -> 7.7048 rps, 0.0272 SLA violation
- `fifo` 0.9:0.1 -> 7.7209 rps, 0.0275 SLA violation
- `agentic-priority` 0.9:0.1 -> 7.7209 rps, 0.0275 SLA violation

Interpretation: at baseline load, policy choice matters less than staying in streaming-heavy mix; among Pareto points, `shortest-job-first` gives slightly lower SLA risk while `fifo` gives slightly higher throughput.

## High-Contention Simulator Sweep

### Best policy per metric

- Throughput: `shortest-job-first` at 0.9:0.1 (1.6760 +- 0.0927 rps)
- P95 latency: `shortest-job-first` at 0.9:0.1 (289371.2 +- 17591.6 ms)
- SLA violation: `shortest-job-first` at 0.9:0.1 (0.5031 +- 0.0063)
- Cost per success: `shortest-job-first` at 0.9:0.1 (0.0037 +- 0.0001)

### Pareto frontier (throughput up, SLA violation down)

- `shortest-job-first` 0.9:0.1 -> 1.6760 rps, 0.5031 SLA violation

Interpretation: under heavy contention, one policy dominates; this is a strong default recommendation unless objective weights change materially.

## Live Ollama Smoke Run (No API Key)

Config: `configs/live_ollama.json` (mode `live-ollama`, model `qwen3:4b` for both classes).

### Aggregate run summary

- total jobs: 10
- success jobs: 10
- timeout jobs: 0
- throughput: 0.4682 rps
- p95 latency: 10993.59 ms
- p99 latency: 10995.32 ms
- SLA violation rate: 0.3000
- cost per success: 0.0020

### Request-level trace summary

- trace rows: 10
- backend status counts: `ok` = 10
- timeout flags: 0/10
- job mix observed: 8 streaming, 2 agentic
- qualitative behavior: queue wait grows substantially for late-arriving requests (peaking around 8.47 s), with tail latency around 11 s.

## Live Ollama Sweep (Real Backend)

Command used:

`uv run mws-bench sweep --config configs/live_ollama.json --output results/live_ollama_sweep.csv --trace-output-dir results/traces/live_ollama`

### Key results (replicates=1)

- 0.9:0.1 mix:
	- `agentic-priority`: 0.5140 rps, p95 4883.2 ms, SLA violation 0.0
	- `shortest-job-first`: 0.5115 rps, p95 4945.1 ms, SLA violation 0.0
	- `fifo`: 0.5001 rps, p95 5251.8 ms, SLA violation 0.0
- 0.5:0.5 mix:
	- `shortest-job-first`/`agentic-priority`/`fifo` are effectively tied on throughput (~0.406 rps) with near-identical p95 (~4.87-4.89 s), SLA violation 0.0
- 0.1:0.9 mix:
	- `agentic-priority`: 0.2611 rps, p95 12048.8 ms, SLA violation 0.0
	- `shortest-job-first`: 0.2604 rps, p95 12108.4 ms, SLA violation 0.0
	- `fifo`: 0.2524 rps, p95 12680.7 ms, SLA violation 0.0

### Interpretation and caveat

- The live sweep supports the expected trend that agentic-heavy mixes reduce throughput and increase latency.
- Differences between policies are present but small in this short smoke profile.
- Because `replicates=1`, treat these as directional; do not make hard policy commitments without multi-replicate live runs.

## Practical Takeaways

- For simulator-driven policy selection, start with `shortest-job-first` when contention risk is high.
- Keep a streaming-heavy admission mix where possible; it dominates mixed/agentic-heavy mixes in both throughput and SLA.
- Live local runs are now instrumented enough for failure-mode analysis; immediate next step is increasing live replicates to reduce variance and validate ranking stability.
