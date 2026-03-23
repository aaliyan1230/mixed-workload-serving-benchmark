# Mixed Workload Benchmark Results

Data sources used in this report:

- `results/sweep.csv` (baseline simulator sweep)
- `results/high_contention_sweep.csv` (high-contention simulator sweep)
- `results/live_ollama_run.json` (live local-model run)
- `results/live_ollama_trace.jsonl` (request-level live trace)

## Executive Summary

- Under baseline conditions, the 0.9:0.1 mix (streaming:agentic) dominates all other mixes for both throughput and SLA reliability.
- Under high contention, `shortest-job-first` is clearly superior across all tracked metrics, especially throughput and SLA violation.
- Live Ollama smoke run validates end-to-end trace instrumentation and exposes queueing effects (no hard timeouts, but rising queue wait/latency for later requests).

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

## Practical Takeaways

- For simulator-driven policy selection, start with `shortest-job-first` when contention risk is high.
- Keep a streaming-heavy admission mix where possible; it dominates mixed/agentic-heavy mixes in both throughput and SLA.
- Live local runs are now instrumented enough for failure-mode analysis; next step is multi-replicate live sweeps to reduce variance and validate policy ranking stability.
