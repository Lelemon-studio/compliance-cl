"""Strictly allowlisted read-only Oracle catalog collection."""

from __future__ import annotations

import re
from typing import Any, Callable, Mapping, Optional

from oracle_collector.models import EvidenceRecord


class UnsafeDatabaseSessionError(ValueError):
    """Raised when target metadata indicates an elevated/data session."""


ALLOWED_CATALOG_QUERIES: dict[str, str] = {
    "encryption_wallet": "SELECT WRL_TYPE, STATUS, WALLET_TYPE FROM V$ENCRYPTION_WALLET",
    "encrypted_tablespaces": "SELECT TS#, ENCRYPTIONALG, STATUS FROM V$ENCRYPTED_TABLESPACES",
    "audit_management": "SELECT PARAMETER_NAME, PARAMETER_VALUE, AUDIT_TRAIL FROM DBA_AUDIT_MGMT_CONFIG_PARAMS",
    "unified_audit_policies": "SELECT POLICY_NAME, ENABLED_OPTION, ENTITY_NAME FROM AUDIT_UNIFIED_POLICIES",
    "rman_backup_jobs": "SELECT SESSION_KEY, STATUS, START_TIME, END_TIME, INPUT_TYPE FROM V$RMAN_BACKUP_JOB_DETAILS",
    "backup_status": "SELECT FILE#, STATUS, CHANGE# FROM V$BACKUP",
    "database_role": "SELECT DATABASE_ROLE, PROTECTION_MODE, OPEN_MODE FROM V$DATABASE",
    "dataguard_config": "SELECT DB_UNIQUE_NAME, PARENT_DBUN, DEST_ROLE FROM V$DATAGUARD_CONFIG",
    "rac_instances": "SELECT INST_ID, INSTANCE_NAME, STATUS FROM GV$INSTANCE",
}

_QUERY_CONTROLS = {
    "encryption_wallet": ["sec-rest"],
    "encrypted_tablespaces": ["sec-rest"],
    "audit_management": ["sec-logs", "gov-auditoria"],
    "unified_audit_policies": ["sec-logs", "gov-auditoria"],
    "rman_backup_jobs": ["sec-backups"],
    "backup_status": ["sec-backups"],
    "database_role": ["sec-backups"],
    "dataguard_config": ["sec-backups"],
    "rac_instances": ["sec-monitoring"],
}

_NORMALIZED_ALLOWLIST = {
    re.sub(r"\s+", " ", statement.strip()).upper() for statement in ALLOWED_CATALOG_QUERIES.values()
}
_FORBIDDEN_SQL = re.compile(
    r"\b(?:INSERT|UPDATE|DELETE|MERGE|ALTER|DROP|CREATE|TRUNCATE|GRANT|REVOKE|EXECUTE|BEGIN|CALL)\b",
    re.IGNORECASE,
)


def validate_catalog_query(statement: str) -> None:
    """Reject every statement that is not byte-equivalent to the audited allowlist."""

    normalized = re.sub(r"\s+", " ", statement.strip()).upper()
    if ";" in normalized or not normalized.startswith("SELECT ") or _FORBIDDEN_SQL.search(normalized):
        raise ValueError("Only one read-only SELECT statement is permitted")
    if normalized not in _NORMALIZED_ALLOWLIST:
        raise ValueError("Query is not in the catalog allowlist")


def _validate_target(target: Mapping[str, Any]) -> None:
    username = str(target.get("username") or target.get("user") or "").strip().upper()
    role = str(target.get("role", "")).strip().upper()
    mode = str(target.get("privilege_mode") or target.get("mode") or "").strip().upper()
    if username in {"SYS", "SYSTEM"}:
        raise UnsafeDatabaseSessionError("SYS and SYSTEM sessions are forbidden")
    if role in {"SYSDBA", "SYSOPER", "SYSASM", "DBA"} or mode in {
        "SYSDBA",
        "SYSOPER",
        "SYSASM",
        "SYSBACKUP",
        "SYSDG",
        "SYSKM",
    }:
        raise UnsafeDatabaseSessionError("Privileged database sessions are forbidden")
    if role.lower() not in {"readonly_monitor", "select_catalog_role"}:
        raise UnsafeDatabaseSessionError("A catalog-only monitoring role is required")
    if any(key in target for key in ("password", "passwd", "pwd", "wallet_password")):
        raise UnsafeDatabaseSessionError("Plaintext database passwords are forbidden")


def _column_name(description: Any, index: int) -> str:
    column = description[index]
    if hasattr(column, "name"):
        return str(column.name).lower()
    return str(column[0]).lower()


class DirectSQLCollector:
    """Run only audited Oracle catalog queries over a non-privileged session."""

    def __init__(
        self, connection_factory: Optional[Callable[[Mapping[str, Any]], Any]] = None
    ) -> None:
        self._connection_factory = connection_factory

    def _connect(self, target: Mapping[str, Any]) -> Any:
        try:
            oracledb = __import__("oracledb")
        except ImportError as error:
            raise RuntimeError(
                "oracledb optional dependency is required for direct SQL collection"
            ) from error
        kwargs = {
            key: target[key]
            for key in ("dsn", "wallet_location", "config_dir")
            if target.get(key) is not None
        }
        kwargs["user"] = target.get("username") or target.get("user")
        return oracledb.connect(**kwargs)

    def collect(self, target: Mapping[str, Any]) -> list[EvidenceRecord]:
        _validate_target(target)
        connection = (
            self._connection_factory(target) if self._connection_factory else self._connect(target)
        )
        cursor = connection.cursor()
        records: list[EvidenceRecord] = []
        alias = str(target.get("alias", "database"))
        try:
            for query_name, statement in ALLOWED_CATALOG_QUERIES.items():
                validate_catalog_query(statement)
                cursor.execute(statement)
                rows = cursor.fetchall()
                description = cursor.description or []
                values = [
                    {
                        _column_name(description, index): value
                        for index, value in enumerate(row)
                    }
                    for row in rows
                ]
                records.append(
                    EvidenceRecord(
                        id=f"direct-sql-{alias}-{query_name}",
                        layer="database",
                        resource=alias,
                        attribute=query_name,
                        value={"rows": values, "row_count": len(values)},
                        signal="present" if values else "absent",
                        control_ids=_QUERY_CONTROLS[query_name],
                        law_refs=["Art. 14 quinquies"],
                        remediation_candidates=[],
                        source={
                            "collector": "direct_sql",
                            "ref": f"catalog:{query_name}",
                        },
                        confidence="high",
                    )
                )
        finally:
            cursor.close()
            connection.close()
        return records
