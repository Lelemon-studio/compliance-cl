from __future__ import annotations

import os
import shutil
import stat
import subprocess
from pathlib import Path

import pytest


COLLECTOR_ROOT = Path(__file__).resolve().parents[1]
WRAPPER = COLLECTOR_ROOT / "run-collector.sh"


def _write_executable(path: Path, body: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("#!/bin/bash\n" + body, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return path


def _fake_collector(path: Path, *, label: str = "") -> Path:
    prefix = f"printf '%s\\n' '{label}'\n" if label else ""
    return _write_executable(
        path,
        prefix
        + "printf '%s\\n' \"$@\"\n"
        + "exit \"${FAKE_COLLECTOR_EXIT:-0}\"\n",
    )


def _run(
    cwd: Path,
    *arguments: str,
    env: dict[str, str] | None = None,
    wrapper: Path = WRAPPER,
) -> subprocess.CompletedProcess[str]:
    effective_env = os.environ.copy()
    if env:
        effective_env.update(env)
    return subprocess.run(
        ["/bin/bash", str(wrapper), *arguments],
        cwd=cwd,
        env=effective_env,
        capture_output=True,
        text=True,
        check=False,
    )


def _config(cwd: Path, name: str = "collector.config.yaml") -> Path:
    path = cwd / name
    path.write_text("run:\n  name: wrapper-test\n", encoding="utf-8")
    return path


def _copy_wrapper(tmp_path: Path) -> Path:
    destination = tmp_path / "app" / "run-collector.sh"
    destination.parent.mkdir(parents=True)
    shutil.copy2(WRAPPER, destination)
    destination.chmod(destination.stat().st_mode | stat.S_IXUSR)
    (destination.parent / "src").mkdir()
    return destination


def test_wrapper_is_executable():
    assert WRAPPER.is_file()
    assert os.access(WRAPPER, os.X_OK)


def test_help_is_available_without_config_or_collector(tmp_path):
    result = _run(tmp_path, "--help")

    assert result.returncode == 0
    assert "Usage:" in result.stdout
    assert "--collector-bin" in result.stdout
    assert "--offline-only" in result.stdout


def test_version_is_available_without_config_or_collector(tmp_path):
    result = _run(tmp_path, "--version")

    assert result.returncode == 0
    assert "0.1.0" in result.stdout


def test_defaults_are_forwarded_to_explicit_collector(tmp_path):
    _config(tmp_path)
    binary = _fake_collector(tmp_path / "fake collector")

    result = _run(tmp_path, "--collector-bin", str(binary))

    assert result.returncode == 0
    assert result.stdout.splitlines() == [
        "run",
        "--config",
        "./collector.config.yaml",
        "--out",
        "./out",
    ]


def test_all_run_options_and_repeated_filters_are_forwarded_in_order(tmp_path):
    config = _config(tmp_path, "custom config.yaml")
    key = tmp_path / "bundle key"
    key.write_bytes(b"x" * 32)
    binary = _fake_collector(tmp_path / "fake")

    result = _run(
        tmp_path,
        "--only",
        "dbsat",
        "--skip",
        "oci.compute",
        "--only",
        "middleware",
        "--config",
        str(config),
        "--out",
        "output with spaces",
        "--dry-run",
        "--offline-only",
        "--encryption-key-file",
        str(key),
        "--skip",
        "direct_sql",
        "--collector-bin",
        str(binary),
    )

    assert result.returncode == 0
    assert result.stdout.splitlines() == [
        "run",
        "--config",
        str(config),
        "--out",
        "output with spaces",
        "--only",
        "dbsat",
        "--skip",
        "oci.compute",
        "--only",
        "middleware",
        "--dry-run",
        "--offline-only",
        "--encryption-key-file",
        str(key),
        "--skip",
        "direct_sql",
    ]


@pytest.mark.parametrize(
    "hostile_value",
    ["value with spaces", "*.json", "out; echo must-not-run", "$(touch {marker})"],
)
def test_arguments_are_not_evaluated_by_the_shell(tmp_path, hostile_value):
    _config(tmp_path)
    binary = _fake_collector(tmp_path / "fake")
    marker = tmp_path / "must-not-exist"
    hostile_value = hostile_value.format(marker=marker)

    result = _run(
        tmp_path,
        "--collector-bin",
        str(binary),
        "--out",
        hostile_value,
    )

    assert result.returncode == 0
    assert hostile_value in result.stdout.splitlines()
    assert not marker.exists()


def test_wrapper_contains_no_eval_or_dependency_install_commands():
    source = WRAPPER.read_text(encoding="utf-8")

    assert "eval " not in source
    assert "pip install" not in source
    assert "apt-get" not in source
    assert "brew install" not in source


@pytest.mark.parametrize(
    "option",
    ["--config", "--out", "--only", "--skip", "--encryption-key-file", "--collector-bin"],
)
def test_value_options_reject_missing_values(tmp_path, option):
    result = _run(tmp_path, option)

    assert result.returncode == 2
    assert f"{option} requires a value" in result.stderr


def test_value_options_do_not_consume_the_next_option(tmp_path):
    result = _run(tmp_path, "--config", "--dry-run")

    assert result.returncode == 2
    assert "--config requires a value" in result.stderr


def test_unknown_options_and_positional_arguments_are_rejected(tmp_path):
    unknown = _run(tmp_path, "--unknown")
    positional = _run(tmp_path, "surprise")

    assert unknown.returncode == 2
    assert "Unknown option: --unknown" in unknown.stderr
    assert positional.returncode == 2
    assert "Unexpected argument: surprise" in positional.stderr


def test_missing_config_is_reported_before_execution(tmp_path):
    binary = _fake_collector(tmp_path / "fake")

    result = _run(tmp_path, "--collector-bin", str(binary))

    assert result.returncode == 2
    assert "Configuration file not found" in result.stderr
    assert result.stdout == ""


def test_unusable_explicit_binary_is_rejected(tmp_path):
    _config(tmp_path)
    binary = tmp_path / "not-executable"
    binary.write_text("not executable", encoding="utf-8")

    result = _run(tmp_path, "--collector-bin", str(binary))

    assert result.returncode == 2
    assert "Collector executable is not usable" in result.stderr


def test_encryption_key_file_must_be_a_readable_regular_file(tmp_path):
    _config(tmp_path)
    binary = _fake_collector(tmp_path / "fake")
    missing_key = tmp_path / "missing.key"

    result = _run(
        tmp_path,
        "--collector-bin",
        str(binary),
        "--encryption-key-file",
        str(missing_key),
    )

    assert result.returncode == 2
    assert "Encryption key file is not readable" in result.stderr


def test_explicit_binary_takes_precedence(tmp_path):
    _config(tmp_path)
    wrapper = _copy_wrapper(tmp_path)
    explicit = _fake_collector(tmp_path / "explicit", label="explicit")
    _fake_collector(wrapper.parent.parent / ".venv" / "bin" / "collector", label="venv")
    path_dir = tmp_path / "path-bin"
    _fake_collector(path_dir / "collector", label="path")

    result = _run(
        tmp_path,
        "--collector-bin",
        str(explicit),
        env={"PATH": f"{path_dir}:/usr/bin:/bin"},
        wrapper=wrapper,
    )

    assert result.returncode == 0
    assert result.stdout.splitlines()[0] == "explicit"


def test_repository_virtualenv_precedes_path_collector(tmp_path):
    _config(tmp_path)
    wrapper = _copy_wrapper(tmp_path)
    _fake_collector(wrapper.parent.parent / ".venv" / "bin" / "collector", label="venv")
    path_dir = tmp_path / "path-bin"
    _fake_collector(path_dir / "collector", label="path")

    result = _run(
        tmp_path,
        env={"PATH": f"{path_dir}:/usr/bin:/bin"},
        wrapper=wrapper,
    )

    assert result.returncode == 0
    assert result.stdout.splitlines()[0] == "venv"


def test_path_collector_precedes_local_python_fallback(tmp_path):
    _config(tmp_path)
    wrapper = _copy_wrapper(tmp_path)
    path_dir = tmp_path / "path-bin"
    _fake_collector(path_dir / "collector", label="path")
    _write_executable(path_dir / "python3", "printf '%s\\n' python\n")

    result = _run(
        tmp_path,
        env={"PATH": f"{path_dir}:/usr/bin:/bin"},
        wrapper=wrapper,
    )

    assert result.returncode == 0
    assert result.stdout.splitlines()[0] == "path"


def test_local_python_module_is_final_fallback_and_gets_src_pythonpath(tmp_path):
    _config(tmp_path)
    wrapper = _copy_wrapper(tmp_path)
    path_dir = tmp_path / "path-bin"
    _write_executable(
        path_dir / "python3",
        "printf 'PYTHONPATH=%s\\n' \"$PYTHONPATH\"\nprintf '%s\\n' \"$@\"\n",
    )

    result = _run(
        tmp_path,
        env={"PATH": f"{path_dir}:/usr/bin:/bin", "PYTHONPATH": "/existing/path"},
        wrapper=wrapper,
    )

    assert result.returncode == 0
    lines = result.stdout.splitlines()
    assert lines[0] == f"PYTHONPATH={wrapper.parent / 'src'}:/existing/path"
    assert lines[1:4] == ["-m", "oracle_collector", "run"]


def test_error_when_no_collector_or_python_is_available(tmp_path):
    _config(tmp_path)
    wrapper = _copy_wrapper(tmp_path)
    empty_path = tmp_path / "empty-path"
    empty_path.mkdir()

    result = _run(tmp_path, env={"PATH": str(empty_path)}, wrapper=wrapper)

    assert result.returncode == 2
    assert "No usable collector executable or python3 found" in result.stderr


@pytest.mark.parametrize("exit_code", [0, 1, 2, 23])
def test_collector_exit_code_is_preserved(tmp_path, exit_code):
    _config(tmp_path)
    binary = _fake_collector(tmp_path / "fake")

    result = _run(
        tmp_path,
        "--collector-bin",
        str(binary),
        env={"FAKE_COLLECTOR_EXIT": str(exit_code)},
    )

    assert result.returncode == exit_code
