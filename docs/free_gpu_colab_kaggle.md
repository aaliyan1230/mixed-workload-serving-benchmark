# Free GPU Plan: Colab vs Kaggle

## Short answer

- Most feasible first: **Colab**.
- Why: easier ad-hoc runtime setup and endpoint tunneling workflow for remote API serving.
- Highest free GPU config: usually **similar class** (T4/P100 range) across free tiers; neither is reliable for guaranteed high-end GPUs on free plans.
- If your goal is stable weekly budget over convenience, Kaggle can still be useful.

## Recommendation for this repo

1. Start with Colab for `vLLM` endpoint bring-up and quick iteration.
2. If Colab GPU quota is exhausted, use Kaggle as fallback with the same tunnel pattern.
3. Keep your local benchmark runner here; only host model servers remotely.

## Colab: quick start (vLLM)

In a Colab notebook with GPU runtime enabled:

```bash
!pip -q install vllm pyngrok
```

```python
from pyngrok import ngrok
import subprocess, time, os

# Optional: ngrok auth token for stable behavior
# os.environ["NGROK_AUTHTOKEN"] = "..."
# ngrok.set_auth_token(os.environ["NGROK_AUTHTOKEN"])

# Start vLLM server locally in notebook VM
proc = subprocess.Popen([
    "python", "-m", "vllm.entrypoints.openai.api_server",
    "--host", "0.0.0.0",
    "--port", "8000",
    "--model", "Qwen/Qwen2.5-3B-Instruct",
])

time.sleep(15)
public = ngrok.connect(8000, "http")
print("Public URL:", public.public_url)
```

Use the printed URL as your local config base URL.

## Kaggle: fallback start (vLLM/SGLang style endpoint)

- Enable GPU and Internet in notebook settings.
- Install serving stack and `pyngrok`.
- Start server on port `8000`.
- Expose with ngrok and copy URL.

Kaggle is workable, but setup ergonomics and environment constraints can be trickier than Colab for rapid server iteration.

## Use remote endpoint from local repo

Create endpoint-specific config:

```bash
uv run python scripts/cloud/write_remote_config.py \
  --backend vllm \
  --base-url https://YOUR-NGROK-URL \
  --r5 \
  --output configs/live_vllm_remote_r5.json
```

Probe and run:

```bash
uv run python scripts/probe_live_endpoints.py --config configs/live_vllm_remote_r5.json
uv run mws-bench sweep --config configs/live_vllm_remote_r5.json --output results/live_vllm_remote_sweep_r5.csv --trace-output-dir results/traces/live_vllm_remote_r5
```

Repeat the same pattern for `sglang` or `ray-serve` backends.
