from __future__ import annotations

from dataclasses import dataclass

from .config import ExperimentConfig
from .simulator import JobResult


@dataclass(frozen=True)
class AggregateMetrics:
    total_jobs: int
    success_jobs: int
    timeout_jobs: int
    throughput_rps: float
    p95_latency_ms: float
    p99_latency_ms: float
    sla_violation_rate: float
    cost_per_success: float


def _percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    rank = (len(ordered) - 1) * pct
    low = int(rank)
    high = min(low + 1, len(ordered) - 1)
    weight = rank - low
    return ordered[low] * (1.0 - weight) + ordered[high] * weight


def compute_metrics(
    cfg: ExperimentConfig, results: list[JobResult]
) -> AggregateMetrics:
    if not results:
        return AggregateMetrics(
            total_jobs=0,
            success_jobs=0,
            timeout_jobs=0,
            throughput_rps=0.0,
            p95_latency_ms=0.0,
            p99_latency_ms=0.0,
            sla_violation_rate=0.0,
            cost_per_success=0.0,
        )

    latencies = [(r.end_s - r.arrival_s) * 1000.0 for r in results]
    timeout_jobs = sum(1 for r in results if r.timed_out)
    success_jobs = len(results) - timeout_jobs

    span_s = max(r.end_s for r in results)
    throughput = success_jobs / span_s if span_s > 0 else 0.0

    violations = 0
    for r, latency in zip(results, latencies):
        threshold = (
            cfg.sla.streaming_ms if r.job_type == "streaming" else cfg.sla.agentic_ms
        )
        if latency > threshold:
            violations += 1
    sla_violation_rate = violations / len(results)

    total_cost = 0.0
    for r in results:
        unit = (
            cfg.cost.streaming_unit
            if r.job_type == "streaming"
            else cfg.cost.agentic_unit
        )
        total_cost += unit
        if r.timed_out:
            total_cost += cfg.cost.timeout_penalty
    cost_per_success = total_cost / success_jobs if success_jobs > 0 else float("inf")

    return AggregateMetrics(
        total_jobs=len(results),
        success_jobs=success_jobs,
        timeout_jobs=timeout_jobs,
        throughput_rps=throughput,
        p95_latency_ms=_percentile(latencies, 0.95),
        p99_latency_ms=_percentile(latencies, 0.99),
        sla_violation_rate=sla_violation_rate,
        cost_per_success=cost_per_success,
    )
