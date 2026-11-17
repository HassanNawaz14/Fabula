"""Fabula generation evaluation harness.

Lives OUTSIDE the Fabula repository and never edits it. It imports Fabula's own
pipeline functions unchanged and wraps the model runner only to *observe* it
(time each model call, count tokens, save the raw model text).

Subcommands
-----------
  env       Capture hardware/software/model-hash/git info -> results/environment.json
  run       Run one pre-registered plan step (see PLAN below)
  analyze   Build runs.csv, summary statistics, automated checks, charts, case sheets
  plan      Print the pre-registered plan
  selftest  Exercise the harness with a FAKE model (checks the plumbing, produces no results)

Typical use (PowerShell, from the folder that contains this file):
  python fabula_eval.py env     --repo ..\\Fabula
  python fabula_eval.py run     --repo ..\\Fabula --step pilot_fast
  python fabula_eval.py analyze --steps pilot_fast,pilot_staged

Timing definitions (identical for both routes)
-----------------------------------------------
  e2e_s      Fabula's own GenerationResult.elapsed_seconds. Timer starts at the top of
             generate_bundle()/generate_neurosymbolic_bundle() and stops after the bundle
             is atomically published. Includes model load (if cold), every model call,
             all Python parsing/validation/compilation/repair, and the publish step.
             Excludes interpreter start-up, imports, and model unload.
  load_s     Time to load the GGUF into memory (only non-zero on the first run in a process).
  infer_s    Sum of time spent inside model calls (prompt prefill + decoding; for the
             staged route this also includes llama.cpp grammar compilation and retries).
  python_s   e2e_s - load_s - infer_s: everything Fabula does in Python around the model.
  tok_per_s  output tokens / infer_s ("effective" throughput, prefill included).
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import platform
import random
import statistics
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
RESULTS = HERE / "results"
RUNS_FILE = RESULTS / "runs.jsonl"
ENV_FILE = RESULTS / "environment.json"

# Fixed generation inputs for every run in the study (only the seed varies).
FIXED_SETTINGS = {"mystery_type": "theft", "tone": "cozy", "difficulty": "normal"}

# ----------------------------------------------------------------------------
# Pre-registered plan. Each step is a list of process groups. A group is ONE
# fresh Python process: an optional warm-up run (recorded, excluded from stats)
# followed by the listed seeds in order. The first non-warm-up run in a group
# without a warm-up is "cold" (includes model load); later runs are "warm".
# ----------------------------------------------------------------------------
MIN = 60
PLAN: dict[str, dict[str, Any]] = {
    "pilot_fast": {
        "route": "fast",
        "purpose": "Check the 1B route really uses the GGUF and that every field is recorded.",
        "groups": [
            {"warmup": None, "seeds": [901]},  # one cold process
            {"warmup": 900, "seeds": [901, 902, 903]},  # warm runs
        ],
        "timeout_s": 20 * MIN,
    },
    "pilot_staged": {
        "route": "staged",
        "purpose": "Check the 3B route loads, see how long stage 1 takes, predict a full run.",
        "groups": [{"warmup": None, "seeds": [901]}],
        "timeout_s": 15 * MIN,
    },
    "e1_fast_cold": {
        "route": "fast",
        "purpose": "Cold-start latency: a fresh process per run, model load included.",
        "groups": [{"warmup": None, "seeds": [s]} for s in range(1, 6)],
        "timeout_s": 15 * MIN,
    },
    "e1_fast_warm": {
        "route": "fast",
        "purpose": "Main 1B benchmark: 30 seeds, model already loaded.",
        "groups": [{"warmup": 1000, "seeds": list(range(1, 31))}],
        "timeout_s": 90 * MIN,
    },
    "e3_fast_repeat": {
        "route": "fast",
        "purpose": "Repeatability: seeds 1-3 three more times each (interleaved).",
        "groups": [{"warmup": 1000, "seeds": [1, 2, 3, 1, 2, 3, 1, 2, 3]}],
        "timeout_s": 45 * MIN,
    },
    "e2_staged": {
        "route": "staged",
        "purpose": "3B case studies on seeds shared with the 1B benchmark.",
        "groups": [{"warmup": None, "seeds": [s]} for s in (1, 2, 3)],
        "timeout_s": 40 * MIN,
    },
    "e3_staged_repeat": {
        "route": "staged",
        "purpose": "Only if time permits: repeat 3B seed 1.",
        "groups": [{"warmup": None, "seeds": [1]}],
        "timeout_s": 40 * MIN,
    },
}


# ============================================================================ utils
def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def append_jsonl(path: Path, record: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")
        fh.flush()
        os.fsync(fh.fileno())


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            out.append(json.loads(line))
    return out


def ensure_fabula_importable(repo: Path) -> None:
    try:
        import fabula  # noqa: F401
    except ImportError:
        sys.path.insert(0, str(repo / "src"))


def default_models(repo: Path) -> dict[str, Path]:
    return {
        "fast": repo / "models" / "Llama-3.2-1B-Instruct.Q4_K_M.gguf",
        "staged": repo / "models" / "Qwen2.5-3B-Instruct.Q4_K_M.gguf",
    }


class RamSampler:
    """Samples this process's resident memory (RSS / Windows working set)."""

    def __init__(self, interval: float = 0.25) -> None:
        try:
            import psutil

            self._proc = psutil.Process()
        except Exception:
            self._proc = None
        self.interval = interval
        self.peak = 0
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    @property
    def available(self) -> bool:
        return self._proc is not None

    def current_mb(self) -> float | None:
        if self._proc is None:
            return None
        return self._proc.memory_info().rss / (1024 * 1024)

    def start(self) -> None:
        if self._proc is None:
            return
        self.peak = self._proc.memory_info().rss
        self._stop.clear()

        def loop() -> None:
            while not self._stop.is_set():
                try:
                    self.peak = max(self.peak, self._proc.memory_info().rss)
                except Exception:
                    pass
                self._stop.wait(self.interval)

        self._thread = threading.Thread(target=loop, daemon=True)
        self._thread.start()

    def stop_mb(self) -> float | None:
        if self._proc is None:
            return None
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=2)
        self.peak = max(self.peak, self._proc.memory_info().rss)
        return self.peak / (1024 * 1024)


# ============================================================================ env
def capture_environment(repo: Path, models: dict[str, Path]) -> dict[str, Any]:
    ensure_fabula_importable(repo)
    from importlib import metadata

    def version(pkg: str) -> str | None:
        try:
            return metadata.version(pkg)
        except Exception:
            return None

    def git(*args: str) -> str | None:
        try:
            return subprocess.run(
                ["git", "-C", str(repo), *args], capture_output=True, text=True, check=True
            ).stdout.strip()
        except Exception:
            return None

    env: dict[str, Any] = {
        "captured_at": now_iso(),
        "git_commit": git("rev-parse", "HEAD"),
        "git_dirty": bool(git("status", "--porcelain")),
        "git_dirty_detail": git("status", "--porcelain"),
        "python": sys.version,
        "platform": platform.platform(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "cpu_logical": os.cpu_count(),
        "packages": {
            p: version(p) for p in ("fabula", "llama-cpp-python", "llama_cpp_python", "pydantic", "psutil")
        },
        "fixed_settings": FIXED_SETTINGS,
        "fabula_env_vars": {k: v for k, v in os.environ.items() if k.startswith("FABULA_")},
    }
    try:
        import psutil

        env["cpu_physical"] = psutil.cpu_count(logical=False)
        env["ram_total_gb"] = round(psutil.virtual_memory().total / 1024**3, 2)
        env["on_battery"] = (
            None if psutil.sensors_battery() is None else not psutil.sensors_battery().power_plugged
        )
    except Exception:
        env["cpu_physical"] = env["ram_total_gb"] = env["on_battery"] = None

    from fabula.generation import config_from_env, load_model_manifest

    try:
        # Fabula resolves its default manifest path relative to the current folder,
        # so pass the repository's manifest explicitly.
        manifest = load_model_manifest(repo / "models" / "model_manifest.json")
    except Exception:
        manifest = None
    expected = {
        "staged": (manifest or {}).get("sha256"),
        "fast": ((manifest or {}).get("fast_model") or {}).get("sha256"),
    }
    env["models"] = {}
    for route, path in models.items():
        entry: dict[str, Any] = {"path": str(path), "exists": path.is_file()}
        if path.is_file():
            print(f"hashing {path.name} ...", flush=True)
            digest = sha256_file(path)
            entry.update(
                size_bytes=path.stat().st_size,
                sha256=digest,
                manifest_sha256=expected[route],
                manifest_match=(expected[route] or "").lower() == digest,
            )
        cfg = config_from_env(model_path=path)
        entry["config"] = {
            "n_ctx": cfg.n_ctx,
            "n_threads": cfg.n_threads or max(1, (os.cpu_count() or 4) - 1),
            "n_gpu_layers": cfg.n_gpu_layers,
            "temperature": cfg.temperature,
            "top_p": cfg.top_p,
            "repeat_penalty": cfg.repeat_penalty,
            "max_tokens": dict(cfg.max_tokens),
            "retry_attempts": cfg.retry_attempts,
        }
        env["models"][route] = entry
    return env


# ============================================================================ child
class ObservedRunner:
    """Wraps Fabula's LocalModelRunner to time each call; never changes its output."""

    def __init__(self, inner: Any, run_dir: Path, events: Path) -> None:
        self.inner = inner
        self.run_dir = run_dir
        self.events = events
        self.reset("init")

    def reset(self, run_id: str) -> None:
        self.run_id = run_id
        self.load_s = 0.0
        self.infer_s = 0.0
        self.calls = 0
        self.prompt_tokens = 0
        self.output_tokens = 0
        self.tokens_known = True
        self.raw_texts: list[str] = []

    def _maybe_load(self) -> None:
        if getattr(self.inner, "_backend", "absent") is None:
            t = time.perf_counter()
            self.inner._ensure_backend()
            self.load_s += time.perf_counter() - t
            append_jsonl(self.events, {"event": "model_loaded", "run_id": self.run_id,
                                       "load_s": round(self.load_s, 3), "at": now_iso()})

    def _record(self, stage: str, npc_id: str | None, elapsed: float, text: str | None, error: str | None) -> None:
        self.calls += 1
        stats = getattr(self.inner, "last_stats", {}) or {}
        pt, ot = stats.get("prompt_tokens"), stats.get("output_tokens")
        if error is None:
            if pt is None or ot is None:
                self.tokens_known = False
            self.prompt_tokens += pt or 0
            self.output_tokens += ot or 0
        raw_file = None
        if text is not None:
            raw_file = self.run_dir / f"call{self.calls:02d}_{stage.replace('->', '_to_').replace('+', '_')}{'_' + npc_id if npc_id else ''}.txt"
            raw_file.write_text(text, encoding="utf-8")
            self.raw_texts.append(text)
        append_jsonl(
            self.events,
            {
                "event": "model_call",
                "run_id": self.run_id,
                "call_no": self.calls,
                "stage": stage,
                "npc_id": npc_id,
                "infer_s": round(elapsed, 4),
                "prompt_tokens": pt if error is None else None,
                "output_tokens": ot if error is None else None,
                "raw_file": str(raw_file) if raw_file else None,
                "error": error,
                "at": now_iso(),
            },
        )

    # staged route (ModelRunner protocol)
    def generate(self, stage, stage_input, output_model, seed):  # noqa: ANN001
        self._maybe_load()
        t = time.perf_counter()
        try:
            text = self.inner.generate(stage, stage_input, output_model, seed)
        except Exception as exc:
            elapsed = time.perf_counter() - t
            self.infer_s += elapsed
            self._record(stage, getattr(stage_input, "npc_id", None), elapsed, None, f"{type(exc).__name__}: {exc}")
            raise
        elapsed = time.perf_counter() - t
        self.infer_s += elapsed
        self._record(stage, getattr(stage_input, "npc_id", None), elapsed, text, None)
        return text

    # fast route
    def generate_blueprint(self, mystery_type, tone, difficulty, seed):  # noqa: ANN001
        self._maybe_load()
        t = time.perf_counter()
        try:
            text = self.inner.generate_blueprint(mystery_type=mystery_type, tone=tone, difficulty=difficulty, seed=seed)
        except Exception as exc:
            elapsed = time.perf_counter() - t
            self.infer_s += elapsed
            self._record("blueprint", None, elapsed, None, f"{type(exc).__name__}: {exc}")
            raise
        elapsed = time.perf_counter() - t
        self.infer_s += elapsed
        self._record("blueprint", None, elapsed, text, None)
        return text

    def close(self) -> None:
        close = getattr(self.inner, "close", None)
        if callable(close):
            close()


class _FakeBackend:
    """Self-test only: returns a built-in blueprint after a short sleep."""

    def __init__(self, *_: Any) -> None:
        time.sleep(0.2)
        self.last_prompt_tokens = 60
        self.last_output_tokens = 150

    def generate(self, prompt: str, **kw: Any) -> str:
        from fabula.generation.synthetic_blueprint import generate_synthetic_blueprint_sample

        time.sleep(0.05)
        return generate_synthetic_blueprint_sample(kw["seed"])["messages"][2]["content"]

    def close(self) -> None:
        pass


def child_main(spec_path: Path) -> int:
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    repo = Path(spec["repo"])
    ensure_fabula_importable(repo)
    t_import = time.perf_counter()
    from fabula.generation import (
        GenerationError,
        LocalModelRunner,
        MockModelRunner,
        RetryPolicy,
        config_from_env,
        generate_bundle,
        resolve_mystery_type,
    )
    from fabula.generation.orchestrator import generate_neurosymbolic_bundle
    from fabula.schemas import GenerationSettings
    from fabula.training_data import generate_skeleton

    import_s = time.perf_counter() - t_import
    route = spec["route"]
    model_path = Path(spec["model_path"])
    group_dir = Path(spec["group_dir"])
    events = group_dir / "events.jsonl"
    config = config_from_env(model_path=model_path)
    settings = GenerationSettings(**FIXED_SETTINGS)
    env = json.loads(ENV_FILE.read_text(encoding="utf-8")) if ENV_FILE.is_file() else {}
    model_info = (env.get("models") or {}).get(route, {})

    fake = spec.get("fake", False)
    if fake and route == "staged":
        inner = None  # MockModelRunner is built per seed below
    elif fake:
        inner = LocalModelRunner(model_path, config, backend_factory=_FakeBackend)
    else:
        inner = LocalModelRunner(model_path, config)
    observed = ObservedRunner(inner, group_dir, events) if inner is not None else None
    ram = RamSampler()
    rss_process_start = ram.current_mb()

    runs = [("warmup", spec["warmup"])] if spec.get("warmup") is not None else []
    runs += [("main", s) for s in spec["seeds"]]
    exit_code = 0
    for index, (kind, seed) in enumerate(runs):
        run_id = f"{spec['step']}__g{spec['group_index']}__{index:02d}_s{seed}" + ("_warmup" if kind == "warmup" else "")
        run_dir = group_dir / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        if fake and route == "staged":
            resolved = resolve_mystery_type(settings.mystery_type, seed)
            observed = ObservedRunner(
                MockModelRunner(generate_skeleton(resolved, seed, tone=settings.tone, difficulty=settings.difficulty)),
                group_dir,
                events,
            )
        assert observed is not None
        # First run in a fresh process pays the model load -> "cold"; later runs -> "warm".
        condition = "warmup" if kind == "warmup" else ("cold" if index == 0 else "warm")
        observed.reset(run_id)
        observed.run_dir = run_dir
        append_jsonl(events, {"event": "run_started", "run_id": run_id, "seed": seed, "at": now_iso()})
        rss_before = ram.current_mb()
        ram.start()
        record: dict[str, Any] = {
            "run_id": run_id,
            "step": spec["step"],
            "route": route,
            "condition": condition,
            "group_index": spec["group_index"],
            "index_in_process": index,
            "seed": seed,
            **FIXED_SETTINGS,
            "fake_model": fake,
            "model_path": str(model_path),
            "model_sha256": model_info.get("sha256"),
            "git_commit": env.get("git_commit"),
            "config": model_info.get("config"),
            "process_import_s": round(import_s, 3),
            "started_at": now_iso(),
        }
        t0 = time.perf_counter()
        try:
            if route == "fast":
                result = generate_neurosymbolic_bundle(
                    settings, model_runner=observed, output_dir=run_dir / "bundle", seed=seed
                )
            else:
                result = generate_bundle(
                    settings,
                    observed,
                    run_dir / "bundle",
                    seed=seed,
                    retry_policy=RetryPolicy(config.retry_attempts),
                )
            wall = time.perf_counter() - t0
            e2e = result.elapsed_seconds
            record.update(
                status="ok",
                error=None,
                e2e_s=round(e2e, 4),
                bundle_dir=str(result.bundle_dir),
                blueprint_source=result.blueprint_source,
                fallback_reason=result.fallback_reason,
                stage_attempts=sum(r.attempts for r in result.stage_attempts),
                retries=sum(r.attempts - 1 for r in result.stage_attempts) if route == "staged" else None,
            )
            if route == "fast" and result.blueprint_source != "model":
                record["status"] = "fallback"
        except GenerationError as exc:
            wall = time.perf_counter() - t0
            e2e = None
            record.update(status="failed", error=f"{type(exc).__name__}: {exc}"[:2000], e2e_s=None, bundle_dir=None)
        except Exception as exc:  # unexpected: still recorded, never dropped
            wall = time.perf_counter() - t0
            e2e = None
            record.update(status="error", error=f"{type(exc).__name__}: {exc}"[:2000], e2e_s=None, bundle_dir=None)
        rss_peak = ram.stop_mb()
        infer = observed.infer_s
        load = observed.load_s
        record.update(
            harness_wall_s=round(wall, 4),
            load_s=round(load, 4),
            infer_s=round(infer, 4),
            python_s=round(e2e - load - infer, 4) if e2e is not None else None,
            model_calls=observed.calls,
            prompt_tokens=observed.prompt_tokens if observed.tokens_known else None,
            output_tokens=observed.output_tokens if observed.tokens_known else None,
            tok_per_s=(
                round(observed.output_tokens / infer, 3)
                if observed.tokens_known and infer > 0 and observed.output_tokens
                else None
            ),
            rss_process_start_mb=round(rss_process_start, 1) if rss_process_start else None,
            rss_before_mb=round(rss_before, 1) if rss_before else None,
            rss_peak_mb=round(rss_peak, 1) if rss_peak else None,
            raw_dir=str(run_dir),
            finished_at=now_iso(),
        )
        append_jsonl(RUNS_FILE, record)
        append_jsonl(events, {"event": "run_finished", "run_id": run_id, "status": record["status"], "at": now_iso()})
        shown = record.get("e2e_s")
        print(
            f"[{run_id}] {record['status']:8s} cond={condition:6s} e2e={shown}s load={record['load_s']}s "
            f"infer={record['infer_s']}s tok/s={record['tok_per_s']} src={record.get('blueprint_source')}",
            flush=True,
        )
        if record["status"] == "fallback" and spec.get("stop_on_fallback", True):
            print(f"STOP: fallback used ({record.get('fallback_reason')}). Investigate before continuing.", flush=True)
            exit_code = 4
            break
    if observed is not None:
        observed.close()
    return exit_code


# ============================================================================ parent
def run_step(args: argparse.Namespace) -> int:
    repo = Path(args.repo).resolve()
    models = default_models(repo)
    if args.fast_model:
        models["fast"] = Path(args.fast_model).resolve()
    if args.staged_model:
        models["staged"] = Path(args.staged_model).resolve()
    step = PLAN[args.step]
    route = step["route"]
    if not ENV_FILE.is_file():
        print("No environment.json yet; capturing it first.")
        RESULTS.mkdir(parents=True, exist_ok=True)
        ENV_FILE.write_text(json.dumps(capture_environment(repo, models), indent=2), encoding="utf-8")
    if not args.fake and not models[route].is_file():
        print(f"Model not found: {models[route]} -- refusing to run (it would silently use the fallback).")
        return 2
    done = {r["run_id"] for r in read_jsonl(RUNS_FILE)}
    print(f"== {args.step}: {step['purpose']}")
    timeout = args.timeout_min * 60 if args.timeout_min else step["timeout_s"]
    for gi, group in enumerate(step["groups"]):
        group_dir = RESULTS / "raw" / args.step / f"g{gi}"
        if group_dir.exists() and any(rid.startswith(f"{args.step}__g{gi}__") for rid in done):
            print(f"group g{gi} already has records; skipping (delete results/raw/{args.step}/g{gi} to redo).")
            continue
        group_dir.mkdir(parents=True, exist_ok=True)
        spec = {
            "step": args.step,
            "group_index": gi,
            "route": route,
            "repo": str(repo),
            "model_path": str(models[route]),
            "warmup": group["warmup"],
            "seeds": group["seeds"],
            "group_dir": str(group_dir),
            "fake": args.fake,
            "stop_on_fallback": not args.allow_fallback,
        }
        spec_path = group_dir / "spec.json"
        spec_path.write_text(json.dumps(spec, indent=2), encoding="utf-8")
        log_path = group_dir / "child.log"
        print(f"-- group g{gi}: warmup={group['warmup']} seeds={group['seeds']} timeout={timeout / 60:.0f} min")
        t0 = time.perf_counter()
        with open(log_path, "w", encoding="utf-8") as log:
            proc = subprocess.Popen(
                [sys.executable, str(Path(__file__).resolve()), "_child", str(spec_path)],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                env={**os.environ, "PYTHONUNBUFFERED": "1"},
            )
            reader = threading.Thread(
                target=lambda: [(log.write(line), log.flush(), print("   " + line, end="", flush=True)) for line in proc.stdout],  # type: ignore[union-attr]
                daemon=True,
            )
            reader.start()
            try:
                code = proc.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()
                code = "timeout"
            reader.join(timeout=5)
        wall = time.perf_counter() - t0
        if code == "timeout":
            _record_timeout(args.step, gi, route, group_dir, timeout, wall)
            print(f"   TIMEOUT after {timeout / 60:.0f} min; partial calls kept in {group_dir / 'events.jsonl'}")
        elif code == 4:
            print("   Stopped because the synthetic fallback was used. Not continuing this step.")
            return 4
        elif code != 0:
            print(f"   child exited with code {code}; see {log_path}")
    return 0


def _record_timeout(step: str, gi: int, route: str, group_dir: Path, timeout: float, wall: float) -> None:
    events = read_jsonl(group_dir / "events.jsonl")
    started = [e for e in events if e["event"] == "run_started"]
    finished = {e["run_id"] for e in events if e["event"] == "run_finished"}
    pending = [e for e in started if e["run_id"] not in finished]
    if not pending:
        return
    run = pending[-1]
    calls = [e for e in events if e["event"] == "model_call" and e["run_id"] == run["run_id"]]
    env = json.loads(ENV_FILE.read_text(encoding="utf-8")) if ENV_FILE.is_file() else {}
    append_jsonl(
        RUNS_FILE,
        {
            "run_id": run["run_id"],
            "step": step,
            "route": route,
            "condition": "timeout",
            "group_index": gi,
            "seed": run["seed"],
            **FIXED_SETTINGS,
            "model_sha256": ((env.get("models") or {}).get(route) or {}).get("sha256"),
            "git_commit": env.get("git_commit"),
            "status": "timeout",
            "error": f"killed after {timeout / 60:.0f} min limit",
            "e2e_s": None,
            "timeout_limit_s": timeout,
            "group_wall_s": round(wall, 1),
            "partial_model_calls_completed": sum(1 for c in calls if not c.get("error")),
            "partial_infer_s": round(sum(c["infer_s"] for c in calls), 2),
            "partial_output_tokens": sum(c.get("output_tokens") or 0 for c in calls),
            "partial_last_stage": calls[-1]["stage"] if calls else None,
            "partial_load_s": next((e["load_s"] for e in events if e["event"] == "model_loaded" and e["run_id"] == run["run_id"]), None),
            "raw_dir": str(group_dir / run["run_id"]),
            "finished_at": now_iso(),
        },
    )


# ============================================================================ analysis
DSL_MARKERS = ("[CASE:", "PREMISE:", "CAST:", "CRIME:")


def dsl_coverage(raw: str) -> dict[str, Any]:
    """How much of the blueprint did the model actually write?

    parse_dsl() never rejects text: missing parts silently become defaults, so even
    'hello world' compiles. We therefore count what is literally present.
    """
    from fabula.generation.dsl import parse_dsl

    lines = [line.strip() for line in raw.splitlines()]
    present = {m.strip("[:").lower(): any(line.startswith(m) for line in lines) for m in DSL_MARKERS}
    bp = parse_dsl(raw)
    cov = {
        "dsl_chars": len(raw),
        "dsl_has_header": present["case"],
        "dsl_has_premise": present["premise"],
        "dsl_has_cast": present["cast"],
        "dsl_has_crime": present["crime"],
        "dsl_suspects": len(bp.cast.suspects),
        "dsl_timeline_lines": len(bp.timeline),
        "dsl_clue_lines": len(bp.clues),
        "dsl_knowledge_lines": len(bp.knowledge),
    }
    cov["dsl_substantive"] = bool(
        all(present.values()) and cov["dsl_timeline_lines"] >= 1 and cov["dsl_clue_lines"] >= 1
    )
    return cov


def load_bundle_dir(path: Path):
    from fabula.schemas import (
        Bundle,
        CluesDocument,
        Identity,
        Memory,
        NpcFiles,
        TruthDocument,
        WorldDocument,
    )

    def read(p: Path) -> str:
        return p.read_text(encoding="utf-8")

    npcs = {}
    for d in sorted((path / "npcs").iterdir()):
        npcs[d.name] = NpcFiles(
            identity=Identity.model_validate_json(read(d / "identity.json")),
            memory=Memory.model_validate_json(read(d / "memory.json")),
        )
    return Bundle(
        world=WorldDocument.model_validate_json(read(path / "world.json")),
        truth=TruthDocument.model_validate_json(read(path / "truth.json")),
        clues=CluesDocument.model_validate_json(read(path / "clues.json")),
        npcs=npcs,
    )


def bundle_fingerprint(path: Path) -> str:
    h = hashlib.sha256()
    for f in sorted(path.rglob("*.json")):
        h.update(str(f.relative_to(path)).replace("\\", "/").encode())
        h.update(f.read_bytes())
    return h.hexdigest()[:16]


def bundle_checks(route: str, path: Path) -> dict[str, Any]:
    from fabula.generation.compiler import BlueprintCompiler
    from fabula.schemas import FactSource, validate_bundle

    out: dict[str, Any] = {"fingerprint": bundle_fingerprint(path)}
    try:
        bundle = load_bundle_dir(path)
        out["schema_valid"] = True
    except Exception as exc:
        out.update(schema_valid=False, schema_error=str(exc)[:500])
        return out
    issues = validate_bundle(bundle)
    out["validator_issue_count"] = len(issues)
    out["validator_issue_codes"] = ";".join(sorted({str(i.code) for i in issues}))
    culprit = bundle.truth.solution.correct_culprit_id
    facts = {f.id: (npc, f) for npc, files in bundle.npcs.items() for f in files.memory.facts}
    implied = {fid for c in bundle.clues.clues for fid in c.implies if fid in facts}
    did_owners = {
        facts[fid][0] for fid in implied if facts[fid][1].source is FactSource.DID and facts[fid][1].secret
    }
    # DESCRIPTIVE ONLY, not a solvability verdict: how many people own a secret 'did'
    # fact that some clue points to. The 1B compiler requires this to be exactly the
    # culprit; the staged training data deliberately points red-herring clues at an
    # innocent's own secret, so ">1" is by design there and is not an error.
    out["evidence_points_only_at_culprit"] = did_owners == {culprit}
    out["npcs_with_clue_linked_secret_deed"] = len(did_owners)
    out["culprit_has_clue_linked_secret_deed"] = culprit in did_owners
    # Fabula's own compiler proof also requires '<npc>_alibi' facts, a naming
    # convention only the blueprint compiler uses, so it is not applied to staged bundles.
    out["compiler_solvability_proof"] = (
        BlueprintCompiler.verify_solvability(None, bundle) if route == "fast" else None  # type: ignore[arg-type]
    )
    out["staged_culprit_account_repaired"] = (
        any(f.id.startswith("account_") for f in bundle.npcs[culprit].memory.facts) if route == "staged" else None
    )
    out.update(
        n_locations=len(bundle.world.locations),
        n_npcs=len(bundle.npcs),
        n_clues=len(bundle.clues.clues),
        n_timeline=len(bundle.truth.timeline),
        n_red_herrings=len(bundle.truth.red_herrings),
        n_facts=len(facts),
        n_lie_facts=sum(1 for _, f in facts.values() if f.disclosure.value == "lie"),
        title=bundle.world.title,
        culprit_name=next(
            (n.display_name for n in bundle.world.npcs if n.id == culprit), culprit
        ),
    )
    return out


def describe(values: list[float]) -> dict[str, Any]:
    vals = [v for v in values if v is not None]
    n = len(vals)
    if n == 0:
        return {"n": 0}
    return {
        "n": n,
        "mean": round(statistics.fmean(vals), 3),
        "median": round(statistics.median(vals), 3),
        "sd": round(statistics.stdev(vals), 3) if n >= 2 else None,
        "min": round(min(vals), 3),
        "max": round(max(vals), 3),
    }


METRICS = ("e2e_s", "load_s", "infer_s", "python_s", "output_tokens", "tok_per_s", "rss_peak_mb")


def analyze(args: argparse.Namespace) -> int:
    repo = Path(args.repo).resolve()
    ensure_fabula_importable(repo)
    records = read_jsonl(RUNS_FILE)
    if args.steps:
        wanted = set(args.steps.split(","))
        records = [r for r in records if r["step"] in wanted]
    if not records:
        print("No run records found.")
        return 1
    out_dir = RESULTS / "analysis"
    out_dir.mkdir(parents=True, exist_ok=True)

    rows = []
    for r in records:
        row = {k: v for k, v in r.items() if k != "config"}
        if r.get("bundle_dir") and Path(r["bundle_dir"]).is_dir():
            row.update(bundle_checks(r["route"], Path(r["bundle_dir"])))
        if r["route"] == "fast" and r.get("raw_dir"):
            raws = sorted(Path(r["raw_dir"]).glob("call*_blueprint.txt"))
            if raws:
                text = raws[-1].read_text(encoding="utf-8")
                row.update(dsl_coverage(text))
                row["dsl_hash"] = hashlib.sha256(text.encode()).hexdigest()[:16]
        rows.append(row)

    keys: list[str] = []
    for row in rows:
        keys += [k for k in row if k not in keys]
    with open(out_dir / "runs.csv", "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)

    lines = [f"# Analysis summary ({now_iso()})", ""]
    env = json.loads(ENV_FILE.read_text(encoding="utf-8")) if ENV_FILE.is_file() else {}
    lines.append(f"git commit `{env.get('git_commit')}` (dirty={env.get('git_dirty')}); "
                 f"CPU {env.get('processor') or env.get('machine')}, {env.get('cpu_physical')} physical / "
                 f"{env.get('cpu_logical')} logical cores, RAM {env.get('ram_total_gb')} GB, on battery={env.get('on_battery')}")
    for route, m in (env.get("models") or {}).items():
        lines.append(f"- {route}: `{Path(m['path']).name}` sha256 match={m.get('manifest_match')} "
                     f"threads={m['config']['n_threads']} temp={m['config']['temperature']}")
    if any(r.get("fake_model") for r in rows):
        lines += ["", "**WARNING: contains FAKE-model self-test runs. These are not results.**"]

    lines += ["", "## Every run (failures included)", "",
              "| run | cond | status | e2e s | load s | infer s | python s | out tok | tok/s | peak RAM MB | source | substantive DSL | schema ok | validator issues | clue reaches culprit deed | compiler proof (1B only) |",
              "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        lines.append("| " + " | ".join(str(r.get(k, "")) if r.get(k) is not None else "–" for k in (
            "run_id", "condition", "status", "e2e_s", "load_s", "infer_s", "python_s", "output_tokens",
            "tok_per_s", "rss_peak_mb", "blueprint_source", "dsl_substantive", "schema_valid",
            "validator_issue_count", "culprit_has_clue_linked_secret_deed", "compiler_solvability_proof")) + " |")

    lines += ["", "## Outcome counts per step (nothing excluded)", ""]
    for step in sorted({r["step"] for r in rows}):
        sub = [r for r in rows if r["step"] == step]
        counts: dict[str, int] = {}
        for r in sub:
            counts[r["status"]] = counts.get(r["status"], 0) + 1
        lines.append(f"- **{step}**: {len(sub)} records -> {counts}")

    lines += ["", "## Descriptive statistics (successful, non-warm-up runs)", "",
              "SD is shown only for n ≥ 2; treat any statistic with n < 5 as a case study, not an estimate.", ""]
    stats_out = {}
    groups: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
    for r in rows:
        if r["status"] in ("ok",) and r["condition"] != "warmup":
            groups.setdefault((r["route"], r["condition"], r["step"]), []).append(r)
    lines += ["| route | condition | step | metric | n | mean | median | sd | min | max |",
              "|---|---|---|---|---|---|---|---|---|---|"]
    for key, sub in sorted(groups.items()):
        for metric in METRICS:
            d = describe([s.get(metric) for s in sub])
            stats_out[f"{key[0]}|{key[1]}|{key[2]}|{metric}"] = d
            if d["n"]:
                lines.append(f"| {key[0]} | {key[1]} | {key[2]} | {metric} | " + " | ".join(
                    "–" if d.get(k) is None else str(d[k]) for k in ("n", "mean", "median", "sd", "min", "max")) + " |")
    (out_dir / "summary_stats.json").write_text(json.dumps(stats_out, indent=2), encoding="utf-8")

    fast_main = [r for r in rows if r["route"] == "fast" and r["condition"] != "warmup"]
    if fast_main:
        model_src = sum(1 for r in fast_main if r.get("blueprint_source") == "model")
        subst = sum(1 for r in fast_main if r.get("dsl_substantive"))
        lines += ["", "## 1B blueprint provenance", "",
                  f"- `Blueprint: model`: {model_src}/{len(fast_main)} runs",
                  f"- model blueprint contained header + premise + cast + crime + ≥1 timeline + ≥1 clue line: {subst}/{len(fast_main)}",
                  "- (A run can say `model` while most content is compiler defaults; the second line checks that.)"]

    lines += ["", "## Repeatability (same seed, same settings)", "",
              "| route | seed | runs | distinct bundles | distinct raw model texts | e2e range s |", "|---|---|---|---|---|---|"]
    by_seed: dict[tuple[str, int], list[dict[str, Any]]] = {}
    for r in rows:
        if r["status"] in ("ok", "fallback") and r["condition"] != "warmup" and r.get("fingerprint"):
            by_seed.setdefault((r["route"], r["seed"]), []).append(r)
    for (route, seed), sub in sorted(by_seed.items()):
        if len(sub) < 2:
            continue
        e2e = [s["e2e_s"] for s in sub if s.get("e2e_s") is not None]
        lines.append(f"| {route} | {seed} | {len(sub)} | {len({s['fingerprint'] for s in sub})} | "
                     f"{len({s.get('dsl_hash') for s in sub}) if route == 'fast' else 'see raw/'} | "
                     f"{(round(min(e2e), 2), round(max(e2e), 2)) if e2e else '–'} |")

    warm = [r for r in rows if r["step"] == "e1_fast_warm" and r["status"] == "ok" and r.get("fingerprint")]
    if warm:
        lines += ["", "## Does the seed change the mystery? (e1_fast_warm)", "",
                  f"- {len({r['fingerprint'] for r in warm})} distinct bundles from {len(warm)} seeds",
                  f"- {len({r.get('title') for r in warm})} distinct titles, {len({r.get('culprit_name') for r in warm})} distinct culprit names"]

    (out_dir / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    make_charts(rows, out_dir)
    if args.case_sheets:
        make_case_sheets(rows, out_dir)
    print("\n".join(lines))
    print(f"\nWrote {out_dir / 'runs.csv'}, {out_dir / 'summary.md'}, charts in {out_dir}")
    return 0


def make_charts(rows: list[dict[str, Any]], out_dir: Path) -> None:
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception:
        print("matplotlib not installed; skipping charts")
        return
    ok = [r for r in rows if r["status"] == "ok" and r["condition"] != "warmup" and r.get("e2e_s") is not None]
    if not ok:
        return
    # 1. Latency breakdown per run (stacked: load / inference / python)
    ok_sorted = sorted(ok, key=lambda r: (r["route"], r["condition"], r["seed"]))
    labels = [f"{r['route'][0].upper()}-{r['condition'][0]}-s{r['seed']}" for r in ok_sorted]
    load = [r.get("load_s") or 0 for r in ok_sorted]
    infer = [r.get("infer_s") or 0 for r in ok_sorted]
    py = [max(r.get("python_s") or 0, 0) for r in ok_sorted]
    fig, ax = plt.subplots(figsize=(max(6, len(ok_sorted) * 0.35), 4))
    ax.bar(labels, load, label="model load", color="#9aa5b1")
    ax.bar(labels, infer, bottom=load, label="model inference", color="#3b6ea5")
    ax.bar(labels, py, bottom=[a + b for a, b in zip(load, infer)], label="Python (parse/validate/compile/publish)", color="#e0a43a")
    ax.set_ylabel("seconds")
    ax.set_title("End-to-end generation time per run (F=fast 1B, S=staged 3B; c=cold, w=warm)")
    ax.tick_params(axis="x", rotation=90, labelsize=7)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(out_dir / "latency_breakdown.png", dpi=150)
    plt.close(fig)
    # 2. Distribution by route x condition (points, so small n stays visible)
    cats = sorted({(r["route"], r["condition"]) for r in ok})
    fig, ax = plt.subplots(figsize=(6, 4))
    for i, cat in enumerate(cats):
        ys = [r["e2e_s"] for r in ok if (r["route"], r["condition"]) == cat]
        xs = [i + (random.Random(j).random() - 0.5) * 0.25 for j in range(len(ys))]
        ax.scatter(xs, ys, s=18, alpha=0.8)
        ax.hlines(statistics.median(ys), i - 0.3, i + 0.3, color="black")
    ax.set_xticks(range(len(cats)), [f"{a}\n{b}\n(n={sum(1 for r in ok if (r['route'], r['condition']) == (a, b))})" for a, b in cats])
    ax.set_ylabel("end-to-end seconds")
    ax.set_yscale("log")
    ax.set_title("End-to-end latency (each dot = one run, line = median, log scale)")
    fig.tight_layout()
    fig.savefig(out_dir / "latency_by_condition.png", dpi=150)
    plt.close(fig)
    # 3. Staged per-call time
    staged_runs = {r["run_id"] for r in rows if r["route"] == "staged"}
    calls = []
    for f in (RESULTS / "raw").rglob("events.jsonl"):
        calls += [e for e in read_jsonl(f) if e["event"] == "model_call" and e["run_id"] in staged_runs]
    if calls:
        fig, ax = plt.subplots(figsize=(8, 4))
        for run_id in sorted({c["run_id"] for c in calls}):
            sub = [c for c in calls if c["run_id"] == run_id]
            ax.plot(range(1, len(sub) + 1), [c["infer_s"] / 60 for c in sub], marker="o", label=run_id.split("__")[-1])
        ax.set_xlabel("model call number (1=world, 2=cast, 3=truth+clues, 4+=one per NPC; retries add calls)")
        ax.set_ylabel("minutes")
        ax.set_title("Staged 3B: time per model call")
        ax.legend(fontsize=7)
        fig.tight_layout()
        fig.savefig(out_dir / "staged_per_call.png", dpi=150)
        plt.close(fig)


def make_case_sheets(rows: list[dict[str, Any]], out_dir: Path) -> None:
    """Neutral, route-blind case sheets for rubric scoring on matched seeds."""
    staged_ok = {r["seed"]: r for r in rows if r["route"] == "staged" and r["status"] == "ok" and r.get("schema_valid")}
    fast_ok: dict[int, dict[str, Any]] = {}
    for r in rows:
        if r["route"] == "fast" and r["status"] == "ok" and r.get("schema_valid") and r["condition"] != "warmup":
            fast_ok.setdefault(r["seed"], r)
    matched = sorted(set(staged_ok) & set(fast_ok))
    chosen = [staged_ok[s] for s in matched] + [fast_ok[s] for s in matched]
    selection = f"matched seeds {matched}: every staged bundle that succeeded + the first successful 1B bundle with the same seed"
    if not chosen:
        chosen = [fast_ok[s] for s in sorted(fast_ok)[:3]]
        selection = "no staged bundle succeeded; 1B seeds 1-3 only (no matched comparison possible)"
    rng = random.Random(20261117)
    codes = rng.sample(range(100, 1000), len(chosen))
    order = list(zip(codes, chosen))
    rng.shuffle(order)
    sheet_dir = out_dir / "case_sheets"
    sheet_dir.mkdir(exist_ok=True)
    key = {"selection": selection, "cases": {}}
    score_rows = []
    for code, r in order:
        bundle = load_bundle_dir(Path(r["bundle_dir"]))
        (sheet_dir / f"case_{code}.md").write_text(render_case(bundle, code), encoding="utf-8")
        key["cases"][f"case_{code}"] = {"run_id": r["run_id"], "route": r["route"], "seed": r["seed"]}
        for dim in RUBRIC_DIMENSIONS:
            score_rows.append({"case": f"case_{code}", "dimension": dim, "score_1to5": "", "evidence": ""})
    (out_dir / "case_key_DO_NOT_OPEN_UNTIL_SCORED.json").write_text(json.dumps(key, indent=2), encoding="utf-8")
    score_file = out_dir / "rubric_scores.csv"
    if not score_file.exists():
        with open(score_file, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=["case", "dimension", "score_1to5", "evidence"])
            w.writeheader()
            w.writerows(score_rows)
    print(f"Case sheets: {sheet_dir} ({len(order)} cases; {selection})")


RUBRIC_DIMENSIONS = (
    "logical_consistency",
    "mystery_coherence",
    "clue_relevance",
    "npc_identity_memory_consistency",
    "solvability_human",
    "narrative_quality",
)


def render_case(bundle: Any, code: int) -> str:
    names = {n.id: n.display_name for n in bundle.world.npcs}
    locs = {loc.id: loc.name for loc in bundle.world.locations}
    opts = {o.id: o.text for o in bundle.world.accusation_options.methods + bundle.world.accusation_options.motives}
    facts = {f.id: f for files in bundle.npcs.values() for f in files.memory.facts}

    def n(x: str) -> str:
        return names.get(x, locs.get(x, x))

    t = bundle.truth
    out = [f"# Case {code}", "", f"**Title:** {bundle.world.title}  ", f"**Town:** {bundle.world.town_name}", "",
           f"> {bundle.world.intro_text}", "", "## Places"]
    out += [f"- {loc.name} ({loc.type.value}) — {loc.description} Connects to: {', '.join(n(c) for c in loc.connections)}"
            for loc in bundle.world.locations]
    out += ["", "## Hidden truth", f"- Crime: {t.crime.type.value} of **{t.crime.target}** at {n(t.crime.location_id)}, minutes {t.crime.time_window.start}–{t.crime.time_window.end}",
            f"- Culprit: **{n(t.solution.correct_culprit_id)}**", f"- Method: {opts.get(t.solution.correct_method_id, t.solution.correct_method_id)}",
            f"- Motive: {opts.get(t.solution.correct_motive_id, t.solution.correct_motive_id)}", f"- How: {t.solution.how}", f"- Why: {t.solution.why}",
            "", "### Timeline"]
    out += [f"- minute {e.t}: {n(e.who)} at {n(e.where)} — {e.what}" for e in sorted(t.timeline, key=lambda e: e.t)]
    out += ["", "### Red herrings"] + ([f"- {n(h.npc)}: {h.secret}" for h in t.red_herrings] or ["- none"])
    out += ["", "## Clues"]
    for c in bundle.clues.clues:
        linked = "; ".join(f"{n(facts[i].who)}: \"{facts[i].what}\"" for i in c.implies if i in facts)
        who = f" (revealed by {n(c.revealed_by_npc)})" if c.revealed_by_npc else ""
        out.append(f"- at {n(c.location_id)}, {c.discovery.value}{who}: {c.description}  \n  → points to: {linked or 'nothing'}")
    out += ["", "## Characters"]
    for npc_id, files in bundle.npcs.items():
        ident = files.identity
        out += ["", f"### {ident.display_name if hasattr(ident, 'display_name') else n(npc_id)}",
                "```", json.dumps(ident.model_dump(mode="json", exclude={"id", "schema_version"}), ensure_ascii=False, indent=1)[:1500], "```", "Memory:"]
        for f in files.memory.facts:
            out.append(f"- [{f.source.value}, {f.disclosure.value}{', secret' if f.secret else ''}] {f.what} ({n(f.where)}, {f.when})")
        cover = getattr(files.memory, "cover_story", None)
        if cover:
            out.append(f"- cover story: {json.dumps(cover.model_dump(mode='json'), ensure_ascii=False)[:600]}")
    return "\n".join(out) + "\n"


# ============================================================================ self-test
def selftest(args: argparse.Namespace) -> int:
    """Run the plumbing with a fake model in a scratch results folder."""
    global RESULTS, RUNS_FILE, ENV_FILE
    scratch = HERE / "selftest_results"
    if scratch.exists():
        import shutil

        shutil.rmtree(scratch)
    RESULTS, RUNS_FILE, ENV_FILE = scratch, scratch / "runs.jsonl", scratch / "environment.json"
    os.environ["FABULA_EVAL_RESULTS"] = str(scratch)
    repo = Path(args.repo).resolve()
    dummy = scratch / "fake.gguf"
    scratch.mkdir(parents=True)
    dummy.write_bytes(b"not a model")
    ENV_FILE.write_text(json.dumps(capture_environment(repo, {"fast": dummy, "staged": dummy}), indent=2), encoding="utf-8")
    ns = argparse.Namespace(repo=str(repo), fast_model=str(dummy), staged_model=str(dummy), fake=True,
                            allow_fallback=False, timeout_min=None)
    for step in ("pilot_fast", "pilot_staged"):
        ns.step = step
        run_step(ns)
    return analyze(argparse.Namespace(repo=str(repo), steps=None, case_sheets=True))


# ============================================================================ main
def main(argv: list[str] | None = None) -> int:
    global RESULTS, RUNS_FILE, ENV_FILE
    if os.environ.get("FABULA_EVAL_RESULTS"):
        RESULTS = Path(os.environ["FABULA_EVAL_RESULTS"])
        RUNS_FILE, ENV_FILE = RESULTS / "runs.jsonl", RESULTS / "environment.json"
    argv = sys.argv[1:] if argv is None else argv
    if argv and argv[0] == "_child":
        return child_main(Path(argv[1]))
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    for name in ("env", "run", "analyze", "selftest", "plan"):
        sp = sub.add_parser(name)
        sp.add_argument("--repo", default=str(HERE.parent / "Fabula"))
        if name in ("env", "run"):
            sp.add_argument("--fast-model")
            sp.add_argument("--staged-model")
        if name == "run":
            sp.add_argument("--step", required=True, choices=sorted(PLAN))
            sp.add_argument("--timeout-min", type=float, help="override the step's timeout")
            sp.add_argument("--allow-fallback", action="store_true", help="do not stop when the fallback is used")
            sp.add_argument("--fake", action="store_true", help=argparse.SUPPRESS)
        if name == "analyze":
            sp.add_argument("--steps", help="comma-separated plan steps (default: all)")
            sp.add_argument("--case-sheets", action="store_true", help="write blind rubric case sheets")
    args = p.parse_args(argv)
    if args.cmd == "plan":
        for k, v in PLAN.items():
            print(f"{k:18s} route={v['route']:6s} timeout={v['timeout_s'] / 60:.0f}min groups={v['groups']}\n{'':18s} {v['purpose']}")
        return 0
    if args.cmd == "env":
        repo = Path(args.repo).resolve()
        models = default_models(repo)
        if args.fast_model:
            models["fast"] = Path(args.fast_model).resolve()
        if args.staged_model:
            models["staged"] = Path(args.staged_model).resolve()
        RESULTS.mkdir(parents=True, exist_ok=True)
        env = capture_environment(repo, models)
        ENV_FILE.write_text(json.dumps(env, indent=2), encoding="utf-8")
        print(json.dumps(env, indent=2))
        return 0
    if args.cmd == "run":
        return run_step(args)
    if args.cmd == "analyze":
        return analyze(args)
    if args.cmd == "selftest":
        return selftest(args)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
