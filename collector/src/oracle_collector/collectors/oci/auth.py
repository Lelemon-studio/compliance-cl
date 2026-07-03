from __future__ import annotations

from pathlib import Path
from typing import Any

from ...config import OciConfig


class OciAuthError(RuntimeError):
    pass


def _oci() -> Any:
    try:
        import oci
    except ImportError as exc:  # pragma: no cover - optional dependency
        raise OciAuthError("install the 'oci' extra to collect OCI evidence") from exc
    return oci


def auth_context(config: OciConfig) -> tuple[dict[str, Any], Any | None]:
    oci = _oci()
    if config.auth == "instance_principal":
        return {}, oci.auth.signers.InstancePrincipalsSecurityTokenSigner()
    if config.auth == "resource_principal":
        return {}, oci.auth.signers.get_resource_principals_signer()
    path = str(Path(config.config_path).expanduser())
    values = oci.config.from_file(path, config.profile)
    if config.auth == "session_token":
        token_file = values.get("security_token_file")
        if not token_file:
            raise OciAuthError("session_token auth requires security_token_file in OCI config")
        private_key = oci.signer.load_private_key_from_file(
            str(Path(values["key_file"]).expanduser()),
            values.get("pass_phrase"),
        )
        signer = oci.auth.signers.SecurityTokenSigner(
            Path(token_file).expanduser().read_text(encoding="utf-8"),
            private_key,
        )
        return values, signer
    try:
        oci.config.validate_config(values)
    except Exception as exc:
        raise OciAuthError(f"invalid OCI config profile: {exc}") from exc
    return values, None


CLIENT_PATHS = {
    "iam": "identity.IdentityClient",
    "cloud_guard": "cloud_guard.CloudGuardClient",
    "security_zones": "cloud_guard.CloudGuardClient",
    "vault": "key_management.KmsVaultClient",
    "data_safe": "data_safe.DataSafeClient",
    "database": "database.DatabaseClient",
    "goldengate": "golden_gate.GoldenGateClient",
    "mysql": "mysql.DbSystemClient",
    "postgresql": "psql.PostgresqlClient",
    "nosql": "nosql.NosqlClient",
    "compute": "core.ComputeClient",
    "block_storage": "core.BlockstorageClient",
    "oke": "container_engine.ContainerEngineClient",
    "object_storage": "object_storage.ObjectStorageClient",
    "functions": "functions.FunctionsManagementClient",
    "container_instances": "container_instances.ContainerInstanceClient",
    "networking": "core.VirtualNetworkClient",
    "waf": "waf.WafClient",
    "network_firewall": "network_firewall.NetworkFirewallClient",
    "load_balancer": "load_balancer.LoadBalancerClient",
    "bastion": "bastion.BastionClient",
    "certificates": "certificates_management.CertificatesManagementClient",
    "api_gateway": "apigateway.GatewayClient",
    "audit": "audit.AuditClient",
    "logging": "logging.LoggingManagementClient",
    "logging_analytics": "log_analytics.LogAnalyticsClient",
    "monitoring": "monitoring.MonitoringClient",
    "events": "events.EventsClient",
    "notifications": "ons.NotificationControlPlaneClient",
    "threat_intelligence": "threat_intelligence.ThreatintelClient",
    "disaster_recovery": "disaster_recovery.DisasterRecoveryClient",
}


def create_client(service: str, config: OciConfig, region: str) -> Any:
    oci = _oci()
    dotted = CLIENT_PATHS[service]
    target: Any = oci
    for part in dotted.split("."):
        target = getattr(target, part)
    values, signer = auth_context(config)
    kwargs: dict[str, Any] = {}
    if signer is not None:
        kwargs["signer"] = signer
    client = target(values, **kwargs)
    if hasattr(client, "base_client"):
        client.base_client.set_region(region)
    return client
