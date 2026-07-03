from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Iterable

from ...models import CollectorResult, EvidenceRecord
from ..base import as_mapping, evidence_id
from . import compute, database, identity_governance, network, observability
from .traversal import paginate


@dataclass(frozen=True)
class ServiceSpec:
    layer: str
    list_operations: tuple[str, ...]
    attribute: str
    control_ids: tuple[str, ...]


def _definitions() -> dict[str, ServiceSpec]:
    definitions: dict[str, ServiceSpec] = {}
    for module in (identity_governance, database, compute, network, observability):
        for name, (layer, operations, attribute, controls) in module.SERVICE_DEFINITIONS.items():
            definitions[name] = ServiceSpec(layer, tuple(operations), attribute, tuple(controls))
    return definitions


SERVICE_COLLECTORS = _definitions()


def _resource_name(item: dict[str, Any]) -> str:
    return str(item.get("display_name") or item.get("name") or item.get("id") or "unknown")


def _signal(spec: ServiceSpec, item: dict[str, Any]) -> str:
    if spec.attribute == "public_access":
        public = item.get("is_public") is True or str(item.get("public_access_type", "")).lower() not in {
            "",
            "no_public_access",
            "private",
        }
        return "misconfigured" if public else "present"
    operation = str(item.get("_collector_operation", ""))
    if operation == "list_users":
        mfa = item.get("is_mfa_activated")
        return "present" if mfa is True else "absent" if mfa is False else "unknown"
    presence_operations = {
        "list_policies",
        "list_targets",
        "list_security_zones",
        "list_vaults",
        "list_registered_databases",
        "list_deployments",
        "list_applications",
        "list_functions",
        "list_web_app_firewalls",
        "list_web_app_firewall_policies",
        "list_network_firewalls",
        "list_bastions",
        "list_log_groups",
        "list_log_analytics_entities",
        "list_alarms",
        "list_rules",
        "list_topics",
        "list_indicators",
        "list_dr_protection_groups",
    }
    return "present" if operation in presence_operations else "unknown"


OPERATION_ATTRIBUTES = {
    "list_users": "mfa_state",
    "list_groups": "iam_group",
    "list_policies": "iam_policy",
    "list_applications": "function_application",
    "list_functions": "function_security",
    "list_volumes": "volume_encryption",
    "list_boot_volumes": "boot_volume_encryption",
    "list_log_analytics_entities": "logging_analytics",
}


def _record_error(result: CollectorResult, name: str, operation: str, region: str, exc: Exception) -> None:
    result.errors.append(
        {
            "collector": f"oci.{name}.{operation}",
            "region": region,
            "error": type(exc).__name__,
            "fatal": False,
        }
    )


def collect_registered_service(
    name: str,
    client: Any,
    compartment_id: str,
    region: str,
    *,
    context: dict[str, Any] | None = None,
) -> CollectorResult:
    spec = SERVICE_COLLECTORS.get(name)
    if spec is None:
        return CollectorResult(
            services_skipped=[{"service": name, "reason": "unsupported service"}],
        )
    context = context or {}
    operation_names = [op for op in spec.list_operations if hasattr(client, op)]
    if not operation_names:
        return CollectorResult(
            services_skipped=[{"service": name, "reason": "SDK client exposes no supported list operation"}],
        )
    result = CollectorResult()
    raw_path = f"oci/{name}/{region}.json"
    mapped: list[dict[str, Any]] = []
    successful_operations = 0

    def collect_operation(operation_name: str, **kwargs: Any) -> list[dict[str, Any]]:
        nonlocal successful_operations
        operation = getattr(client, operation_name)
        try:
            resources = paginate(operation, **kwargs)
        except Exception as exc:
            _record_error(result, name, operation_name, region, exc)
            return []
        successful_operations += 1
        normalized: list[dict[str, Any]] = []
        for resource in resources:
            item = as_mapping(resource)
            item.setdefault("_collector_operation", operation_name)
            normalized.append(item)
        return normalized

    if name == "functions":
        applications = collect_operation("list_applications", compartment_id=compartment_id)
        mapped.extend(applications)
        for application in applications:
            application_id = application.get("id")
            if application_id:
                mapped.extend(collect_operation("list_functions", application_id=str(application_id)))
    elif name == "block_storage":
        if "list_volumes" in operation_names:
            mapped.extend(collect_operation("list_volumes", compartment_id=compartment_id))
        if "list_boot_volumes" in operation_names:
            domains = list(context.get("availability_domains", []))
            if not domains:
                _record_error(result, name, "list_boot_volumes", region, ValueError("availability domains unavailable"))
            for domain in domains:
                mapped.extend(
                    collect_operation(
                        "list_boot_volumes",
                        compartment_id=compartment_id,
                        availability_domain=domain,
                    )
                )
    elif name == "logging_analytics":
        if not hasattr(client, "list_namespaces"):
            _record_error(result, name, "list_namespaces", region, AttributeError("list_namespaces unavailable"))
        else:
            namespaces = collect_operation("list_namespaces", compartment_id=compartment_id)
            for namespace in namespaces:
                namespace_name = namespace.get("namespace_name") or namespace.get("namespaceName") or namespace.get("name")
                if namespace_name:
                    mapped.extend(
                        collect_operation(
                            "list_log_analytics_entities",
                            namespace_name=str(namespace_name),
                            compartment_id=compartment_id,
                        )
                    )
    else:
        for operation_name in operation_names:
            kwargs: dict[str, Any] = {"compartment_id": compartment_id}
            if name == "object_storage":
                namespace = client.get_namespace(compartment_id=compartment_id).data
                kwargs["namespace_name"] = namespace
            elif name == "audit" and operation_name == "list_events":
                kwargs["start_time"] = datetime.now(timezone.utc) - timedelta(days=30)
                kwargs["end_time"] = datetime.now(timezone.utc)
            mapped.extend(collect_operation(operation_name, **kwargs))

    if successful_operations:
        result.services_scanned.append(name)
    else:
        result.services_skipped.append({"service": name, "reason": "all supported operations failed"})
    result.raw_files[raw_path] = mapped
    for item in mapped:
        resource = _resource_name(item)
        result.inventory.append(
            {
                "id": item.get("id", resource),
                "layer": spec.layer,
                "type": name,
                "region": region,
                "compartment": compartment_id,
                "name": resource,
            }
        )
        result.evidence.append(
            EvidenceRecord(
                id=evidence_id(f"oci.{name}", f"{region}:{compartment_id}:{resource}", spec.attribute),
                layer=spec.layer,
                resource=resource,
                attribute=OPERATION_ATTRIBUTES.get(str(item.get("_collector_operation", "")), spec.attribute),
                value=item,
                signal=_signal(spec, item),
                control_ids=list(spec.control_ids),
                source={"collector": f"oci.{name}", "ref": f"raw/{raw_path}"},
                confidence="medium",
            )
        )
        if name == "iam":
            statements = item.get("statements", [])
            if isinstance(statements, list) and any(
                any(verb in str(statement).lower().split() for verb in ("manage", "use"))
                for statement in statements
            ):
                result.warnings.append(
                    f"IAM policy {resource!r} concede permisos de escritura; el colector no los usó"
                )
    return result


def collect_service_across_compartments(
    name: str,
    client: Any,
    compartments: Iterable[str],
    region: str,
    *,
    context_by_compartment: dict[str, dict[str, Any]] | None = None,
) -> CollectorResult:
    aggregate = CollectorResult()
    raw_path = f"oci/{name}/{region}.json"
    combined_raw: list[Any] = []
    context_by_compartment = context_by_compartment or {}
    for compartment_id in compartments:
        partial = collect_registered_service(
            name,
            client,
            compartment_id,
            region,
            context=context_by_compartment.get(compartment_id, {}),
        )
        raw = partial.raw_files.pop(raw_path, [])
        if isinstance(raw, list):
            combined_raw.extend(raw)
        elif raw:
            combined_raw.append(raw)
        aggregate.merge(partial)
    if combined_raw:
        aggregate.raw_files[raw_path] = combined_raw
    return aggregate
