from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any

from . import __version__
from .config import CollectorConfig
from .encryption import encrypt_payload
from .mapper import apply_mapping
from .models import CollectorResult
from .redaction import redact, sanitize_log_text


DEFAULT_CATALOG = {
    "source": "specs/ldp.pdf (Art. 14 / 14 quinquies)",
    "onprem": [],
    "cloud": [],
    "zero_trust": [],
}


def load_remediation_catalog() -> dict[str, Any]:
    candidates = (
        Path(__file__).resolve().parents[2] / "remediation_catalog.json",
        Path(sys.prefix) / "oracle_collector_data" / "remediation_catalog.json",
    )
    for path in candidates:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    return dict(DEFAULT_CATALOG)


def build_bundle(
    config: CollectorConfig,
    result: CollectorResult,
    *,
    generated_at: datetime | None = None,
) -> dict[str, Any]:
    timestamp = generated_at or datetime.now(timezone.utc)
    evidence = [apply_mapping(item).to_dict() for item in result.evidence]
    environment = dict(result.environment)
    environment.setdefault(
        "oci",
        {
            "tenancy_ocid": config.oci.tenancy_ocid,
            "regions": list(config.oci.regions),
            "compartments_scanned": 0,
        }
        if config.oci.enabled
        else None,
    )
    bundle = {
        "schema": 1,
        "generated_at": timestamp.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
        "collector_version": __version__,
        "run": {"name": config.run.name, "redaction": config.run.redaction},
        "environment": environment,
        "inventory": list(result.inventory),
        "evidence": evidence,
        "remediation_catalog": load_remediation_catalog(),
        "resilience_tier_observed": dict(result.resilience_tier_observed),
        "coverage": {
            "services_scanned": list(result.services_scanned),
            "services_skipped": list(result.services_skipped),
            "warnings": list(result.warnings),
        },
        "errors": list(result.errors),
    }
    return redact(bundle, config.run.redaction)


def _safe_raw_path(relative: str) -> PurePosixPath:
    path = PurePosixPath(relative)
    if path.is_absolute() or ".." in path.parts or not path.parts:
        raise ValueError(f"unsafe raw artifact path: {relative!r}")
    return path


def write_output(
    bundle: dict[str, Any],
    result: CollectorResult,
    out_dir: str | Path,
    *,
    encryption_key: bytes | None = None,
) -> Path:
    run_name = str(bundle["run"]["name"])
    run_dir = Path(out_dir) / run_name
    raw_dir = run_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    for relative, content in result.raw_files.items():
        target = raw_dir.joinpath(*_safe_raw_path(relative).parts)
        target.parent.mkdir(parents=True, exist_ok=True)
        redacted_content = redact(content, str(bundle["run"]["redaction"]))
        if isinstance(redacted_content, (dict, list)):
            target.write_text(json.dumps(redacted_content, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        else:
            target.write_text(
                sanitize_log_text(str(redacted_content), str(bundle["run"]["redaction"])) + "\n",
                encoding="utf-8",
            )

    if encryption_key is None:
        (run_dir / "evidence-bundle.json").write_text(
            json.dumps(bundle, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    else:
        (run_dir / "evidence-bundle.json.aesgcm").write_bytes(encrypt_payload(bundle, encryption_key))
    log_lines = [
        f"collector_version={__version__}",
        f"run={run_name}",
        f"services_scanned={len(result.services_scanned)}",
        f"errors={len(result.errors)}",
    ]
    (run_dir / "collector.log").write_text(sanitize_log_text("\n".join(log_lines)) + "\n", encoding="utf-8")
    return run_dir
