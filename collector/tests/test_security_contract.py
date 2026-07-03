"""Security contracts for evidence models and output redaction."""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
import json
from typing import Any, Mapping

import pytest

from oracle_collector.models import EvidenceRecord
from oracle_collector.redaction import redact, sanitize_log_text


def _record_kwargs(*, signal: str = "present", value: Any = True) -> dict[str, Any]:
    return {
        "id": "ev-security-001",
        "layer": "iam",
        "resource": "security-policy",
        "attribute": "mfa_enabled",
        "value": value,
        "signal": signal,
        "control_ids": ["sec-mfa"],
        "law_refs": ["Art. 14 quinquies"],
        "remediation_candidates": [],
        "source": {"collector": "test", "ref": "raw/test/security.json"},
        "confidence": "high",
    }


def _as_mapping(value: Any) -> Mapping[str, Any]:
    if hasattr(value, "model_dump"):
        return value.model_dump()
    if hasattr(value, "dict"):
        return value.dict()
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, Mapping):
        return value
    raise AssertionError(f"EvidenceRecord is not serializable: {type(value)!r}")


@pytest.mark.parametrize("signal", ["present", "absent", "unknown", "misconfigured"])
def test_evidence_record_accepts_only_documented_technical_signals(signal: str) -> None:
    record = EvidenceRecord(**_record_kwargs(signal=signal))

    assert _as_mapping(record)["signal"] == signal


def test_evidence_record_rejects_unsupported_signal() -> None:
    with pytest.raises((TypeError, ValueError)):
        EvidenceRecord(**_record_kwargs(signal="compliant"))


def test_evidence_record_rejects_or_omits_legal_status() -> None:
    try:
        record = EvidenceRecord(**_record_kwargs(), status="compliant")
    except (TypeError, ValueError):
        return

    serialized = _as_mapping(record)
    assert "status" not in serialized
    assert not hasattr(record, "status")


def test_strict_redaction_removes_secrets_and_deterministically_hashes_ocids() -> None:
    tenancy_ocid = "ocid1.tenancy.oc1..aaaaexampletenancy"
    instance_ocid = "ocid1.instance.oc1.sa-santiago-1.aaaaexampleinstance"
    secrets = {
        "password": "P@ssword-should-never-leak",
        "api_token": "token-should-never-leak",
        "authorization": "Bearer eyJhbGciOiJub25lIn0.secret.signature",
        "private_key": "-----BEGIN PRIVATE KEY-----\nbase64-secret\n-----END PRIVATE KEY-----",
    }
    payload = {
        **secrets,
        "tenancy_ocid": tenancy_ocid,
        "resource_ocid": instance_ocid,
    }

    first = redact(payload, mode="strict")
    second = redact(payload, mode="strict")
    other = redact({"resource_ocid": tenancy_ocid}, mode="strict")
    encoded = json.dumps(first, sort_keys=True)

    for secret in secrets.values():
        assert secret not in encoded
    assert tenancy_ocid not in encoded
    assert instance_ocid not in encoded
    assert first["resource_ocid"] == second["resource_ocid"]
    assert first["resource_ocid"] != other["resource_ocid"]


def test_log_sanitizer_removes_common_secret_forms() -> None:
    secret_corpus = [
        "LogPassword-42!",
        "eyJhbGciOiJub25lIn0.log-token.signature",
        "raw-api-token-value",
        "private-key-material",
    ]
    text = (
        "password=LogPassword-42! "
        "Authorization: Bearer eyJhbGciOiJub25lIn0.log-token.signature "
        "api_token=raw-api-token-value "
        "-----BEGIN PRIVATE KEY----- private-key-material -----END PRIVATE KEY-----"
    )

    sanitized = sanitize_log_text(text, mode="strict")

    for secret in secret_corpus:
        assert secret not in sanitized
    assert "password" in sanitized.lower()


def test_redacted_bundle_serialization_does_not_leak_secret_corpus() -> None:
    secret_corpus = [
        "NestedPassword-77!",
        "nested-access-token",
        "nested-private-key-material",
    ]
    record = EvidenceRecord(
        **_record_kwargs(
            value={
                "password": secret_corpus[0],
                "access_token": secret_corpus[1],
                "private_key": (
                    "-----BEGIN PRIVATE KEY-----\n"
                    f"{secret_corpus[2]}\n"
                    "-----END PRIVATE KEY-----"
                ),
            }
        )
    )
    bundle = {
        "schema": 1,
        "evidence": [_as_mapping(record)],
        "coverage": {"warnings": []},
        "errors": [],
    }

    serialized = json.dumps(redact(bundle, mode="strict"), sort_keys=True)

    for secret in secret_corpus:
        assert secret not in serialized
