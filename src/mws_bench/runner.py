from __future__ import annotations

import csv
import json
from dataclasses import asdict, replace
from pathlib import Path

from .config import ExperimentConfig, MixConfig, PolicyConfig
from .metrics import AggregateMetrics, compute_metrics
from .simulator import simulate
from .workload import generate_jobs


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

    keys = [
        "throughput_rps",
        "p95_latency_ms",
        "p99_latency_ms",
        "sla_violation_rate",
        "cost_per_success",
    ]
    out: dict[str, float] = {}
    for key in keys:
        out[key] = sum(getattr(m, key) for m in metrics) / len(metrics)
    out["total_jobs"] = sum(m.total_jobs for m in metrics) / len(metrics)
    out["success_jobs"] = sum(m.success_jobs for m in metrics) / len(metrics)
    out["timeout_jobs"] = sum(m.timeout_jobs for m in metrics) / len(metrics)
    return out


def run_single_to_json(cfg: ExperimentConfig, output_path: str | Path) -> None:
    metrics = run_replicates(cfg)
    summary = summarize(metrics)

    payload = {
        "config": asdict(cfg),
        "replicates": [asdict(m) for m in metrics],
        "summary": summary,
    }
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2))


def run_sweep_to_csv(cfg: ExperimentConfig, output_path: str | Path) -> None:
    policies = ["fifo", "shortest-job-first", "agentic-priority"]
    mixes = [
        (0.9, 0.1),
        (0.5, 0.5),
        (0.1, 0.9),
    ]

    rows: list[dict[str, float | str]] = []
    for policy in policies:
        for stream_ratio, agent_ratio in mixes:
            run_cfg = replace(
                cfg,
                policy=PolicyConfig(name=policy),
                mix=MixConfig(streaming_ratio=stream_ratio, agentic_ratio=agent_ratio),
            )
            metrics = run_replicates(run_cfg)
            row = summarize(metrics)
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
        "p95_latency_ms",
        "p99_latency_ms",
        "sla_violation_rate",
        "cost_per_success",
        "total_jobs",
        "success_jobs",
        "timeout_jobs",
    ]
    with path.open("w", newline="") as fp:
        writer = csv.DictWriter(fp, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
