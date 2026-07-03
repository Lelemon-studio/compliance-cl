from __future__ import annotations

from collections.abc import Iterable
from typing import Any, Mapping

from .models import EvidenceRecord


def infer_resilience_tier(observed: Mapping[str, Any]) -> dict[str, Any]:
    signals: list[str] = []
    if observed.get("rman_backup"):
        signals.append("RMAN backup active")
    if observed.get("data_guard"):
        signals.append("Data Guard active")
    if observed.get("rac"):
        signals.append("RAC active")
    if observed.get("cross_region_dr"):
        signals.append("Cross-region DR active")

    if observed.get("cross_region_dr") and observed.get("rac") and observed.get("data_guard"):
        tier = "platinum"
    elif observed.get("cross_region_dr") and observed.get("data_guard"):
        tier = "gold"
    elif observed.get("data_guard") and observed.get("rman_backup"):
        tier = "silver"
    else:
        tier = "bronze"
    if not observed.get("cross_region_dr"):
        signals.append("no cross-region DR")
    return {"tier": tier, "signals": signals, "provisional": True}


def derive_resilience_observations(records: Iterable[EvidenceRecord]) -> dict[str, Any]:
    database_signals: dict[str, dict[str, bool]] = {}
    for record in records:
        if record.layer != "database" or record.signal != "present":
            continue
        signals = database_signals.setdefault(
            record.resource,
            {"data_guard": False, "rman_backup": False, "rac": False, "cross_region_dr": False},
        )
        if record.attribute == "dataguard_config":
            signals["data_guard"] = True
        elif record.attribute in {"rman_backup_jobs", "backup_status"}:
            signals["rman_backup"] = True
        elif record.attribute == "rac_instances":
            signals["rac"] = True
        elif record.attribute == "cross_region_dr":
            signals["cross_region_dr"] = True
    return {resource: infer_resilience_tier(signals) for resource, signals in database_signals.items()}
