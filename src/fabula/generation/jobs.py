"""Background case-generation jobs shared by the local and Kaggle routes."""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from queue import Empty, Queue
from random import SystemRandom
from threading import Event, Thread

from fabula.case_library import library_root, unique_case_id, validate_case
from fabula.generation.config import (
    GenerationConfig,
    config_from_env,
    resolve_fast_model_path,
)
from fabula.generation.errors import GenerationCancelled
from fabula.generation.orchestrator import (
    NPC_STAGE,
    generate_bundle,
    generate_neurosymbolic_bundle,
)
from fabula.generation.protocols import CancellationFlag, ProgressEvent
from fabula.generation.retries import RetryPolicy
from fabula.schemas import GenerationSettings

STAGE_LABELS = {
    "neural_story_planning": "Sketching the case blueprint…",
    "symbolic_compilation": "Building the town from the blueprint…",
    "settings->world": "Writing the town…",
    "world->cast": "Casting the suspects…",
    "world+cast->truth+clues": "Hiding the truth and planting clues…",
    NPC_STAGE: "Writing an NPC's secrets…",
}


@dataclass(frozen=True)
class JobUpdate:
    """One human-readable progress line from a running job."""

    message: str
    stage: str | None = None
    attempt: int | None = None
    elapsed: float = 0.0


class CaseJob:
    """A case generation task running on a daemon thread."""

    def __init__(self, label: str, estimate: str) -> None:
        self.label = label
        self.estimate = estimate
        self.error: str | None = None
        self.result_path: Path | None = None
        self._updates: Queue[JobUpdate] = Queue()
        self._done = Event()
        self._cancel = CancellationFlag()
        self._thread: Thread | None = None
        self._started_at = time.perf_counter()
        self._result_taken = False

    def start(self) -> None:
        if self._thread is not None:
            return
        self._started_at = time.perf_counter()
        self._thread = Thread(target=self._run, name=f"fabula-{self.label}", daemon=True)
        self._thread.start()

    def _run(self) -> None:
        try:
            self.result_path = self._work(self._emit, self._cancel)
            self._emit("The case is ready.")
        except GenerationCancelled:
            self._emit("Generation stopped.")
        except Exception as exc:  # noqa: BLE001 - surfaced to the player in the UI
            self.error = str(exc) or exc.__class__.__name__
            self._emit(f"Generation failed: {self.error}")
        finally:
            self._done.set()

    def _work(
        self,
        emit: Callable[[str, str | None, int | None], None],
        cancel: CancellationFlag,
    ) -> Path:
        raise NotImplementedError

    def _emit(self, message: str, stage: str | None = None, attempt: int | None = None) -> None:
        self._updates.put(
            JobUpdate(
                message=message,
                stage=stage,
                attempt=attempt,
                elapsed=time.perf_counter() - self._started_at,
            )
        )

    def drain(self) -> list[JobUpdate]:
        updates: list[JobUpdate] = []
        while True:
            try:
                updates.append(self._updates.get_nowait())
            except Empty:
                return updates

    @property
    def is_done(self) -> bool:
        return self._done.is_set()

    @property
    def elapsed(self) -> float:
        return time.perf_counter() - self._started_at

    def cancel(self) -> None:
        self._cancel.cancel()

    def take_result(self) -> Path | None:
        if self._result_taken or not self.is_done or self.error is not None:
            return None
        self._result_taken = True
        return self.result_path


class LocalCaseJob(CaseJob):
    """Generate a case with the fine-tuned model on this machine."""

    def __init__(
        self,
        settings: GenerationSettings,
        *,
        runner: object | None = None,
        config: GenerationConfig | None = None,
        output_dir: str | Path | None = None,
        environ: dict[str, str] | None = None,
    ) -> None:
        super().__init__("local-generation", "usually under a minute")
        self.settings = settings
        self._runner = runner
        self._config = config
        self._output_dir = Path(output_dir) if output_dir is not None else None
        self._environ = environ
        self._seed = SystemRandom().randrange(2**31)

    def _work(
        self,
        emit: Callable[[str, str | None, int | None], None],
        cancel: CancellationFlag,
    ) -> Path:
        config = self._config or config_from_env(self._environ)
        runner = self._runner
        owns_runner = False
        if runner is None:
            fast_model = resolve_fast_model_path(environ=self._environ)
            if fast_model.is_file():
                emit("Loading the local model…", None, None)
                from fabula.generation.local_runner import LocalModelRunner

                runner = LocalModelRunner(fast_model, config)
                owns_runner = True

        target = self._output_dir
        if target is None:
            prefix = f"local_{time.strftime('%Y%m%d_%H%M%S')}"
            target = library_root() / unique_case_id(prefix)
        try:
            if runner is None:
                emit(
                    "No local model file found — using the built-in blueprint library.",
                    None,
                    None,
                )
                generate_neurosymbolic_bundle(
                    self.settings,
                    model_runner=None,
                    output_dir=target,
                    seed=self._seed,
                    cancel_token=cancel,
                    on_progress=lambda event: _emit_progress(emit, event),
                )
            elif hasattr(runner, "generate_blueprint"):
                generate_neurosymbolic_bundle(
                    self.settings,
                    model_runner=runner,
                    output_dir=target,
                    seed=self._seed,
                    cancel_token=cancel,
                    on_progress=lambda event: _emit_progress(emit, event),
                )
            else:
                emit("Generating the mystery. This can take a while…", None, None)
                generate_bundle(
                    self.settings,
                    runner,
                    target,
                    seed=self._seed,
                    retry_policy=RetryPolicy(config.retry_attempts),
                    cancellation=cancel,
                    on_progress=lambda event: _emit_progress(emit, event),
                )
        finally:
            if owns_runner:
                close = getattr(runner, "close", None)
                if close is not None:
                    close()
        emit("Checking the finished case…", None, None)
        validate_case(target)
        return target


class KaggleCaseJob(CaseJob):
    """Send one generation request to the player's Kaggle GPU notebook."""

    def __init__(
        self,
        settings: GenerationSettings,
        *,
        api_factory: Callable[[], object] | None = None,
        environ: dict[str, str] | None = None,
    ) -> None:
        super().__init__("kaggle-generation", "about 6–8 minutes")
        self.settings = settings
        self._api_factory = api_factory
        self._environ = environ
        self._seed = SystemRandom().randrange(2**31)

    def _work(
        self,
        emit: Callable[[str, str | None, int | None], None],
        cancel: CancellationFlag,
    ) -> Path:
        from fabula.generation.kaggle_runner import (
            kaggle_settings_from_env,
            run_kaggle_case,
        )

        settings = kaggle_settings_from_env(self._environ)
        emit("Sending the request to Kaggle…", None, None)
        destination = library_root() / unique_case_id(f"kaggle_{time.strftime('%Y%m%d_%H%M%S')}")
        return run_kaggle_case(
            settings,
            self.settings,
            seed=self._seed,
            destination=destination,
            emit=lambda message: emit(message, None, None),
            cancel=cancel,
            api_factory=self._api_factory,
        )


def _emit_progress(
    emit: Callable[[str, str | None, int | None], None], event: ProgressEvent
) -> None:
    label = STAGE_LABELS.get(event.stage or "", "Working on the case…")
    if event.stage == NPC_STAGE and event.detail:
        label = f"Writing the secrets of {event.detail}…"
    if event.kind == "stage_attempt" and event.attempt > 1:
        emit(f"{label} Retrying (attempt {event.attempt}).", event.stage, event.attempt)
    elif event.kind == "stage_started":
        emit(label, event.stage, None)
    elif event.kind == "stage_succeeded":
        emit(f"{label} Done.", event.stage, event.attempt)


__all__ = ["CaseJob", "JobUpdate", "KaggleCaseJob", "LocalCaseJob", "STAGE_LABELS"]
