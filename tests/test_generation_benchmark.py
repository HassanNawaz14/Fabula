from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import ModuleType


def _load_benchmark_module() -> ModuleType:
    path = Path(__file__).resolve().parents[1] / "evaluation" / "generation_benchmark.py"
    spec = importlib.util.spec_from_file_location("fabula_generation_benchmark", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_fixture_benchmark_writes_valid_report(tmp_path: Path) -> None:
    module = _load_benchmark_module()
    report_path = tmp_path / "report.json"
    bundle_path = tmp_path / "bundle"

    assert module.main(["--out", str(report_path), "--bundle-out", str(bundle_path)]) == 0

    report = json.loads(report_path.read_text(encoding="utf-8"))
    module.validate_report(report)
    assert report["mode"] == "fixture"
    assert report["totals"]["calls"] == 9
    assert report["totals"]["retries"] == 0
    assert report["model"]["sha256"] is None
    assert len(report["stages"]) == 9
    assert report["bundle"] == str(bundle_path.resolve())
    assert (bundle_path / "world.json").is_file()


def test_real_mode_requires_opt_in(tmp_path: Path, monkeypatch) -> None:
    module = _load_benchmark_module()
    monkeypatch.delenv("FABULA_MODEL_TESTS", raising=False)
    report_path = tmp_path / "report.json"

    assert module.main(["--real", "--out", str(report_path)]) == 2
    assert not report_path.exists()
