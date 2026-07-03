SERVICE_DEFINITIONS = {
    "compute": ("compute", ("list_instances",), "compute_hardening", ["sec-rest", "sec-monitoring"]),
    "block_storage": ("storage", ("list_volumes", "list_boot_volumes"), "volume_encryption", ["sec-rest", "sec-backups"]),
    "oke": ("oke", ("list_clusters", "list_node_pools"), "cluster_security", ["sec-secrets", "sec-monitoring"]),
    "object_storage": ("storage", ("list_buckets",), "public_access", ["sec-rest", "sec-backups", "inc-brechas"]),
    "functions": ("compute", ("list_applications", "list_functions"), "function_security", ["sec-secrets", "sec-tenant"]),
    "container_instances": ("compute", ("list_container_instances",), "container_security", ["sec-secrets", "sec-tenant"]),
}
