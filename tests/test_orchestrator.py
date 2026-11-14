import json
from pathlib import Path

import pytest

from fabula.generation import (
    NPC_STAGE,
    CancellationFlag,
    FinalBundleError,
    GenerationCancelled,
    GenerationError,
    MockModelRunner,
    StageExhaustedError,
    generate_bundle,
    resolve_mystery_type,
)
from fabula.generation.protocols import ProgressEvent, StageName
from fabula.schemas import (
    Bundle,
    CluesDocument,
    FactSource,
    GenerationSettings,
    Identity,
    Memory,
    MysteryType,
    NpcFiles,
    TruthDocument,
    WorldDocument,
    validate_bundle,
)
from fabula.training_data import generate_skeleton

SETTINGS = GenerationSettings(mystery_type="theft", tone="cozy", difficulty="easy")


def load_bundle(root: Path) -> Bundle:
    npcs = {}
    for npc_dir in sorted((root / "npcs").iterdir()):
        identity = Identity.model_validate_json(
            (npc_dir / "identity.json").read_text(encoding="utf-8")
        )
        memory = Memory.model_validate_json((npc_dir / "memory.json").read_text(encoding="utf-8"))
        npcs[npc_dir.name] = NpcFiles(identity=identity, memory=memory)
    return Bundle(
        world=WorldDocument.model_validate_json((root / "world.json").read_text(encoding="utf-8")),
        truth=TruthDocument.model_validate_json((root / "truth.json").read_text(encoding="utf-8")),
        clues=CluesDocument.model_validate_json((root / "clues.json").read_text(encoding="utf-8")),
        npcs=npcs,
    )


def make_runner(fail_stage_times: dict[StageName, int] | None = None) -> MockModelRunner:
    bundle = generate_skeleton(
        MysteryType.THEFT,
        seed=3,
        tone="cozy",
        difficulty="easy",
    )
    return MockModelRunner(bundle, fail_stage_times=fail_stage_times)


def test_success_publishes_valid_bundle_in_stage_order(tmp_path: Path) -> None:
    runner = make_runner()
    output_dir = tmp_path / "bundle"

    result = generate_bundle(SETTINGS, runner, output_dir, seed=7)

    assert result.bundle_dir == output_dir.resolve()
    assert result.resolved_type is MysteryType.THEFT
    assert validate_bundle(result.bundle) == []
    assert (output_dir / "world.json").is_file()
    assert (output_dir / "truth.json").is_file()
    assert (output_dir / "clues.json").is_file()
    assert load_bundle(output_dir) == result.bundle
    assert runner.calls == [
        "settings->world",
        "world->cast",
        "world+cast->truth+clues",
        *([NPC_STAGE] * len(result.bundle.world.npcs)),
    ]
    assert [record.attempts for record in result.stage_attempts] == [1] * (
        3 + len(result.bundle.world.npcs)
    )


def test_retries_only_the_failed_stage(tmp_path: Path) -> None:
    runner = make_runner({"world->cast": 2})

    result = generate_bundle(SETTINGS, runner, tmp_path / "bundle")

    attempts = {record.stage: record.attempts for record in result.stage_attempts[:3]}
    assert attempts == {
        "settings->world": 1,
        "world->cast": 3,
        "world+cast->truth+clues": 1,
    }
    assert (tmp_path / "bundle" / "world.json").is_file()


def test_exhausted_stage_leaves_no_bundle_or_temp_files(tmp_path: Path) -> None:
    runner = make_runner({"world+cast->truth+clues": 3})
    output_dir = tmp_path / "bundle"

    with pytest.raises(StageExhaustedError) as excinfo:
        generate_bundle(SETTINGS, runner, output_dir)

    assert excinfo.value.stage == "world+cast->truth+clues"
    assert excinfo.value.attempts == 3
    assert not output_dir.exists()
    assert list(tmp_path.glob(".bundle.tmp-*")) == []
    assert runner.calls.count("world+cast->truth+clues") == 3


def test_cancellation_stops_before_next_stage(tmp_path: Path) -> None:
    runner = make_runner()
    flag = CancellationFlag()

    def on_progress(event: ProgressEvent) -> None:
        if event.kind == "stage_succeeded" and event.stage == "settings->world":
            flag.cancel()

    with pytest.raises(GenerationCancelled) as excinfo:
        generate_bundle(
            SETTINGS, runner, tmp_path / "bundle", cancellation=flag, on_progress=on_progress
        )

    assert excinfo.value.stage == "world->cast"
    assert runner.calls == ["settings->world"]
    assert not (tmp_path / "bundle").exists()
    assert list(tmp_path.glob(".bundle.tmp-*")) == []


def test_failed_generation_preserves_existing_bundle(tmp_path: Path) -> None:
    output_dir = tmp_path / "bundle"
    output_dir.mkdir()
    sentinel = output_dir / "previous.txt"
    sentinel.write_text("keep me", encoding="utf-8")

    runner = make_runner({"settings->world": 3})
    with pytest.raises(StageExhaustedError):
        generate_bundle(SETTINGS, runner, output_dir)

    assert sentinel.read_text(encoding="utf-8") == "keep me"
    assert not (output_dir / "world.json").exists()


def test_success_replaces_existing_bundle_atomically(tmp_path: Path) -> None:
    output_dir = tmp_path / "bundle"
    output_dir.mkdir()
    (output_dir / "previous.txt").write_text("old", encoding="utf-8")

    generate_bundle(SETTINGS, make_runner(), output_dir)

    assert not (output_dir / "previous.txt").exists()
    assert (output_dir / "world.json").is_file()
    assert list(tmp_path.glob(".bundle.bak-*")) == []


def test_random_type_is_resolved_deterministically(tmp_path: Path) -> None:
    settings = GenerationSettings(mystery_type="random", tone="cozy", difficulty="easy")
    resolved = resolve_mystery_type(settings.mystery_type, seed=123)
    assert resolve_mystery_type("random", 123) is resolved
    bundle = generate_skeleton(resolved, seed=5, tone="cozy", difficulty="easy")

    result = generate_bundle(settings, MockModelRunner(bundle), tmp_path / "bundle", seed=123)

    assert result.resolved_type is resolved
    assert result.bundle.world.mystery_type is resolved


class _MismatchedTruthRunner(MockModelRunner):
    def generate(self, stage, stage_input, output_model, seed):  # type: ignore[no-untyped-def]
        raw = super().generate(stage, stage_input, output_model, seed)
        if stage == "world+cast->truth+clues":
            payload = json.loads(raw)
            payload["truth"]["crime"]["type"] = MysteryType.MURDER.value
            return json.dumps(payload)
        return raw


class _NoEvidenceRunner(MockModelRunner):
    def generate(self, stage, stage_input, output_model, seed):  # type: ignore[no-untyped-def]
        raw = super().generate(stage, stage_input, output_model, seed)
        if stage == "world+cast->truth+clues":
            payload = json.loads(raw)
            for clue in payload["clues"]["clues"]:
                clue["implies"] = []
            return json.dumps(payload)
        return raw


class _MissingAccountRunner(MockModelRunner):
    def generate(self, stage, stage_input, output_model, seed):  # type: ignore[no-untyped-def]
        raw = super().generate(stage, stage_input, output_model, seed)
        if stage == "world+cast->truth+clues":
            payload = json.loads(raw)
            for clue in payload["clues"]["clues"]:
                clue["implies"] = []
            return json.dumps(payload)
        if stage == NPC_STAGE:
            culprit_id = self.bundle.truth.solution.correct_culprit_id
            if stage_input.npc_id == culprit_id:
                payload = json.loads(raw)
                payload["memory"]["facts"] = [
                    fact
                    for fact in payload["memory"]["facts"]
                    if not (fact["source"] == FactSource.DID and fact["secret"])
                ]
                return json.dumps(payload)
        return raw


def test_missing_culprit_account_is_repaired_before_publish(tmp_path: Path) -> None:
    runner = _MissingAccountRunner(
        generate_skeleton(MysteryType.THEFT, seed=3, tone="cozy", difficulty="easy")
    )

    result = generate_bundle(SETTINGS, runner, tmp_path / "bundle")

    assert validate_bundle(result.bundle) == []
    culprit_id = result.bundle.truth.solution.correct_culprit_id
    assert any(
        fact.source == FactSource.DID and fact.secret
        for fact in result.bundle.npcs[culprit_id].memory.facts
    )


def test_missing_culprit_evidence_is_repaired_before_publish(tmp_path: Path) -> None:
    runner = _NoEvidenceRunner(
        generate_skeleton(MysteryType.THEFT, seed=3, tone="cozy", difficulty="easy")
    )

    result = generate_bundle(SETTINGS, runner, tmp_path / "bundle")

    assert validate_bundle(result.bundle) == []
    culprit_id = result.bundle.truth.solution.correct_culprit_id
    account_ids = {
        fact.id
        for fact in result.bundle.npcs[culprit_id].memory.facts
        if fact.source == FactSource.DID and fact.secret
    }
    assert account_ids
    assert any(set(clue.implies) & account_ids for clue in result.bundle.clues.clues)


def test_cross_stage_inconsistency_fails_final_validation(tmp_path: Path) -> None:
    output_dir = tmp_path / "bundle"
    runner = _MismatchedTruthRunner(
        generate_skeleton(MysteryType.THEFT, seed=3, tone="cozy", difficulty="easy")
    )

    with pytest.raises(FinalBundleError):
        generate_bundle(SETTINGS, runner, output_dir)

    assert not output_dir.exists()


def test_invalid_settings_raise_generation_error(tmp_path: Path) -> None:
    with pytest.raises(GenerationError):
        generate_bundle({"mystery_type": "theft"}, make_runner(), tmp_path / "bundle")


def test_world_must_match_requested_tone(tmp_path: Path) -> None:
    runner = MockModelRunner(
        generate_skeleton(MysteryType.THEFT, seed=3, tone="dark", difficulty="easy")
    )

    with pytest.raises(StageExhaustedError) as excinfo:
        generate_bundle(SETTINGS, runner, tmp_path / "bundle")

    assert excinfo.value.stage == "settings->world"
