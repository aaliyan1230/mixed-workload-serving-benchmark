from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

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


def test_shared_worker_pool_handles_mixed_workload() -> None:
    cfg = load_config(_default_cfg_path())
    cfg = replace(cfg, workers=replace(cfg.workers, streaming=0, agentic=0, shared=4))

    jobs = generate_jobs(cfg, seed_offset=1)
    results = simulate(cfg, jobs)

    assert len(results) == len(jobs)
    assert any(r.job_type == "streaming" for r in results)
    assert any(r.job_type == "agentic" for r in results)


def test_invalid_capacity_config_raises(tmp_path: Path) -> None:
    config_path = tmp_path / "bad_config.json"
    config_path.write_text(
        """
{
  "seed": 1,
  "duration_s": 10,
  "arrival_rate_rps": 2,
  "mix": {"streaming_ratio": 0.0, "agentic_ratio": 1.0},
  "policy": {"name": "fifo"},
  "workers": {"streaming": 2, "agentic": 0, "shared": 0},
  "sla": {"streaming_ms": 1000, "agentic_ms": 5000},
  "cost": {"streaming_unit": 0.001, "agentic_unit": 0.005, "timeout_penalty": 0.001},
  "streaming_profile": {"service_ms_mean": 100, "service_ms_std": 10, "timeout_ms": 1000},
  "agentic_profile": {
    "steps_mean": 2,
    "steps_std": 1,
    "step_ms_mean": 300,
    "step_ms_std": 100,
    "stall_probability": 0.0,
    "stall_ms": 500,
    "timeout_ms": 5000
  },
  "replicates": 1
}
""".strip()
    )

    with pytest.raises(ValueError, match="agentic workload requires"):
        load_config(config_path)
