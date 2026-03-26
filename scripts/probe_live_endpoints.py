from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from urllib import error, request

from mws_bench.config import load_config


def _candidate_urls(base_url: str) -> list[str]:
    base = base_url.rstrip("/")
    roots = [base]
    if base.endswith("/v1"):
        roots.append(base[: -len("/v1")])

    paths = [
        "/v1/chat/completions",
        "/chat/completions",
        "/v1/completions",
        "/completions",
    ]

    out: list[str] = []
    seen: set[str] = set()
    for root in roots:
        for path in paths:
            url = root + path
            if url not in seen:
                out.append(url)
                seen.add(url)
    return out


def _probe_backend(name: str, base_url: str, api_key_env: str, model: str) -> bool:
    print(f"\\n[{name}] base_url={base_url}")

    headers = {"Content-Type": "application/json"}
    key = os.environ.get(api_key_env, "")
    if key:
        headers["Authorization"] = f"Bearer {key}"

    chat_payload = {
        "model": model,
        "messages": [{"role": "user", "content": "ping"}],
        "max_tokens": 8,
        "temperature": 0.0,
    }
    completion_payload = {
        "model": model,
        "prompt": "ping",
        "max_tokens": 8,
        "temperature": 0.0,
    }

    any_non_404 = False
    for url in _candidate_urls(base_url):
        payload = chat_payload if "chat/completions" in url else completion_payload
        req = request.Request(
            url=url,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=2.0) as resp:
                body = resp.read(160).decode("utf-8", "replace").replace("\n", " ")
                print(f"  {url} -> HTTP {resp.status} body={body[:120]}")
                any_non_404 = True
        except error.HTTPError as exc:
            body = exc.read(160).decode("utf-8", "replace").replace("\n", " ")
            print(f"  {url} -> HTTP {exc.code} body={body[:120]}")
            if exc.code != 404:
                any_non_404 = True
        except error.URLError as exc:
            print(f"  {url} -> URL error {exc}")
        except TimeoutError as exc:
            print(f"  {url} -> timeout {exc}")

    return any_non_404


def main() -> int:
    parser = argparse.ArgumentParser(description="Probe live backend endpoint readiness")
    parser.add_argument(
        "--config",
        action="append",
        default=[],
        help="Config path(s) to inspect. If omitted, probes live_vllm.json, live_sglang.json, live_ray_serve.json.",
    )
    args = parser.parse_args()

    config_paths = [Path(p) for p in args.config]
    if not config_paths:
        config_paths = [
            Path("configs/live_vllm.json"),
            Path("configs/live_sglang.json"),
            Path("configs/live_ray_serve.json"),
        ]

    overall_ok = False
    for path in config_paths:
        cfg = load_config(path)
        print(f"\\n=== probing from {path} (mode={cfg.execution.mode}) ===")
        if cfg.execution.mode == "live-vllm":
            overall_ok = _probe_backend(
                "vllm", cfg.vllm.base_url, cfg.vllm.api_key_env, cfg.vllm.streaming_model
            ) or overall_ok
        elif cfg.execution.mode == "live-sglang":
            overall_ok = _probe_backend(
                "sglang",
                cfg.sglang.base_url,
                cfg.sglang.api_key_env,
                cfg.sglang.streaming_model,
            ) or overall_ok
        elif cfg.execution.mode == "live-ray-serve":
            overall_ok = _probe_backend(
                "ray_serve",
                cfg.ray_serve.base_url,
                cfg.ray_serve.api_key_env,
                cfg.ray_serve.streaming_model,
            ) or overall_ok
        else:
            print("  skipped: non-live OpenAI-compatible mode")

    if not overall_ok:
        print("\\nNo non-404 successful probe observed. Check base_url, server startup, and API route compatibility.")
        return 1

    print("\\nAt least one backend endpoint responded with a non-404 result.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
