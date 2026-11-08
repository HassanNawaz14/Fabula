"""Typed generation errors that are safe to surface to the player."""

from __future__ import annotations

from fabula.schemas.validators import Issue


class GenerationError(Exception):
    """Base class for all pre-play generation failures."""


class StageValidationError(GenerationError):
    """A single stage attempt produced invalid or semantically unusable output."""

    def __init__(self, stage: str, attempt: int, detail: str) -> None:
        self.stage = stage
        self.attempt = attempt
        self.detail = detail
        super().__init__(f"stage {stage} attempt {attempt} failed validation: {detail}")


class StageExhaustedError(GenerationError):
    """A stage still failed after every retry was spent."""

    def __init__(
        self,
        stage: str,
        attempts: int,
        last_error: StageValidationError | None = None,
    ) -> None:
        self.stage = stage
        self.attempts = attempts
        self.last_error = last_error
        detail = f": {last_error.detail}" if last_error is not None else ""
        super().__init__(f"stage {stage} failed after {attempts} attempt(s){detail}")


class GenerationCancelled(GenerationError):
    """The caller cancelled generation before the bundle was published."""

    def __init__(self, stage: str | None = None) -> None:
        self.stage = stage
        where = f" during stage {stage}" if stage is not None else ""
        super().__init__(f"generation cancelled{where}")


class BundlePublishError(GenerationError):
    """The validated bundle could not be written to disk atomically."""


class FinalBundleError(GenerationError):
    """Stage outputs parsed individually but do not form a valid bundle."""

    def __init__(self, detail: str, issues: tuple[Issue, ...] = ()) -> None:
        self.issues = issues
        super().__init__(f"generated bundle failed final validation: {detail}")
