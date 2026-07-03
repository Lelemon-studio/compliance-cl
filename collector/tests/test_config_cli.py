from __future__ import annotations

from pathlib import Path

import pytest

from oracle_collector.cli import build_parser, resolve_selection
from oracle_collector.config import ConfigError, load_config


def test_load_config_and_cli_overrides(tmp_path: Path) -> None:
    config_path = tmp_path / "collector.yaml"
    config_path.write_text(
        """
run:
  name: test-run
  redaction: strict
  parallelism: 4
oci:
  enabled: true
  auth: instance_principal
  tenancy_ocid: ocid1.tenancy.oc1..example
  regions: [sa-santiago-1]
  compartments: all
  services: all
onprem_db:
  enabled: false
onprem_middleware:
  enabled: false
""".strip(),
        encoding="utf-8",
    )

    config = load_config(config_path)
    assert config.run.name == "test-run"
    assert config.run.redaction == "strict"
    assert config.oci.regions == ("sa-santiago-1",)

    args = build_parser().parse_args(
        ["run", "--config", str(config_path), "--only", "oci.object_storage", "--skip", "dbsat"]
    )
    selection = resolve_selection(config, args)
    assert selection.only == ("oci.object_storage",)
    assert "dbsat" in selection.skip


@pytest.mark.parametrize("redaction", ["none", "unsafe", ""])
def test_invalid_redaction_is_rejected(tmp_path: Path, redaction: str) -> None:
    config_path = tmp_path / "collector.yaml"
    config_path.write_text(
        f"run:\n  name: x\n  redaction: {redaction!r}\noci:\n  enabled: false\n",
        encoding="utf-8",
    )
    with pytest.raises(ConfigError):
        load_config(config_path)


def test_cleartext_password_in_config_is_rejected(tmp_path: Path) -> None:
    config_path = tmp_path / "collector.yaml"
    config_path.write_text(
        "run:\n  name: x\n  redaction: strict\noci:\n  enabled: false\npassword: secret\n",
        encoding="utf-8",
    )
    with pytest.raises(ConfigError, match="secret|password"):
        load_config(config_path)


@pytest.mark.parametrize("key", ["client_secret", "auth_token", "wallet_password", "signing_private_key"])
def test_secret_key_variants_are_rejected(tmp_path: Path, key: str) -> None:
    config_path = tmp_path / "collector.yaml"
    config_path.write_text(
        f"run:\n  name: x\n  redaction: strict\noci:\n  enabled: false\n{key}: forbidden\n",
        encoding="utf-8",
    )
    with pytest.raises(ConfigError, match="secret|password"):
        load_config(config_path)
