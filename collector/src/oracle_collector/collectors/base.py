from __future__ import annotations

import hashlib
from collections.abc import Mapping
from datetime import date, datetime
from enum import Enum
from pathlib import Path
from typing import Any


def evidence_id(collector: str, resource: str, attribute: str) -> str:
    digest = hashlib.sha256(f"{collector}|{resource}|{attribute}".encode("utf-8")).hexdigest()[:12]
    return f"ev-{digest}"


def json_safe(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Enum):
        return json_safe(value.value)
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, bytes):
        return f"<bytes:{len(value)}>"
    if isinstance(value, Mapping):
        return {str(key): json_safe(child) for key, child in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [json_safe(child) for child in value]
    if hasattr(value, "to_dict"):
        return json_safe(value.to_dict())
    if hasattr(value, "__dict__"):
        return json_safe({key: child for key, child in vars(value).items() if not key.startswith("_")})
    return str(value)


def as_mapping(resource: Any) -> dict[str, Any]:
    if isinstance(resource, dict):
        return json_safe(resource)
    if hasattr(resource, "to_dict"):
        return json_safe(resource.to_dict())
    if hasattr(resource, "__dict__"):
        return json_safe({key: value for key, value in vars(resource).items() if not key.startswith("_")})
    return {"value": str(resource)}
