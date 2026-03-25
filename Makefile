.PHONY: help setup kernel run run-trace run-ollama run-ollama-trace run-vllm run-sglang run-ray-serve probe-live mk-remote-vllm-r5 mk-remote-sglang-r5 mk-remote-ray-r5 sweep sweep-contention sweep-ollama-r5 sweep-vllm-r5 sweep-sglang-r5 sweep-ray-serve-r5 plots report test notebook all

help:
	@printf "Available targets:\n"
	@printf "  make setup            # create/update uv env with dev deps\n"
	@printf "  make kernel           # register Jupyter kernel\n"
	@printf "  make run              # run one baseline config\n"
	@printf "  make run-trace        # run baseline config with request-level trace\n"
	@printf "  make run-ollama       # run local Ollama live benchmark\n"
	@printf "  make run-ollama-trace # run local Ollama benchmark with request-level trace\n"
	@printf "  make run-vllm         # run vLLM OpenAI-compatible benchmark with trace\n"
	@printf "  make run-sglang       # run SGLang OpenAI-compatible benchmark with trace\n"
	@printf "  make run-ray-serve    # run Ray Serve OpenAI-compatible benchmark with trace\n"
	@printf "  make probe-live       # probe live backend endpoints/routes\n"
	@printf "  make mk-remote-vllm-r5 BASE_URL=...   # write remote vLLM r5 config\n"
	@printf "  make mk-remote-sglang-r5 BASE_URL=... # write remote SGLang r5 config\n"
	@printf "  make mk-remote-ray-r5 BASE_URL=...    # write remote Ray Serve r5 config\n"
	@printf "  make sweep            # run baseline sweep\n"
	@printf "  make sweep-contention # run high-contention sweep\n"
	@printf "  make sweep-ollama-r5  # run replicate-5 local Ollama sweep with traces\n"
	@printf "  make sweep-vllm-r5    # run replicate-5 vLLM sweep with traces\n"
	@printf "  make sweep-sglang-r5  # run replicate-5 SGLang sweep with traces\n"
	@printf "  make sweep-ray-serve-r5 # run replicate-5 Ray Serve sweep with traces\n"
	@printf "  make plots            # generate plots for both sweeps\n"
	@printf "  make report           # generate docs/results.md\n"
	@printf "  make test             # run test suite\n"
	@printf "  make notebook         # launch analysis notebook\n"
	@printf "  make all              # run full pipeline\n"

setup:
	uv venv .venv
	uv sync --extra dev

kernel:
	uv run python -m ipykernel install --user --name mws-bench --display-name "Python (mws-bench)"

run:
	uv run mws-bench run --config configs/default.json --output results/default_run.json

run-trace:
	uv run mws-bench run --config configs/default.json --output results/default_run.json --trace-output results/default_trace.jsonl

run-ollama:
	uv run mws-bench run --config configs/live_ollama.json --output results/live_ollama_run.json

run-ollama-trace:
	uv run mws-bench run --config configs/live_ollama.json --output results/live_ollama_run.json --trace-output results/live_ollama_trace.jsonl

run-vllm:
	uv run mws-bench run --config configs/live_vllm.json --output results/live_vllm_run.json --trace-output results/live_vllm_trace.jsonl

run-sglang:
	uv run mws-bench run --config configs/live_sglang.json --output results/live_sglang_run.json --trace-output results/live_sglang_trace.jsonl

run-ray-serve:
	uv run mws-bench run --config configs/live_ray_serve.json --output results/live_ray_serve_run.json --trace-output results/live_ray_serve_trace.jsonl

probe-live:
	uv run python scripts/probe_live_endpoints.py

mk-remote-vllm-r5:
	uv run python scripts/cloud/write_remote_config.py --backend vllm --base-url "$(BASE_URL)" --r5 --output configs/live_vllm_remote_r5.json

mk-remote-sglang-r5:
	uv run python scripts/cloud/write_remote_config.py --backend sglang --base-url "$(BASE_URL)" --r5 --output configs/live_sglang_remote_r5.json

mk-remote-ray-r5:
	uv run python scripts/cloud/write_remote_config.py --backend ray-serve --base-url "$(BASE_URL)" --r5 --output configs/live_ray_serve_remote_r5.json

sweep:
	uv run mws-bench sweep --config configs/default.json --output results/sweep.csv

sweep-contention:
	uv run mws-bench sweep --config configs/high_contention.json --output results/high_contention_sweep.csv

sweep-ollama-r5:
	uv run mws-bench sweep --config configs/live_ollama_r5.json --output results/live_ollama_sweep_r5.csv --trace-output-dir results/traces/live_ollama_r5

sweep-vllm-r5:
	uv run mws-bench sweep --config configs/live_vllm_r5.json --output results/live_vllm_sweep_r5.csv --trace-output-dir results/traces/live_vllm_r5

sweep-sglang-r5:
	uv run mws-bench sweep --config configs/live_sglang_r5.json --output results/live_sglang_sweep_r5.csv --trace-output-dir results/traces/live_sglang_r5

sweep-ray-serve-r5:
	uv run mws-bench sweep --config configs/live_ray_serve_r5.json --output results/live_ray_serve_sweep_r5.csv --trace-output-dir results/traces/live_ray_serve_r5

plots:
	uv run python scripts/plot_sweep.py --input results/sweep.csv --output-dir results/plots/default
	uv run python scripts/plot_sweep.py --input results/high_contention_sweep.csv --output-dir results/plots/high_contention

report:
	uv run python scripts/make_report_md.py --baseline results/sweep.csv --contention results/high_contention_sweep.csv --output docs/results.md

test:
	uv run pytest -q

notebook:
	uv run jupyter lab notebooks/analysis_entrypoint.ipynb

all: sweep sweep-contention plots report test
	@printf "Full pipeline complete. See results/ and docs/results.md\n"
