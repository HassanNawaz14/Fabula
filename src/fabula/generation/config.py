"""Local generation configuration, environment overrides, and model artifact helpers."""

from __future__ import annotations

import hashlib
import json
import os
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path

from fabula.generation.errors import GenerationSetupError

DEFAULT_MODEL_FILENAME = "Qwen2.5-3B-Instruct.Q4_K_M.gguf"
DEFAULT_MODEL_PATH = Path("models") / DEFAULT_MODEL_FILENAME
DEFAULT_MANIFEST_PATH = Path("models") / "model_manifest.json"
DEFAULT_N_CTX = 4096
DEFAULT_TEMPERATURE = 0.6
DEFAULT_TOP_P = 0.9
DEFAULT_REPEAT_PENALTY = 1.1
DEFAULT_RETRY_ATTEMPTS = 3
DEFAULT_OUTPUT_DIR = Path("bundles/latest")

STAGE_MAX_TOKENS: dict[str, int] = {
    "settings->world": 2400,
    "world->cast": 900,
    "world+cast->truth+clues": 1600,
    "world+cast+truth+clues+npc_id->identity+memory": 900,
}


@dataclass(frozen=True)
class GenerationConfig:
    model_path: Path = DEFAULT_MODEL_PATH
    n_ctx: int = DEFAULT_N_CTX
    n_threads: int | None = None
    temperature: float = DEFAULT_TEMPERATURE
    top_p: float = DEFAULT_TOP_P
    repeat_penalty: float = DEFAULT_REPEAT_PENALTY
    max_tokens: Mapping[str, int] = field(default_factory=lambda: dict(STAGE_MAX_TOKENS))
    retry_attempts: int = DEFAULT_RETRY_ATTEMPTS
    output_dir: Path = DEFAULT_OUTPUT_DIR

    def __post_init__(self) -> None:
        object.__setattr__(self, "model_path", Path(self.model_path))
        object.__setattr__(self, "output_dir", Path(self.output_dir))
        object.__setattr__(self, "max_tokens", dict(self.max_tokens))
        if self.n_ctx < 512:
            raise ValueError("n_ctx must be at least 512")
        if self.n_threads is not None and self.n_threads < 1:
            raise ValueError("n_threads must be positive when set")
        if self.retry_attempts < 1:
            raise ValueError("retry_attempts must be at least 1")
        if not 0.0 < self.temperature <= 2.0:
            raise ValueError("temperature must be in (0, 2]")
        if not 0.0 < self.top_p <= 1.0:
            raise ValueError("top_p must be in (0, 1]")
        if self.repeat_penalty <= 0.0:
            raise ValueError("repeat_penalty must be positive")
        for stage, value in self.max_tokens.items():
            if value < 1:
                raise ValueError(f"max_tokens[{stage!r}] must be positive")


def _env_int(env: Mapping[str, str], name: str, default: int | None) -> int | None:
    raw = env.get(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise GenerationSetupError(f"{name} must be an integer, got {raw!r}") from exc


def resolve_model_path(
    explicit: str | Path | None = None,
    *,
    environ: Mapping[str, str] | None = None,
) -> Path:
    env = os.environ if environ is None else environ
    if explicit is not None:
        return Path(explicit).expanduser()
    from_env = env.get("FABULA_MODEL_PATH")
    if from_env:
        return Path(from_env).expanduser()
    return DEFAULT_MODEL_PATH


def config_from_env(
    environ: Mapping[str, str] | None = None,
    *,
    model_path: str | Path | None = None,
    output_dir: str | Path | None = None,
    retry_attempts: int | None = None,
) -> GenerationConfig:
    env = os.environ if environ is None else environ
    resolved_output = (
        Path(output_dir)
        if output_dir is not None
        else Path(env.get("FABULA_GENERATION_OUT", str(DEFAULT_OUTPUT_DIR)))
    )
    resolved_retries = (
        retry_attempts
        if retry_attempts is not None
        else _env_int(env, "FABULA_GENERATION_RETRIES", DEFAULT_RETRY_ATTEMPTS)
    )
    n_ctx = _env_int(env, "FABULA_MODEL_CTX", DEFAULT_N_CTX)
    return GenerationConfig(
        model_path=resolve_model_path(model_path, environ=env),
        n_ctx=n_ctx if n_ctx is not None else DEFAULT_N_CTX,
        n_threads=_env_int(env, "FABULA_MODEL_THREADS", None),
        retry_attempts=(
            resolved_retries if resolved_retries is not None else DEFAULT_RETRY_ATTEMPTS
        ),
        output_dir=resolved_output,
    )


def sha256_file(path: str | Path, *, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    try:
        with Path(path).open("rb") as handle:
            for chunk in iter(lambda: handle.read(chunk_size), b""):
                digest.update(chunk)
    except OSError as exc:
        raise GenerationSetupError(f"cannot read model file {path}: {exc}") from exc
    return digest.hexdigest()


def verify_model_artifact(
    path: str | Path,
    *,
    expected_sha256: str | None = None,
) -> str:
    model_path = Path(path)
    if not model_path.is_file():
        raise GenerationSetupError(
            f"model artifact not found at {model_path}. "
            "Place the fine-tuned GGUF there or set FABULA_MODEL_PATH; "
            "see docs/local-generation.md."
        )
    computed = sha256_file(model_path)
    if expected_sha256 is not None and computed.lower() != expected_sha256.lower():
        raise GenerationSetupError(
            f"SHA-256 mismatch for {model_path}: expected {expected_sha256.lower()}, "
            f"computed {computed}"
        )
    return computed


def load_model_manifest(
    manifest_path: str | Path | None = None,
) -> dict[str, object] | None:
    path = DEFAULT_MANIFEST_PATH if manifest_path is None else Path(manifest_path)
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise GenerationSetupError(f"cannot read model manifest {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise GenerationSetupError(f"model manifest {path} must contain a JSON object")
    return payload


def manifest_sha256(manifest: Mapping[str, object] | None) -> str | None:
    if manifest is None:
        return None
    value = manifest.get("sha256")
    if value is None:
        return None
    if not isinstance(value, str):
        raise GenerationSetupError("model manifest sha256 must be a string")
    return value
