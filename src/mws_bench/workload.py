from __future__ import annotations

import random
from dataclasses import dataclass

from .config import ExperimentConfig


@dataclass(frozen=True)
class Job:
    id: int
    job_type: str
    arrival_s: float
    service_ms: float
    timeout_ms: float


def _sample_positive_normal(
    rng: random.Random, mean: float, std: float, floor: float = 1.0
) -> float:
    value = rng.gauss(mean, std)
    return max(value, floor)


def _sample_agentic_service_ms(rng: random.Random, cfg: ExperimentConfig) -> float:
    profile = cfg.agentic_profile
    steps = int(
        round(
            _sample_positive_normal(
                rng, profile.steps_mean, profile.steps_std, floor=1.0
            )
        )
    )
    total = 0.0
    for _ in range(steps):
        total += _sample_positive_normal(
            rng, profile.step_ms_mean, profile.step_ms_std, floor=5.0
        )
        if rng.random() < profile.stall_probability:
            total += profile.stall_ms
    return total


def generate_jobs(cfg: ExperimentConfig, seed_offset: int = 0) -> list[Job]:
    rng = random.Random(cfg.seed + seed_offset)
    jobs: list[Job] = []

    t = 0.0
    job_id = 0
    while t < cfg.duration_s:
        interarrival = rng.expovariate(cfg.arrival_rate_rps)
        t += interarrival
        if t > cfg.duration_s:
            break

        is_streaming = rng.random() < cfg.mix.streaming_ratio
        if is_streaming:
            service_ms = _sample_positive_normal(
                rng,
                cfg.streaming_profile.service_ms_mean,
                cfg.streaming_profile.service_ms_std,
                floor=1.0,
            )
            jobs.append(
                Job(
                    id=job_id,
                    job_type="streaming",
                    arrival_s=t,
                    service_ms=service_ms,
                    timeout_ms=cfg.streaming_profile.timeout_ms,
                )
            )
        else:
            service_ms = _sample_agentic_service_ms(rng, cfg)
            jobs.append(
                Job(
                    id=job_id,
                    job_type="agentic",
                    arrival_s=t,
                    service_ms=service_ms,
                    timeout_ms=cfg.agentic_profile.timeout_ms,
                )
            )

        job_id += 1

    return jobs
