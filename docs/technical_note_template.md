# Mixed Workload Serving Benchmark - Technical Note Template

## 1. Motivation

- Problem statement: jointly serving short streaming requests and long agentic tool chains creates scheduling trade-offs.
- Goal: identify policy + configuration choices that improve tail latency and reliability under mixed load.

## 2. Experimental Setup

- Workload mixes: 0.9:0.1, 0.5:0.5, 0.1:0.9 (streaming:agentic).
- Policies: fifo, shortest-job-first, agentic-priority.
- Scenarios: baseline and high-contention.
- Replicates: report mean +- 95% CI.

## 3. Metrics

- Throughput (rps)
- P95/P99 latency (ms)
- SLA violation rate
- Cost per successful task

## 4. Main Results

Use plots from:
- `results/plots/default/`
- `results/plots/high_contention/`

Use tables from:
- `docs/results.md`

Prompting checklist:
- Which policy dominates under each mix?
- Does dominance change under contention?
- What trade-off appears between throughput and tail latency?

## 5. Failure Analysis

- Where do timeouts concentrate (policy x mix)?
- Which class is harmed most (streaming vs agentic)?
- Which configuration knobs likely shift those failure modes?

## 6. Practical Recommendations

- Suggested default policy by deployment objective.
- Suggested worker split for traffic regimes.
- Guardrails: timeout thresholds, queue-depth alarms, fallback strategy.

## 7. Limitations and Next Steps

- Current simulator assumptions.
- Missing real backend effects.
- Next steps: connect to Ray Serve/vLLM/SGLang traces.
