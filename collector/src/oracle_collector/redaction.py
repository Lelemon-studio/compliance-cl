from __future__ import annotations

import hashlib
import re
from collections.abc import Mapping
from typing import Any


REDACTED = "[REDACTED]"
SECRET_FIELD_PATTERN = re.compile(
    r"(?:password|passwd|secret(?:_value)?|token|authorization|api[_-]?key|private[_-]?key)", re.IGNORECASE
)
OCID_PATTERN = re.compile(r"\bocid1\.[a-z0-9_-]+\.[a-z0-9_.-]+", re.IGNORECASE)
BEARER_PATTERN = re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+\-/]+=*")
ASSIGNMENT_PATTERN = re.compile(
    r"(?i)\b([a-z0-9_-]*(?:password|passwd|secret|token|authorization|api[_-]?key))"
    r"\s*[:=]\s*(\"[^\"]*\"|'[^']*'|[^\s,;]+)"
)
PRIVATE_KEY_PATTERN = re.compile(
    r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----",
    re.DOTALL,
)
PRIVATE_KEY_START_PATTERN = re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*", re.DOTALL)
URI_CREDENTIAL_PATTERN = re.compile(
    r"(?i)([a-z][a-z0-9+.-]*://)([^:/\s]+):([^@\s]+)@"
)
ORACLE_CREDENTIAL_PATTERN = re.compile(r"\b([A-Za-z][\w.-]*)/([^@\s/]+)@(?=//|[A-Za-z0-9])")


def _hash_identifier(value: str) -> str:
    kind = value.split(".", 2)[1] if value.startswith("ocid1.") and "." in value else "id"
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]
    return f"ocid1.{kind}.sha256:{digest}"


def _truncate_identifier(value: str) -> str:
    kind = value.split(".", 2)[1] if value.startswith("ocid1.") and "." in value else "id"
    return f"ocid1.{kind}.redacted:{value[-10:]}"


def sanitize_log_text(text: str, mode: str = "strict") -> str:
    sanitized = PRIVATE_KEY_PATTERN.sub(REDACTED, text)
    sanitized = PRIVATE_KEY_START_PATTERN.sub(REDACTED, sanitized)
    sanitized = URI_CREDENTIAL_PATTERN.sub(lambda match: f"{match.group(1)}{match.group(2)}:{REDACTED}@", sanitized)
    sanitized = ORACLE_CREDENTIAL_PATTERN.sub(lambda match: f"{match.group(1)}/{REDACTED}@", sanitized)
    sanitized = BEARER_PATTERN.sub(f"Bearer {REDACTED}", sanitized)
    sanitized = ASSIGNMENT_PATTERN.sub(lambda match: f"{match.group(1)}={REDACTED}", sanitized)
    if mode == "strict":
        sanitized = OCID_PATTERN.sub(lambda match: _hash_identifier(match.group(0)), sanitized)
    else:
        sanitized = OCID_PATTERN.sub(lambda match: _truncate_identifier(match.group(0)), sanitized)
    return sanitized


def redact(value: Any, mode: str = "strict") -> Any:
    if mode not in {"strict", "minimal"}:
        raise ValueError("redaction mode must be strict or minimal")
    if isinstance(value, Mapping):
        result: dict[str, Any] = {}
        for key, child in value.items():
            if SECRET_FIELD_PATTERN.search(str(key)):
                result[str(key)] = REDACTED
            else:
                result[str(key)] = redact(child, mode)
        return result
    if isinstance(value, list):
        return [redact(item, mode) for item in value]
    if isinstance(value, tuple):
        return [redact(item, mode) for item in value]
    if isinstance(value, str):
        return sanitize_log_text(value, mode)
    return value
