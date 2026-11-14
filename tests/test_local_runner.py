from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from fabula.generation import NPC_STAGE, STAGE_MAX_TOKENS
from fabula.generation.config import GenerationConfig
from fabula.generation.errors import GenerationSetupError
from fabula.generation.local_runner import (
    LlamaCppBackend,
    LocalModelRunner,
    pin_npc_identity,
    simplify_json_schema,
)
from fabula.generation.mock_runner import cast_from_bundle
from fabula.generation.orchestrator import generate_bundle
from fabula.generation.prompts import STAGE_SYSTEM_PROMPTS, STOP_TOKENS
from fabula.generation.retries import RetryPolicy
from fabula.schemas import (
    CastStageInput,
    GenerationSettings,
    NpcStageInput,
    NpcStageOutput,
    TruthStageOutput,
    WorldDocument,
    validate_bundle,
)
from fabula.training_data import generate_skeleton

SETTINGS = GenerationSettings(mystery_type="theft", tone="cozy", difficulty="easy")


class FakeBackend:
    def __init__(self, bundle) -> None:
        self.bundle = bundle
        self.calls: list[dict[str, object]] = []
        self.closed = False
        self.last_prompt_tokens = 11
        self.last_output_tokens = 22

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
        self.calls.append(
            {
                "prompt": prompt,
                "grammar": grammar,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "top_p": top_p,
                "repeat_penalty": repeat_penalty,
                "seed": seed,
                "stop": stop,
            }
        )
        user_json = prompt.split("<|im_start|>user\n", 1)[1].split("<|im_end|>", 1)[0]
        payload = json.loads(user_json)
        if "mystery_type" in payload:
            return self.bundle.world.model_dump_json()
        if "cast" not in payload:
            return cast_from_bundle(self.bundle).model_dump_json()
        if "npc_id" not in payload:
            return TruthStageOutput(
                truth=self.bundle.truth, clues=self.bundle.clues
            ).model_dump_json()
        npc_id = payload["npc_id"]
        files = self.bundle.npcs[npc_id]
        return NpcStageOutput(identity=files.identity, memory=files.memory).model_dump_json()

    def close(self) -> None:
        self.closed = True


@pytest.fixture
def skeleton_bundle():
    return generate_skeleton("theft", 3, tone="cozy", difficulty="easy")


@pytest.fixture
def fake_model_path(tmp_path: Path) -> Path:
    path = tmp_path / "model.gguf"
    path.write_bytes(b"fake")
    return path


def test_runner_publishes_valid_bundle_with_fake_backend(
    tmp_path: Path, skeleton_bundle, fake_model_path: Path
) -> None:
    created: list[FakeBackend] = []

    def factory(_path: Path, _config: GenerationConfig) -> FakeBackend:
        backend = FakeBackend(skeleton_bundle)
        created.append(backend)
        return backend

    config = GenerationConfig(model_path=fake_model_path)
    runner = LocalModelRunner(fake_model_path, config, backend_factory=factory)
    try:
        result = generate_bundle(
            SETTINGS,
            runner,
            tmp_path / "bundle",
            seed=7,
            retry_policy=RetryPolicy(1),
        )
    finally:
        runner.close()

    assert validate_bundle(result.bundle) == []
    assert len(created) == 1
    assert created[0].closed is True
    assert len(created[0].calls) == 3 + len(skeleton_bundle.world.npcs)

    first = created[0].calls[0]
    assert STAGE_SYSTEM_PROMPTS["settings->world"] in first["prompt"]
    assert first["stop"] == STOP_TOKENS
    assert first["max_tokens"] == STAGE_MAX_TOKENS["settings->world"]
    assert first["grammar"] is not None
    assert first["temperature"] == config.temperature

    npc_seeds = [call["seed"] for call in created[0].calls[3:]]
    assert npc_seeds == list(range(7, 7 + len(skeleton_bundle.world.npcs)))
    assert runner.last_stats == {"prompt_tokens": 11, "output_tokens": 22}


def test_runner_reuses_backend_and_increments_stage_seed(
    skeleton_bundle, fake_model_path: Path
) -> None:
    created: list[FakeBackend] = []

    def factory(_path: Path, _config: GenerationConfig) -> FakeBackend:
        backend = FakeBackend(skeleton_bundle)
        created.append(backend)
        return backend

    cast = cast_from_bundle(skeleton_bundle)
    culprit_id = skeleton_bundle.truth.solution.correct_culprit_id
    stage_input = NpcStageInput(
        world=skeleton_bundle.world,
        cast=cast,
        truth=skeleton_bundle.truth,
        clues=skeleton_bundle.clues,
        npc_id=culprit_id,
    )
    runner = LocalModelRunner(
        fake_model_path,
        GenerationConfig(model_path=fake_model_path),
        backend_factory=factory,
    )
    try:
        runner.generate(NPC_STAGE, stage_input, NpcStageOutput, seed=5)
        runner.generate(NPC_STAGE, stage_input, NpcStageOutput, seed=5)
    finally:
        runner.close()

    assert len(created) == 1
    assert [call["seed"] for call in created[0].calls] == [5, 6]
    assert len(runner._call_counts) == 1


def test_missing_model_raises_before_backend_factory(tmp_path: Path) -> None:
    called = False

    def factory(_path: Path, _config: GenerationConfig) -> FakeBackend:
        nonlocal called
        called = True
        raise AssertionError("factory must not run for a missing model")

    missing = tmp_path / "missing.gguf"
    runner = LocalModelRunner(
        missing,
        GenerationConfig(model_path=missing),
        backend_factory=factory,
    )
    with pytest.raises(GenerationSetupError, match="not found"):
        runner.generate("settings->world", SETTINGS, WorldDocument, seed=0)
    assert called is False


def test_close_without_generating_is_safe(tmp_path: Path) -> None:
    missing = tmp_path / "missing.gguf"
    runner = LocalModelRunner(missing, GenerationConfig(model_path=missing))
    runner.close()
    runner.close()


def test_missing_llama_cpp_raises_setup_error(
    fake_model_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setitem(sys.modules, "llama_cpp", None)
    with pytest.raises(GenerationSetupError, match="llama-cpp-python"):
        LlamaCppBackend(fake_model_path, GenerationConfig(model_path=fake_model_path))


def test_grammar_is_forwarded_for_each_stage(skeleton_bundle, fake_model_path: Path) -> None:
    created: list[FakeBackend] = []

    def factory(_path: Path, _config: GenerationConfig) -> FakeBackend:
        backend = FakeBackend(skeleton_bundle)
        created.append(backend)
        return backend

    runner = LocalModelRunner(
        fake_model_path,
        GenerationConfig(model_path=fake_model_path),
        backend_factory=factory,
    )
    try:
        runner.generate(
            "world->cast", CastStageInput(world=skeleton_bundle.world), WorldDocument, 1
        )
    finally:
        runner.close()

    grammar = created[0].calls[0]["grammar"]
    assert isinstance(grammar, str)
    assert '"properties"' in grammar


def test_grammar_schema_drops_deeply_nested_constraints(
    skeleton_bundle, fake_model_path: Path
) -> None:
    created: list[FakeBackend] = []

    def factory(_path: Path, _config: GenerationConfig) -> FakeBackend:
        backend = FakeBackend(skeleton_bundle)
        created.append(backend)
        return backend

    runner = LocalModelRunner(
        fake_model_path,
        GenerationConfig(model_path=fake_model_path),
        backend_factory=factory,
    )
    try:
        runner.generate(
            "settings->world",
            SETTINGS,
            WorldDocument,
            1,
        )
    finally:
        runner.close()

    grammar = created[0].calls[0]["grammar"]
    assert isinstance(grammar, str)
    assert '"maxLength": 300' in grammar
    assert '"maxLength": 4000' not in grammar
    assert "maxItems" in grammar
    assert "minItems" in grammar
    assert "required" in grammar


def test_npc_grammar_pins_identity_and_memory_ownership(
    skeleton_bundle, fake_model_path: Path
) -> None:
    created: list[FakeBackend] = []

    def factory(_path: Path, _config: GenerationConfig) -> FakeBackend:
        backend = FakeBackend(skeleton_bundle)
        created.append(backend)
        return backend

    culprit_id = skeleton_bundle.truth.solution.correct_culprit_id
    stage_input = NpcStageInput(
        world=skeleton_bundle.world,
        cast=cast_from_bundle(skeleton_bundle),
        truth=skeleton_bundle.truth,
        clues=skeleton_bundle.clues,
        npc_id=culprit_id,
    )
    runner = LocalModelRunner(
        fake_model_path,
        GenerationConfig(model_path=fake_model_path),
        backend_factory=factory,
    )
    try:
        runner.generate(NPC_STAGE, stage_input, NpcStageOutput, seed=5)
    finally:
        runner.close()

    grammar = created[0].calls[0]["grammar"]
    assert isinstance(grammar, str)
    definitions = json.loads(grammar)["$defs"]
    assert definitions["Identity"]["properties"]["id"]["enum"] == [culprit_id]
    assert definitions["Memory"]["properties"]["npc_id"]["enum"] == [culprit_id]
    assert definitions["Fact"]["properties"]["who"]["enum"] == [culprit_id]


def test_pin_npc_identity_is_a_noop_without_definitions() -> None:
    schema = {"type": "object"}
    assert pin_npc_identity(schema, "npc_01") == {"type": "object"}


def test_simplify_json_schema_strips_only_constraints() -> None:
    schema = {
        "type": "object",
        "title": "Example",
        "maxProperties": 4,
        "required": ["name", "title", "description", "tags"],
        "properties": {
            "name": {
                "type": "string",
                "maxLength": 400,
                "description": "A name",
                "enum": ["a", "b"],
            },
            "title": {"type": "string", "maxLength": 80},
            "description": {"type": "string", "description": "The description field"},
            "tags": {
                "type": "array",
                "items": {"type": "string"},
                "minItems": 1,
                "maxItems": 6,
            },
        },
    }
    assert simplify_json_schema(schema) == {
        "type": "object",
        "maxProperties": 4,
        "required": ["name", "title", "description", "tags"],
        "properties": {
            "name": {
                "type": "string",
                "maxLength": 300,
                "enum": ["a", "b"],
            },
            "title": {"type": "string", "maxLength": 80},
            "description": {"type": "string"},
            "tags": {
                "type": "array",
                "items": {"type": "string"},
                "minItems": 1,
                "maxItems": 6,
            },
        },
    }
