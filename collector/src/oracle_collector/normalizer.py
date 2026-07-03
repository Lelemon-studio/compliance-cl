from __future__ import annotations

from typing import Any, Mapping

from .collectors.base import evidence_id
from .models import EvidenceRecord


def normalize_record(
    *,
    collector: str,
    layer: str,
    resource: str,
    attribute: str,
    value: Any,
    signal: str,
    control_ids: list[str] | None = None,
    source_ref: str | None = None,
) -> EvidenceRecord:
    source: dict[str, Any] = {"collector": collector}
    if source_ref:
        source["ref"] = source_ref
    return EvidenceRecord(
        id=evidence_id(collector, resource, attribute),
        layer=layer,
        resource=resource,
        attribute=attribute,
        value=value,
        signal=signal,
        control_ids=list(control_ids or []),
        source=source,
    )

