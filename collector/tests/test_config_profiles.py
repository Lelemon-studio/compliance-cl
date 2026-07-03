from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pytest
import yaml

from oracle_collector.config import load_config


COLLECTOR_ROOT = Path(__file__).resolve().parents[1]
CONFIG_ROOT = COLLECTOR_ROOT / "configs"

ONPREM_DATABASE = {
    "onprem/database/dbsat-only.yaml",
    "onprem/database/direct-sql-only.yaml",
    "onprem/database/database-full.yaml",
}
ONPREM_MIDDLEWARE = {
    "onprem/middleware/weblogic.yaml",
    "onprem/middleware/ohs.yaml",
    "onprem/middleware/oam.yaml",
    "onprem/middleware/oaa.yaml",
    "onprem/middleware/webgate.yaml",
    "onprem/middleware/oag.yaml",
    "onprem/middleware/avdf.yaml",
    "onprem/middleware/middleware-full.yaml",
}
OCI_PROFILES = {
    "oci/full-stack.yaml",
    "oci/identity-governance.yaml",
    "oci/database-data-safe.yaml",
    "oci/compute-storage-oke.yaml",
    "oci/network-perimeter.yaml",
    "oci/observability-dr.yaml",
    "oci/object-storage.yaml",
}
HYBRID_PROFILES = {"hybrid/onprem-oci-full.yaml"}
EXPECTED_PROFILES = ONPREM_DATABASE | ONPREM_MIDDLEWARE | OCI_PROFILES | HYBRID_PROFILES

OCI_SERVICE_SUBSETS = {
    "oci/full-stack.yaml": "all",
    "oci/identity-governance.yaml": {
        "iam",
        "cloud_guard",
        "security_zones",
        "vault",
    },
    "oci/database-data-safe.yaml": {
        "data_safe",
        "database",
        "goldengate",
        "mysql",
        "postgresql",
        "nosql",
    },
    "oci/compute-storage-oke.yaml": {
        "compute",
        "block_storage",
        "oke",
        "object_storage",
        "functions",
        "container_instances",
    },
    "oci/network-perimeter.yaml": {
        "networking",
        "waf",
        "network_firewall",
        "load_balancer",
        "bastion",
        "certificates",
        "api_gateway",
    },
    "oci/observability-dr.yaml": {
        "audit",
        "logging",
        "logging_analytics",
        "monitoring",
        "events",
        "notifications",
        "threat_intelligence",
        "disaster_recovery",
    },
    "oci/object-storage.yaml": {"object_storage"},
}

SECRET_KEY_PATTERN = re.compile(
    r"(?:^|_)(?:password|passwd|secret|token|api_key|private_key|authorization)$",
    re.IGNORECASE,
)
SAFE_RUN_NAME = re.compile(r"^[a-z0-9][a-z0-9._-]*$")


def _raw(path: str) -> dict[str, Any]:
    value = yaml.safe_load((CONFIG_ROOT / path).read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def _enabled(raw: dict[str, Any], section: str) -> bool:
    value = raw.get(section, {})
    assert isinstance(value, dict)
    return value.get("enabled") is True


def _assert_no_secret_values(value: Any, location: str = "config") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            normalized = str(key).lower().replace("-", "_")
            if SECRET_KEY_PATTERN.search(normalized):
                assert child in (None, "", False), f"secret material at {location}.{key}"
            _assert_no_secret_values(child, f"{location}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _assert_no_secret_values(child, f"{location}[{index}]")
    elif isinstance(value, str):
        assert "-----BEGIN " not in value
        assert not re.search(r"(?i)(?:password|passwd|secret|token)\s*=", value)


def test_complete_approved_yaml_tree_exists_without_extra_profiles():
    actual = {
        path.relative_to(CONFIG_ROOT).as_posix()
        for path in CONFIG_ROOT.rglob("*.yaml")
    }

    assert actual == EXPECTED_PROFILES


@pytest.mark.parametrize("relative_path", sorted(EXPECTED_PROFILES))
def test_every_profile_loads_through_production_parser(relative_path):
    config = load_config(CONFIG_ROOT / relative_path)

    assert config.run.name


def test_run_names_are_unique_and_safe():
    names = [load_config(CONFIG_ROOT / path).run.name for path in sorted(EXPECTED_PROFILES)]

    assert len(names) == len(set(names))
    assert all(SAFE_RUN_NAME.fullmatch(name) for name in names)


@pytest.mark.parametrize("relative_path", sorted(EXPECTED_PROFILES))
def test_profiles_contain_no_secret_material_and_have_replacement_markers(relative_path):
    raw = _raw(relative_path)
    text = (CONFIG_ROOT / relative_path).read_text(encoding="utf-8")

    _assert_no_secret_values(raw)
    assert "replace" in text.lower()


@pytest.mark.parametrize("relative_path", sorted(ONPREM_DATABASE))
def test_database_profiles_enable_only_onprem_database(relative_path):
    raw = _raw(relative_path)

    assert _enabled(raw, "onprem_db")
    assert not _enabled(raw, "onprem_middleware")
    assert not _enabled(raw, "oci")
    assert raw["run"]["offline_only"] is True


def test_database_profiles_select_the_documented_collectors():
    dbsat = _raw("onprem/database/dbsat-only.yaml")["onprem_db"]
    direct = _raw("onprem/database/direct-sql-only.yaml")["onprem_db"]
    combined = _raw("onprem/database/database-full.yaml")["onprem_db"]

    assert dbsat["dbsat"]["targets"] and dbsat["direct_sql"]["enabled"] is False
    assert dbsat["direct_sql"]["targets"] == []
    assert direct["dbsat"]["targets"] == [] and direct["direct_sql"]["enabled"] is True
    assert direct["direct_sql"]["targets"]
    assert combined["dbsat"]["targets"] and combined["direct_sql"]["enabled"] is True
    assert combined["direct_sql"]["targets"]


@pytest.mark.parametrize("relative_path", sorted(ONPREM_MIDDLEWARE))
def test_middleware_profiles_enable_only_onprem_middleware(relative_path):
    raw = _raw(relative_path)

    assert not _enabled(raw, "onprem_db")
    assert _enabled(raw, "onprem_middleware")
    assert not _enabled(raw, "oci")
    assert raw["run"]["offline_only"] is True


@pytest.mark.parametrize("kind", ["weblogic", "ohs", "oam", "oaa", "webgate", "oag", "avdf"])
def test_single_middleware_profiles_have_one_read_only_export_target(kind):
    raw = _raw(f"onprem/middleware/{kind}.yaml")
    targets = raw["onprem_middleware"]["targets"]

    assert len(targets) == 1
    assert targets[0]["type"] == kind
    assert targets[0]["read_config_only"] is True
    assert targets[0]["config_path"].endswith(".json")
    assert "replace" in targets[0]["config_path"].lower()


def test_combined_middleware_profile_has_every_read_only_export_target():
    raw = _raw("onprem/middleware/middleware-full.yaml")
    targets = raw["onprem_middleware"]["targets"]

    assert {target["type"] for target in targets} == {
        "weblogic",
        "ohs",
        "oam",
        "oaa",
        "webgate",
        "oag",
        "avdf",
    }
    assert all(target["read_config_only"] is True for target in targets)
    assert all(target["config_path"].endswith(".json") for target in targets)


@pytest.mark.parametrize("relative_path", sorted(OCI_PROFILES))
def test_oci_profiles_enable_only_oci_with_the_documented_service_subset(relative_path):
    raw = _raw(relative_path)
    config = load_config(CONFIG_ROOT / relative_path)

    assert not _enabled(raw, "onprem_db")
    assert not _enabled(raw, "onprem_middleware")
    assert config.oci.enabled is True
    expected = OCI_SERVICE_SUBSETS[relative_path]
    if expected == "all":
        assert config.oci.services == "all"
    else:
        assert set(config.oci.services) == expected


def test_hybrid_profile_enables_all_three_stack_sections():
    relative_path = "hybrid/onprem-oci-full.yaml"
    raw = _raw(relative_path)
    config = load_config(CONFIG_ROOT / relative_path)

    assert _enabled(raw, "onprem_db")
    assert _enabled(raw, "onprem_middleware")
    assert config.oci.enabled is True
    assert config.oci.services == "all"
