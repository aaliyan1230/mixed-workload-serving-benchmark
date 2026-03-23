.PHONY: help setup kernel run run-trace run-ollama run-ollama-trace run-vllm sweep sweep-contention sweep-ollama-r5 plots report test notebook all

help:
	@printf "Available targets:\n"
	@printf "  make setup            # create/update uv env with dev deps\n"
	@printf "  make kernel           # register Jupyter kernel\n"
	@printf "  make run              # run one baseline config\n"
	@printf "  make run-trace        # run baseline config with request-level trace\n"
	@printf "  make run-ollama       # run local Ollama live benchmark\n"
	@printf "  make run-ollama-trace # run local Ollama benchmark with request-level trace\n"
	@printf "  make run-vllm         # run vLLM OpenAI-compatible benchmark with trace\n"
	@printf "  make sweep            # run baseline sweep\n"
	@printf "  make sweep-contention # run high-contention sweep\n"
	@printf "  make sweep-ollama-r5  # run replicate-5 local Ollama sweep with traces\n"
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

sweep:
	uv run mws-bench sweep --config configs/default.json --output results/sweep.csv

sweep-contention:
	uv run mws-bench sweep --config configs/high_contention.json --output results/high_contention_sweep.csv

sweep-ollama-r5:
	uv run mws-bench sweep --config configs/live_ollama_r5.json --output results/live_ollama_sweep_r5.csv --trace-output-dir results/traces/live_ollama_r5

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
