"""Read exported Oracle middleware configuration without endpoint mutation."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Mapping, Sequence

from oracle_collector.models import EvidenceRecord


class UnsafeMiddlewareTargetError(ValueError):
    """Raised when middleware input is not demonstrably read-only."""


SUPPORTED_TYPES = {"weblogic", "ohs", "oam", "oaa", "webgate", "oag", "avdf"}

_ATTRIBUTE_CONTROLS: dict[str, list[str]] = {
    "tls_enabled": ["sec-tls"],
    "tls_minimum_protocol": ["sec-tls"],
    "tls_ciphers": ["sec-tls"],
    "listeners": ["sec-tls"],
    "node_manager_secure_listener": ["sec-tls"],
    "password_policy": ["sec-secrets"],
    "mfa_enabled": ["sec-mfa"],
    "strong_authentication": ["sec-mfa"],
    "fido_enabled": ["sec-mfa"],
    "access_policies": ["sec-tenant"],
    "edge_authentication": ["sec-tenant"],
    "throttling_enabled": ["sec-monitoring"],
    "monitored_databases": ["sec-logs"],
    "sql_firewall_enabled": ["sec-monitoring", "inc-brechas"],
    "blocking_enabled": ["sec-monitoring", "inc-brechas"],
}


def _safe_id(value: object) -> str:
    return re.sub(r"[^a-zA-Z0-9_.-]+", "-", str(value)).strip("-") or "unknown"


def _load_data(target: Mapping[str, Any]) -> tuple[Mapping[str, Any], str]:
    injected = target.get("data")
    if isinstance(injected, Mapping):
        return injected, "injected"

    configured_path = target.get("config_path") or target.get("config_dir")
    if configured_path is None:
        raise UnsafeMiddlewareTargetError(
            "Middleware collection requires injected data or an exported config path"
        )
    path = Path(configured_path)
    if path.is_dir():
        kind = str(target.get("type", "middleware")).lower()
        candidates = [path / f"{kind}.json", path / "config.json"]
        candidates.extend(sorted(path.glob("*.json")))
        path = next((candidate for candidate in candidates if candidate.is_file()), path)
    if not path.is_file():
        raise UnsafeMiddlewareTargetError(f"Exported config does not exist: {path}")
    if path.suffix.lower() != ".json":
        raise UnsafeMiddlewareTargetError("Only exported JSON middleware configuration is supported")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise ValueError("Middleware configuration root must be an object")
    return payload, str(path)


def _extract(kind: str, data: Mapping[str, Any]) -> dict[str, Any]:
    extracted: dict[str, Any] = {}
    if kind in {"weblogic", "ohs"}:
        ssl = data.get("ssl", {})
        if isinstance(ssl, Mapping):
            extracted.update(
                {
                    "tls_enabled": ssl.get("enabled"),
                    "tls_minimum_protocol": ssl.get("minimum_protocol"),
                    "tls_ciphers": ssl.get("ciphers"),
                }
            )
        if kind == "weblogic":
            node_manager = data.get("node_manager", {})
            extracted["listeners"] = data.get("listeners")
            extracted["node_manager_secure_listener"] = (
                node_manager.get("secure_listener")
                if isinstance(node_manager, Mapping)
                else None
            )
            extracted["password_policy"] = data.get("password_policy")
    if kind in {"oam", "oaa", "webgate"}:
        for name in ("mfa_enabled", "strong_authentication", "fido_enabled", "access_policies"):
            if name in data:
                extracted[name] = data[name]
    if kind == "oag":
        for name in ("edge_authentication", "throttling_enabled"):
            if name in data:
                extracted[name] = data[name]
    if kind == "avdf":
        for name in ("monitored_databases", "sql_firewall_enabled", "blocking_enabled"):
            if name in data:
                extracted[name] = data[name]
    return {name: value for name, value in extracted.items() if value is not None}


def _signal(value: Any) -> str:
    if value is None:
        return "unknown"
    if isinstance(value, bool):
        return "present" if value else "absent"
    if isinstance(value, (list, tuple, set, Mapping)):
        return "present" if len(value) else "absent"
    if isinstance(value, (int, float)):
        return "present" if value > 0 else "absent"
    return "present" if str(value).strip() else "absent"


class MiddlewareCollector:
    """Normalize known security settings from read-only middleware exports."""

    def collect(self, targets: Sequence[Mapping[str, Any]]) -> list[EvidenceRecord]:
        records: list[EvidenceRecord] = []
        for target in targets:
            kind = str(target.get("type", "")).lower()
            if kind not in SUPPORTED_TYPES:
                raise ValueError(f"Unsupported middleware type: {kind}")
            if target.get("read_config_only") is not True:
                raise UnsafeMiddlewareTargetError("read_config_only=true is required")
            data, source_ref = _load_data(target)
            resource = str(target.get("name") or data.get("name") or f"{kind}-target")
            for attribute, value in _extract(kind, data).items():
                records.append(
                    EvidenceRecord(
                        id=f"middleware-{_safe_id(resource)}-{attribute}",
                        layer="middleware",
                        resource=resource,
                        attribute=attribute,
                        value={"observed": value},
                        signal=_signal(value),
                        control_ids=_ATTRIBUTE_CONTROLS[attribute],
                        law_refs=["Art. 14 quinquies"],
                        remediation_candidates=[],
                        source={
                            "collector": "middleware",
                            "ref": f"{source_ref}#/{attribute}",
                            "product": kind,
                        },
                        confidence="high" if source_ref != "injected" else "medium",
                    )
                )
        return records
