from __future__ import annotations

from pathlib import Path

from mws_bench.config import load_config
from mws_bench.metrics import compute_metrics
from mws_bench.simulator import simulate
from mws_bench.workload import generate_jobs


def _default_cfg_path() -> Path:
    return Path(__file__).resolve().parents[1] / "configs" / "default.json"


def test_generation_and_simulation_smoke() -> None:
    cfg = load_config(_default_cfg_path())
    jobs = generate_jobs(cfg)
    assert jobs, "expected generated jobs"

    results = simulate(cfg, jobs)
    assert len(results) == len(jobs)

    metrics = compute_metrics(cfg, results)
    assert metrics.total_jobs > 0
    assert metrics.success_jobs + metrics.timeout_jobs == metrics.total_jobs
    assert metrics.p95_latency_ms >= 0
    assert metrics.p99_latency_ms >= metrics.p95_latency_ms
