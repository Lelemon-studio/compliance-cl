from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, ClassVar


ALLOWED_SIGNALS = frozenset({"present", "absent", "unknown", "misconfigured"})


@dataclass
class EvidenceRecord:
    id: str
    layer: str
    resource: str
    attribute: str
    value: Any
    signal: str
    control_ids: list[str] = field(default_factory=list)
    law_refs: list[str] = field(default_factory=list)
    remediation_candidates: list[dict[str, Any]] = field(default_factory=list)
    source: dict[str, Any] = field(default_factory=dict)
    confidence: str | None = None

    allowed_signals: ClassVar[frozenset[str]] = ALLOWED_SIGNALS

    def __post_init__(self) -> None:
        if self.signal not in self.allowed_signals:
            raise ValueError(f"invalid technical signal: {self.signal!r}")
        if not self.id or not self.layer or not self.attribute:
            raise ValueError("evidence id, layer, and attribute are required")

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "id": self.id,
            "layer": self.layer,
            "resource": self.resource,
            "attribute": self.attribute,
            "value": self.value,
            "signal": self.signal,
            "control_ids": list(self.control_ids),
            "law_refs": list(self.law_refs),
            "remediation_candidates": list(self.remediation_candidates),
            "source": dict(self.source),
        }
        if self.confidence is not None:
            payload["confidence"] = self.confidence
        return payload


@dataclass
class CollectorResult:
    evidence: list[EvidenceRecord] = field(default_factory=list)
    inventory: list[dict[str, Any]] = field(default_factory=list)
    raw_files: dict[str, Any] = field(default_factory=dict)
    services_scanned: list[str] = field(default_factory=list)
    services_skipped: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    errors: list[dict[str, Any]] = field(default_factory=list)
    environment: dict[str, Any] = field(default_factory=dict)
    resilience_tier_observed: dict[str, Any] = field(default_factory=dict)

    @property
    def exit_code(self) -> int:
        if any(bool(error.get("fatal")) for error in self.errors):
            return 1
        if self.errors or self.services_skipped:
            return 2
        return 0

    def merge(self, other: "CollectorResult") -> None:
        self.evidence.extend(other.evidence)
        self.inventory.extend(other.inventory)
        self.raw_files.update(other.raw_files)
        self.services_scanned.extend(x for x in other.services_scanned if x not in self.services_scanned)
        self.services_skipped.extend(other.services_skipped)
        self.warnings.extend(other.warnings)
        self.errors.extend(other.errors)
        self.environment.update(other.environment)
        self.resilience_tier_observed.update(other.resilience_tier_observed)

