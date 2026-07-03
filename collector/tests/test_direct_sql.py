import builtins

import pytest

from oracle_collector.collectors.direct_sql import (
    ALLOWED_CATALOG_QUERIES,
    DirectSQLCollector,
    UnsafeDatabaseSessionError,
    validate_catalog_query,
)


class FakeCursor:
    def __init__(self):
        self.executed = []
        self.description = [("VALUE",)]

    def execute(self, statement):
        self.executed.append(statement)
        self.description = [("VALUE",)]

    def fetchall(self):
        return [("observed",)]

    def close(self):
        pass


class FakeConnection:
    def __init__(self):
        self.cursor_instance = FakeCursor()
        self.closed = False

    def cursor(self):
        return self.cursor_instance

    def close(self):
        self.closed = True


def test_allowlist_contains_only_single_catalog_selects():
    expected_sources = {
        "V$ENCRYPTION_WALLET",
        "V$ENCRYPTED_TABLESPACES",
        "DBA_AUDIT_MGMT_CONFIG_PARAMS",
        "AUDIT_UNIFIED_POLICIES",
        "V$RMAN_BACKUP_JOB_DETAILS",
        "V$BACKUP",
        "V$DATABASE",
        "V$DATAGUARD_CONFIG",
        "GV$INSTANCE",
    }

    combined = "\n".join(ALLOWED_CATALOG_QUERIES.values()).upper()
    assert expected_sources <= {source for source in expected_sources if source in combined}
    for statement in ALLOWED_CATALOG_QUERIES.values():
        validate_catalog_query(statement)
        assert statement.lstrip().upper().startswith("SELECT ")
        assert ";" not in statement


@pytest.mark.parametrize(
    "statement",
    [
        "SELECT * FROM CUSTOMER_ORDERS",
        "UPDATE V$DATABASE SET NAME = 'X'",
        "SELECT * FROM V$DATABASE; DELETE FROM USERS",
        "BEGIN EXECUTE IMMEDIATE 'SELECT 1 FROM DUAL'; END;",
    ],
)
def test_query_validator_rejects_non_allowlisted_or_mutating_sql(statement):
    with pytest.raises(ValueError):
        validate_catalog_query(statement)


@pytest.mark.parametrize(
    "target",
    [
        {"alias": "db", "username": "SYS", "role": "readonly_monitor"},
        {"alias": "db", "username": "SYSTEM", "role": "readonly_monitor"},
        {"alias": "db", "username": "monitor", "role": "SYSDBA"},
        {"alias": "db", "username": "monitor", "privilege_mode": "SYSOPER"},
        {"alias": "db", "username": "monitor", "role": "DBA"},
        {
            "alias": "db",
            "username": "monitor",
            "role": "readonly_monitor",
            "wallet_password": "plaintext-secret",
        },
    ],
)
def test_collector_rejects_privileged_or_unsafe_sessions(target):
    with pytest.raises(UnsafeDatabaseSessionError):
        DirectSQLCollector(connection_factory=lambda _: FakeConnection()).collect(target)


def test_collect_executes_exact_allowlist_and_returns_evidence():
    connection = FakeConnection()
    collector = DirectSQLCollector(connection_factory=lambda _: connection)

    records = collector.collect(
        {"alias": "coreprod", "username": "monitor", "role": "readonly_monitor"}
    )

    assert connection.cursor_instance.executed == list(ALLOWED_CATALOG_QUERIES.values())
    assert len(records) == len(ALLOWED_CATALOG_QUERIES)
    assert all(record.layer == "database" for record in records)
    assert all(record.source["collector"] == "direct_sql" for record in records)
    assert all(record.signal in {"present", "absent", "unknown", "misconfigured"} for record in records)


def test_oracledb_is_lazy_imported(monkeypatch):
    imported = []
    real_import = builtins.__import__

    def tracking_import(name, *args, **kwargs):
        if name == "oracledb":
            imported.append(name)
            raise ImportError("not installed")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", tracking_import)
    collector = DirectSQLCollector()
    assert imported == []

    with pytest.raises(RuntimeError, match="optional dependency"):
        collector.collect(
            {
                "alias": "db",
                "username": "monitor",
                "role": "readonly_monitor",
                "dsn": "db:1521/PDB",
            }
        )
    assert imported == ["oracledb"]
