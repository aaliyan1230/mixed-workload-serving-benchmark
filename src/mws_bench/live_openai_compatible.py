from __future__ import annotations

import json
import os
import time
from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
from dataclasses import dataclass
from typing import Literal
from urllib import error, request

from .config import ExperimentConfig, RayServeConfig, SglangConfig, VllmConfig
from .simulator import JobResult
from .workload import Job


@dataclass(frozen=True)
class _Outcome:
    end_s: float
    timed_out: bool
    backend_status: str
    backend_error: str | None
    backend_model: str


OpenAICompatibleConfig = VllmConfig | SglangConfig | RayServeConfig


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


def _build_request(cfg: OpenAICompatibleConfig, job: Job) -> tuple[str, bytes, dict[str, str], str]:
    if job.job_type == "streaming":
        model = cfg.streaming_model
        prompt = cfg.streaming_prompt
        max_tokens = cfg.streaming_max_tokens
    else:
        model = cfg.agentic_model
        prompt = cfg.agentic_prompt
        max_tokens = cfg.agentic_max_tokens

    payload = {
        "model": model,
        "messages": [
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.0,
        "max_tokens": max_tokens,
    }

    headers = {"Content-Type": "application/json"}
    api_key = os.environ.get(cfg.api_key_env, "")
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    url = cfg.base_url.rstrip("/") + "/v1/chat/completions"
    return url, json.dumps(payload).encode("utf-8"), headers, model


def _run_one(run_cfg: OpenAICompatibleConfig, job: Job, start_s: float) -> _Outcome:
    deadline_s = min(run_cfg.request_timeout_s, job.timeout_ms / 1000.0)
    timed_out = False
    backend_status = "ok"
    backend_error: str | None = None

    url, payload, headers, model = _build_request(run_cfg, job)

    req = request.Request(
        url=url,
        data=payload,
        headers=headers,
        method="POST",
    )

    try:
        with request.urlopen(req, timeout=deadline_s) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            if body.get("error"):
                backend_status = "backend-error"
                backend_error = str(body.get("error"))
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


def run_live_vllm(cfg: ExperimentConfig, jobs: list[Job]) -> list[JobResult]:
    return _run_live_openai_compatible(cfg, jobs, backend="vllm")


def run_live_sglang(cfg: ExperimentConfig, jobs: list[Job]) -> list[JobResult]:
    return _run_live_openai_compatible(cfg, jobs, backend="sglang")


def run_live_ray_serve(cfg: ExperimentConfig, jobs: list[Job]) -> list[JobResult]:
    return _run_live_openai_compatible(cfg, jobs, backend="ray-serve")


def _run_live_openai_compatible(
    cfg: ExperimentConfig,
    jobs: list[Job],
    backend: Literal["vllm", "sglang", "ray-serve"],
) -> list[JobResult]:
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
                if backend == "vllm":
                    run_cfg = cfg.vllm
                elif backend == "sglang":
                    run_cfg = cfg.sglang
                else:
                    run_cfg = cfg.ray_serve
                fut = pool.submit(_run_one, run_cfg, job, start_clock)
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
                            timed_out=outcome.timed_out
                            or ((end_s - job.arrival_s) * 1000.0 > job.timeout_ms),
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
