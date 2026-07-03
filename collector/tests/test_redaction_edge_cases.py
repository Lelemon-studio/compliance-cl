from __future__ import annotations

import json

from oracle_collector.redaction import redact, sanitize_log_text


def test_minimal_mode_still_masks_full_ocids() -> None:
    ocid = "ocid1.instance.oc1.sa-santiago-1.aaaaexampleinstance"
    payload = redact({"resource": ocid}, mode="minimal")
    assert ocid not in json.dumps(payload)
    assert payload["resource"].startswith("ocid1.instance.")


def test_log_sanitizer_removes_uri_and_oracle_dsn_passwords() -> None:
    text = "https://alice:uri-secret@example.test reader/oracle-secret@//db:1521/PDB"
    sanitized = sanitize_log_text(text)
    assert "uri-secret" not in sanitized
    assert "oracle-secret" not in sanitized
    assert "alice" in sanitized
    assert "reader" in sanitized


def test_log_sanitizer_removes_quoted_values_and_incomplete_private_keys() -> None:
    text = 'client_secret="two word secret" auth_token=raw-token -----BEGIN PRIVATE KEY----- partial-key-material'
    sanitized = sanitize_log_text(text)
    assert "two word secret" not in sanitized
    assert "raw-token" not in sanitized
    assert "partial-key-material" not in sanitized
