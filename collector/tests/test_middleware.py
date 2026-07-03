from pathlib import Path

import pytest

from oracle_collector.collectors.middleware import (
    MiddlewareCollector,
    UnsafeMiddlewareTargetError,
)


FIXTURES = Path(__file__).parent / "fixtures" / "onprem"


def test_reads_exported_weblogic_json_and_maps_security_signals():
    records = MiddlewareCollector().collect(
        [
            {
                "type": "weblogic",
                "name": "payments-domain",
                "read_config_only": True,
                "config_path": FIXTURES / "middleware-weblogic.json",
            }
        ]
    )

    attributes = {record.attribute: record for record in records}
    assert attributes["tls_enabled"].signal == "present"
    assert attributes["tls_enabled"].control_ids == ["sec-tls"]
    assert attributes["node_manager_secure_listener"].signal == "present"
    assert attributes["password_policy"].control_ids == ["sec-secrets"]
    assert all(record.source["collector"] == "middleware" for record in records)


@pytest.mark.parametrize(
    ("kind", "data", "expected_attribute", "expected_control"),
    [
        ("oam", {"mfa_enabled": True, "fido_enabled": True}, "mfa_enabled", "sec-mfa"),
        ("oaa", {"strong_authentication": True}, "strong_authentication", "sec-mfa"),
        ("webgate", {"fido_enabled": True}, "fido_enabled", "sec-mfa"),
        ("oag", {"edge_authentication": True, "throttling_enabled": True}, "edge_authentication", "sec-tenant"),
        ("avdf", {"monitored_databases": 4, "sql_firewall_enabled": True}, "sql_firewall_enabled", "sec-monitoring"),
        ("ohs", {"ssl": {"enabled": True, "minimum_protocol": "TLSv1.2"}}, "tls_enabled", "sec-tls"),
    ],
)
def test_supported_middleware_types_consume_injected_read_only_data(
    kind, data, expected_attribute, expected_control
):
    records = MiddlewareCollector().collect(
        [{"type": kind, "name": f"{kind}-1", "read_config_only": True, "data": data}]
    )

    by_attribute = {record.attribute: record for record in records}
    assert expected_attribute in by_attribute
    assert expected_control in by_attribute[expected_attribute].control_ids


def test_endpoint_only_target_is_rejected_instead_of_calling_network():
    target = {
        "type": "weblogic",
        "name": "domain",
        "admin_url": "t3s://middleware.example:7002",
        "read_config_only": True,
    }

    with pytest.raises(UnsafeMiddlewareTargetError, match="exported config"):
        MiddlewareCollector().collect([target])


def test_mutating_mode_and_unknown_types_are_rejected():
    collector = MiddlewareCollector()

    with pytest.raises(UnsafeMiddlewareTargetError, match="read_config_only"):
        collector.collect([{"type": "weblogic", "read_config_only": False, "data": {}}])

    with pytest.raises(ValueError, match="Unsupported middleware type"):
        collector.collect([{"type": "unknown", "read_config_only": True, "data": {}}])
