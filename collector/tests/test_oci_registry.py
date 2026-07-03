from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json

from oracle_collector.collectors.oci.auth import CLIENT_PATHS
from oracle_collector.collectors.oci.registry import (
    SERVICE_COLLECTORS,
    collect_registered_service,
    collect_service_across_compartments,
)
from oracle_collector.collectors.oci.traversal import paginate, resolve_compartments


REQUIRED_SERVICES = {
    "iam",
    "cloud_guard",
    "security_zones",
    "vault",
    "data_safe",
    "database",
    "goldengate",
    "mysql",
    "postgresql",
    "nosql",
    "compute",
    "block_storage",
    "oke",
    "object_storage",
    "functions",
    "container_instances",
    "networking",
    "waf",
    "network_firewall",
    "load_balancer",
    "bastion",
    "certificates",
    "api_gateway",
    "audit",
    "logging",
    "logging_analytics",
    "monitoring",
    "events",
    "notifications",
    "threat_intelligence",
    "disaster_recovery",
}


@dataclass
class Data:
    items: list[dict[str, str]]


@dataclass
class Response:
    data: Data
    headers: dict[str, str]


def test_registry_covers_every_service_family_in_spec() -> None:
    assert REQUIRED_SERVICES.issubset(SERVICE_COLLECTORS)


def test_paginate_follows_opc_next_page() -> None:
    calls: list[str | None] = []

    def list_resources(page: str | None = None) -> Response:
        calls.append(page)
        if page is None:
            return Response(Data([{"id": "one"}]), {"opc-next-page": "page-2"})
        return Response(Data([{"id": "two"}]), {})

    assert paginate(list_resources) == [{"id": "one"}, {"id": "two"}]
    assert calls == [None, "page-2"]


def test_unsupported_service_is_skipped_not_fatal() -> None:
    result = collect_registered_service("not-real", object(), "ocid.compartment", "sa-santiago-1")
    assert result.exit_code == 2
    assert result.services_skipped[0]["service"] == "not-real"


def test_compartment_traversal_accepts_sdk_objects_and_dicts() -> None:
    class Identity:
        def list_compartments(self, **_: object) -> Response:
            return Response(Data([{"id": "ocid.compartment.dict"}]), {})

    assert resolve_compartments(Identity(), "ocid.tenancy", "all") == [
        "ocid.tenancy",
        "ocid.compartment.dict",
    ]


def test_object_storage_supplies_namespace_and_aggregates_compartments() -> None:
    class Namespace:
        data = "tenant-namespace"

    class ObjectStorage:
        def get_namespace(self, **_: object) -> Namespace:
            return Namespace()

        def list_buckets(self, *, namespace_name: str, compartment_id: str, page: str | None = None) -> Response:
            assert namespace_name == "tenant-namespace"
            return Response(
                Data(
                    [
                        {
                            "id": f"bucket-{compartment_id}",
                            "name": "exports",
                            "public_access_type": "ObjectRead",
                        }
                    ]
                ),
                {},
            )

    result = collect_service_across_compartments(
        "object_storage",
        ObjectStorage(),
        ["compartment-a", "compartment-b"],
        "sa-santiago-1",
    )

    assert len(result.evidence) == 2
    assert len({record.id for record in result.evidence}) == 2
    assert all(record.signal == "misconfigured" for record in result.evidence)
    assert len(result.raw_files["oci/object_storage/sa-santiago-1.json"]) == 2


def test_service_collects_every_supported_read_operation() -> None:
    class Identity:
        def list_users(self, **_: object) -> Response:
            return Response(Data([{"id": "user-1", "name": "alice", "is_mfa_activated": False}]), {})

        def list_groups(self, **_: object) -> Response:
            return Response(Data([{"id": "group-1", "name": "admins"}]), {})

        def list_policies(self, **_: object) -> Response:
            return Response(
                Data([{"id": "policy-1", "name": "writers", "statements": ["Allow group writers to manage all-resources in tenancy"]}]),
                {},
            )

    result = collect_registered_service("iam", Identity(), "ocid.tenancy", "sa-santiago-1")

    assert {item["id"] for item in result.inventory} == {"user-1", "group-1", "policy-1"}
    assert any("permisos de escritura" in warning for warning in result.warnings)
    by_resource = {record.resource: record for record in result.evidence}
    assert by_resource["alice"].attribute == "mfa_state"
    assert by_resource["alice"].signal == "absent"
    assert by_resource["writers"].attribute == "iam_policy"


def test_sdk_datetime_values_are_json_serializable() -> None:
    class Compute:
        def list_instances(self, **_: object) -> Response:
            return Response(
                Data([{"id": "instance-1", "display_name": "app", "time_created": datetime(2026, 7, 3, tzinfo=timezone.utc)}]),
                {},
            )

    result = collect_registered_service("compute", Compute(), "compartment", "sa-santiago-1")
    json.dumps(result.raw_files)
    assert result.evidence[0].value["time_created"] == "2026-07-03T00:00:00+00:00"
    assert result.evidence[0].signal == "unknown"


def test_functions_traverses_applications_before_functions() -> None:
    class Functions:
        def list_applications(self, *, compartment_id: str, page: str | None = None) -> Response:
            return Response(Data([{"id": f"app-{compartment_id}", "display_name": "payments"}]), {})

        def list_functions(self, *, application_id: str, page: str | None = None) -> Response:
            return Response(Data([{"id": "fn-1", "display_name": "redact", "application_id": application_id}]), {})

    result = collect_registered_service("functions", Functions(), "compartment", "sa-santiago-1")
    assert {item["id"] for item in result.inventory} == {"app-compartment", "fn-1"}
    assert result.errors == []
    assert result.services_scanned == ["functions"]


def test_boot_volumes_receive_each_availability_domain() -> None:
    class BlockStorage:
        def list_volumes(self, *, compartment_id: str, page: str | None = None) -> Response:
            return Response(Data([{"id": "volume-1"}]), {})

        def list_boot_volumes(
            self,
            *,
            availability_domain: str,
            compartment_id: str,
            page: str | None = None,
        ) -> Response:
            return Response(Data([{"id": f"boot-{availability_domain}"}]), {})

    result = collect_registered_service(
        "block_storage",
        BlockStorage(),
        "compartment",
        "sa-santiago-1",
        context={"availability_domains": ["AD-1", "AD-2"]},
    )
    assert {item["id"] for item in result.inventory} == {"volume-1", "boot-AD-1", "boot-AD-2"}
    assert result.errors == []


def test_logging_analytics_resolves_namespace_before_entities() -> None:
    class LogAnalytics:
        def list_namespaces(self, *, compartment_id: str, page: str | None = None) -> Response:
            return Response(Data([{"namespace_name": "tenant_ns"}]), {})

        def list_log_analytics_entities(
            self,
            namespace_name: str,
            compartment_id: str,
            *,
            page: str | None = None,
        ) -> Response:
            assert namespace_name == "tenant_ns"
            return Response(Data([{"id": "entity-1", "name": "db-host"}]), {})

    result = collect_registered_service("logging_analytics", LogAnalytics(), "compartment", "sa-santiago-1")
    assert {item["id"] for item in result.inventory} == {"entity-1"}
    assert result.errors == []


def test_total_operation_failure_is_not_reported_as_scanned() -> None:
    class BrokenCompute:
        def list_instances(self, *, compartment_id: str, page: str | None = None) -> Response:
            raise PermissionError("denied")

    result = collect_registered_service("compute", BrokenCompute(), "compartment", "sa-santiago-1")
    assert result.services_scanned == []
    assert result.services_skipped == [{"service": "compute", "reason": "all supported operations failed"}]
    assert result.exit_code == 2


def test_notifications_uses_control_plane_client() -> None:
    assert CLIENT_PATHS["notifications"] == "ons.NotificationControlPlaneClient"
