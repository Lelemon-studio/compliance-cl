import json
from pathlib import Path
from subprocess import CompletedProcess

import pytest

from oracle_collector.collectors.dbsat import (
    DBSATCollector,
    UnsafeDBSATTargetError,
    build_dbsat_commands,
    invoke_dbsat,
    parse_dbsat_json,
)


FIXTURES = Path(__file__).parent / "fixtures" / "onprem"


def test_parse_dbsat_json_emits_normalized_evidence_records():
    records = parse_dbsat_json(FIXTURES / "dbsat-report.json", alias="coreprod")

    assert len(records) == 2
    tde = records[0]
    assert tde.layer == "database"
    assert tde.resource == "coreprod"
    assert tde.attribute == "dbsat:TDE-001"
    assert tde.signal == "present"
    assert tde.control_ids == ["sec-rest"]
    assert tde.value["wallet_status"] == "OPEN"
    assert tde.source["collector"] == "dbsat"
    assert "#/findings/0" in tde.source["ref"]

    audit = records[1]
    assert audit.signal == "misconfigured"
    assert set(audit.control_ids) == {"sec-logs", "gov-auditoria"}


def test_parse_dbsat_json_accepts_document_and_preserves_no_legal_verdict():
    document = json.loads((FIXTURES / "dbsat-report.json").read_text())

    payloads = [record.to_dict() for record in parse_dbsat_json(document, alias="db")]

    assert all("status" not in payload for payload in payloads)
    assert {payload["signal"] for payload in payloads} == {"present", "misconfigured"}


def test_build_commands_are_argument_lists_without_credentials():
    target = {
        "alias": "coreprod",
        "connect": "coreprod_reader@//db1:1521/PDB1",
        "wallet": "/secure/wallet",
    }

    collect_cmd, report_cmd = build_dbsat_commands("/opt/dbsat/dbsat", target, Path("/tmp/coreprod"))

    assert collect_cmd == [
        "/opt/dbsat/dbsat",
        "collect",
        "-n",
        "coreprod_reader@//db1:1521/PDB1",
        "/tmp/coreprod",
    ]
    assert report_cmd == [
        "/opt/dbsat/dbsat",
        "report",
        "-f",
        "json",
        "/tmp/coreprod",
    ]
    assert all("password" not in argument.lower() for command in (collect_cmd, report_cmd) for argument in command)


@pytest.mark.parametrize(
    "connect",
    ["scott/tiger@db", "user:secret@db", "user@db?password=secret", "SYS@db AS SYSDBA"],
)
def test_dbsat_rejects_embedded_passwords_and_sysdba(connect):
    with pytest.raises(UnsafeDBSATTargetError):
        build_dbsat_commands("dbsat", {"alias": "db", "connect": connect}, Path("/tmp/db"))


def test_invoke_dbsat_never_uses_a_shell_or_places_wallet_in_command(tmp_path):
    calls = []

    def runner(command, **kwargs):
        calls.append((command, kwargs))
        return CompletedProcess(command, 0, stdout="", stderr="")

    report_path = invoke_dbsat(
        "dbsat",
        {"alias": "db", "connect": "reader@//db:1521/PDB", "wallet": "/secret/wallet"},
        tmp_path,
        runner=runner,
    )

    assert report_path == tmp_path / "db.report.json"
    assert len(calls) == 2
    assert all(isinstance(command, list) for command, _ in calls)
    assert all(kwargs.get("shell") is False for _, kwargs in calls)
    assert all("/secret/wallet" not in command for command, _ in calls)
    assert all(kwargs["check"] is True for _, kwargs in calls)


def test_invoke_dbsat_accepts_the_native_report_filename(tmp_path):
    native_report = tmp_path / "db_report.json"

    def runner(command, **kwargs):
        if command[1] == "report":
            native_report.write_text("{\"findings\": []}")
        return CompletedProcess(command, 0, stdout="", stderr="")

    report_path = invoke_dbsat(
        "dbsat",
        {"alias": "db", "connect": "reader@//db:1521/PDB"},
        tmp_path,
        runner=runner,
    )

    assert report_path == native_report


def test_collector_can_parse_an_existing_read_only_report():
    records = DBSATCollector().collect(
        {"alias": "coreprod", "report_path": FIXTURES / "dbsat-report.json"}
    )

    assert len(records) == 2
