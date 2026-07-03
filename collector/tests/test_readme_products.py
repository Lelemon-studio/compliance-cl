from __future__ import annotations

from pathlib import Path


COLLECTOR_ROOT = Path(__file__).resolve().parents[1]
README = COLLECTOR_ROOT / "README.md"
CONFIG_ROOT = COLLECTOR_ROOT / "configs"
CONFIG_README = CONFIG_ROOT / "README.md"

REQUIRED_PRODUCTS = {
    "DBSAT",
    "Direct SQL",
    "WebLogic",
    "Oracle HTTP Server (OHS)",
    "Oracle Access Manager (OAM)",
    "Oracle Advanced Authentication (OAA)",
    "WebGate",
    "Oracle API Gateway on-premises (OAG)",
    "Audit Vault and Database Firewall (AVDF)",
    "OCI IAM",
    "Cloud Guard",
    "Security Zones",
    "OCI Vault/KMS",
    "OCI Data Safe",
    "OCI Database",
    "GoldenGate",
    "MySQL HeatWave",
    "OCI Database with PostgreSQL",
    "NoSQL Database Cloud",
    "OCI Compute",
    "Block/Boot Volume",
    "Oracle Kubernetes Engine (OKE)",
    "Object Storage",
    "OCI Functions",
    "Container Instances",
    "VCN/Networking",
    "OCI WAF",
    "Network Firewall",
    "Load Balancer",
    "OCI Bastion",
    "OCI Certificates",
    "OCI API Gateway",
    "OCI Audit",
    "OCI Logging",
    "Logging Analytics",
    "OCI Monitoring",
    "OCI Events",
    "OCI Notifications",
    "Threat Intelligence",
    "Full Stack Disaster Recovery",
}


def test_main_readme_indexes_every_supported_product() -> None:
    text = README.read_text(encoding="utf-8")
    missing = sorted(product for product in REQUIRED_PRODUCTS if product not in text)
    assert missing == []


def test_main_readme_links_every_canonical_profile() -> None:
    text = README.read_text(encoding="utf-8")
    profiles = sorted(path.relative_to(COLLECTOR_ROOT).as_posix() for path in CONFIG_ROOT.rglob("*.yaml"))
    assert len(profiles) == 19
    missing = [profile for profile in profiles if profile not in text]
    assert missing == []


def test_main_readme_includes_wrapper_usage_for_each_stack_family() -> None:
    text = README.read_text(encoding="utf-8")
    assert text.count("./collector/run-collector.sh") >= 8
    assert "--only middleware" in text
    assert "--only dbsat" in text
    assert "--only direct_sql" in text
    assert "--only oci" in text
    assert "--only oci.object_storage" in text


def test_config_readme_is_categorized_by_deployment_model() -> None:
    text = CONFIG_README.read_text(encoding="utf-8")
    assert "## On-premises" in text
    assert "## OCI" in text
    assert "## Hybrid" in text

    onprem = text.split("## On-premises", 1)[1].split("## OCI", 1)[0]
    oci = text.split("## OCI", 1)[1].split("## Hybrid", 1)[0]
    hybrid = text.split("## Hybrid", 1)[1]

    assert "configs/onprem/database/dbsat-only.yaml" in onprem
    assert "configs/onprem/middleware/weblogic.yaml" in onprem
    assert "configs/oci/full-stack.yaml" in oci
    assert "configs/oci/object-storage.yaml" in oci
    assert "configs/hybrid/onprem-oci-full.yaml" in hybrid
