from __future__ import annotations

import json
import os
import shutil
import time
import zipfile
from pathlib import Path

import pytest

from fabula.case_library import discover_cases, install_case, validate_case
from fabula.generation.bundle_io import publish_bundle
from fabula.generation.jobs import LocalCaseJob
from fabula.generation.kaggle_runner import (
    KaggleRunError,
    KaggleSettings,
    KaggleSetupError,
    build_kernel_folder,
    kaggle_settings_from_env,
    request_payload,
    run_kaggle_case,
)
from fabula.generation.mock_runner import skeleton_runner
from fabula.schemas import GenerationSettings
from fabula.simulation.loader import BundleLoadError
from fabula.training_data import generate_skeleton


def _publish(root: Path, name: str, seed: int = 1) -> Path:
    bundle = generate_skeleton("theft", seed, tone="cozy", difficulty="easy")
    return publish_bundle(bundle, root / name)


def _wait(job, timeout: float = 10.0) -> bool:
    deadline = time.monotonic() + timeout
    while not job.is_done and time.monotonic() < deadline:
        time.sleep(0.01)
    return job.is_done


def test_discover_cases_lists_valid_bundles_newest_first(tmp_path) -> None:
    older = _publish(tmp_path, "case_older", seed=1)
    newer = _publish(tmp_path, "case_newer", seed=2)
    os.utime(older / "world.json", (1_700_000_000, 1_700_000_000))
    os.utime(newer / "world.json", (1_700_000_100, 1_700_000_100))
    junk = tmp_path / "not_a_case"
    junk.mkdir()
    (junk / "world.json").write_text("not json", encoding="utf-8")

    cases = discover_cases(tmp_path)

    assert [case.case_id for case in cases] == ["case_newer", "case_older"]
    assert cases[0].title
    assert cases[0].mystery_type == "theft"


def test_install_case_rejects_an_invalid_bundle(tmp_path) -> None:
    source = tmp_path / "invalid"
    source.mkdir()
    (source / "world.json").write_text("{}", encoding="utf-8")

    with pytest.raises(BundleLoadError):
        install_case(source, "broken", root=tmp_path / "library")


def test_kaggle_settings_require_credentials_and_default_the_dataset(tmp_path) -> None:
    with pytest.raises(KaggleSetupError):
        kaggle_settings_from_env({}, home=tmp_path)

    settings = kaggle_settings_from_env(
        {"KAGGLE_USERNAME": "hassan", "KAGGLE_KEY": "secret"}, home=tmp_path
    )

    assert settings.kernel_ref == "hassan/fabula-case-generator"
    assert settings.model_dataset == "hassan/fabula-qwen-3b-gguf"

    custom = kaggle_settings_from_env(
        {
            "KAGGLE_USERNAME": "hassan",
            "KAGGLE_KEY": "secret",
            "FABULA_KAGGLE_MODEL_DATASET": "hassan/custom-model",
        },
        home=tmp_path,
    )
    assert custom.model_dataset == "hassan/custom-model"


def test_kernel_folder_embeds_the_request_and_gpu_settings(tmp_path) -> None:
    settings = KaggleSettings(username="hassan", model_dataset="hassan/model")
    request = request_payload(
        settings,
        GenerationSettings(mystery_type="murder", tone="dark", difficulty="hard"),
        seed=1234,
    )

    folder = build_kernel_folder(tmp_path / "kernel", settings, request)
    metadata = json.loads((folder / "kernel-metadata.json").read_text(encoding="utf-8"))
    script = (folder / "generate_case.py").read_text(encoding="utf-8")

    assert metadata["id"] == "hassan/fabula-case-generator"
    assert metadata["enable_gpu"] is True
    assert metadata["enable_internet"] is True
    assert metadata["dataset_sources"] == ["hassan/model"]
    assert "__FABULA_REQUEST__" not in script
    assert "'seed': 1234" in script
    assert "'mystery_type': 'murder'" in script


def test_kernel_script_loads_the_cuda_runtime_and_offloads_layers(tmp_path) -> None:
    settings = KaggleSettings(username="hassan", model_dataset="hassan/model")
    request = request_payload(
        settings,
        GenerationSettings(mystery_type="theft", tone="cozy", difficulty="easy"),
        seed=99,
    )

    folder = build_kernel_folder(tmp_path / "kernel", settings, request)
    script = folder / "generate_case.py"
    source = script.read_text(encoding="utf-8")

    compile(source, str(script), "exec")
    assert "ctypes.CDLL(str(candidate), mode=ctypes.RTLD_GLOBAL)" in source
    assert "libcudart.so.12" in source
    assert 'if "n_gpu_layers" in inspect.signature(GenerationConfig).parameters:' in source
    assert 'options["n_gpu_layers"] = gpu_layers' in source
    assert "local_runner_module.simplify_json_schema = simplify_for_grammar" in source
    assert "orchestrator_module._run_stage = run_stage_checked" in source
    assert "retry_policy=RetryPolicy(4)" in source


class FakeKaggleApi:
    def __init__(self, statuses: list[str], archive: Path, failure: str = "") -> None:
        self.statuses = list(statuses)
        self.archive = archive
        self.failure = failure
        self.pushed: Path | None = None
        self.output_calls = 0

    def kernels_push(self, folder: str) -> None:
        self.pushed = Path(folder)
        assert (self.pushed / "kernel-metadata.json").is_file()

    def kernels_status(self, kernel: str) -> dict[str, str]:
        status = self.statuses.pop(0) if len(self.statuses) > 1 else self.statuses[0]
        return {"status": status, "failureMessage": self.failure}

    def kernels_output(
        self, kernel: str, path: str | None = None, force: bool = False, quiet: bool = True
    ) -> None:
        self.output_calls += 1
        assert path is not None
        shutil.copy(self.archive, Path(path) / "case.zip")


def _case_archive(root: Path, seed: int = 3) -> Path:
    bundle = generate_skeleton("theft", seed, tone="cozy", difficulty="easy")
    case_dir = publish_bundle(bundle, root / "archive_case")
    archive = root / "case.zip"
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as handle:
        for path in case_dir.rglob("*"):
            if path.is_file():
                handle.write(path, Path("case") / path.relative_to(case_dir))
    return archive


def test_kaggle_run_waits_downloads_and_installs_the_case(tmp_path) -> None:
    archive = _case_archive(tmp_path)
    api = FakeKaggleApi(["queued", "running", "complete"], archive)
    settings = KaggleSettings(username="hassan", model_dataset="hassan/model")
    messages: list[str] = []
    destination = tmp_path / "library" / "kaggle_case"

    result = run_kaggle_case(
        settings,
        GenerationSettings(mystery_type="theft", tone="cozy", difficulty="easy"),
        seed=7,
        destination=destination,
        emit=messages.append,
        api_factory=lambda: api,
        sleep=lambda _seconds: None,
        clock=lambda: 0.0,
    )

    assert result == destination
    assert (destination / "world.json").is_file()
    validate_case(destination)
    assert api.pushed is not None
    assert api.output_calls == 1
    assert any("Uploading" in message for message in messages)
    assert any("Downloading" in message for message in messages)


def test_kaggle_run_reports_a_failed_status(tmp_path) -> None:
    archive = _case_archive(tmp_path)
    api = FakeKaggleApi(["running", "error"], archive, failure="GPU quota exceeded")
    settings = KaggleSettings(username="hassan", model_dataset="hassan/model")

    with pytest.raises(KaggleRunError, match="quota"):
        run_kaggle_case(
            settings,
            GenerationSettings(mystery_type="theft", tone="cozy", difficulty="easy"),
            seed=7,
            destination=tmp_path / "case",
            api_factory=lambda: api,
            sleep=lambda _seconds: None,
            clock=lambda: 0.0,
        )


def test_kaggle_run_times_out_while_queued(tmp_path) -> None:
    archive = _case_archive(tmp_path)
    api = FakeKaggleApi(["queued"], archive)
    settings = KaggleSettings(username="hassan", model_dataset="hassan/model", timeout_seconds=60)
    ticks = iter([0.0, 120.0, 120.0, 120.0])

    with pytest.raises(KaggleRunError, match="did not finish in time"):
        run_kaggle_case(
            settings,
            GenerationSettings(mystery_type="theft", tone="cozy", difficulty="easy"),
            seed=7,
            destination=tmp_path / "case",
            api_factory=lambda: api,
            sleep=lambda _seconds: None,
            clock=lambda: next(ticks),
        )


def test_legacy_auth_suppresses_the_personal_token_file(tmp_path, monkeypatch) -> None:
    from fabula.generation import kaggle_runner

    (tmp_path / "kaggle.json").write_text(
        json.dumps({"username": "hassan", "key": "legacy-key"}), encoding="utf-8"
    )
    monkeypatch.setenv("KAGGLE_CONFIG_DIR", str(tmp_path))
    monkeypatch.delenv("KAGGLE_USERNAME", raising=False)
    monkeypatch.delenv("KAGGLE_KEY", raising=False)
    monkeypatch.delenv("KAGGLE_API_TOKEN", raising=False)

    with kaggle_runner._legacy_auth_only():
        override = Path(os.environ["KAGGLE_API_TOKEN"])
        assert override.is_file()
        assert override.read_text(encoding="utf-8") == ""

    assert "KAGGLE_API_TOKEN" not in os.environ
    assert not override.exists()


def test_legacy_auth_leaves_environment_alone_without_kaggle_json(tmp_path, monkeypatch) -> None:
    from fabula.generation import kaggle_runner

    monkeypatch.setenv("KAGGLE_CONFIG_DIR", str(tmp_path))
    monkeypatch.delenv("KAGGLE_USERNAME", raising=False)
    monkeypatch.delenv("KAGGLE_KEY", raising=False)
    monkeypatch.delenv("KAGGLE_API_TOKEN", raising=False)

    with kaggle_runner._legacy_auth_only():
        assert "KAGGLE_API_TOKEN" not in os.environ


def test_status_payload_reads_enum_status_objects() -> None:
    from fabula.generation.kaggle_runner import _status_payload

    class EnumValue:
        name = "ERROR"

    class Response:
        status = EnumValue()
        failure_message = None

    assert _status_payload(Response()) == ("error", "")
    assert _status_payload("KernelWorkerStatus.ERROR") == ("error", "")
    assert _status_payload({"status": "COMPLETE"}) == ("complete", "")


def test_kaggle_login_uses_the_legacy_key_directly(tmp_path, monkeypatch) -> None:
    import sys
    import types

    from fabula.generation import kaggle_runner

    class NoTokenApi:
        def authenticate(self) -> None:
            raise AssertionError("authenticate must not run when kaggle.json exists")

    modules = {
        "kaggle": types.ModuleType("kaggle"),
        "kaggle.api": types.ModuleType("kaggle.api"),
        "kaggle.api.kaggle_api_extended": types.ModuleType("kaggle.api.kaggle_api_extended"),
    }
    for name, module in modules.items():
        module.__path__ = []
        monkeypatch.setitem(sys.modules, name, module)
    modules["kaggle.api.kaggle_api_extended"].KaggleApi = NoTokenApi

    (tmp_path / "kaggle.json").write_text(
        json.dumps({"username": "hassan", "key": "legacy-key"}), encoding="utf-8"
    )
    monkeypatch.setenv("KAGGLE_CONFIG_DIR", str(tmp_path))
    monkeypatch.delenv("KAGGLE_USERNAME", raising=False)
    monkeypatch.delenv("KAGGLE_KEY", raising=False)

    api = kaggle_runner._load_api(None)

    assert isinstance(api, NoTokenApi)
    assert api.config_values == {"username": "hassan", "key": "legacy-key"}


def test_kaggle_cli_batch_installs_every_case(tmp_path, monkeypatch) -> None:
    from fabula.cli import main
    from fabula.generation import kaggle_runner

    archive = _case_archive(tmp_path)
    api = FakeKaggleApi(["complete"], archive)
    monkeypatch.setenv("KAGGLE_USERNAME", "hassan")
    monkeypatch.setenv("KAGGLE_KEY", "secret")
    monkeypatch.setenv("FABULA_LIBRARY_DIR", str(tmp_path / "library"))
    monkeypatch.setattr(kaggle_runner, "_load_api", lambda _factory=None: api)

    assert main(["kaggle", "--count", "2", "--seed", "10"]) == 0

    cases = discover_cases(tmp_path / "library")
    assert len(cases) == 2
    for case in cases:
        validate_case(case.path)


def test_local_job_generates_a_valid_case_with_progress(tmp_path) -> None:
    skeleton = generate_skeleton("theft", 0)
    job = LocalCaseJob(
        GenerationSettings(
            mystery_type=skeleton.world.mystery_type,
            tone=skeleton.world.tone,
            difficulty=skeleton.world.difficulty,
        ),
        runner=skeleton_runner(),
        output_dir=tmp_path / "local_case",
    )
    job.start()

    assert _wait(job)
    assert job.error is None
    assert job.result_path == tmp_path / "local_case"
    validate_case(job.result_path)
    messages = [update.message for update in job.drain()]
    assert any("Writing the town" in message for message in messages)
    assert job.take_result() == tmp_path / "local_case"
    assert job.take_result() is None


def test_local_job_surfaces_a_failure(tmp_path) -> None:
    class BrokenRunner:
        def generate(self, *_args, **_kwargs):
            raise RuntimeError("model exploded")

    job = LocalCaseJob(
        GenerationSettings(mystery_type="theft", tone="cozy", difficulty="easy"),
        runner=BrokenRunner(),
        output_dir=tmp_path / "broken_case",
    )
    job.start()

    assert _wait(job)
    assert job.error is not None
    assert "model exploded" in job.error
    assert job.take_result() is None


def test_local_job_uses_the_fast_blueprint_pipeline(tmp_path) -> None:
    from fabula.generation.synthetic_blueprint import generate_synthetic_blueprint_sample

    dsl = generate_synthetic_blueprint_sample(11)["messages"][2]["content"]

    class BlueprintRunner:
        def generate_blueprint(self, **_kwargs):
            return dsl

    job = LocalCaseJob(
        GenerationSettings(mystery_type="random", tone="cozy", difficulty="normal"),
        runner=BlueprintRunner(),
        output_dir=tmp_path / "fast_case",
    )
    job.start()

    assert _wait(job)
    assert job.error is None
    validate_case(job.result_path)
    messages = [update.message for update in job.drain()]
    assert any("blueprint" in message.lower() for message in messages)


def test_local_job_falls_back_to_the_blueprint_library_without_a_model(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)

    job = LocalCaseJob(
        GenerationSettings(mystery_type="theft", tone="cozy", difficulty="easy"),
        output_dir=tmp_path / "fallback_case",
        environ={},
    )
    job.start()

    assert _wait(job)
    assert job.error is None
    validate_case(job.result_path)
    messages = [update.message for update in job.drain()]
    assert any("built-in blueprint" in message for message in messages)


def test_publish_retries_a_transient_windows_lock(tmp_path, monkeypatch) -> None:
    from fabula.generation import bundle_io

    bundle = generate_skeleton("theft", 3)
    attempts = {"count": 0}
    original_rename = Path.rename

    def flaky_rename(self, destination):
        if self.name.startswith(".retry_case.tmp-"):
            attempts["count"] += 1
            if attempts["count"] == 1:
                raise PermissionError(13, "locked by a scanner", str(self))
        return original_rename(self, destination)

    monkeypatch.setattr(Path, "rename", flaky_rename)

    published = bundle_io.publish_bundle(bundle, tmp_path / "retry_case")

    assert published == (tmp_path / "retry_case").resolve()
    assert attempts["count"] == 2


def test_cli_without_a_command_launches_the_start_menu(monkeypatch) -> None:
    from fabula import cli

    launched = []
    monkeypatch.setattr(cli, "run_game", lambda: launched.append(True) or 0)

    assert cli.main([]) == 0
    assert launched == [True]


def test_play_without_a_bundle_opens_the_start_menu(tmp_path, monkeypatch) -> None:
    from fabula import cli

    monkeypatch.chdir(tmp_path)
    launched = []
    monkeypatch.setattr(cli, "run_game", lambda: launched.append(True) or 0)

    assert cli.main(["play"]) == 0
    assert launched == [True]


def test_play_reports_a_missing_case(tmp_path, monkeypatch) -> None:
    from fabula import cli

    monkeypatch.chdir(tmp_path)

    assert cli.main(["play", "--bundle", "missing-case"]) == 2
