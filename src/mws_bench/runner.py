from __future__ import annotations

import csv
import json
import math
from collections.abc import Iterable
from dataclasses import asdict, replace
from pathlib import Path

from .config import ExperimentConfig, MixConfig, PolicyConfig
from .metrics import AggregateMetrics, compute_metrics
from .simulator import simulate
from .workload import generate_jobs


SWEEP_POLICIES = ["fifo", "shortest-job-first", "agentic-priority"]
SWEEP_MIXES = [
    (0.9, 0.1),
    (0.5, 0.5),
    (0.1, 0.9),
]

SUMMARY_KEYS = [
    "throughput_rps",
    "p95_latency_ms",
    "p99_latency_ms",
    "sla_violation_rate",
    "cost_per_success",
    "total_jobs",
    "success_jobs",
    "timeout_jobs",
]


def _mean(values: Iterable[float]) -> float:
    vals = list(values)
    return sum(vals) / len(vals) if vals else 0.0


def _std(values: Iterable[float]) -> float:
    vals = list(values)
    if len(vals) <= 1:
        return 0.0
    mu = _mean(vals)
    variance = sum((x - mu) ** 2 for x in vals) / (len(vals) - 1)
    return math.sqrt(variance)


def _ci95(values: Iterable[float]) -> float:
    vals = list(values)
    if len(vals) <= 1:
        return 0.0
    return 1.96 * _std(vals) / math.sqrt(len(vals))


def run_replicates(cfg: ExperimentConfig) -> list[AggregateMetrics]:
    rows: list[AggregateMetrics] = []
    for rep in range(cfg.replicates):
        jobs = generate_jobs(cfg, seed_offset=rep)
        result = simulate(cfg, jobs)
        rows.append(compute_metrics(cfg, result))
    return rows


def summarize(metrics: list[AggregateMetrics]) -> dict[str, float]:
    if not metrics:
        return {}

    out: dict[str, float] = {}
    for key in SUMMARY_KEYS:
        out[key] = _mean(float(getattr(m, key)) for m in metrics)
    return out


def summarize_with_uncertainty(metrics: list[AggregateMetrics]) -> dict[str, float]:
    out = summarize(metrics)
    if not metrics:
        return out

    for key in SUMMARY_KEYS:
        values = [float(getattr(m, key)) for m in metrics]
        out[f"{key}_std"] = _std(values)
        out[f"{key}_ci95"] = _ci95(values)
    return out


def summarize_structured(
    metrics: list[AggregateMetrics],
) -> dict[str, dict[str, float]]:
    if not metrics:
        return {}

    out: dict[str, dict[str, float]] = {}
    for key in SUMMARY_KEYS:
        values = [float(getattr(m, key)) for m in metrics]
        out[key] = {
            "mean": _mean(values),
            "std": _std(values),
            "ci95": _ci95(values),
        }
    return out


def run_single_to_json(cfg: ExperimentConfig, output_path: str | Path) -> None:
    metrics = run_replicates(cfg)
    summary = summarize(metrics)
    summary_stats = summarize_structured(metrics)

    payload = {
        "config": asdict(cfg),
        "replicates": [asdict(m) for m in metrics],
        "summary": summary,
        "summary_stats": summary_stats,
    }
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2))


def run_sweep_to_csv(cfg: ExperimentConfig, output_path: str | Path) -> None:
    rows: list[dict[str, float | str]] = []
    for policy in SWEEP_POLICIES:
        for stream_ratio, agent_ratio in SWEEP_MIXES:
            run_cfg = replace(
                cfg,
                policy=PolicyConfig(name=policy),
                mix=MixConfig(streaming_ratio=stream_ratio, agentic_ratio=agent_ratio),
            )
            metrics = run_replicates(run_cfg)
            summary = summarize_with_uncertainty(metrics)
            row: dict[str, float | str] = dict(summary)
            row["policy"] = policy
            row["streaming_ratio"] = stream_ratio
            row["agentic_ratio"] = agent_ratio
            rows.append(row)

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "policy",
        "streaming_ratio",
        "agentic_ratio",
        "throughput_rps",
        "throughput_rps_std",
        "throughput_rps_ci95",
        "p95_latency_ms",
        "p95_latency_ms_std",
        "p95_latency_ms_ci95",
        "p99_latency_ms",
        "p99_latency_ms_std",
        "p99_latency_ms_ci95",
        "sla_violation_rate",
        "sla_violation_rate_std",
        "sla_violation_rate_ci95",
        "cost_per_success",
        "cost_per_success_std",
        "cost_per_success_ci95",
        "total_jobs",
        "total_jobs_std",
        "total_jobs_ci95",
        "success_jobs",
        "success_jobs_std",
        "success_jobs_ci95",
        "timeout_jobs",
        "timeout_jobs_std",
        "timeout_jobs_ci95",
    ]
    with path.open("w", newline="") as fp:
        writer = csv.DictWriter(fp, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
