from __future__ import annotations

import argparse
import json
from pathlib import Path


def _patch_config(
    in_path: Path,
    out_path: Path,
    mode: str,
    base_url: str,
    streaming_model: str | None,
    agentic_model: str | None,
) -> None:
    data = json.loads(in_path.read_text())
    data.setdefault("execution", {})["mode"] = mode

    key = "vllm" if mode == "live-vllm" else "sglang" if mode == "live-sglang" else "ray_serve"
    section = data.setdefault(key, {})
    section["base_url"] = base_url.rstrip("/")
    if streaming_model:
        section["streaming_model"] = streaming_model
    if agentic_model:
        section["agentic_model"] = agentic_model

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(data, indent=2) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Create remote-endpoint config variants for live backends")
    parser.add_argument("--backend", choices=["vllm", "sglang", "ray-serve"], required=True)
    parser.add_argument("--base-url", required=True, help="Remote OpenAI-compatible endpoint base URL")
    parser.add_argument("--r5", action="store_true", help="Use replicate-5 template config")
    parser.add_argument("--streaming-model", help="Override streaming model id in output config")
    parser.add_argument("--agentic-model", help="Override agentic model id in output config")
    parser.add_argument("--output", required=True, help="Output config JSON path")
    args = parser.parse_args()

    if args.backend == "vllm":
        mode = "live-vllm"
        template = "configs/live_vllm_r5.json" if args.r5 else "configs/live_vllm.json"
    elif args.backend == "sglang":
        mode = "live-sglang"
        template = "configs/live_sglang_r5.json" if args.r5 else "configs/live_sglang.json"
    else:
        mode = "live-ray-serve"
        template = "configs/live_ray_serve_r5.json" if args.r5 else "configs/live_ray_serve.json"

    _patch_config(
        Path(template),
        Path(args.output),
        mode,
        args.base_url,
        args.streaming_model,
        args.agentic_model,
    )
    print(f"Wrote {args.output} from {template} with {mode} base_url={args.base_url}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
