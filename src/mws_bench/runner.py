from __future__ import annotations

import csv
import json
import math
from collections.abc import Iterable
from dataclasses import asdict, replace
from pathlib import Path

from .config import ExperimentConfig, MixConfig, PolicyConfig
from .live_openai_compatible import run_live_vllm
from .live_ollama import run_live_ollama
from .metrics import AggregateMetrics, compute_metrics
from .simulator import JobResult, simulate
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


def _execute_once(cfg: ExperimentConfig, rep: int) -> tuple[AggregateMetrics, list[JobResult]]:
    jobs = generate_jobs(cfg, seed_offset=rep)
    if cfg.execution.mode == "simulate":
        result = simulate(cfg, jobs)
    elif cfg.execution.mode == "live-ollama":
        result = run_live_ollama(cfg, jobs)
    elif cfg.execution.mode == "live-vllm":
        result = run_live_vllm(cfg, jobs)
    else:
        raise ValueError(f"Unsupported execution mode: {cfg.execution.mode}")
    return compute_metrics(cfg, result), result


def _trace_record(
    cfg: ExperimentConfig,
    replicate: int,
    job: JobResult,
) -> dict[str, float | int | str | bool | None]:
    return {
        "replicate": replicate,
        "execution_mode": cfg.execution.mode,
        "policy": cfg.policy.name,
        "streaming_ratio": cfg.mix.streaming_ratio,
        "agentic_ratio": cfg.mix.agentic_ratio,
        "job_id": job.id,
        "job_type": job.job_type,
        "arrival_s": job.arrival_s,
        "start_s": job.start_s,
        "end_s": job.end_s,
        "queue_wait_ms": job.queue_wait_ms,
        "service_ms": job.service_ms,
        "latency_ms": (job.end_s - job.arrival_s) * 1000.0,
        "timed_out": job.timed_out,
        "backend_model": job.backend_model,
        "backend_status": job.backend_status,
        "backend_error": job.backend_error,
    }


def _write_trace_jsonl(
    cfg: ExperimentConfig,
    trace_output_path: str | Path,
    replicate_rows: list[tuple[int, list[JobResult]]],
) -> None:
    path = Path(trace_output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as fp:
        for rep, jobs in replicate_rows:
            for job in jobs:
                fp.write(json.dumps(_trace_record(cfg, rep, job)) + "\n")


def run_replicates(cfg: ExperimentConfig) -> list[AggregateMetrics]:
    rows: list[AggregateMetrics] = []
    for rep in range(cfg.replicates):
        metric, _ = _execute_once(cfg, rep)
        rows.append(metric)
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


def run_single_to_json(
    cfg: ExperimentConfig,
    output_path: str | Path,
    trace_output_path: str | Path | None = None,
) -> None:
    metrics: list[AggregateMetrics] = []
    replicate_results: list[tuple[int, list[JobResult]]] = []
    for rep in range(cfg.replicates):
        metric, jobs = _execute_once(cfg, rep)
        metrics.append(metric)
        replicate_results.append((rep, jobs))

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

    if trace_output_path is not None:
        _write_trace_jsonl(cfg, trace_output_path, replicate_results)


def run_sweep_to_csv(
    cfg: ExperimentConfig,
    output_path: str | Path,
    trace_output_dir: str | Path | None = None,
) -> None:
    rows: list[dict[str, float | str]] = []
    sweep_traces: list[tuple[Path, ExperimentConfig, list[tuple[int, list[JobResult]]]]] = []
    for policy in SWEEP_POLICIES:
        for stream_ratio, agent_ratio in SWEEP_MIXES:
            run_cfg = replace(
                cfg,
                policy=PolicyConfig(name=policy),
                mix=MixConfig(streaming_ratio=stream_ratio, agentic_ratio=agent_ratio),
            )
            metrics: list[AggregateMetrics] = []
            replicate_results: list[tuple[int, list[JobResult]]] = []
            for rep in range(run_cfg.replicates):
                metric, jobs = _execute_once(run_cfg, rep)
                metrics.append(metric)
                replicate_results.append((rep, jobs))

            summary = summarize_with_uncertainty(metrics)
            row: dict[str, float | str] = dict(summary)
            row["policy"] = policy
            row["streaming_ratio"] = stream_ratio
            row["agentic_ratio"] = agent_ratio
            rows.append(row)

            if trace_output_dir is not None:
                trace_name = f"trace_{policy}_s{stream_ratio:.1f}_a{agent_ratio:.1f}.jsonl"
                sweep_traces.append(
                    (
                        Path(trace_output_dir) / trace_name,
                        run_cfg,
                        replicate_results,
                    )
                )

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

    if trace_output_dir is not None:
        for trace_path, trace_cfg, replicate_rows in sweep_traces:
            _write_trace_jsonl(trace_cfg, trace_path, replicate_rows)
