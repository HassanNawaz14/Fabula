from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path

from fabula.generation.cli import run_generate, run_model_check
from fabula.generation.config import GenerationConfig
from fabula.generation.mock_runner import MockModelRunner
from fabula.training_data import generate_skeleton


def test_model_check_pass(tmp_path: Path, capsys) -> None:
    model = tmp_path / "model.gguf"
    model.write_bytes(b"model-bytes")
    digest = hashlib.sha256(b"model-bytes").hexdigest()
    manifest = tmp_path / "model_manifest.json"
    manifest.write_text(json.dumps({"sha256": digest}), encoding="utf-8")

    args = argparse.Namespace(model=model, manifest=manifest)
    assert run_model_check(args) == 0

    output = capsys.readouterr().out
    assert "SHA-256" in output
    assert digest in output
    assert "PASS" in output


def test_model_check_fail(tmp_path: Path, capsys) -> None:
    args = argparse.Namespace(model=tmp_path / "missing.gguf", manifest=None)
    assert run_model_check(args) == 2
    assert "FAIL" in capsys.readouterr().err


def test_model_check_hash_mismatch(tmp_path: Path, capsys) -> None:
    model = tmp_path / "model.gguf"
    model.write_bytes(b"model-bytes")
    manifest = tmp_path / "model_manifest.json"
    manifest.write_text(json.dumps({"sha256": "0" * 64}), encoding="utf-8")

    args = argparse.Namespace(model=model, manifest=manifest)
    assert run_model_check(args) == 2
    assert "SHA-256 mismatch" in capsys.readouterr().err


class FakeRunner:
    instances: list[FakeRunner] = []

    def __init__(self, model_path: Path, config: GenerationConfig) -> None:
        self.model_path = model_path
        self.config = config
        self.inner = MockModelRunner(generate_skeleton("theft", 3, tone="cozy", difficulty="easy"))
        self.closed = False
        self.instances.append(self)

    def generate(self, stage, stage_input, output_model, seed):
        return self.inner.generate(stage, stage_input, output_model, seed)

    def generate_blueprint(self, mystery_type: str, tone: str, difficulty: str, seed: int) -> str:
        return (
            "[CASE:theft|cozy|seed_42]\n"
            "PREMISE: test premise\n"
            "CAST: vict:v | culp:npc_01 | susp:npc_02,npc_03,npc_04,npc_05\n"
            "CRIME: mot:debt | meth:theft | scene:loc_library | time:3\n"
            "TIMELINE:\n"
            "- 2 | npc_01 | loc_library | stole\n"
            "CLUES:\n"
            "- c1 | loc_library | physical | links:npc_01 | proves:meth\n"
        )

    def close(self) -> None:
        self.closed = True


def test_generate_command_with_fake_runner(tmp_path: Path, monkeypatch, capsys) -> None:
    monkeypatch.setattr("fabula.generation.cli.LocalModelRunner", FakeRunner)
    FakeRunner.instances.clear()
    args = argparse.Namespace(
        mystery_type="theft",
        tone="cozy",
        difficulty="easy",
        seed=7,
        out=tmp_path / "bundle",
        retries=1,
        model=tmp_path / "model.gguf",
    )

    assert run_generate(args) == 0

    output = capsys.readouterr().out
    assert "Seed: 7" in output
    assert "Resolved type: theft" in output
    assert (tmp_path / "bundle" / "world.json").is_file()
    assert len(FakeRunner.instances) == 1
    assert FakeRunner.instances[0].closed is True


def test_generate_command_fast_mode(tmp_path: Path, capsys) -> None:
    args = argparse.Namespace(
        mystery_type="murder",
        tone="dark",
        difficulty="normal",
        seed=42,
        out=tmp_path / "fast_bundle",
        retries=1,
        model=None,
        fast_mode=True,
    )
    assert run_generate(args) == 0

    output = capsys.readouterr().out
    assert "Seed: 42" in output
    assert "Resolved type: murder" in output
    assert (tmp_path / "fast_bundle" / "world.json").is_file()
    assert (tmp_path / "fast_bundle" / "truth.json").is_file()
    assert (tmp_path / "fast_bundle" / "clues.json").is_file()
    assert (tmp_path / "fast_bundle" / "npcs" / "npc_01" / "identity.json").is_file()


def test_generate_command_fast_mode_with_runner(tmp_path: Path, monkeypatch, capsys) -> None:
    monkeypatch.setattr("fabula.generation.cli.LocalModelRunner", FakeRunner)
    FakeRunner.instances.clear()
    fake_model = tmp_path / "fake_model.gguf"
    fake_model.write_bytes(b"data")
    args = argparse.Namespace(
        mystery_type="theft",
        tone="cozy",
        difficulty="easy",
        seed=42,
        out=tmp_path / "fast_bundle_runner",
        retries=1,
        model=fake_model,
        fast_mode=True,
    )
    assert run_generate(args) == 0

    output = capsys.readouterr().out
    assert "Seed: 42" in output
    assert "Resolved type: theft" in output
    assert (tmp_path / "fast_bundle_runner" / "world.json").is_file()
    assert len(FakeRunner.instances) == 1
    assert FakeRunner.instances[0].closed is True


def test_generation_package_has_no_conversation_or_provider_imports() -> None:
    package = Path(__file__).resolve().parents[1] / "src" / "fabula" / "generation"
    forbidden_prefixes = ("fabula.conversation", "fabula.conversation.providers", "httpx")
    for path in sorted(package.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            names: list[str] = []
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or ""]
            for name in names:
                assert not name.startswith(forbidden_prefixes), (
                    f"{path.name} imports forbidden runtime module {name}"
                )
