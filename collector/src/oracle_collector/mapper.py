from __future__ import annotations

from dataclasses import replace

from .models import EvidenceRecord


ATTRIBUTE_MAPPINGS: dict[str, tuple[list[str], list[dict[str, str]]]] = {
    "public_access": (
        ["sec-rest", "inc-brechas"],
        [
            {
                "product": "Object Storage private + CMK (OCI Vault)",
                "deployment": "oci",
                "applies": "recommended",
            },
            {"product": "Cloud Guard detector", "deployment": "oci", "applies": "recommended"},
        ],
    ),
    "tde_encryption": (
        ["sec-rest"],
        [{"product": "Oracle Advanced Security (TDE)", "deployment": "onprem", "applies": "recommended"}],
    ),
    "tls_configuration": (["sec-tls"], []),
    "mfa_state": (["sec-mfa"], []),
    "backup_configuration": (["sec-backups"], []),
    "audit_configuration": (["sec-logs", "gov-auditoria"], []),
}


def apply_mapping(record: EvidenceRecord) -> EvidenceRecord:
    controls, candidates = ATTRIBUTE_MAPPINGS.get(record.attribute, ([], []))
    merged_controls = list(dict.fromkeys([*record.control_ids, *controls]))
    existing = {(item.get("product"), item.get("deployment")) for item in record.remediation_candidates}
    merged_candidates = [*record.remediation_candidates]
    merged_candidates.extend(
        candidate
        for candidate in candidates
        if (candidate.get("product"), candidate.get("deployment")) not in existing
    )
    return replace(record, control_ids=merged_controls, remediation_candidates=merged_candidates)

