SERVICE_DEFINITIONS = {
    "iam": ("iam", ("list_users", "list_groups", "list_policies"), "mfa_state", ["sec-mfa", "sec-tenant"]),
    "cloud_guard": ("monitoring", ("list_problems", "list_targets"), "cloud_guard", ["inc-brechas", "sec-monitoring"]),
    "security_zones": ("iam", ("list_security_zones",), "security_zone", ["sec-tenant"]),
    "vault": ("iam", ("list_vaults",), "key_management", ["sec-secrets", "sec-rest"]),
}

