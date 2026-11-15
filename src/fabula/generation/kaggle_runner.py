"""Kaggle GPU generation: push a script kernel, wait, and install the result."""

from __future__ import annotations

import contextlib
import json
import os
import shutil
import tempfile
import time
import zipfile
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path

from fabula.case_library import validate_case
from fabula.generation.errors import (
    GenerationCancelled,
    KaggleRunError,
    KaggleSetupError,
)
from fabula.generation.protocols import CancellationFlag
from fabula.schemas import GenerationSettings

DEFAULT_KERNEL_SLUG = "fabula-case-generator"
DEFAULT_MODEL_DATASET_SUFFIX = "fabula-qwen-3b-gguf"
DEFAULT_REPO_URL = "https://github.com/HassanNawaz14/Fabula.git"
DEFAULT_REPO_REF = "main"
DEFAULT_TIMEOUT_SECONDS = 2700
DEFAULT_POLL_SECONDS = 20

_REQUEST_MARKER = "REQUEST = None  # __FABULA_REQUEST__"
_FINISHED = "complete"
_FAILED = {
    "error",
    "failed",
    "cancelled",
    "cancel_acknowledged",
    "cancelacknowledged",
    "cancel_requested",
}


@dataclass(frozen=True)
class KaggleSettings:
    username: str
    kernel_slug: str = DEFAULT_KERNEL_SLUG
    model_dataset: str = ""
    repo_url: str = DEFAULT_REPO_URL
    repo_ref: str = DEFAULT_REPO_REF
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS
    poll_seconds: int = DEFAULT_POLL_SECONDS

    @property
    def kernel_ref(self) -> str:
        return f"{self.username}/{self.kernel_slug}"

    @property
    def kernel_url(self) -> str:
        return f"https://www.kaggle.com/code/{self.kernel_ref}"


KERNEL_SCRIPT = '''"""Fabula case generation on a Kaggle GPU. Generated per request."""

import inspect
import json
import os
import shutil
import subprocess
import sys
import time
import zipfile
from pathlib import Path

REQUEST = None  # __FABULA_REQUEST__


def run(command, **kwargs):
    print("+", " ".join(command), flush=True)
    return subprocess.run(command, check=False, **kwargs)


def cuda_library_directories():
    import glob

    patterns = (
        "/usr/local/cuda*/lib64",
        "/usr/local/lib/python3.*/dist-packages/nvidia/*/lib",
        "/usr/local/lib/python3.*/site-packages/nvidia/*/lib",
    )
    directories = []
    for pattern in patterns:
        for path in sorted(glob.glob(pattern)):
            if path not in directories:
                directories.append(path)
    return directories


gpu = (
    run(["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader"])
    if shutil.which("nvidia-smi")
    else None
)
if gpu is None or gpu.returncode != 0:
    print("no NVIDIA GPU is attached to this Kaggle machine", flush=True)


def preload_cuda_libraries():
    # CUDA wheels link libcudart/libcublas by soname, but Kaggle's Python 3.13
    # image keeps them off the loader path. Loading them globally by absolute
    # path first lets libllama.so resolve its dependencies.
    import ctypes

    loaded = []
    for name in ("libcudart.so.12", "libcublasLt.so.12", "libcublas.so.12"):
        for directory in cuda_library_directories():
            candidate = Path(directory) / name
            if not candidate.is_file():
                continue
            try:
                ctypes.CDLL(str(candidate), mode=ctypes.RTLD_GLOBAL)
                loaded.append(candidate)
            except OSError as exc:
                print("could not preload", candidate, exc, flush=True)
            break
    return loaded


preloaded = preload_cuda_libraries()
names = {path.name for path in preloaded}
if "libcudart.so.12" not in names:
    print("CUDA 12 runtime not found; installing it", flush=True)
    run(
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            "-q",
            "nvidia-cuda-runtime-cu12",
            "nvidia-cublas-cu12",
        ]
    )
    preloaded = preload_cuda_libraries()
    names = {path.name for path in preloaded}
if "libcublas.so.12" not in names:
    print("cuBLAS not found; installing it", flush=True)
    run([sys.executable, "-m", "pip", "install", "-q", "nvidia-cublas-cu12"])
    preloaded = preload_cuda_libraries()
print("cuda libraries", [str(path) for path in preloaded], flush=True)
if preloaded:
    os.environ["LD_LIBRARY_PATH"] = ":".join(
        [str(path.parent) for path in preloaded]
        + [part for part in os.environ.get("LD_LIBRARY_PATH", "").split(":") if part]
    )

repo = Path("/kaggle/working/Fabula")
if repo.exists():
    shutil.rmtree(repo)
clone = ["git", "clone", "--depth", "1"]
if REQUEST["repo_ref"] != "main":
    clone += ["--branch", REQUEST["repo_ref"]]
clone += [REQUEST["repo_url"], str(repo)]
if run(clone).returncode != 0:
    raise SystemExit("could not clone the Fabula repository")

runner_path = repo / "src" / "fabula" / "generation" / "local_runner.py"
source = runner_path.read_text(encoding="utf-8")
if "n_gpu_layers" not in source:
    patched = source.replace("n_threads=threads,", "n_threads=threads, n_gpu_layers=-1,")
    if patched == source:
        raise SystemExit("could not enable GPU offload in the local runner")
    runner_path.write_text(patched, encoding="utf-8")
os.environ["FABULA_MODEL_GPU_LAYERS"] = "-1"
sys.path.insert(0, str(repo / "src"))

wheel_ready = False
for attempt, tag in enumerate(("cu124", "cu123", "cu122", "cu121")):
    command = [
        sys.executable,
        "-m",
        "pip",
        "install",
        "-q",
        "llama-cpp-python",
        "--extra-index-url",
        "https://abetlen.github.io/llama-cpp-python/whl/" + tag,
    ]
    if attempt:
        # Same version from another CUDA tag: swap the wheel without touching deps.
        command += ["--force-reinstall", "--no-deps"]
    if run(command).returncode != 0:
        print("wheel", tag, "did not install", flush=True)
        continue
    for name in [name for name in sys.modules if name.split(".")[0] == "llama_cpp"]:
        del sys.modules[name]
    try:
        import llama_cpp

        if hasattr(llama_cpp, "llama_supports_gpu_offload") and not (
            llama_cpp.llama_supports_gpu_offload()
        ):
            print("wheel", tag, "has no GPU support", flush=True)
            continue
        print("llama_cpp", llama_cpp.__version__, "ready", flush=True)
        wheel_ready = True
        break
    except Exception as exc:
        print("wheel", tag, "failed:", exc, flush=True)
if not wheel_ready:
    raise SystemExit("no CUDA build of llama-cpp-python could be installed")

slug = REQUEST["model_dataset"].split("/", 1)[-1]
models = sorted((Path("/kaggle/input") / slug).rglob("*.gguf"))
if not models:
    models = sorted(Path("/kaggle/input").rglob("*.gguf"))
if not models:
    raise SystemExit("no .gguf model found under /kaggle/input")
model = models[0]
print("model", model, flush=True)

from fabula.generation import local_runner as local_runner_module
from fabula.generation import orchestrator as orchestrator_module
from fabula.generation.config import GenerationConfig
from fabula.generation.local_runner import LocalModelRunner
from fabula.generation.orchestrator import generate_bundle
from fabula.generation.prompts import NPC_STAGE
from fabula.generation.retries import RetryPolicy
from fabula.schemas import GenerationSettings
from fabula.schemas.enums import Disclosure

_GRAMMAR_DROP = frozenset(
    {"minLength", "maxLength", "pattern", "default", "title", "description", "examples"}
)
_SCHEMA_NAME_MAPS = frozenset(
    {"properties", "$defs", "definitions", "patternProperties", "dependentSchemas"}
)


def simplify_for_grammar(value, *, key=None):
    if isinstance(value, dict):
        if key in _SCHEMA_NAME_MAPS:
            return {name: simplify_for_grammar(item) for name, item in value.items()}
        return {
            name: simplify_for_grammar(item, key=name)
            for name, item in value.items()
            if name not in _GRAMMAR_DROP
        }
    if isinstance(value, list):
        return [simplify_for_grammar(item) for item in value]
    return value


# llama.cpp >= 0.3.3x rejects grammars nested deeper than 256 levels, and
# maxLength expands into one nested group per character.
local_runner_module.simplify_json_schema = simplify_for_grammar


def check_world(world):
    location_ids = [location.id for location in world.locations]
    adjacency = {location_id: set() for location_id in location_ids}
    for location in world.locations:
        for neighbor in location.connections:
            if neighbor in adjacency:
                adjacency[location.id].add(neighbor)
                adjacency[neighbor].add(location.id)
    visited = {location_ids[0]}
    frontier = [location_ids[0]]
    while frontier:
        current = frontier.pop()
        for neighbor in adjacency[current]:
            if neighbor not in visited:
                visited.add(neighbor)
                frontier.append(neighbor)
    missing = sorted(set(location_ids) - visited)
    if missing:
        raise ValueError("some locations cannot be reached on foot: " + ", ".join(missing))
    for npc in world.npcs:
        minutes = [entry.at_minute for entry in npc.schedule]
        if len(minutes) != len(set(minutes)):
            raise ValueError("npc " + npc.id + " has two schedule entries at the same minute")


def check_truth(output, world):
    location_ids = {location.id for location in world.locations}
    npc_ids = {npc.id for npc in world.npcs}
    clue_ids = {clue.id for clue in output.clues.clues}
    method_ids = {option.id for option in world.accusation_options.methods}
    motive_ids = {option.id for option in world.accusation_options.motives}
    truth = output.truth
    places = ", ".join(sorted(location_ids))
    if truth.crime.type != world.mystery_type:
        raise ValueError("the crime type must match the world mystery type")
    if truth.crime.location_id not in location_ids:
        raise ValueError("crime location must be one of: " + places)
    if truth.crime.time_window.start > truth.crime.time_window.end:
        raise ValueError("the crime time window starts after it ends")
    for entry in truth.timeline:
        if entry.who not in npc_ids:
            raise ValueError("timeline references unknown npc " + entry.who)
        if entry.where not in location_ids:
            raise ValueError("timeline location " + entry.where + " must be one of: " + places)
    seen_slots = set()
    for entry in truth.timeline:
        slot = (entry.who, entry.t)
        if slot in seen_slots:
            raise ValueError(
                "timeline places " + entry.who + " twice at minute " + str(entry.t)
            )
        seen_slots.add(slot)
    if truth.solution.correct_culprit_id not in npc_ids:
        raise ValueError("the culprit must be one of the townspeople")
    if truth.solution.correct_method_id not in method_ids:
        raise ValueError("the method must be one of the accusation options")
    if truth.solution.correct_motive_id not in motive_ids:
        raise ValueError("the motive must be one of the accusation options")
    for herring in truth.red_herrings:
        if herring.npc not in npc_ids:
            raise ValueError("a red herring references unknown npc " + herring.npc)
    for location in world.locations:
        if not set(location.clue_spots) <= clue_ids:
            raise ValueError("location " + location.id + " lists clue spots that do not exist")
    for clue in output.clues.clues:
        if clue.location_id not in location_ids:
            raise ValueError("clue " + clue.id + " is placed at an unknown location")
        if clue.revealed_by_npc is not None and clue.revealed_by_npc not in npc_ids:
            raise ValueError("clue " + clue.id + " is revealed by an unknown npc")
        if not set(clue.requires) <= clue_ids:
            raise ValueError("clue " + clue.id + " requires a clue that does not exist")


def check_npc(output, world, clues):
    location_ids = {location.id for location in world.locations}
    npc_ids = {npc.id for npc in world.npcs}
    clue_ids = {clue.id for clue in clues.clues}
    memory = output.memory
    if not set(output.identity.relationships) <= npc_ids:
        raise ValueError("relationships must only mention other townspeople")
    fact_ids = {fact.id for fact in memory.facts}
    for fact in memory.facts:
        if fact.where not in location_ids:
            raise ValueError("fact " + fact.id + " happens at unknown location " + fact.where)
        if not set(fact.reveal_requires) <= clue_ids:
            raise ValueError("fact " + fact.id + " requires a clue that does not exist")
        if fact.cover_story_id is not None and (
            memory.cover_story is None or fact.cover_story_id != memory.cover_story.id
        ):
            raise ValueError("fact " + fact.id + " references a cover story that is missing")
    if memory.cover_story is not None:
        if not set(memory.cover_story.supporting_facts) <= fact_ids:
            raise ValueError("the cover story references facts that do not exist")
    elif any(fact.disclosure == Disclosure.LIE for fact in memory.facts):
        raise ValueError("a fact may be lied about, so memory.cover_story must be included")


_original_run_stage = orchestrator_module._run_stage


def run_stage_checked(*args, **kwargs):
    stage = kwargs["stage"]
    base = kwargs.get("extra_validate")
    stage_input = kwargs["stage_input"]

    def extra_validate(candidate):
        if base is not None:
            base(candidate)
        if stage == "settings->world":
            check_world(candidate)
        elif stage == "world+cast->truth+clues":
            check_truth(candidate, stage_input.world)
        elif stage == NPC_STAGE:
            check_npc(candidate, stage_input.world, stage_input.clues)

    kwargs["extra_validate"] = extra_validate
    return _original_run_stage(*args, **kwargs)


# The final Bundle check runs once per bundle and kills every retry. These
# guards move the same cross-document rules into the per-stage retry loop.
orchestrator_module._run_stage = run_stage_checked

output = Path("/kaggle/working/case")
gpu_layers = int(os.environ.get("FABULA_MODEL_GPU_LAYERS", "-1"))
options = {"model_path": model}
if "n_gpu_layers" in inspect.signature(GenerationConfig).parameters:
    options["n_gpu_layers"] = gpu_layers
config = GenerationConfig(**options)
runner = LocalModelRunner(model, config)
print("gpu layers", gpu_layers, flush=True)


def progress(event):
    print(
        "[" + str(event.stage or "bundle") + "]",
        event.kind,
        event.attempt,
        event.detail,
        flush=True,
    )


started = time.time()
result = None
try:
    for bundle_attempt in range(2):
        if bundle_attempt and output.exists():
            shutil.rmtree(output)
        try:
            result = generate_bundle(
                GenerationSettings(**REQUEST["settings"]),
                runner,
                output,
                seed=REQUEST["seed"] + bundle_attempt,
                retry_policy=RetryPolicy(4),
                on_progress=progress,
            )
            break
        except Exception as exc:
            print("bundle attempt", bundle_attempt + 1, "failed:", exc, flush=True)
            if bundle_attempt == 1:
                raise
finally:
    runner.close()

archive_path = Path("/kaggle/working/case.zip")
with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as archive:
    for path in sorted(output.rglob("*")):
        if path.is_file():
            archive.write(path, Path("case") / path.relative_to(output))

summary = {
    "seed": REQUEST["seed"],
    "resolved_type": result.resolved_type.value,
    "seconds": round(time.time() - started, 1),
    "attempts": sum(record.attempts for record in result.stage_attempts),
}
Path("/kaggle/working/result.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
print("KAGGLE_DONE", archive_path, flush=True)
'''


def _config_file(env: Mapping[str, str], home: Path | None = None) -> Path:
    directory = env.get("KAGGLE_CONFIG_DIR", "").strip()
    if directory:
        return Path(directory) / "kaggle.json"
    return (home or Path.home()) / ".kaggle" / "kaggle.json"


def kaggle_credentials(
    environ: Mapping[str, str] | None = None, *, home: Path | None = None
) -> tuple[str, str] | None:
    env = os.environ if environ is None else environ
    username = env.get("KAGGLE_USERNAME", "").strip()
    key = env.get("KAGGLE_KEY", "").strip()
    if username and key:
        return username, key
    config_path = _config_file(env, home)
    try:
        payload = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    stored_user = str(payload.get("username", "")).strip()
    stored_key = str(payload.get("key", "")).strip()
    if stored_user and stored_key:
        return stored_user, stored_key
    return None


def kaggle_credentials_available(
    environ: Mapping[str, str] | None = None, *, home: Path | None = None
) -> bool:
    return kaggle_credentials(environ, home=home) is not None


@contextlib.contextmanager
def _legacy_auth_only():
    """Stop kagglesdk from adding ~/.kaggle/access_token to the request headers.

    The SDK falls back to that file whenever no api_token is passed, even when a
    username and legacy key are configured. A personal token saved as UTF-16 then
    fails inside the HTTP header with ``Invalid header value``. Pointing
    KAGGLE_API_TOKEN at an empty file makes the fallback yield no token, so the
    legacy key is used.
    """
    if kaggle_credentials() is None:
        yield
        return
    handle, path = tempfile.mkstemp(prefix="fabula-no-token-", suffix=".txt")
    os.close(handle)
    previous = os.environ.get("KAGGLE_API_TOKEN")
    os.environ["KAGGLE_API_TOKEN"] = path
    try:
        yield
    finally:
        if previous is None:
            os.environ.pop("KAGGLE_API_TOKEN", None)
        else:
            os.environ["KAGGLE_API_TOKEN"] = previous
        Path(path).unlink(missing_ok=True)


def _int_env(env: Mapping[str, str], name: str, default: int) -> int:
    raw = env.get(name)
    if raw is None or not raw.strip():
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        raise KaggleSetupError(f"{name} must be an integer, got {raw!r}") from exc
    if value < 1:
        raise KaggleSetupError(f"{name} must be positive, got {value}")
    return value


def kaggle_settings_from_env(
    environ: Mapping[str, str] | None = None, *, home: Path | None = None
) -> KaggleSettings:
    env = os.environ if environ is None else environ
    credentials = kaggle_credentials(env, home=home)
    username = env.get("FABULA_KAGGLE_USERNAME", "").strip()
    if not username and credentials is not None:
        username = credentials[0]
    if not username:
        raise KaggleSetupError(
            "Kaggle is not connected. Open kaggle.com → Settings → API → Legacy API "
            "Credentials and click 'Create Legacy API Key'. Save the downloaded kaggle.json "
            "to "
            + str(_config_file(env, home))
            + ", then try again. You can also set KAGGLE_USERNAME and KAGGLE_KEY."
        )
    dataset = env.get("FABULA_KAGGLE_MODEL_DATASET", "").strip()
    if not dataset:
        dataset = f"{username}/{DEFAULT_MODEL_DATASET_SUFFIX}"
    return KaggleSettings(
        username=username,
        kernel_slug=env.get("FABULA_KAGGLE_KERNEL_SLUG", DEFAULT_KERNEL_SLUG).strip()
        or DEFAULT_KERNEL_SLUG,
        model_dataset=dataset,
        repo_url=env.get("FABULA_KAGGLE_REPO_URL", DEFAULT_REPO_URL).strip() or DEFAULT_REPO_URL,
        repo_ref=env.get("FABULA_KAGGLE_REPO_REF", DEFAULT_REPO_REF).strip() or DEFAULT_REPO_REF,
        timeout_seconds=_int_env(env, "FABULA_KAGGLE_TIMEOUT", DEFAULT_TIMEOUT_SECONDS),
        poll_seconds=_int_env(env, "FABULA_KAGGLE_POLL", DEFAULT_POLL_SECONDS),
    )


def _enum_value(value: object) -> str:
    return str(getattr(value, "value", value))


def render_kernel_script(request: Mapping[str, object]) -> str:
    if _REQUEST_MARKER not in KERNEL_SCRIPT:
        raise KaggleRunError("kernel template is missing its request marker")
    return KERNEL_SCRIPT.replace(_REQUEST_MARKER, f"REQUEST = {dict(request)!r}")


def build_kernel_folder(
    folder: str | Path, settings: KaggleSettings, request: Mapping[str, object]
) -> Path:
    target = Path(folder)
    target.mkdir(parents=True, exist_ok=True)
    (target / "generate_case.py").write_text(render_kernel_script(request), encoding="utf-8")
    metadata = {
        "id": settings.kernel_ref,
        "title": "Fabula Case Generator",
        "code_file": "generate_case.py",
        "language": "python",
        "kernel_type": "script",
        "is_private": True,
        "enable_gpu": True,
        "enable_internet": True,
        "dataset_sources": [settings.model_dataset],
        "competition_sources": [],
        "kernel_sources": [],
        "model_sources": [],
    }
    (target / "kernel-metadata.json").write_text(
        json.dumps(metadata, indent=2) + "\n", encoding="utf-8"
    )
    return target


def _load_api(api_factory: Callable[[], object] | None) -> object:
    if api_factory is not None:
        return api_factory()
    try:
        from kaggle.api.kaggle_api_extended import KaggleApi
    except ImportError as exc:
        raise KaggleSetupError(
            'The Kaggle client is not installed. Run: pip install -e ".[kaggle]"'
        ) from exc
    api = KaggleApi()
    legacy = kaggle_credentials()
    if legacy is not None:
        # Kaggle 2.x prefers ~/.kaggle/access_token, which can be stale or saved in
        # UTF-16 and then poisons every request header. An explicit kaggle.json is
        # the credential the player chose, so use it directly.
        api.config_values = {"username": legacy[0], "key": legacy[1]}
        api._authenticated = True
        return api
    try:
        api.authenticate()
    except Exception as exc:  # noqa: BLE001 - re-raised as a setup error
        raise KaggleSetupError(
            f"Kaggle login failed ({exc}). Recreate the key from Settings → API → "
            "Legacy API Credentials, or check KAGGLE_USERNAME/KAGGLE_KEY."
        ) from exc
    return api


def _normalize_status(value: object) -> str:
    """Turn ``KernelWorkerStatus.ERROR`` or ``"ERROR"`` into ``"error"``."""
    name = getattr(value, "name", None)
    text = str(name if isinstance(name, str) else value).strip()
    if "." in text:
        text = text.rsplit(".", 1)[-1]
    return text.lower()


def _status_payload(raw: object) -> tuple[str, str]:
    payload: object = raw
    if isinstance(raw, bytes):
        payload = raw.decode("utf-8", "replace")
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except ValueError:
            return _normalize_status(payload), ""
    if isinstance(payload, dict):
        status = payload.get("status") or payload.get("state") or "queued"
        message = payload.get("failureMessage") or payload.get("failure_message") or ""
        return _normalize_status(status), str(message)
    status = getattr(payload, "status", None)
    if status is None:
        return _normalize_status(payload), ""
    message = getattr(payload, "failure_message", None) or getattr(payload, "failureMessage", None)
    return _normalize_status(status), str(message or "")


def _wait_for_run(
    api: object,
    settings: KaggleSettings,
    emit: Callable[[str], None],
    cancel: CancellationFlag,
    *,
    sleep: Callable[[float], None],
    clock: Callable[[], float],
) -> None:
    deadline = clock() + settings.timeout_seconds
    last_status = ""
    while True:
        if cancel.is_cancelled():
            raise GenerationCancelled()
        if clock() > deadline:
            raise KaggleRunError(
                "Kaggle did not finish in time. Open "
                + settings.kernel_url
                + " to check the run, then try again."
            )
        status, message = _status_payload(api.kernels_status(settings.kernel_ref))
        if status != last_status:
            if status in ("queued", "pending"):
                emit("Kaggle has queued the GPU notebook…")
            elif status in ("running", "inprogress", "in_progress"):
                emit("Kaggle is generating the case on its GPU…")
            last_status = status
        if status == _FINISHED:
            return
        if status in _FAILED:
            detail = f": {message}" if message else ""
            raise KaggleRunError(
                f"Kaggle stopped with status '{status}'{detail}. See {settings.kernel_url}"
            )
        sleep(settings.poll_seconds)


def _find_case_zip(root: Path) -> Path:
    archives = sorted(root.rglob("*.zip"))
    if not archives:
        raise KaggleRunError("Kaggle finished but returned no case archive.")
    preferred = [path for path in archives if path.name == "case.zip"]
    return preferred[0] if preferred else archives[0]


def _extract_zip(archive_path: Path, destination: Path) -> Path:
    destination.mkdir(parents=True, exist_ok=True)
    root = destination.resolve()
    with zipfile.ZipFile(archive_path) as archive:
        for member in archive.infolist():
            target = (destination / member.filename).resolve()
            if not target.is_relative_to(root):
                raise KaggleRunError("Kaggle returned an unsafe archive path.")
        archive.extractall(destination)
    return destination


def _find_case_dir(root: Path) -> Path:
    if (root / "world.json").is_file():
        return root
    worlds = sorted(root.rglob("world.json"))
    if not worlds:
        raise KaggleRunError("Kaggle returned an archive without a case bundle.")
    return worlds[0].parent


def request_payload(
    settings: KaggleSettings, generation_settings: GenerationSettings, seed: int
) -> dict[str, object]:
    return {
        "settings": {
            "mystery_type": _enum_value(generation_settings.mystery_type),
            "tone": _enum_value(generation_settings.tone),
            "difficulty": _enum_value(generation_settings.difficulty),
        },
        "seed": int(seed),
        "repo_url": settings.repo_url,
        "repo_ref": settings.repo_ref,
        "model_dataset": settings.model_dataset,
    }


def run_kaggle_case(
    settings: KaggleSettings,
    generation_settings: GenerationSettings,
    *,
    seed: int,
    destination: Path,
    emit: Callable[[str], None] = lambda _message: None,
    cancel: CancellationFlag | None = None,
    api_factory: Callable[[], object] | None = None,
    sleep: Callable[[float], None] = time.sleep,
    clock: Callable[[], float] = time.perf_counter,
) -> Path:
    """Push a GPU kernel, wait for it, and install the validated bundle."""
    token = cancel if cancel is not None else CancellationFlag()
    api = _load_api(api_factory)
    request = request_payload(settings, generation_settings, seed)
    with _legacy_auth_only(), tempfile.TemporaryDirectory(prefix="fabula-kaggle-") as staging:
        staging_path = Path(staging)
        folder = build_kernel_folder(staging_path / "kernel", settings, request)
        emit("Uploading the generation request to Kaggle…")
        try:
            api.kernels_push(str(folder))
        except Exception as exc:
            detail = str(exc)
            if "401" in detail or "Unauthorized" in detail or "Invalid header" in detail:
                hint = (
                    "Kaggle rejected the credentials. Recreate the legacy key from "
                    "Settings → API → Legacy API Credentials and check the username in "
                    "kaggle.json."
                )
            else:
                hint = (
                    f"Check that the model dataset '{settings.model_dataset}' exists and "
                    "is private to your account."
                )
            raise KaggleRunError(f"Kaggle refused the request: {exc}. {hint}") from exc

        _wait_for_run(api, settings, emit, token, sleep=sleep, clock=clock)

        emit("Downloading the finished case…")
        downloads = staging_path / "downloads"
        downloads.mkdir()
        try:
            api.kernels_output(settings.kernel_ref, path=str(downloads), force=True, quiet=True)
        except Exception as exc:
            raise KaggleRunError(
                f"Could not download the Kaggle result: {exc}. Open {settings.kernel_url}"
            ) from exc

        extracted = _extract_zip(_find_case_zip(downloads), staging_path / "extracted")
        case_dir = _find_case_dir(extracted)
        emit("Validating the finished case…")
        validate_case(case_dir)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(case_dir, destination)
    return destination


__all__ = [
    "KaggleRunError",
    "KaggleSettings",
    "KaggleSetupError",
    "build_kernel_folder",
    "kaggle_credentials",
    "kaggle_credentials_available",
    "kaggle_settings_from_env",
    "render_kernel_script",
    "request_payload",
    "run_kaggle_case",
]
