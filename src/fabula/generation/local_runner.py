"""Local GGUF model runner with JSON-schema-constrained decoding."""

from __future__ import annotations

import json
import os
from collections.abc import Callable
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from fabula.generation.config import GenerationConfig
from fabula.generation.errors import GenerationSetupError, LocalInferenceError
from fabula.generation.prompts import STOP_TOKENS, build_stage_prompt
from fabula.generation.protocols import LocalBackend, StageName
from fabula.schemas import NpcStageInput

BackendFactory = Callable[[Path, GenerationConfig], LocalBackend]

INSTALL_COMMAND = (
    "python -m pip install llama-cpp-python --prefer-binary "
    "--extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cpu"
)

_GRAMMAR_UNSAFE_KEYWORDS = frozenset(
    {
        "minLength",
        "maxLength",
        "pattern",
        "default",
        "title",
        "description",
        "examples",
    }
)


_SCHEMA_NAME_MAPS = frozenset(
    {"properties", "$defs", "definitions", "patternProperties", "dependentSchemas"}
)


def simplify_json_schema(value: Any, *, key: str | None = None) -> Any:
    """Drop schema keywords that make llama.cpp emit deeply nested GBNF groups.

    ``maxLength`` expands into one nested group per character, and llama.cpp
    builds newer than 0.3.3x reject grammars nested beyond 256 levels.
    """
    if isinstance(value, dict):
        if key in _SCHEMA_NAME_MAPS:
            return {name: simplify_json_schema(item) for name, item in value.items()}
        result: dict[str, Any] = {}
        for name, item in value.items():
            if name in _GRAMMAR_UNSAFE_KEYWORDS:
                continue
            result[name] = simplify_json_schema(item, key=name)
        return result
    if isinstance(value, list):
        return [simplify_json_schema(item) for item in value]
    return value


def pin_npc_identity(schema: dict[str, Any], npc_id: str) -> dict[str, Any]:
    """Force identity and memory ownership fields to the requested NPC id."""
    definitions = schema.get("$defs")
    if not isinstance(definitions, dict):
        return schema
    targets = (("Identity", "id"), ("Memory", "npc_id"), ("Fact", "who"))
    for definition_name, field_name in targets:
        definition = definitions.get(definition_name)
        if not isinstance(definition, dict):
            continue
        properties = definition.get("properties")
        if not isinstance(properties, dict):
            continue
        field = properties.get(field_name)
        if isinstance(field, dict):
            field.clear()
            field.update({"type": "string", "enum": [npc_id]})
    return schema


class LlamaCppBackend:
    """Thin adapter around llama-cpp-python; the wheel is imported lazily."""

    def __init__(self, model_path: Path, config: GenerationConfig) -> None:
        try:
            from llama_cpp import Llama, LlamaGrammar
        except ImportError as exc:
            raise GenerationSetupError(
                "llama-cpp-python is not installed. Install the CPU wheel with:\n"
                f"  {INSTALL_COMMAND}"
            ) from exc

        if not Path(model_path).is_file():
            raise GenerationSetupError(
                f"model artifact not found at {model_path}. "
                "Place the fine-tuned GGUF there or set FABULA_MODEL_PATH; "
                "see docs/local-generation.md."
            )

        threads = config.n_threads or max(1, (os.cpu_count() or 4) - 1)
        self._n_ctx = config.n_ctx
        self._grammar_type = LlamaGrammar
        self._grammar_cache: dict[str, Any] = {}
        self.last_prompt_tokens: int | None = None
        self.last_output_tokens: int | None = None
        try:
            self._llm = Llama(
                model_path=str(model_path),
                n_ctx=config.n_ctx,
                n_threads=threads,
                n_gpu_layers=config.n_gpu_layers,
                verbose=False,
                seed=0,
            )
        except Exception as exc:
            raise GenerationSetupError(f"failed to load GGUF model {model_path}: {exc}") from exc

    def _grammar_for(self, grammar: str) -> Any:
        cached = self._grammar_cache.get(grammar)
        if cached is not None:
            return cached
        try:
            compiled = self._grammar_type.from_json_schema(grammar, verbose=False)
        except Exception as exc:
            raise LocalInferenceError(
                f"cannot compile a JSON-schema grammar for this stage: {exc}"
            ) from exc
        self._grammar_cache[grammar] = compiled
        return compiled

    def generate(
        self,
        prompt: str,
        *,
        grammar: str | None,
        max_tokens: int,
        temperature: float,
        top_p: float,
        repeat_penalty: float,
        seed: int,
        stop: tuple[str, ...],
    ) -> str:
        grammar_obj = self._grammar_for(grammar) if grammar is not None else None

        prompt_tokens: int | None
        try:
            prompt_tokens = len(self._llm.tokenize(prompt.encode("utf-8"), add_bos=True))
        except Exception:
            prompt_tokens = None
        if prompt_tokens is not None and prompt_tokens >= self._n_ctx:
            raise LocalInferenceError(
                f"prompt uses {prompt_tokens} tokens but n_ctx is {self._n_ctx}; "
                "raise FABULA_MODEL_CTX or shorten the prompt"
            )

        try:
            response = self._llm(
                prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p,
                repeat_penalty=repeat_penalty,
                seed=seed,
                stop=list(stop),
                echo=False,
                grammar=grammar_obj,
            )
            text = response["choices"][0]["text"]
        except Exception as exc:
            raise LocalInferenceError(f"local model generation failed: {exc}") from exc

        self.last_prompt_tokens = prompt_tokens
        try:
            self.last_output_tokens = len(self._llm.tokenize(text.encode("utf-8"), add_bos=False))
        except Exception:
            self.last_output_tokens = None
        return text

    def close(self) -> None:
        close = getattr(self._llm, "close", None)
        if callable(close):
            close()


class LocalModelRunner:
    """Bind the orchestrator's ModelRunner protocol to a local GGUF backend."""

    def __init__(
        self,
        model_path: str | Path,
        config: GenerationConfig,
        *,
        backend_factory: BackendFactory | None = None,
    ) -> None:
        self.model_path = Path(model_path)
        self.config = config
        self._backend_factory = backend_factory or LlamaCppBackend
        self._backend: LocalBackend | None = None
        self._call_counts: dict[StageName, int] = {}
        self.last_stats: dict[str, int | None] = {}

    def _ensure_backend(self) -> LocalBackend:
        if self._backend is None:
            if not self.model_path.is_file():
                raise GenerationSetupError(
                    f"model artifact not found at {self.model_path}. "
                    "Place the fine-tuned GGUF there or set FABULA_MODEL_PATH; "
                    "see docs/local-generation.md."
                )
            self._backend = self._backend_factory(self.model_path, self.config)
        return self._backend

    def generate(
        self,
        stage: StageName,
        stage_input: BaseModel,
        output_model: type[BaseModel],
        seed: int,
    ) -> str:
        backend = self._ensure_backend()
        prompt = build_stage_prompt(stage, stage_input)
        schema = simplify_json_schema(output_model.model_json_schema())
        if isinstance(stage_input, NpcStageInput):
            schema = pin_npc_identity(schema, stage_input.npc_id)
        grammar = json.dumps(schema, ensure_ascii=False)

        call_index = self._call_counts.get(stage, 0)
        self._call_counts[stage] = call_index + 1
        effective_seed = (seed + call_index) & 0x7FFFFFFF

        text = backend.generate(
            prompt,
            grammar=grammar,
            max_tokens=self.config.max_tokens.get(stage, 900),
            temperature=self.config.temperature,
            top_p=self.config.top_p,
            repeat_penalty=self.config.repeat_penalty,
            seed=effective_seed,
            stop=STOP_TOKENS,
        )
        self.last_stats = {
            "prompt_tokens": getattr(backend, "last_prompt_tokens", None),
            "output_tokens": getattr(backend, "last_output_tokens", None),
        }
        return text

    def generate_blueprint(
        self,
        mystery_type: str,
        tone: str,
        difficulty: str,
        seed: int,
    ) -> str:
        """Generate a Compact Blueprint DSL using the fine-tuned edge model (< 10s)."""
        backend = self._ensure_backend()
        prompt = (
            "<|start_header_id|>system<|end_header_id|>\n\n"
            "You are Fabula's Master Mystery Architect. "
            "Generate a valid Compact Blueprint DSL.<|eot_id|>"
            "<|start_header_id|>user<|end_header_id|>\n\n"
            f"GENERATE_CASE: type={mystery_type} tone={tone} "
            f"difficulty={difficulty} seed={seed}<|eot_id|>"
            "<|start_header_id|>assistant<|end_header_id|>\n\n"
        )
        max_tokens = self.config.max_tokens.get("blueprint", 350)
        text = backend.generate(
            prompt,
            grammar=None,
            max_tokens=max_tokens,
            temperature=self.config.temperature,
            top_p=self.config.top_p,
            repeat_penalty=self.config.repeat_penalty,
            seed=seed & 0x7FFFFFFF,
            stop=("<|eot_id|>", "<|end_of_text|>", "\n\n\n"),
        )
        self.last_stats = {
            "prompt_tokens": getattr(backend, "last_prompt_tokens", None),
            "output_tokens": getattr(backend, "last_output_tokens", None),
        }
        cleaned = text.strip()
        if cleaned.startswith("```"):
            lines = cleaned.splitlines()
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            cleaned = "\n".join(lines).strip()
        return cleaned

    def close(self) -> None:
        if self._backend is not None:
            self._backend.close()
            self._backend = None
