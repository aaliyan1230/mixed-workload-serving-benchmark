from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class MixConfig:
    streaming_ratio: float
    agentic_ratio: float


@dataclass(frozen=True)
class PolicyConfig:
    name: str


@dataclass(frozen=True)
class WorkerConfig:
    streaming: int
    agentic: int
    shared: int


@dataclass(frozen=True)
class SlaConfig:
    streaming_ms: float
    agentic_ms: float


@dataclass(frozen=True)
class CostConfig:
    streaming_unit: float
    agentic_unit: float
    timeout_penalty: float


@dataclass(frozen=True)
class StreamingProfile:
    service_ms_mean: float
    service_ms_std: float
    timeout_ms: float


@dataclass(frozen=True)
class AgenticProfile:
    steps_mean: float
    steps_std: float
    step_ms_mean: float
    step_ms_std: float
    stall_probability: float
    stall_ms: float
    timeout_ms: float


@dataclass(frozen=True)
class ExperimentConfig:
    seed: int
    duration_s: float
    arrival_rate_rps: float
    mix: MixConfig
    policy: PolicyConfig
    workers: WorkerConfig
    sla: SlaConfig
    cost: CostConfig
    streaming_profile: StreamingProfile
    agentic_profile: AgenticProfile
    replicates: int


def _validate_mix(mix: MixConfig) -> None:
    total = mix.streaming_ratio + mix.agentic_ratio
    if abs(total - 1.0) > 1e-6:
        raise ValueError(f"mix ratios must sum to 1.0, got {total}")


def _validate_workers(workers: WorkerConfig) -> None:
    if workers.streaming < 0 or workers.agentic < 0 or workers.shared < 0:
        raise ValueError("worker counts must be non-negative")
    if workers.streaming + workers.agentic + workers.shared == 0:
        raise ValueError("at least one worker is required")


def _validate_capacity(cfg: ExperimentConfig) -> None:
    if cfg.mix.streaming_ratio > 0 and cfg.workers.streaming + cfg.workers.shared == 0:
        raise ValueError("streaming workload requires streaming or shared workers")
    if cfg.mix.agentic_ratio > 0 and cfg.workers.agentic + cfg.workers.shared == 0:
        raise ValueError("agentic workload requires agentic or shared workers")
    if cfg.replicates <= 0:
        raise ValueError("replicates must be positive")


def load_config(path: str | Path) -> ExperimentConfig:
    data = json.loads(Path(path).read_text())

    cfg = ExperimentConfig(
        seed=int(data["seed"]),
        duration_s=float(data["duration_s"]),
        arrival_rate_rps=float(data["arrival_rate_rps"]),
        mix=MixConfig(**data["mix"]),
        policy=PolicyConfig(**data["policy"]),
        workers=WorkerConfig(**data["workers"]),
        sla=SlaConfig(**data["sla"]),
        cost=CostConfig(**data["cost"]),
        streaming_profile=StreamingProfile(**data["streaming_profile"]),
        agentic_profile=AgenticProfile(**data["agentic_profile"]),
        replicates=int(data["replicates"]),
    )

    _validate_mix(cfg.mix)
    _validate_workers(cfg.workers)
    _validate_capacity(cfg)
    return cfg
