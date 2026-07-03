from __future__ import annotations

import pytest

from oracle_collector.mapper import apply_mapping
from oracle_collector.models import EvidenceRecord


def make_record(**overrides: object) -> EvidenceRecord:
    values = {
        "id": "ev-1",
        "layer": "storage",
        "resource": "bucket:exports",
        "attribute": "public_access",
        "value": {"visibility": "public"},
        "signal": "misconfigured",
        "source": {"collector": "oci.object_storage", "ref": "raw/oci/object_storage/test.json"},
    }
    values.update(overrides)
    return EvidenceRecord(**values)


def test_evidence_record_serializes_only_technical_signal() -> None:
    record = make_record()
    payload = record.to_dict()
    assert payload["signal"] == "misconfigured"
    assert "status" not in payload


def test_invalid_signal_is_rejected() -> None:
    with pytest.raises(ValueError, match="signal"):
        make_record(signal="fail")


def test_mapper_attaches_controls_and_remediation_without_verdict() -> None:
    record = make_record(control_ids=[], remediation_candidates=[])
    mapped = apply_mapping(record)
    assert {"sec-rest", "inc-brechas"}.issubset(set(mapped.control_ids))
    assert any(item["deployment"] == "oci" for item in mapped.remediation_candidates)
    assert "status" not in mapped.to_dict()

