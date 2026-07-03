from __future__ import annotations

import json
import base64
from datetime import datetime, timezone
from pathlib import Path

import jsonschema
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from oracle_collector.config import CollectorConfig, OciConfig, RunConfig
from oracle_collector.models import CollectorResult, EvidenceRecord
from oracle_collector.writer import build_bundle, write_output


def test_writer_creates_self_contained_schema_valid_bundle(tmp_path: Path) -> None:
    config = CollectorConfig(
        run=RunConfig(name="schema-test", redaction="strict", parallelism=1),
        oci=OciConfig(enabled=False),
    )
    result = CollectorResult(
        evidence=[
            EvidenceRecord(
                id="ev-1",
                layer="database",
                resource="coreprod",
                attribute="tde_encryption",
                value={"wallet_status": "OPEN"},
                signal="present",
                control_ids=["sec-rest"],
                source={"collector": "dbsat", "ref": "raw/dbsat/coreprod.report.json"},
            )
        ],
        raw_files={"dbsat/coreprod.report.json": {"findings": []}},
        services_scanned=["dbsat"],
    )
    bundle = build_bundle(config, result, generated_at=datetime(2026, 7, 3, tzinfo=timezone.utc))
    run_dir = write_output(bundle, result, tmp_path)

    payload = json.loads((run_dir / "evidence-bundle.json").read_text(encoding="utf-8"))
    schema_path = Path(__file__).parents[1] / "schema" / "evidence-bundle.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    jsonschema.validate(payload, schema)
    assert (run_dir / "raw" / "dbsat" / "coreprod.report.json").exists()
    assert (run_dir / "collector.log").exists()
    assert payload["collector_version"]


def test_encrypted_output_uses_aes_256_gcm_without_plaintext_copy(tmp_path: Path) -> None:
    config = CollectorConfig(run=RunConfig(name="encrypted", redaction="strict"), oci=OciConfig(enabled=False))
    result = CollectorResult()
    bundle = build_bundle(config, result, generated_at=datetime(2026, 7, 3, tzinfo=timezone.utc))
    key = b"k" * 32
    run_dir = write_output(bundle, result, tmp_path, encryption_key=key)

    assert not (run_dir / "evidence-bundle.json").exists()
    envelope = json.loads((run_dir / "evidence-bundle.json.aesgcm").read_text(encoding="utf-8"))
    plaintext = AESGCM(key).decrypt(
        base64.b64decode(envelope["nonce"]),
        base64.b64decode(envelope["ciphertext"]),
        b"oracle-compliance-collector:v1",
    )
    assert json.loads(plaintext)["run"]["name"] == "encrypted"
