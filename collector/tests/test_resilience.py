from __future__ import annotations

from oracle_collector.models import EvidenceRecord
from oracle_collector.resilience import derive_resilience_observations, infer_resilience_tier


def test_resilience_tier_is_a_proposal_with_supporting_signals() -> None:
    observed = infer_resilience_tier(
        {
            "data_guard": True,
            "rman_backup": True,
            "cross_region_dr": False,
            "rac": False,
        }
    )
    assert observed["tier"] == "silver"
    assert "Data Guard active" in observed["signals"]
    assert observed["provisional"] is True


def test_direct_sql_evidence_is_grouped_into_database_tier_proposals() -> None:
    records = [
        EvidenceRecord(
            id=f"ev-{attribute}",
            layer="database",
            resource="coreprod",
            attribute=attribute,
            value={"rows": [{"observed": True}]},
            signal="present",
            source={"collector": "direct_sql"},
        )
        for attribute in ("database_role", "dataguard_config", "rman_backup_jobs")
    ]
    observed = derive_resilience_observations(records)
    assert observed["coreprod"]["tier"] == "silver"
    assert observed["coreprod"]["provisional"] is True
