SERVICE_DEFINITIONS = {
    "audit": ("monitoring", ("list_events",), "audit_configuration", ["sec-logs", "gov-auditoria"]),
    "logging": ("monitoring", ("list_log_groups",), "logging_configuration", ["sec-logs"]),
    "logging_analytics": ("monitoring", ("list_log_analytics_entities",), "logging_analytics", ["sec-monitoring"]),
    "monitoring": ("monitoring", ("list_alarms",), "security_alarms", ["sec-monitoring"]),
    "events": ("monitoring", ("list_rules",), "event_rules", ["inc-brechas"]),
    "notifications": ("monitoring", ("list_topics",), "notifications", ["inc-brechas"]),
    "threat_intelligence": ("monitoring", ("list_indicators",), "threat_intelligence", ["sec-monitoring"]),
    "disaster_recovery": ("monitoring", ("list_dr_protection_groups",), "disaster_recovery", ["sec-backups", "inc-brechas"]),
}

