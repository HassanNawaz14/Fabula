"""Pre-play staged generation with validation, retries and atomic publication."""

from fabula.generation.errors import (
    BundlePublishError,
    FinalBundleError,
    GenerationCancelled,
    GenerationError,
    StageExhaustedError,
    StageValidationError,
)
from fabula.generation.mock_runner import MockModelRunner, cast_from_bundle, skeleton_runner
from fabula.generation.orchestrator import (
    NPC_STAGE,
    GenerationResult,
    StageAttemptRecord,
    generate_bundle,
    resolve_mystery_type,
)
from fabula.generation.protocols import (
    STAGES,
    CancellationFlag,
    CancellationToken,
    ModelRunner,
    ProgressCallback,
    ProgressEvent,
    StageName,
)
from fabula.generation.retries import RetryPolicy

__all__ = [
    "NPC_STAGE",
    "STAGES",
    "BundlePublishError",
    "CancellationFlag",
    "CancellationToken",
    "FinalBundleError",
    "GenerationCancelled",
    "GenerationError",
    "GenerationResult",
    "MockModelRunner",
    "ModelRunner",
    "ProgressCallback",
    "ProgressEvent",
    "RetryPolicy",
    "StageAttemptRecord",
    "StageExhaustedError",
    "StageName",
    "StageValidationError",
    "cast_from_bundle",
    "generate_bundle",
    "resolve_mystery_type",
    "skeleton_runner",
]
