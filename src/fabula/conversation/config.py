"""Configuration, credentials, and mode resolution for runtime conversation."""

from __future__ import annotations

import json
import os
from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path

DEFAULT_PROVIDER_ORDER = ("gemini", "xai")
DEFAULT_GEMINI_MODEL = "gemini-2.0-flash"
DEFAULT_XAI_MODEL = "grok-3-mini"
DEFAULT_TOKEN_CAP = 20_000
DEFAULT_TIMEOUT_SECONDS = 20.0
DEFAULT_MAX_OUTPUT_TOKENS = 300


class ConversationMode(StrEnum):
    AUTO = "auto"
    LIVE = "live"
    SCRIPTED = "scripted"


@dataclass(frozen=True)
class ApiKeys:
    gemini: str | None = None
    xai: str | None = None

    def any(self) -> bool:
        return bool(self.gemini or self.xai)

    def for_provider(self, provider: str) -> str | None:
        return {"gemini": self.gemini, "xai": self.xai}.get(provider)


@dataclass(frozen=True)
class ConversationConfig:
    mode: ConversationMode = ConversationMode.AUTO
    provider: str = "gemini"
    provider_order: tuple[str, ...] = DEFAULT_PROVIDER_ORDER
    gemini_model: str = DEFAULT_GEMINI_MODEL
    xai_model: str = DEFAULT_XAI_MODEL
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS
    max_output_tokens: int = DEFAULT_MAX_OUTPUT_TOKENS
    temperature: float = 0.7
    token_cap: int = DEFAULT_TOKEN_CAP
    max_history_messages: int = 12
    leak_filter: bool = False
    gated_reveal: bool = False
    scripted_seed: int = 0
    keys: ApiKeys = field(default_factory=ApiKeys)

    def __post_init__(self) -> None:
        if not isinstance(self.mode, ConversationMode):
            object.__setattr__(self, "mode", ConversationMode(self.mode))
        object.__setattr__(self, "provider_order", tuple(self.provider_order))

    def model_for(self, provider: str) -> str:
        return {"gemini": self.gemini_model, "xai": self.xai_model}.get(provider, self.gemini_model)


def load_api_keys(
    environ: Mapping[str, str] | None = None,
    keys_file: str | Path | None = None,
) -> ApiKeys:
    env = os.environ if environ is None else environ
    gemini = env.get("GEMINI_API_KEY") or env.get("GOOGLE_API_KEY")
    xai = env.get("XAI_API_KEY")

    path = keys_file if keys_file is not None else env.get("FABULA_KEYS_FILE")
    if path:
        try:
            payload = json.loads(Path(path).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(f"cannot read API key file {path}: {exc}") from exc
        if isinstance(payload, dict):
            gemini = gemini or payload.get("gemini")
            xai = xai or payload.get("xai")

    return ApiKeys(
        gemini=str(gemini) if gemini else None,
        xai=str(xai) if xai else None,
    )


def config_from_env(environ: Mapping[str, str] | None = None) -> ConversationConfig:
    env = os.environ if environ is None else environ
    raw_mode = env.get("FABULA_CONVERSATION_MODE", ConversationMode.AUTO.value)
    try:
        mode = ConversationMode(raw_mode)
    except ValueError as exc:
        raise ValueError(
            f"FABULA_CONVERSATION_MODE must be auto, live, or scripted; got {raw_mode!r}"
        ) from exc

    return ConversationConfig(
        mode=mode,
        gemini_model=env.get("FABULA_GEMINI_MODEL", DEFAULT_GEMINI_MODEL),
        xai_model=env.get("FABULA_XAI_MODEL", DEFAULT_XAI_MODEL),
        token_cap=int(env.get("FABULA_TOKEN_CAP", DEFAULT_TOKEN_CAP)),
        leak_filter=env.get("FABULA_LEAK_FILTER", "0") == "1",
        gated_reveal=env.get("FABULA_GATED_REVEAL", "0") == "1",
        keys=load_api_keys(env),
    )
