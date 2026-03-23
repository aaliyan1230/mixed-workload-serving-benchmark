# Mixed Workload Serving Benchmark

Lightweight benchmark harness for **mixed streaming + agentic workloads**.

This project is designed for fast, reproducible experiments on scheduling behavior under realistic stressors:
- workload mix shifts (90:10, 50:50, 10:90)
- tool stalls and timeout behavior
- queue contention in shared worker pools

## What You Get

- deterministic workload generator (seeded)
- discrete-event simulator for serving policies
- built-in metrics:
  - throughput
  - p95/p99 latency
  - SLA violation rate
  - cost per successful task
- one-command sweep for policy comparison

## Quick Start

```bash
uv venv .venv
source .venv/bin/activate
uv sync --extra dev

# Register notebook kernel for this repo (one time)
uv run python -m ipykernel install --user --name mws-bench --display-name "Python (mws-bench)"

# Run one config
uv run mws-bench run --config configs/default.json --output results/default_run.json

# Optional: write request-level trace JSONL for one run
uv run mws-bench run --config configs/default.json --output results/default_run.json --trace-output results/default_trace.jsonl

# Run matrix sweep (mix x policy)
uv run mws-bench sweep --output results/sweep.csv

# Optional: write per-scenario request-level trace JSONL files for sweep
uv run mws-bench sweep --output results/sweep.csv --trace-output-dir results/traces/default

# Run high-contention scenario
uv run mws-bench sweep --config configs/high_contention.json --output results/high_contention_sweep.csv

# Plot a sweep CSV
uv run python scripts/plot_sweep.py --input results/sweep.csv --output-dir results/plots/default

# Run against local Ollama (no API key)
uv run mws-bench run --config configs/live_ollama.json --output results/live_ollama_run.json

# Run against local Ollama and emit request-level trace
uv run mws-bench run --config configs/live_ollama.json --output results/live_ollama_run.json --trace-output results/live_ollama_trace.jsonl

# Run replicate-5 local Ollama sweep with per-scenario traces
uv run mws-bench sweep --config configs/live_ollama_r5.json --output results/live_ollama_sweep_r5.csv --trace-output-dir results/traces/live_ollama_r5

# Run against vLLM OpenAI-compatible endpoint
uv run mws-bench run --config configs/live_vllm.json --output results/live_vllm_run.json --trace-output results/live_vllm_trace.jsonl

# Run against SGLang OpenAI-compatible endpoint
uv run mws-bench run --config configs/live_sglang.json --output results/live_sglang_run.json --trace-output results/live_sglang_trace.jsonl

# Optional: plot high-contention sweep
uv run python scripts/plot_sweep.py --input results/high_contention_sweep.csv --output-dir results/plots/high_contention

# Auto-generate markdown report from both sweeps
uv run python scripts/make_report_md.py --baseline results/sweep.csv --contention results/high_contention_sweep.csv --output docs/results.md

# Open notebook entrypoint for analysis and write-up
uv run jupyter lab notebooks/analysis_entrypoint.ipynb
```

## Lockfile

```bash
# Generate or update uv.lock
uv lock

# Sync the environment to the lockfile
uv sync
```

## Contributing

```bash
# Standard setup
uv sync
```

## Make Targets

```bash
# See available commands
make help

# One-time environment + kernel
make setup
make kernel

# Full pipeline
make all

# Open notebook
make notebook
```

## Project Layout

- `src/mws_bench/config.py`: typed experiment config and JSON loader
- `src/mws_bench/workload.py`: arrival and job-shape generation
- `src/mws_bench/simulator.py`: event-loop simulation engine
- `src/mws_bench/metrics.py`: aggregate metrics and class-level stats
- `src/mws_bench/runner.py`: replicate runner + sweep matrix
- `src/mws_bench/cli.py`: `run` and `sweep` commands
- `configs/default.json`: baseline experiment config
- `configs/high_contention.json`: stress profile for queue pressure and timeouts
- `tests/`: smoke tests for generation, simulation, and metrics
- `scripts/plot_sweep.py`: grouped bar-chart generator for core metrics
- `scripts/make_report_md.py`: auto-generates `docs/results.md` from sweep CSVs
- `docs/technical_note_template.md`: 2-3 page note scaffold
- `notebooks/analysis_entrypoint.ipynb`: analysis/report notebook entrypoint

## Notes

- This scaffold intentionally uses standard library only.
- You can extend it to real serving backends (Ray Serve, vLLM, SGLang) after validating synthetic policy trends.

## Live Backend Modes

### Local Ollama Mode (No Key)

- Install and start Ollama locally (`ollama serve`).
- Pull at least one model (`ollama pull llama3.2:3b`).
- Use `configs/live_ollama.json` and set model names that exist on your machine.

Example:

```bash
uv run mws-bench run --config configs/live_ollama.json --output results/live_ollama_run.json
```

Config fields:

- `execution.mode`: use `simulate` or `live-ollama`
- `ollama.base_url`: default `http://127.0.0.1:11434`
- `ollama.streaming_model` / `ollama.agentic_model`: local model tags
- `ollama.request_timeout_s`: per-request timeout ceiling
- `ollama.*_prompt`, `ollama.*_num_predict`: load-shape controls for each class

### vLLM Mode (OpenAI-Compatible)

- Start a vLLM OpenAI-compatible server (for example on `http://127.0.0.1:8000`).
- Use `configs/live_vllm.json` and set model names that your server exposes.
- Optional auth: set `VLLM_API_KEY` (or your configured env var in `vllm.api_key_env`).

Example:

```bash
uv run mws-bench run --config configs/live_vllm.json --output results/live_vllm_run.json --trace-output results/live_vllm_trace.jsonl
```

Config fields:

- `execution.mode`: `live-vllm`
- `vllm.base_url`: OpenAI-compatible base URL
- `vllm.api_key_env`: env var name used for bearer token
- `vllm.streaming_model` / `vllm.agentic_model`: model ids
- `vllm.request_timeout_s`: per-request timeout ceiling
- `vllm.*_prompt`, `vllm.*_max_tokens`: load-shape controls for each class

### SGLang Mode (OpenAI-Compatible)

- Start an SGLang OpenAI-compatible server (for example on `http://127.0.0.1:30000`).
- Use `configs/live_sglang.json` and set model names that your server exposes.
- Optional auth: set `SGLANG_API_KEY` (or your configured env var in `sglang.api_key_env`).

Example:

```bash
uv run mws-bench run --config configs/live_sglang.json --output results/live_sglang_run.json --trace-output results/live_sglang_trace.jsonl
```

Config fields:

- `execution.mode`: `live-sglang`
- `sglang.base_url`: OpenAI-compatible base URL
- `sglang.api_key_env`: env var name used for bearer token
- `sglang.streaming_model` / `sglang.agentic_model`: model ids
- `sglang.request_timeout_s`: per-request timeout ceiling
- `sglang.*_prompt`, `sglang.*_max_tokens`: load-shape controls for each class

Trace fields include per-request latency and backend metadata:

- `replicate`, `policy`, workload mix
- `job_id`, `job_type`, `arrival_s`, `start_s`, `end_s`
- `queue_wait_ms`, `service_ms`, `latency_ms`, `timed_out`
- `backend_model`, `backend_status`, `backend_error`

## Notebook Workflow

- Use `notebooks/analysis_entrypoint.ipynb` as the main analysis entrypoint.
- The notebook loads `results/sweep.csv` and `results/high_contention_sweep.csv`, builds quick tables/plots, and provides markdown prompts for findings.
- Save finalized narrative in `docs/results.md` and/or `docs/technical_note_template.md`.
