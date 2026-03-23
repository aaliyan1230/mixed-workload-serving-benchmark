from __future__ import annotations

import json
import time
from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
from dataclasses import dataclass
from urllib import error, request

from .config import ExperimentConfig
from .simulator import JobResult
from .workload import Job


@dataclass(frozen=True)
class _Outcome:
    end_s: float
    timed_out: bool
    backend_status: str
    backend_error: str | None
    backend_model: str


def _pick_job(policy_name: str, pending: list[Job]) -> Job:
    if policy_name == "fifo":
        idx = min(range(len(pending)), key=lambda i: pending[i].arrival_s)
    elif policy_name == "shortest-job-first":
        idx = min(range(len(pending)), key=lambda i: pending[i].service_ms)
    elif policy_name == "agentic-priority":
        agentic_indices = [i for i, job in enumerate(pending) if job.job_type == "agentic"]
        if agentic_indices:
            idx = agentic_indices[0]
        else:
            idx = min(range(len(pending)), key=lambda i: pending[i].arrival_s)
    else:
        idx = min(range(len(pending)), key=lambda i: pending[i].arrival_s)

    return pending.pop(idx)


def _build_payload(cfg: ExperimentConfig, job: Job) -> bytes:
    if job.job_type == "streaming":
        model = cfg.ollama.streaming_model
        prompt = cfg.ollama.streaming_prompt
        num_predict = cfg.ollama.streaming_num_predict
    else:
        model = cfg.ollama.agentic_model
        prompt = cfg.ollama.agentic_prompt
        num_predict = cfg.ollama.agentic_num_predict

    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "num_predict": num_predict,
        },
    }
    return json.dumps(payload).encode("utf-8")


def _run_one(cfg: ExperimentConfig, job: Job, start_s: float) -> _Outcome:
    deadline_s = min(cfg.ollama.request_timeout_s, job.timeout_ms / 1000.0)
    timed_out = False
    backend_status = "ok"
    backend_error: str | None = None

    model = (
        cfg.ollama.streaming_model
        if job.job_type == "streaming"
        else cfg.ollama.agentic_model
    )

    req = request.Request(
        url=cfg.ollama.base_url.rstrip("/") + "/api/generate",
        data=_build_payload(cfg, job),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with request.urlopen(req, timeout=deadline_s) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
            if payload.get("error"):
                backend_status = "backend-error"
                backend_error = str(payload.get("error"))
            else:
                backend_status = "ok"
    except TimeoutError as exc:
        timed_out = True
        backend_status = "timeout"
        backend_error = str(exc)
    except error.HTTPError as exc:
        timed_out = True
        backend_status = "http-error"
        backend_error = str(exc)
    except error.URLError as exc:
        timed_out = True
        backend_status = "url-error"
        backend_error = str(exc)

    ended = time.monotonic() - start_s
    return _Outcome(
        end_s=ended,
        timed_out=timed_out,
        backend_status=backend_status,
        backend_error=backend_error,
        backend_model=model,
    )


def run_live_ollama(cfg: ExperimentConfig, jobs: list[Job]) -> list[JobResult]:
    arrivals = sorted(jobs, key=lambda j: j.arrival_s)
    total_jobs = len(arrivals)
    next_arrival_idx = 0
    pending: list[Job] = []

    total_workers = cfg.workers.streaming + cfg.workers.agentic + cfg.workers.shared
    max_workers = max(total_workers, 1)

    start_clock = time.monotonic()
    active: dict[Future[_Outcome], tuple[Job, float]] = {}
    results: list[JobResult] = []

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        while len(results) < total_jobs:
            now = time.monotonic() - start_clock

            while next_arrival_idx < total_jobs and arrivals[next_arrival_idx].arrival_s <= now:
                pending.append(arrivals[next_arrival_idx])
                next_arrival_idx += 1

            while pending and len(active) < max_workers:
                job = _pick_job(cfg.policy.name, pending)
                start_s = time.monotonic() - start_clock
                fut = pool.submit(_run_one, cfg, job, start_clock)
                active[fut] = (job, start_s)

            if active:
                done, _ = wait(active.keys(), timeout=0.01, return_when=FIRST_COMPLETED)
                for fut in done:
                    outcome = fut.result()
                    job, start_s = active.pop(fut)
                    end_s = max(outcome.end_s, start_s)
                    results.append(
                        JobResult(
                            id=job.id,
                            job_type=job.job_type,
                            arrival_s=job.arrival_s,
                            start_s=start_s,
                            end_s=end_s,
                            queue_wait_ms=max((start_s - job.arrival_s) * 1000.0, 0.0),
                            service_ms=max((end_s - start_s) * 1000.0, 0.0),
                            timed_out=outcome.timed_out or ((end_s - job.arrival_s) * 1000.0 > job.timeout_ms),
                            backend_model=outcome.backend_model,
                            backend_status=outcome.backend_status,
                            backend_error=outcome.backend_error,
                        )
                    )
                continue

            if next_arrival_idx < total_jobs:
                next_arrival = arrivals[next_arrival_idx].arrival_s
                sleep_s = max(min(next_arrival - now, 0.05), 0.001)
                time.sleep(sleep_s)
                continue

            break

    return results
