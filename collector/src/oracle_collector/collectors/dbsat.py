"""Read-only Oracle Database Security Assessment Tool integration."""

from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence, Union

from oracle_collector.models import EvidenceRecord


JsonSource = Union[Path, str, Mapping[str, Any]]


class UnsafeDBSATTargetError(ValueError):
    """Raised when a DBSAT target could expose a secret or elevated session."""


_CATEGORY_CONTROLS = {
    "encrypt": ["sec-rest"],
    "tde": ["sec-rest"],
    "redact": ["data-pseudonym"],
    "mask": ["data-pseudonym"],
    "vault": ["sec-tenant"],
    "label security": ["sec-tenant"],
    "audit": ["sec-logs", "gov-auditoria"],
    "privilege": ["sec-tenant"],
    "user": ["sec-tenant"],
    "auth": ["sec-passwords"],
    "password": ["sec-passwords"],
    "patch": ["sec-monitoring"],
    "version": ["sec-monitoring"],
    "network": ["sec-tls"],
    "tls": ["sec-tls"],
    "stig": ["sec-monitoring"],
    "cis": ["sec-monitoring"],
}

_CATEGORY_REMEDIATIONS = {
    "encrypt": "Oracle Advanced Security (TDE)",
    "tde": "Oracle Advanced Security (TDE)",
    "redact": "Oracle Data Redaction",
    "mask": "Oracle Data Masking & Subsetting",
    "vault": "Oracle Database Vault",
    "label security": "Oracle Label Security",
    "audit": "Oracle Audit Vault & Database Firewall",
}

_PRESENT_STATUSES = {"pass", "passed", "enabled", "present", "compliant", "success", "ok"}
_ABSENT_STATUSES = {"absent", "disabled", "not installed", "not_applicable", "n/a"}
_MISCONFIGURED_STATUSES = {"fail", "failed", "warning", "finding", "risk", "non-compliant"}


def _safe_id(value: object) -> str:
    return re.sub(r"[^a-zA-Z0-9_.-]+", "-", str(value)).strip("-") or "unknown"


def _controls_for(finding: Mapping[str, Any]) -> list[str]:
    text = " ".join(
        str(finding.get(key, "")) for key in ("id", "category", "section", "title", "description")
    ).lower()
    controls: list[str] = []
    for marker, candidates in _CATEGORY_CONTROLS.items():
        if marker in text:
            controls.extend(candidates)
    return list(dict.fromkeys(controls)) or ["sec-monitoring"]


def _remediations_for(finding: Mapping[str, Any]) -> list[dict[str, str]]:
    text = " ".join(
        str(finding.get(key, "")) for key in ("id", "category", "section", "title", "description")
    ).lower()
    remediations = []
    for marker, product in _CATEGORY_REMEDIATIONS.items():
        if marker in text and product not in {item["product"] for item in remediations}:
            remediations.append(
                {"product": product, "deployment": "onprem", "applies": "candidate"}
            )
    return remediations


def _signal_for(status: object) -> str:
    normalized = str(status or "").strip().lower()
    if normalized in _PRESENT_STATUSES:
        return "present"
    if normalized in _ABSENT_STATUSES:
        return "absent"
    if normalized in _MISCONFIGURED_STATUSES:
        return "misconfigured"
    return "unknown"


def _load_document(source: JsonSource) -> tuple[Mapping[str, Any], str]:
    if isinstance(source, Mapping):
        return source, "report.json"
    path = Path(source)
    document = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(document, Mapping):
        raise ValueError("DBSAT JSON root must be an object")
    return document, path.name


def _findings(document: Mapping[str, Any]) -> list[tuple[Mapping[str, Any], str]]:
    findings = document.get("findings", [])
    if isinstance(findings, list):
        return [
            (finding, f"#/findings/{index}")
            for index, finding in enumerate(findings)
            if isinstance(finding, Mapping)
        ]

    # Some DBSAT exports group findings into named sections.
    if isinstance(findings, Mapping):
        grouped: list[tuple[Mapping[str, Any], str]] = []
        for section, values in findings.items():
            if isinstance(values, list):
                grouped.extend(
                    (finding, f"#/findings/{section}/{index}")
                    for index, finding in enumerate(values)
                    if isinstance(finding, Mapping)
                )
            elif isinstance(values, Mapping):
                grouped.append((values, f"#/findings/{section}"))
        return grouped
    return []


def parse_dbsat_json(source: JsonSource, *, alias: str) -> list[EvidenceRecord]:
    """Convert a DBSAT 4 JSON report into neutral technical evidence."""

    document, report_name = _load_document(source)
    records: list[EvidenceRecord] = []
    for index, (finding, pointer) in enumerate(_findings(document)):
        finding_id = finding.get("id") or finding.get("rule_id") or f"finding-{index + 1}"
        details = finding.get("details")
        value = dict(details) if isinstance(details, Mapping) else {
            key: value
            for key, value in finding.items()
            if key not in {"status", "result", "outcome"}
        }
        records.append(
            EvidenceRecord(
                id=f"dbsat-{_safe_id(alias)}-{_safe_id(finding_id)}",
                layer="database",
                resource=alias,
                attribute=f"dbsat:{finding_id}",
                value=value,
                signal=_signal_for(
                    finding.get("status") or finding.get("result") or finding.get("outcome")
                ),
                control_ids=_controls_for(finding),
                law_refs=["Art. 14 quinquies"],
                remediation_candidates=_remediations_for(finding),
                source={
                    "collector": "dbsat",
                    "ref": f"raw/dbsat/{report_name}{pointer}",
                },
                confidence="high",
            )
        )
    return records


def _validate_target(target: Mapping[str, Any]) -> None:
    connect = str(target.get("connect", ""))
    if not connect:
        raise UnsafeDBSATTargetError("DBSAT target requires a connect identifier")
    before_at = connect.split("@", 1)[0]
    if "/" in before_at or ":" in before_at:
        raise UnsafeDBSATTargetError("DBSAT connect identifier must not embed a password")
    lowered = connect.lower()
    if "password=" in lowered or "pwd=" in lowered:
        raise UnsafeDBSATTargetError("DBSAT connect identifier must not embed a password")
    if re.search(r"\bas\s+sys(?:dba|oper|asm|backup|dg|km)\b", lowered):
        raise UnsafeDBSATTargetError("Privileged DBSAT sessions are not allowed")
    if before_at.strip().upper() in {"SYS", "SYSTEM"}:
        raise UnsafeDBSATTargetError("SYS and SYSTEM DBSAT sessions are not allowed")


def build_dbsat_commands(
    binary: Union[str, Path], target: Mapping[str, Any], work_prefix: Path
) -> tuple[list[str], list[str]]:
    """Build fixed argument-vector commands without secrets or shell syntax."""

    _validate_target(target)
    binary_path = str(binary)
    prefix = str(work_prefix)
    connect = str(target["connect"])
    return (
        [binary_path, "collect", "-n", connect, prefix],
        [binary_path, "report", "-f", "json", prefix],
    )


def invoke_dbsat(
    binary: Union[str, Path],
    target: Mapping[str, Any],
    output_dir: Union[str, Path],
    *,
    runner: Callable[..., Any] = subprocess.run,
) -> Path:
    """Run DBSAT with argument arrays and return the expected raw report path."""

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    alias = _safe_id(target.get("alias", "database"))
    prefix = output_path / alias
    collect_command, report_command = build_dbsat_commands(binary, target, prefix)
    environment = os.environ.copy()
    if target.get("wallet"):
        environment["TNS_ADMIN"] = str(target["wallet"])
    for command in (collect_command, report_command):
        runner(
            command,
            shell=False,
            check=True,
            capture_output=True,
            text=True,
            env=environment,
        )
    preferred = output_path / f"{alias}.report.json"
    candidates = (preferred, output_path / f"{alias}_report.json", output_path / f"{alias}.json")
    return next((candidate for candidate in candidates if candidate.is_file()), preferred)


class DBSATCollector:
    """Collect from an existing DBSAT report or invoke DBSAT read-only."""

    def __init__(self, runner: Callable[..., Any] = subprocess.run) -> None:
        self._runner = runner

    def collect(
        self,
        target: Mapping[str, Any],
        *,
        binary: Union[str, Path, None] = None,
        raw_dir: Union[str, Path, None] = None,
    ) -> list[EvidenceRecord]:
        alias = str(target.get("alias", "database"))
        report_path = target.get("report_path")
        if report_path is None:
            if binary is None or raw_dir is None:
                raise ValueError("DBSAT invocation requires binary and raw_dir")
            report_path = invoke_dbsat(binary, target, raw_dir, runner=self._runner)
        return parse_dbsat_json(report_path, alias=alias)
