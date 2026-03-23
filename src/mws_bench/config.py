from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class MixConfig:
    streaming_ratio: float
    agentic_ratio: float


@dataclass(frozen=True)
class PolicyConfig:
    name: str


@dataclass(frozen=True)
class WorkerConfig:
    streaming: int
    agentic: int
    shared: int


@dataclass(frozen=True)
class SlaConfig:
    streaming_ms: float
    agentic_ms: float


@dataclass(frozen=True)
class CostConfig:
    streaming_unit: float
    agentic_unit: float
    timeout_penalty: float


@dataclass(frozen=True)
class StreamingProfile:
    service_ms_mean: float
    service_ms_std: float
    timeout_ms: float


@dataclass(frozen=True)
class AgenticProfile:
    steps_mean: float
    steps_std: float
    step_ms_mean: float
    step_ms_std: float
    stall_probability: float
    stall_ms: float
    timeout_ms: float


@dataclass(frozen=True)
class ExecutionConfig:
    mode: str


@dataclass(frozen=True)
class OllamaConfig:
    base_url: str
    streaming_model: str
    agentic_model: str
    request_timeout_s: float
    streaming_prompt: str
    agentic_prompt: str
    streaming_num_predict: int
    agentic_num_predict: int


@dataclass(frozen=True)
class VllmConfig:
    base_url: str
    api_key_env: str
    request_timeout_s: float
    streaming_model: str
    agentic_model: str
    streaming_prompt: str
    agentic_prompt: str
    streaming_max_tokens: int
    agentic_max_tokens: int


@dataclass(frozen=True)
class SglangConfig:
    base_url: str
    api_key_env: str
    request_timeout_s: float
    streaming_model: str
    agentic_model: str
    streaming_prompt: str
    agentic_prompt: str
    streaming_max_tokens: int
    agentic_max_tokens: int


@dataclass(frozen=True)
class RayServeConfig:
    base_url: str
    api_key_env: str
    request_timeout_s: float
    streaming_model: str
    agentic_model: str
    streaming_prompt: str
    agentic_prompt: str
    streaming_max_tokens: int
    agentic_max_tokens: int


@dataclass(frozen=True)
class ExperimentConfig:
    seed: int
    duration_s: float
    arrival_rate_rps: float
    mix: MixConfig
    policy: PolicyConfig
    workers: WorkerConfig
    sla: SlaConfig
    cost: CostConfig
    streaming_profile: StreamingProfile
    agentic_profile: AgenticProfile
    execution: ExecutionConfig
    ollama: OllamaConfig
    vllm: VllmConfig
    sglang: SglangConfig
    ray_serve: RayServeConfig
    replicates: int


def _validate_mix(mix: MixConfig) -> None:
    total = mix.streaming_ratio + mix.agentic_ratio
    if abs(total - 1.0) > 1e-6:
        raise ValueError(f"mix ratios must sum to 1.0, got {total}")


def _validate_workers(workers: WorkerConfig) -> None:
    if workers.streaming < 0 or workers.agentic < 0 or workers.shared < 0:
        raise ValueError("worker counts must be non-negative")
    if workers.streaming + workers.agentic + workers.shared == 0:
        raise ValueError("at least one worker is required")


def _validate_capacity(cfg: ExperimentConfig) -> None:
    if cfg.mix.streaming_ratio > 0 and cfg.workers.streaming + cfg.workers.shared == 0:
        raise ValueError("streaming workload requires streaming or shared workers")
    if cfg.mix.agentic_ratio > 0 and cfg.workers.agentic + cfg.workers.shared == 0:
        raise ValueError("agentic workload requires agentic or shared workers")
    if cfg.replicates <= 0:
        raise ValueError("replicates must be positive")


def _validate_execution(cfg: ExperimentConfig) -> None:
    supported_modes = {
        "simulate",
        "live-ollama",
        "live-vllm",
        "live-sglang",
        "live-ray-serve",
    }
    if cfg.execution.mode not in supported_modes:
        raise ValueError(
            f"execution mode must be one of {sorted(supported_modes)}, got {cfg.execution.mode}"
        )

    if cfg.execution.mode == "live-ollama":
        if cfg.ollama.request_timeout_s <= 0:
            raise ValueError("ollama request_timeout_s must be positive")
        if not cfg.ollama.base_url:
            raise ValueError("ollama base_url is required for live-ollama mode")
        if not cfg.ollama.streaming_model or not cfg.ollama.agentic_model:
            raise ValueError("ollama models are required for live-ollama mode")

    if cfg.execution.mode == "live-vllm":
        if cfg.vllm.request_timeout_s <= 0:
            raise ValueError("vllm request_timeout_s must be positive")
        if not cfg.vllm.base_url:
            raise ValueError("vllm base_url is required for live-vllm mode")
        if not cfg.vllm.streaming_model or not cfg.vllm.agentic_model:
            raise ValueError("vllm models are required for live-vllm mode")

    if cfg.execution.mode == "live-sglang":
        if cfg.sglang.request_timeout_s <= 0:
            raise ValueError("sglang request_timeout_s must be positive")
        if not cfg.sglang.base_url:
            raise ValueError("sglang base_url is required for live-sglang mode")
        if not cfg.sglang.streaming_model or not cfg.sglang.agentic_model:
            raise ValueError("sglang models are required for live-sglang mode")

    if cfg.execution.mode == "live-ray-serve":
        if cfg.ray_serve.request_timeout_s <= 0:
            raise ValueError("ray_serve request_timeout_s must be positive")
        if not cfg.ray_serve.base_url:
            raise ValueError("ray_serve base_url is required for live-ray-serve mode")
        if not cfg.ray_serve.streaming_model or not cfg.ray_serve.agentic_model:
            raise ValueError("ray_serve models are required for live-ray-serve mode")


def load_config(path: str | Path) -> ExperimentConfig:
    data = json.loads(Path(path).read_text())

    execution_data = data.get("execution", {"mode": "simulate"})
    ollama_data = data.get("ollama", {})
    vllm_data = data.get("vllm", {})
    sglang_data = data.get("sglang", {})
    ray_serve_data = data.get("ray_serve", {})

    cfg = ExperimentConfig(
        seed=int(data["seed"]),
        duration_s=float(data["duration_s"]),
        arrival_rate_rps=float(data["arrival_rate_rps"]),
        mix=MixConfig(**data["mix"]),
        policy=PolicyConfig(**data["policy"]),
        workers=WorkerConfig(**data["workers"]),
        sla=SlaConfig(**data["sla"]),
        cost=CostConfig(**data["cost"]),
        streaming_profile=StreamingProfile(**data["streaming_profile"]),
        agentic_profile=AgenticProfile(**data["agentic_profile"]),
        execution=ExecutionConfig(mode=str(execution_data.get("mode", "simulate"))),
        ollama=OllamaConfig(
            base_url=str(ollama_data.get("base_url", "http://127.0.0.1:11434")),
            streaming_model=str(ollama_data.get("streaming_model", "llama3.2:3b")),
            agentic_model=str(ollama_data.get("agentic_model", "llama3.2:3b")),
            request_timeout_s=float(ollama_data.get("request_timeout_s", 30.0)),
            streaming_prompt=str(
                ollama_data.get(
                    "streaming_prompt",
                    "Answer in one short sentence: what is 2+2?",
                )
            ),
            agentic_prompt=str(
                ollama_data.get(
                    "agentic_prompt",
                    "Summarize this in three bullet points: local benchmark smoke run.",
                )
            ),
            streaming_num_predict=int(ollama_data.get("streaming_num_predict", 64)),
            agentic_num_predict=int(ollama_data.get("agentic_num_predict", 192)),
        ),
        vllm=VllmConfig(
            base_url=str(vllm_data.get("base_url", "http://127.0.0.1:8000")),
            api_key_env=str(vllm_data.get("api_key_env", "VLLM_API_KEY")),
            request_timeout_s=float(vllm_data.get("request_timeout_s", 45.0)),
            streaming_model=str(vllm_data.get("streaming_model", "Qwen/Qwen2.5-3B-Instruct")),
            agentic_model=str(vllm_data.get("agentic_model", "Qwen/Qwen2.5-3B-Instruct")),
            streaming_prompt=str(
                vllm_data.get(
                    "streaming_prompt",
                    "Answer in one short sentence: what is 2+2?",
                )
            ),
            agentic_prompt=str(
                vllm_data.get(
                    "agentic_prompt",
                    "List 5 concise bullet points on why latency benchmarking matters.",
                )
            ),
            streaming_max_tokens=int(vllm_data.get("streaming_max_tokens", 64)),
            agentic_max_tokens=int(vllm_data.get("agentic_max_tokens", 192)),
        ),
        sglang=SglangConfig(
            base_url=str(sglang_data.get("base_url", "http://127.0.0.1:30000")),
            api_key_env=str(sglang_data.get("api_key_env", "SGLANG_API_KEY")),
            request_timeout_s=float(sglang_data.get("request_timeout_s", 45.0)),
            streaming_model=str(
                sglang_data.get("streaming_model", "Qwen/Qwen2.5-3B-Instruct")
            ),
            agentic_model=str(
                sglang_data.get("agentic_model", "Qwen/Qwen2.5-3B-Instruct")
            ),
            streaming_prompt=str(
                sglang_data.get(
                    "streaming_prompt",
                    "Answer in one short sentence: what is 2+2?",
                )
            ),
            agentic_prompt=str(
                sglang_data.get(
                    "agentic_prompt",
                    "List 5 concise bullet points on why latency benchmarking matters.",
                )
            ),
            streaming_max_tokens=int(sglang_data.get("streaming_max_tokens", 64)),
            agentic_max_tokens=int(sglang_data.get("agentic_max_tokens", 192)),
        ),
        ray_serve=RayServeConfig(
            base_url=str(ray_serve_data.get("base_url", "http://127.0.0.1:8001")),
            api_key_env=str(ray_serve_data.get("api_key_env", "RAY_SERVE_API_KEY")),
            request_timeout_s=float(ray_serve_data.get("request_timeout_s", 45.0)),
            streaming_model=str(
                ray_serve_data.get("streaming_model", "Qwen/Qwen2.5-3B-Instruct")
            ),
            agentic_model=str(
                ray_serve_data.get("agentic_model", "Qwen/Qwen2.5-3B-Instruct")
            ),
            streaming_prompt=str(
                ray_serve_data.get(
                    "streaming_prompt",
                    "Answer in one short sentence: what is 2+2?",
                )
            ),
            agentic_prompt=str(
                ray_serve_data.get(
                    "agentic_prompt",
                    "List 5 concise bullet points on why latency benchmarking matters.",
                )
            ),
            streaming_max_tokens=int(ray_serve_data.get("streaming_max_tokens", 64)),
            agentic_max_tokens=int(ray_serve_data.get("agentic_max_tokens", 192)),
        ),
        replicates=int(data["replicates"]),
    )

    _validate_mix(cfg.mix)
    _validate_workers(cfg.workers)
    _validate_capacity(cfg)
    _validate_execution(cfg)
    return cfg
