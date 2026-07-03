from __future__ import annotations

import os
import shutil
import stat
import subprocess
import sys
import tarfile
from pathlib import Path

import pytest


COLLECTOR_ROOT = Path(__file__).resolve().parents[1]
BUILDER = COLLECTOR_ROOT / "build-customer-package.sh"
LAUNCHER_TEMPLATE = COLLECTOR_ROOT / "package" / "collector.sh"


def _run(*args: object, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [os.fspath(arg) for arg in args],
        cwd=cwd,
        text=True,
        capture_output=True,
        check=False,
    )


def _build_and_extract(tmp_path: Path) -> Path:
    archive = tmp_path / "customer-collector.tar.gz"
    result = _run(
        BUILDER,
        "--output",
        archive,
        "--mode",
        "online",
        "--extras",
        "core",
        "--python",
        sys.executable,
    )
    assert result.returncode == 0, result.stderr
    assert archive.is_file()

    extract_root = tmp_path / "extracted"
    extract_root.mkdir()
    with tarfile.open(archive, "r:gz") as bundle:
        names = bundle.getnames()
        assert names
        assert all(not name.startswith("/") and ".." not in Path(name).parts for name in names)
        bundle.extractall(extract_root, filter="data")

    children = list(extract_root.iterdir())
    assert len(children) == 1
    return children[0]


def test_packaging_scripts_exist_and_are_executable():
    for script in (BUILDER, LAUNCHER_TEMPLATE):
        assert script.is_file()
        assert script.stat().st_mode & stat.S_IXUSR


def test_builder_help_exposes_delivery_modes_without_building():
    result = _run(BUILDER, "--help")

    assert result.returncode == 0
    assert "--output" in result.stdout
    assert "--mode online|offline" in result.stdout
    assert "--extras core|oci|oracle|all" in result.stdout
    assert "--python" in result.stdout


@pytest.mark.parametrize(
    ("option", "value"),
    [("--mode", "connected-ish"), ("--extras", "everything-ish")],
)
def test_builder_rejects_unsupported_delivery_options(option: str, value: str, tmp_path: Path):
    result = _run(BUILDER, option, value, "--output", tmp_path / "bundle.tar.gz")

    assert result.returncode == 2
    assert "unsupported" in result.stderr.lower()
    assert not (tmp_path / "bundle.tar.gz").exists()


def test_online_bundle_contains_launcher_docs_profiles_wheel_and_integrity_manifest(tmp_path: Path):
    bundle_root = _build_and_extract(tmp_path)

    assert (bundle_root / "collector.sh").stat().st_mode & stat.S_IXUSR
    assert (bundle_root / "QUICKSTART.md").is_file()
    assert (bundle_root / "CONFIGURATION.md").is_file()
    assert (bundle_root / "BUNDLE-METADATA").is_file()
    assert (bundle_root / "SHA256SUMS").is_file()
    assert (bundle_root / "customer-config").is_dir()
    assert len(list((bundle_root / "profiles").rglob("*.yaml"))) == 19
    assert len(list((bundle_root / "wheelhouse").glob("oracle_compliance_collector-*.whl"))) == 1

    metadata = (bundle_root / "BUNDLE-METADATA").read_text()
    assert "mode=online" in metadata
    assert "extras=core" in metadata


def test_customer_launcher_lists_profiles_and_initializes_selected_config(tmp_path: Path):
    bundle_root = _build_and_extract(tmp_path)
    launcher = bundle_root / "collector.sh"

    listed = _run(launcher, "list-profiles", cwd=bundle_root)
    assert listed.returncode == 0
    assert "onprem/middleware/weblogic" in listed.stdout
    assert "oci/database-data-safe" in listed.stdout
    assert "hybrid/onprem-oci-full" in listed.stdout

    config = tmp_path / "customer.yaml"
    initialized = _run(
        launcher,
        "init",
        "--profile",
        "oci/database-data-safe",
        "--config",
        config,
        cwd=bundle_root,
    )
    assert initialized.returncode == 0, initialized.stderr
    assert config.read_text() == (bundle_root / "profiles/oci/database-data-safe.yaml").read_text()

    repeated = _run(
        launcher,
        "init",
        "--profile",
        "oci/database-data-safe",
        "--config",
        config,
        cwd=bundle_root,
    )
    assert repeated.returncode == 2
    assert "already exists" in repeated.stderr.lower()


def test_init_can_create_environment_config_separate_from_immutable_profiles(tmp_path: Path):
    bundle_root = _build_and_extract(tmp_path)
    launcher = bundle_root / "collector.sh"
    source = bundle_root / "profiles/onprem/middleware/weblogic.yaml"
    source_before = source.read_bytes()

    initialized = _run(
        launcher,
        "init",
        "--profile",
        "onprem/middleware/weblogic",
        "--environment",
        "production-cl",
        cwd=bundle_root,
    )

    config = bundle_root / "customer-config/production-cl.yaml"
    assert initialized.returncode == 0, initialized.stderr
    assert config.is_file()
    assert stat.S_IMODE(config.stat().st_mode) == 0o600
    assert config.read_bytes() == source_before
    assert source.read_bytes() == source_before


@pytest.mark.parametrize("environment", ["../prod", "prod/subdir", "", "prod config"])
def test_init_rejects_unsafe_environment_names(environment: str, tmp_path: Path):
    bundle_root = _build_and_extract(tmp_path)
    result = _run(
        bundle_root / "collector.sh",
        "init",
        "--profile",
        "oci/object-storage",
        "--environment",
        environment,
        cwd=bundle_root,
    )

    assert result.returncode == 2
    assert "environment" in result.stderr.lower()


def test_launcher_refuses_unknown_or_traversal_profile_names(tmp_path: Path):
    bundle_root = _build_and_extract(tmp_path)
    launcher = bundle_root / "collector.sh"

    for profile in ("oci/not-real", "../../collector.config"):
        result = _run(
            launcher,
            "init",
            "--profile",
            profile,
            "--config",
            tmp_path / "config.yaml",
            cwd=bundle_root,
        )
        assert result.returncode == 2
        assert "profile" in result.stderr.lower()


def test_doctor_fails_fast_on_unresolved_placeholders_without_bootstrapping(tmp_path: Path):
    bundle_root = _build_and_extract(tmp_path)
    launcher = bundle_root / "collector.sh"
    config = tmp_path / "customer.yaml"
    shutil.copy2(bundle_root / "profiles/oci/full-stack.yaml", config)

    result = _run(launcher, "doctor", "--config", config, cwd=bundle_root)

    assert result.returncode == 2
    assert "replace" in result.stderr.lower()
    assert not (bundle_root / ".runtime").exists()


def test_integrity_verification_detects_bundle_tampering(tmp_path: Path):
    bundle_root = _build_and_extract(tmp_path)
    launcher = bundle_root / "collector.sh"

    clean = _run(launcher, "verify", cwd=bundle_root)
    assert clean.returncode == 0, clean.stderr

    with (bundle_root / "QUICKSTART.md").open("a") as handle:
        handle.write("\ntampered\n")

    tampered = _run(launcher, "verify", cwd=bundle_root)
    assert tampered.returncode != 0
    assert "integrity" in tampered.stderr.lower() or "failed" in tampered.stderr.lower()


def test_scripts_avoid_privilege_escalation_eval_and_network_download_tools():
    scripts = BUILDER.read_text() + "\n" + LAUNCHER_TEMPLATE.read_text()

    assert "sudo " not in scripts
    assert "eval " not in scripts
    assert "curl " not in scripts
    assert "wget " not in scripts
    assert "--no-index" in scripts
    assert "--require-virtualenv" in scripts
