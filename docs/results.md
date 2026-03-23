# Mixed Workload Benchmark Results

This document is auto-generated from sweep CSV outputs. Values are mean +- 95% CI across replicates.

## Baseline Scenario

### Best policy per metric

- Throughput (rps): `fifo` (higher is better)
- P95 latency (ms): `shortest-job-first` (lower is better)
- SLA violation rate: `shortest-job-first` (lower is better)
- Cost per success: `fifo` (lower is better)

### Full table

| policy | mix (s:a) | throughput | p95 latency | SLA viol. | cost/success |
|---|---:|---:|---:|---:|---:|
| fifo | 0.9:0.1 | 7.7209 +- 0.3700 | 4423.7 +- 513.9 | 0.0275 +- 0.0075 | 0.0015 +- 0.0000 |
| fifo | 0.5:0.5 | 1.0136 +- 0.0525 | 346484.9 +- 23467.3 | 0.4911 +- 0.0109 | 0.0072 +- 0.0003 |
| fifo | 0.1:0.9 | 0.1261 +- 0.0083 | 726153.2 +- 22474.2 | 0.8916 +- 0.0047 | 0.0508 +- 0.0030 |
| shortest-job-first | 0.9:0.1 | 7.7048 +- 0.4212 | 3892.1 +- 262.7 | 0.0272 +- 0.0068 | 0.0015 +- 0.0000 |
| shortest-job-first | 0.5:0.5 | 1.3727 +- 0.0681 | 341348.5 +- 17805.6 | 0.3237 +- 0.0111 | 0.0051 +- 0.0002 |
| shortest-job-first | 0.1:0.9 | 0.3798 +- 0.0105 | 725691.4 +- 23169.2 | 0.6699 +- 0.0072 | 0.0164 +- 0.0003 |
| agentic-priority | 0.9:0.1 | 7.7209 +- 0.3700 | 4423.7 +- 513.9 | 0.0275 +- 0.0075 | 0.0015 +- 0.0000 |
| agentic-priority | 0.5:0.5 | 1.0136 +- 0.0525 | 346484.9 +- 23467.3 | 0.4911 +- 0.0109 | 0.0072 +- 0.0003 |
| agentic-priority | 0.1:0.9 | 0.1261 +- 0.0083 | 726153.2 +- 22474.2 | 0.8916 +- 0.0047 | 0.0508 +- 0.0030 |

## High-Contention Scenario

### Best policy per metric

- Throughput (rps): `shortest-job-first` (higher is better)
- P95 latency (ms): `shortest-job-first` (lower is better)
- SLA violation rate: `shortest-job-first` (lower is better)
- Cost per success: `shortest-job-first` (lower is better)

### Full table

| policy | mix (s:a) | throughput | p95 latency | SLA viol. | cost/success |
|---|---:|---:|---:|---:|---:|
| fifo | 0.9:0.1 | 0.0416 +- 0.0047 | 311073.7 +- 28645.3 | 0.9954 +- 0.0011 | 0.2301 +- 0.0309 |
| fifo | 0.5:0.5 | 0.0108 +- 0.0034 | 3219598.7 +- 80235.5 | 0.9955 +- 0.0011 | 0.3643 +- 0.1155 |
| fifo | 0.1:0.9 | 0.0384 +- 0.0011 | 6132573.1 +- 88651.5 | 0.8992 +- 0.0028 | 0.0691 +- 0.0020 |
| shortest-job-first | 0.9:0.1 | 1.6760 +- 0.0927 | 289371.2 +- 17591.6 | 0.5031 +- 0.0063 | 0.0037 +- 0.0001 |
| shortest-job-first | 0.5:0.5 | 0.3246 +- 0.0086 | 2970589.3 +- 67502.0 | 0.5926 +- 0.0061 | 0.0089 +- 0.0002 |
| shortest-job-first | 0.1:0.9 | 0.0674 +- 0.0020 | 5748122.7 +- 87726.8 | 0.8368 +- 0.0046 | 0.0388 +- 0.0013 |
| agentic-priority | 0.9:0.1 | 0.0359 +- 0.0063 | 311050.6 +- 28210.9 | 0.9957 +- 0.0010 | 0.2745 +- 0.0506 |
| agentic-priority | 0.5:0.5 | 0.0108 +- 0.0034 | 3219598.7 +- 80235.5 | 0.9955 +- 0.0011 | 0.3643 +- 0.1155 |
| agentic-priority | 0.1:0.9 | 0.0384 +- 0.0011 | 6132573.1 +- 88651.5 | 0.8992 +- 0.0028 | 0.0691 +- 0.0020 |
