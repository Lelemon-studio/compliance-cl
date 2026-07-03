SERVICE_DEFINITIONS = {
    "data_safe": ("database", ("list_security_assessments", "list_registered_databases"), "data_safe", ["sec-rest", "data-pseudonym", "sec-logs", "inc-brechas"]),
    "database": ("database", ("list_db_systems", "list_autonomous_databases"), "tde_encryption", ["sec-rest", "sec-backups"]),
    "goldengate": ("database", ("list_deployments",), "replication", ["sec-backups"]),
    "mysql": ("database", ("list_db_systems",), "managed_database", ["sec-rest", "sec-backups"]),
    "postgresql": ("database", ("list_db_systems",), "managed_database", ["sec-rest", "sec-backups"]),
    "nosql": ("database", ("list_tables",), "managed_database", ["sec-rest", "sec-backups"]),
}

