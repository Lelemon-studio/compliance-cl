SERVICE_DEFINITIONS = {
    "networking": ("network", ("list_vcns", "list_subnets", "list_network_security_groups"), "network_segmentation", ["sec-tenant"]),
    "waf": ("waf", ("list_web_app_firewalls", "list_web_app_firewall_policies"), "waf_policy", ["sec-monitoring"]),
    "network_firewall": ("network", ("list_network_firewalls",), "network_firewall", ["sec-monitoring"]),
    "load_balancer": ("network", ("list_load_balancers",), "tls_configuration", ["sec-tls"]),
    "bastion": ("network", ("list_bastions",), "bastion_access", ["sec-tenant"]),
    "certificates": ("network", ("list_certificates",), "tls_certificate", ["sec-tls"]),
    "api_gateway": ("network", ("list_gateways",), "gateway_security", ["sec-tls", "sec-tenant"]),
}

