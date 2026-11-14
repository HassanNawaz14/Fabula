from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from fabula.generation.config import (
    DEFAULT_MODEL_PATH,
    GenerationConfig,
    config_from_env,
    load_model_manifest,
    manifest_sha256,
    resolve_model_path,
    sha256_file,
    verify_model_artifact,
)
from fabula.generation.errors import GenerationSetupError


def test_resolve_model_path_precedence(tmp_path: Path) -> None:
    explicit = tmp_path / "explicit.gguf"
    from_env = tmp_path / "env.gguf"
    env = {"FABULA_MODEL_PATH": str(from_env)}

    assert resolve_model_path(explicit, environ=env) == explicit
    assert resolve_model_path(None, environ=env) == from_env
    assert resolve_model_path(None, environ={}) == DEFAULT_MODEL_PATH


def test_config_from_env(tmp_path: Path) -> None:
    env = {
        "FABULA_MODEL_PATH": str(tmp_path / "model.gguf"),
        "FABULA_MODEL_CTX": "2048",
        "FABULA_MODEL_THREADS": "3",
        "FABULA_GENERATION_RETRIES": "1",
        "FABULA_GENERATION_OUT": str(tmp_path / "out"),
    }
    config = config_from_env(env)
    assert config.model_path == tmp_path / "model.gguf"
    assert config.n_ctx == 2048
    assert config.n_threads == 3
    assert config.retry_attempts == 1
    assert config.output_dir == tmp_path / "out"


def test_config_cli_overrides_env(tmp_path: Path) -> None:
    env = {"FABULA_MODEL_PATH": "env.gguf", "FABULA_GENERATION_RETRIES": "2"}
    config = config_from_env(
        env,
        model_path=tmp_path / "cli.gguf",
        output_dir=tmp_path / "cli-out",
        retry_attempts=5,
    )
    assert config.model_path == tmp_path / "cli.gguf"
    assert config.output_dir == tmp_path / "cli-out"
    assert config.retry_attempts == 5


def test_invalid_integer_environment_raises() -> None:
    with pytest.raises(GenerationSetupError, match="FABULA_MODEL_CTX"):
        config_from_env({"FABULA_MODEL_CTX": "many"})


def test_invalid_config_values_raise() -> None:
    with pytest.raises(ValueError, match="retry_attempts"):
        GenerationConfig(retry_attempts=0)
    with pytest.raises(ValueError, match="n_ctx"):
        GenerationConfig(n_ctx=128)


def test_sha256_file(tmp_path: Path) -> None:
    path = tmp_path / "payload.bin"
    path.write_bytes(b"fabula")
    assert sha256_file(path) == hashlib.sha256(b"fabula").hexdigest()


def test_verify_model_artifact_missing(tmp_path: Path) -> None:
    with pytest.raises(GenerationSetupError, match="not found"):
        verify_model_artifact(tmp_path / "missing.gguf")


def test_verify_model_artifact_hash(tmp_path: Path) -> None:
    path = tmp_path / "model.gguf"
    path.write_bytes(b"weights")
    digest = hashlib.sha256(b"weights").hexdigest()

    assert verify_model_artifact(path, expected_sha256=digest) == digest
    with pytest.raises(GenerationSetupError, match="SHA-256 mismatch"):
        verify_model_artifact(path, expected_sha256="0" * 64)


def test_load_model_manifest_and_hash(tmp_path: Path) -> None:
    path = tmp_path / "model_manifest.json"
    path.write_text(json.dumps({"sha256": "abc"}), encoding="utf-8")
    manifest = load_model_manifest(path)
    assert manifest == {"sha256": "abc"}
    assert manifest_sha256(manifest) == "abc"

    assert load_model_manifest(tmp_path / "missing.json") is None
    assert manifest_sha256(None) is None


def test_manifest_sha256_rejects_non_string(tmp_path: Path) -> None:
    path = tmp_path / "model_manifest.json"
    path.write_text(json.dumps({"sha256": 123}), encoding="utf-8")
    with pytest.raises(GenerationSetupError, match="sha256"):
        manifest_sha256(load_model_manifest(path))
