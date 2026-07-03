from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

import yaml


class ConfigError(ValueError):
    """Raised when collector configuration is unsafe or invalid."""


@dataclass(frozen=True)
class RunConfig:
    name: str
    redaction: str = "strict"
    offline_only: bool = False
    parallelism: int = 8

    def __post_init__(self) -> None:
        if not self.name or any(part in self.name for part in ("/", "\\", "..")):
            raise ConfigError("run.name must be a safe non-empty directory name")
        if self.redaction not in {"strict", "minimal"}:
            raise ConfigError("run.redaction must be strict or minimal")
        if not 1 <= self.parallelism <= 64:
            raise ConfigError("run.parallelism must be between 1 and 64")


@dataclass(frozen=True)
class OciConfig:
    enabled: bool = False
    auth: str = "config_file"
    profile: str = "DEFAULT"
    config_path: str = "~/.oci/config"
    tenancy_ocid: str | None = None
    regions: tuple[str, ...] = ()
    compartments: str | tuple[str, ...] = "all"
    services: str | tuple[str, ...] = "all"

    def __post_init__(self) -> None:
        allowed = {"config_file", "instance_principal", "session_token", "resource_principal"}
        if self.auth not in allowed:
            raise ConfigError(f"unsupported OCI auth mode: {self.auth}")
        if self.enabled and not self.regions:
            raise ConfigError("oci.regions is required when OCI collection is enabled")


@dataclass(frozen=True)
class CollectorConfig:
    run: RunConfig
    oci: OciConfig = field(default_factory=OciConfig)
    onprem_db: Mapping[str, Any] = field(default_factory=dict)
    onprem_middleware: Mapping[str, Any] = field(default_factory=dict)


SECRET_KEYS = frozenset(
    {
        "password",
        "passwd",
        "secret",
        "secret_value",
        "token",
        "api_key",
        "private_key",
        "authorization",
    }
)


def _reject_embedded_secrets(value: Any, path: str = "config") -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            normalized = str(key).lower().replace("-", "_")
            is_secret = normalized in SECRET_KEYS or normalized.endswith(
                ("_password", "_passwd", "_secret", "_token", "_api_key", "_private_key")
            )
            if is_secret and child not in (None, "", False):
                raise ConfigError(f"secret/password material is forbidden at {path}.{key}")
            _reject_embedded_secrets(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _reject_embedded_secrets(child, f"{path}[{index}]")


def _tuple_or_all(value: Any, field_name: str) -> str | tuple[str, ...]:
    if value == "all":
        return "all"
    if isinstance(value, list) and all(isinstance(item, str) and item for item in value):
        return tuple(value)
    raise ConfigError(f"{field_name} must be 'all' or a list of strings")


def load_config(path: str | Path) -> CollectorConfig:
    config_path = Path(path).expanduser()
    try:
        raw = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError) as exc:
        raise ConfigError(f"cannot read configuration: {exc}") from exc
    if not isinstance(raw, Mapping):
        raise ConfigError("configuration root must be an object")
    _reject_embedded_secrets(raw)

    run_raw = raw.get("run", {})
    if not isinstance(run_raw, Mapping):
        raise ConfigError("run must be an object")
    run = RunConfig(
        name=str(run_raw.get("name", "")),
        redaction=str(run_raw.get("redaction", "strict")),
        offline_only=bool(run_raw.get("offline_only", False)),
        parallelism=int(run_raw.get("parallelism", 8)),
    )

    oci_raw = raw.get("oci", {}) or {}
    if not isinstance(oci_raw, Mapping):
        raise ConfigError("oci must be an object")
    regions = oci_raw.get("regions", [])
    if not isinstance(regions, list) or not all(isinstance(item, str) for item in regions):
        raise ConfigError("oci.regions must be a list")
    oci = OciConfig(
        enabled=bool(oci_raw.get("enabled", False)),
        auth=str(oci_raw.get("auth", "config_file")),
        profile=str(oci_raw.get("profile", "DEFAULT")),
        config_path=str(oci_raw.get("config_path", "~/.oci/config")),
        tenancy_ocid=oci_raw.get("tenancy_ocid"),
        regions=tuple(regions),
        compartments=_tuple_or_all(oci_raw.get("compartments", "all"), "oci.compartments"),
        services=_tuple_or_all(oci_raw.get("services", "all"), "oci.services"),
    )
    onprem_db = raw.get("onprem_db", {}) or {}
    middleware = raw.get("onprem_middleware", {}) or {}
    if not isinstance(onprem_db, Mapping) or not isinstance(middleware, Mapping):
        raise ConfigError("on-prem configuration sections must be objects")
    return CollectorConfig(run=run, oci=oci, onprem_db=dict(onprem_db), onprem_middleware=dict(middleware))
