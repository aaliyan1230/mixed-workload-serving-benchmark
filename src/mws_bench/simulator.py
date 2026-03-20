from __future__ import annotations

from collections import deque
from dataclasses import dataclass

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


def _worker_count(cfg: ExperimentConfig, job_type: str) -> int:
    dedicated = (
        cfg.workers.streaming if job_type == "streaming" else cfg.workers.agentic
    )
    return dedicated + cfg.workers.shared


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


def _pick_next_job_fixed(policy_name: str, queue: deque[Job]) -> Job:
    if policy_name == "fifo":
        return queue.popleft()

    if policy_name == "shortest-job-first":
        idx = min(range(len(queue)), key=lambda i: queue[i].service_ms)
        return _remove_index(queue, idx)

    if policy_name == "agentic-priority":
        for idx, job in enumerate(queue):
            if job.job_type == "agentic":
                return _remove_index(queue, idx)
        return queue.popleft()

    return queue.popleft()


def simulate(cfg: ExperimentConfig, jobs: list[Job]) -> list[JobResult]:
    # Uses a simple event progression over sorted arrivals and worker free-times.
    pending: deque[Job] = deque()
    arrivals = iter(sorted(jobs, key=lambda j: j.arrival_s))
    next_arrival = next(arrivals, None)

    worker_free = {
        "streaming": [0.0 for _ in range(_worker_count(cfg, "streaming"))],
        "agentic": [0.0 for _ in range(_worker_count(cfg, "agentic"))],
    }

    results: list[JobResult] = []

    current = 0.0
    while next_arrival is not None or pending:
        next_free = min(
            min(worker_free["streaming"], default=float("inf")),
            min(worker_free["agentic"], default=float("inf")),
        )

        if next_arrival is not None and (
            not pending or next_arrival.arrival_s <= next_free
        ):
            current = max(current, next_arrival.arrival_s)
            pending.append(next_arrival)
            next_arrival = next(arrivals, None)
            continue

        if not pending:
            current = max(current, next_free)
            continue

        job = _pick_next_job_fixed(cfg.policy.name, pending)
        pool = worker_free[job.job_type]
        idx = min(range(len(pool)), key=lambda i: pool[i])
        start = max(current, pool[idx], job.arrival_s)
        end = start + (job.service_ms / 1000.0)
        pool[idx] = end

        latency_ms = (end - job.arrival_s) * 1000.0
        timed_out = latency_ms > job.timeout_ms

        results.append(
            JobResult(
                id=job.id,
                job_type=job.job_type,
                arrival_s=job.arrival_s,
                start_s=start,
                end_s=end,
                queue_wait_ms=(start - job.arrival_s) * 1000.0,
                service_ms=job.service_ms,
                timed_out=timed_out,
            )
        )

        current = min(
            min(worker_free["streaming"], default=current),
            min(worker_free["agentic"], default=current),
        )

    return results
