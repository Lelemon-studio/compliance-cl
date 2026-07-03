from __future__ import annotations

from oracle_collector.models import CollectorResult, EvidenceRecord
from oracle_collector.orchestrator import CollectorTask, run_tasks


def evidence() -> EvidenceRecord:
    return EvidenceRecord(
        id="ev-ok",
        layer="database",
        resource="coreprod",
        attribute="tde_encryption",
        value={"wallet_status": "OPEN"},
        signal="present",
        source={"collector": "dbsat", "ref": "raw/dbsat/coreprod.json"},
    )


def test_partial_failure_does_not_abort_other_collectors() -> None:
    def succeeds() -> CollectorResult:
        return CollectorResult(evidence=[evidence()], services_scanned=["dbsat"])

    def fails() -> CollectorResult:
        raise TimeoutError("OCI timeout")

    result = run_tasks(
        [CollectorTask("dbsat", succeeds), CollectorTask("oci.oke", fails, region="sa-santiago-1")],
        parallelism=2,
    )

    assert [item.id for item in result.evidence] == ["ev-ok"]
    assert result.exit_code == 2
    assert result.errors == [
        {"collector": "oci.oke", "region": "sa-santiago-1", "error": "TimeoutError", "fatal": False}
    ]


def test_all_successful_collectors_return_zero() -> None:
    result = run_tasks([CollectorTask("dbsat", lambda: CollectorResult(evidence=[evidence()]))])
    assert result.exit_code == 0

