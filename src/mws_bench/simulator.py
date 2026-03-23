from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from math import inf

from .config import ExperimentConfig
from .workload import Job


@dataclass(frozen=True)
class JobResult:
    id: int
    job_type: str
    arrival_s: float
    start_s: float
    end_s: float
    queue_wait_ms: float
    service_ms: float
    timed_out: bool
    backend_model: str | None = None
    backend_status: str | None = None
    backend_error: str | None = None


def _remove_index(q: deque[Job], idx: int) -> Job:
    if idx == 0:
        return q.popleft()
    if idx == len(q) - 1:
        return q.pop()

    tmp = deque()
    for _ in range(idx):
        tmp.append(q.popleft())
    target = q.popleft()
    while tmp:
        q.appendleft(tmp.pop())
    return target


def _available_worker_indices(free_times: list[float], now_s: float) -> list[int]:
    return [idx for idx, free_t in enumerate(free_times) if free_t <= now_s]


def _remove_job(queues: dict[str, deque[Job]], job_type: str, idx: int) -> Job:
    return _remove_index(queues[job_type], idx)


def _pick_job(
    policy_name: str, queues: dict[str, deque[Job]], eligible_types: tuple[str, ...]
) -> Job | None:
    candidates: list[tuple[str, int, Job]] = []
    for job_type in eligible_types:
        for idx, job in enumerate(queues[job_type]):
            candidates.append((job_type, idx, job))

    if not candidates:
        return None

    if policy_name == "fifo":
        job_type, idx, _ = min(candidates, key=lambda item: item[2].arrival_s)
        return _remove_job(queues, job_type, idx)

    if policy_name == "shortest-job-first":
        job_type, idx, _ = min(candidates, key=lambda item: item[2].service_ms)
        return _remove_job(queues, job_type, idx)

    if policy_name == "agentic-priority":
        for job_type, idx, _ in candidates:
            if job_type == "agentic":
                return _remove_job(queues, job_type, idx)
        job_type, idx, _ = candidates[0]
        return _remove_job(queues, job_type, idx)

    job_type, idx, _ = min(candidates, key=lambda item: item[2].arrival_s)
    return _remove_job(queues, job_type, idx)


def _next_busy_free_time(workers: dict[str, list[float]], now_s: float) -> float:
    next_time = inf
    for free_times in workers.values():
        for free_t in free_times:
            if free_t > now_s and free_t < next_time:
                next_time = free_t
    return next_time


def simulate(cfg: ExperimentConfig, jobs: list[Job]) -> list[JobResult]:
    arrivals = sorted(jobs, key=lambda j: j.arrival_s)
    total_jobs = len(arrivals)
    next_arrival_idx = 0

    queues: dict[str, deque[Job]] = {
        "streaming": deque(),
        "agentic": deque(),
    }

    workers = {
        "streaming": [0.0 for _ in range(cfg.workers.streaming)],
        "agentic": [0.0 for _ in range(cfg.workers.agentic)],
        "shared": [0.0 for _ in range(cfg.workers.shared)],
    }

    current = 0.0
    results: list[JobResult] = []

    while len(results) < total_jobs:
        while (
            next_arrival_idx < total_jobs
            and arrivals[next_arrival_idx].arrival_s <= current
        ):
            arriving = arrivals[next_arrival_idx]
            queues[arriving.job_type].append(arriving)
            next_arrival_idx += 1

        dispatched = True
        while dispatched:
            dispatched = False

            for idx in _available_worker_indices(workers["streaming"], current):
                job = _pick_job(cfg.policy.name, queues, ("streaming",))
                if job is None:
                    break
                end = current + (job.service_ms / 1000.0)
                workers["streaming"][idx] = end
                latency_ms = (end - job.arrival_s) * 1000.0
                results.append(
                    JobResult(
                        id=job.id,
                        job_type=job.job_type,
                        arrival_s=job.arrival_s,
                        start_s=current,
                        end_s=end,
                        queue_wait_ms=(current - job.arrival_s) * 1000.0,
                        service_ms=job.service_ms,
                        timed_out=latency_ms > job.timeout_ms,
                        backend_model="simulated",
                        backend_status="simulated",
                    )
                )
                dispatched = True

            for idx in _available_worker_indices(workers["agentic"], current):
                job = _pick_job(cfg.policy.name, queues, ("agentic",))
                if job is None:
                    break
                end = current + (job.service_ms / 1000.0)
                workers["agentic"][idx] = end
                latency_ms = (end - job.arrival_s) * 1000.0
                results.append(
                    JobResult(
                        id=job.id,
                        job_type=job.job_type,
                        arrival_s=job.arrival_s,
                        start_s=current,
                        end_s=end,
                        queue_wait_ms=(current - job.arrival_s) * 1000.0,
                        service_ms=job.service_ms,
                        timed_out=latency_ms > job.timeout_ms,
                        backend_model="simulated",
                        backend_status="simulated",
                    )
                )
                dispatched = True

            for idx in _available_worker_indices(workers["shared"], current):
                job = _pick_job(
                    cfg.policy.name,
                    queues,
                    ("streaming", "agentic"),
                )
                if job is None:
                    break
                end = current + (job.service_ms / 1000.0)
                workers["shared"][idx] = end
                latency_ms = (end - job.arrival_s) * 1000.0
                results.append(
                    JobResult(
                        id=job.id,
                        job_type=job.job_type,
                        arrival_s=job.arrival_s,
                        start_s=current,
                        end_s=end,
                        queue_wait_ms=(current - job.arrival_s) * 1000.0,
                        service_ms=job.service_ms,
                        timed_out=latency_ms > job.timeout_ms,
                        backend_model="simulated",
                        backend_status="simulated",
                    )
                )
                dispatched = True

        if len(results) >= total_jobs:
            break

        next_arrival_time = (
            arrivals[next_arrival_idx].arrival_s
            if next_arrival_idx < total_jobs
            else inf
        )
        next_free_time = _next_busy_free_time(workers, current)
        current = min(next_arrival_time, next_free_time)

        if current == inf:
            break

    return results
