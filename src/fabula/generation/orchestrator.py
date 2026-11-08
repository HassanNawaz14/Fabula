"""Staged generation orchestrator: settings -> world -> cast -> truth+clues -> NPC files."""

from __future__ import annotations

import random
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Generic, TypeVar

from pydantic import BaseModel, ValidationError

from fabula.generation.bundle_io import publish_bundle
from fabula.generation.errors import (
    FinalBundleError,
    GenerationCancelled,
    GenerationError,
    StageValidationError,
)
from fabula.generation.protocols import (
    CancellationToken,
    ModelRunner,
    ProgressCallback,
    ProgressEvent,
    StageName,
)
from fabula.generation.retries import RetryPolicy, call_with_retries
from fabula.schemas import (
    Bundle,
    CastDocument,
    CastStageInput,
    GenerationSettings,
    MysteryType,
    NpcFiles,
    NpcStageInput,
    NpcStageOutput,
    SettingsMysteryType,
    TruthStageInput,
    TruthStageOutput,
    WorldDocument,
    validate_bundle,
)

NPC_STAGE: StageName = "world+cast+truth+clues+npc_id->identity+memory"
T = TypeVar("T", bound=BaseModel)


@dataclass(frozen=True)
class StageAttemptRecord:
    stage: StageName
    attempts: int
    npc_id: str | None = None


@dataclass(frozen=True)
class GenerationResult:
    bundle_dir: Path
    bundle: Bundle
    resolved_type: MysteryType
    stage_attempts: tuple[StageAttemptRecord, ...]
    elapsed_seconds: float


@dataclass(frozen=True)
class _StageRun(Generic[T]):
    value: T
    attempts: int


class _NeverCancelled:
    def is_cancelled(self) -> bool:
        return False


def resolve_mystery_type(
    mystery_type: SettingsMysteryType | str,
    seed: int,
) -> MysteryType:
    """Resolve the input-only `random` setting to a concrete v1 mystery type."""
    requested = SettingsMysteryType(mystery_type)
    if requested is not SettingsMysteryType.RANDOM:
        return MysteryType(requested.value)
    rng = random.Random(f"fabula-generation-v1:{seed}")
    concrete = list(MysteryType)
    return concrete[rng.randrange(len(concrete))]


def _short(error: BaseException, limit: int = 600) -> str:
    text = str(error).replace("\n", " ")
    return text[:limit]


def _emit(callback: ProgressCallback | None, event: ProgressEvent) -> None:
    if callback is not None:
        callback(event)


def _ensure_not_cancelled(token: CancellationToken, stage: StageName | None) -> None:
    if token.is_cancelled():
        raise GenerationCancelled(stage)


def _run_stage(
    *,
    stage: StageName,
    stage_input: BaseModel,
    output_model: type[T],
    runner: ModelRunner,
    seed: int,
    policy: RetryPolicy,
    cancellation: CancellationToken,
    on_progress: ProgressCallback | None,
    npc_id: str | None = None,
    extra_validate: Callable[[T], None] | None = None,
) -> _StageRun[T]:
    _ensure_not_cancelled(cancellation, stage)
    detail = npc_id or ""
    _emit(on_progress, ProgressEvent("stage_started", stage=stage, detail=detail))

    def attempt(number: int) -> T:
        _ensure_not_cancelled(cancellation, stage)
        raw = runner.generate(stage, stage_input, output_model, seed)
        try:
            parsed = output_model.model_validate_json(raw)
            if extra_validate is not None:
                extra_validate(parsed)
            return parsed
        except ValueError as exc:
            raise StageValidationError(stage, number, _short(exc)) from exc

    outcome = call_with_retries(
        stage,
        policy,
        attempt,
        is_cancelled=cancellation.is_cancelled,
        on_attempt=lambda _stage, number: _emit(
            on_progress,
            ProgressEvent("stage_attempt", stage=stage, attempt=number, detail=detail),
        ),
    )
    _emit(
        on_progress,
        ProgressEvent(
            "stage_succeeded",
            stage=stage,
            attempt=outcome.attempts,
            detail=detail,
        ),
    )
    return _StageRun(value=outcome.value, attempts=outcome.attempts)


def _check_world_matches_settings(
    world: WorldDocument,
    settings: GenerationSettings,
    resolved_type: MysteryType,
) -> None:
    if world.mystery_type.value != resolved_type.value:
        raise ValueError(
            f"world mystery_type {world.mystery_type.value!r} does not match "
            f"the resolved type {resolved_type.value!r}"
        )
    if world.tone != settings.tone:
        raise ValueError(
            f"world tone {world.tone.value!r} does not match requested tone {settings.tone.value!r}"
        )
    if world.difficulty != settings.difficulty:
        raise ValueError(
            f"world difficulty {world.difficulty.value!r} does not match requested "
            f"difficulty {settings.difficulty.value!r}"
        )


def _check_npc_files(output: NpcStageOutput, npc_id: str) -> None:
    if output.identity.id != npc_id:
        raise ValueError(f"identity id {output.identity.id!r} does not match npc {npc_id!r}")
    if output.memory.npc_id != npc_id:
        raise ValueError(f"memory npc_id {output.memory.npc_id!r} does not match npc {npc_id!r}")


def generate_bundle(
    settings: GenerationSettings | dict[str, object],
    runner: ModelRunner,
    output_dir: str | Path,
    *,
    seed: int = 0,
    retry_policy: RetryPolicy | None = None,
    cancellation: CancellationToken | None = None,
    on_progress: ProgressCallback | None = None,
) -> GenerationResult:
    """Run every generation stage, validate, and publish an atomic bundle.

    Every stage is parsed and validated before the next one starts and is
    retried on validation failure per `retry_policy`. The bundle is only
    written after the complete `Bundle` passes both Pydantic cross-reference
    validation and `validate_bundle()`.
    """
    started = time.perf_counter()
    try:
        resolved_settings = GenerationSettings.model_validate(settings)
    except ValidationError as exc:
        raise GenerationError(f"invalid generation settings: {_short(exc)}") from exc

    resolved_type = resolve_mystery_type(resolved_settings.mystery_type, seed)
    stage_settings = GenerationSettings(
        mystery_type=SettingsMysteryType(resolved_type.value),
        tone=resolved_settings.tone,
        difficulty=resolved_settings.difficulty,
    )
    policy = retry_policy if retry_policy is not None else RetryPolicy()
    token = cancellation if cancellation is not None else _NeverCancelled()
    records: list[StageAttemptRecord] = []

    def run(stage: StageName, stage_input: BaseModel, output_model: type[T], **kwargs) -> T:
        run_result = _run_stage(
            stage=stage,
            stage_input=stage_input,
            output_model=output_model,
            runner=runner,
            seed=seed,
            policy=policy,
            cancellation=token,
            on_progress=on_progress,
            **kwargs,
        )
        records.append(
            StageAttemptRecord(
                stage=stage,
                attempts=run_result.attempts,
                npc_id=kwargs.get("npc_id"),
            )
        )
        return run_result.value

    world = run(
        "settings->world",
        stage_settings,
        WorldDocument,
        extra_validate=lambda candidate: _check_world_matches_settings(
            candidate, stage_settings, resolved_type
        ),
    )
    cast = run("world->cast", CastStageInput(world=world), CastDocument)
    truth_output = run(
        "world+cast->truth+clues",
        TruthStageInput(world=world, cast=cast),
        TruthStageOutput,
    )

    npc_files: dict[str, NpcFiles] = {}
    for roster_entry in world.npcs:
        output = run(
            NPC_STAGE,
            NpcStageInput(
                world=world,
                cast=cast,
                truth=truth_output.truth,
                clues=truth_output.clues,
                npc_id=roster_entry.id,
            ),
            NpcStageOutput,
            npc_id=roster_entry.id,
            extra_validate=lambda candidate, expected=roster_entry.id: _check_npc_files(
                candidate, expected
            ),
        )
        npc_files[roster_entry.id] = NpcFiles(
            identity=output.identity,
            memory=output.memory,
        )

    try:
        bundle = Bundle(
            world=world,
            truth=truth_output.truth,
            clues=truth_output.clues,
            npcs=npc_files,
        )
    except ValueError as exc:
        raise FinalBundleError(_short(exc)) from exc

    issues = validate_bundle(bundle)
    if issues:
        detail = "; ".join(f"{issue.code}: {issue.message}" for issue in issues)
        raise FinalBundleError(detail, issues=tuple(issues))

    target = Path(output_dir)
    _ensure_not_cancelled(token, None)
    published = publish_bundle(bundle, target)
    _emit(on_progress, ProgressEvent("bundle_published", detail=str(published)))
    return GenerationResult(
        bundle_dir=published,
        bundle=bundle,
        resolved_type=resolved_type,
        stage_attempts=tuple(records),
        elapsed_seconds=time.perf_counter() - started,
    )
