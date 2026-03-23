# Mixed Workload Serving Benchmark - Technical Note (Current Draft)

## 1. Motivation

Mixed serving systems must handle low-latency streaming requests and longer agentic chains on shared capacity. The main design question is whether scheduling policy can materially improve throughput and SLA outcomes as mix and contention shift.

## 2. Setup Used in This Draft

- Mixes: 0.9:0.1, 0.5:0.5, 0.1:0.9 (streaming:agentic)
- Policies: `fifo`, `shortest-job-first`, `agentic-priority`
- Simulator scenarios: baseline and high-contention sweeps
- Live scenario: local Ollama smoke run (`qwen3:4b`, no API key)
- Metrics: throughput, p95/p99 latency, SLA violation, cost/success

## 3. Findings

### 3.1 Baseline simulator

- Throughput winner: `fifo` at 0.9:0.1 (7.7209 rps)
- Reliability winner: `shortest-job-first` at 0.9:0.1 (SLA violation 0.0272)
- Pareto points are all at 0.9:0.1, indicating mix dominates policy for this regime.

### 3.2 High-contention simulator

- `shortest-job-first` dominates across throughput, tail latency, SLA, and cost.
- Only Pareto point is `shortest-job-first` at 0.9:0.1 (1.6760 rps, SLA violation 0.5031).

### 3.3 Live Ollama smoke run

- 10/10 requests succeeded, 0 timeouts.
- Throughput: 0.4682 rps.
- Tail latency: p95 ~ 10.99 s.
- Trace shows increasing queue wait for later requests (up to ~8.47 s), indicating queueing pressure even without hard failures.

## 4. Interpretation

- Under normal conditions, policy differences are second-order once workload is streaming-heavy.
- Under contention, policy choice becomes first-order; `shortest-job-first` is the robust default from current evidence.
- Live run confirms instrumentation is functioning and uncovers queue buildup behavior not obvious from aggregate metrics alone.

## 5. Immediate Recommendations

- Default simulator recommendation for contested systems: `shortest-job-first`.
- Operational recommendation: keep admission or shaping biased toward streaming-heavy mix when feasible.
- Keep request-level trace logging enabled in live runs; aggregate-only reporting hides queue dynamics.

## 6. Current Gaps

- Live evidence is still single-run smoke and single-model profile.
- No live sweep across policy x mix yet.
- No external backend comparison (Ray Serve, vLLM, SGLang) yet.

## 7. Next Immediate Actions

- Run traced live sweep and persist per-scenario trace files:
	`uv run mws-bench sweep --config configs/live_ollama.json --output results/live_ollama_sweep.csv --trace-output-dir results/traces/live_ollama`
- Add notebook section for class-level queue-wait distributions across sweep traces.
- Promote this file to final note once live multi-replicate results are available.
