from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from .collectors.oci.auth import OciAuthError, auth_context, create_client
from .collectors.oci.registry import SERVICE_COLLECTORS, collect_service_across_compartments
from .collectors.oci.traversal import resolve_availability_domains, resolve_compartments
from .config import CollectorConfig, ConfigError, load_config
from .encryption import load_key
from .models import CollectorResult
from .orchestrator import CollectorTask, run_tasks
from .resilience import derive_resilience_observations
from .writer import build_bundle, write_output


@dataclass(frozen=True)
class RunSelection:
    only: tuple[str, ...] = ()
    skip: tuple[str, ...] = ()
    offline_only: bool = False
    dry_run: bool = False

    def includes(self, name: str) -> bool:
        if self.offline_only and name.startswith("oci"):
            return False
        if any(name == skipped or name.startswith(f"{skipped}.") for skipped in self.skip):
            return False
        if not self.only:
            return True
        return any(name == selected or name.startswith(f"{selected}.") or selected == "oci" and name.startswith("oci.") for selected in self.only)


def _csv_items(values: Iterable[str] | None) -> tuple[str, ...]:
    items: list[str] = []
    for value in values or ():
        items.extend(part.strip() for part in value.split(",") if part.strip())
    return tuple(dict.fromkeys(items))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="collector", description="Read-only Oracle security evidence collector")
    parser.add_argument("--version", action="version", version="%(prog)s 0.1.0")
    subparsers = parser.add_subparsers(dest="command", required=True)
    run = subparsers.add_parser("run", help="collect and normalize technical evidence")
    run.add_argument("--config", required=True, help="path to collector.config.yaml")
    run.add_argument("--out", default="./out", help="parent output directory")
    run.add_argument("--only", action="append", help="collector or OCI service; repeat or comma-separate")
    run.add_argument("--skip", action="append", help="collector to skip; repeat or comma-separate")
    run.add_argument("--dry-run", action="store_true", help="validate configuration/auth and show the plan")
    run.add_argument("--offline-only", action="store_true", help="disable every OCI collector")
    run.add_argument("--encryption-key-file", help="32-byte raw or base64 AES-256-GCM key")
    return parser


def resolve_selection(config: CollectorConfig, args: argparse.Namespace) -> RunSelection:
    return RunSelection(
        only=_csv_items(args.only),
        skip=_csv_items(args.skip),
        offline_only=bool(args.offline_only or config.run.offline_only),
        dry_run=bool(args.dry_run),
    )


def _selected_oci_services(config: CollectorConfig, selection: RunSelection) -> list[str]:
    configured = list(SERVICE_COLLECTORS) if config.oci.services == "all" else list(config.oci.services)
    return [service for service in configured if selection.includes(f"oci.{service}")]


def _result_from_records(records: list[Any], service: str) -> CollectorResult:
    return CollectorResult(evidence=records, services_scanned=[service])


def _onprem_tasks(config: CollectorConfig, selection: RunSelection, out_dir: Path) -> list[CollectorTask]:
    tasks: list[CollectorTask] = []
    db_config = dict(config.onprem_db)
    if bool(db_config.get("enabled", False)):
        dbsat = dict(db_config.get("dbsat", {}) or {})
        if selection.includes("dbsat"):
            from .collectors.dbsat import DBSATCollector

            binary = dbsat.get("binary")
            for target_value in dbsat.get("targets", []):
                target = dict(target_value)
                alias = str(target.get("alias", "database"))

                def collect_dbsat(target: dict[str, Any] = target, alias: str = alias) -> CollectorResult:
                    staging = out_dir / config.run.name / "raw" / "dbsat"
                    records = DBSATCollector().collect(target, binary=binary, raw_dir=staging)
                    result = _result_from_records(records, "dbsat")
                    report = target.get("report_path") or staging / f"{alias}.report.json"
                    report_path = Path(report)
                    if report_path.exists():
                        result.raw_files[f"dbsat/{alias}.report.json"] = json.loads(report_path.read_text(encoding="utf-8"))
                    return result

                tasks.append(CollectorTask(f"dbsat.{alias}", collect_dbsat))

        direct = dict(db_config.get("direct_sql", {}) or {})
        if bool(direct.get("enabled", False)) and selection.includes("direct_sql"):
            from .collectors.direct_sql import DirectSQLCollector

            defaults = {key: value for key, value in direct.items() if key != "targets"}
            for target_value in direct.get("targets", []):
                target = {**defaults, **dict(target_value)}
                alias = str(target.get("alias", "database"))
                tasks.append(
                    CollectorTask(
                        f"direct_sql.{alias}",
                        lambda target=target: _result_from_records(DirectSQLCollector().collect(target), "direct_sql"),
                    )
                )

    middleware = dict(config.onprem_middleware)
    if bool(middleware.get("enabled", False)) and selection.includes("middleware"):
        from .collectors.middleware import MiddlewareCollector

        targets = [dict(target) for target in middleware.get("targets", [])]
        tasks.append(
            CollectorTask(
                "middleware",
                lambda: _result_from_records(MiddlewareCollector().collect(targets), "middleware"),
            )
        )
    return tasks


def _oci_tasks(config: CollectorConfig, selection: RunSelection) -> tuple[list[CollectorTask], dict[str, Any]]:
    if not config.oci.enabled or selection.offline_only:
        return [], {}
    services = _selected_oci_services(config, selection)
    if not services:
        return [], {}
    identity_region = config.oci.regions[0]
    identity = create_client("iam", config.oci, identity_region)
    tenancy = config.oci.tenancy_ocid
    if not tenancy:
        values, _ = auth_context(config.oci)
        tenancy = values.get("tenancy")
    if not tenancy:
        raise OciAuthError("OCI tenancy OCID is required")
    compartments = resolve_compartments(identity, tenancy, config.oci.compartments)
    context_by_compartment: dict[str, dict[str, Any]] = {}
    if "block_storage" in services:
        for compartment in compartments:
            try:
                domains = resolve_availability_domains(identity, compartment)
            except Exception:
                domains = []
            context_by_compartment[compartment] = {"availability_domains": domains}
    tasks: list[CollectorTask] = []
    for region in config.oci.regions:
        for service in services:
            client = create_client(service, config.oci, region)
            tasks.append(
                CollectorTask(
                    f"oci.{service}",
                    lambda service=service, client=client, compartments=tuple(compartments), region=region, contexts=context_by_compartment: collect_service_across_compartments(
                        service, client, compartments, region, context_by_compartment=contexts
                    ),
                    region=region,
                )
            )
    environment = {
        "oci": {
            "tenancy_ocid": tenancy,
            "regions": list(config.oci.regions),
            "compartments_scanned": len(compartments),
        }
    }
    return tasks, environment


def _plan(config: CollectorConfig, selection: RunSelection) -> dict[str, Any]:
    services = _selected_oci_services(config, selection) if config.oci.enabled and not selection.offline_only else []
    return {
        "run": config.run.name,
        "redaction": config.run.redaction,
        "offline_only": selection.offline_only,
        "only": list(selection.only),
        "skip": list(selection.skip),
        "oci_regions": list(config.oci.regions) if services else [],
        "oci_services": services,
        "onprem_db": bool(config.onprem_db.get("enabled", False)),
        "onprem_middleware": bool(config.onprem_middleware.get("enabled", False)),
        "mutations": [],
    }


def execute(config: CollectorConfig, args: argparse.Namespace) -> int:
    selection = resolve_selection(config, args)
    if selection.dry_run:
        if config.oci.enabled and not selection.offline_only and _selected_oci_services(config, selection):
            auth_context(config.oci)
        print(json.dumps(_plan(config, selection), indent=2, sort_keys=True))
        return 0

    out_dir = Path(args.out)
    tasks = _onprem_tasks(config, selection, out_dir)
    oci_tasks, environment = _oci_tasks(config, selection)
    tasks.extend(oci_tasks)
    result = run_tasks(tasks, config.run.parallelism)
    result.environment.update(environment)
    db_targets = []
    db_config = dict(config.onprem_db)
    for section_name in ("dbsat", "direct_sql"):
        section = dict(db_config.get(section_name, {}) or {})
        db_targets.extend(
            {"alias": str(target.get("alias", "database"))}
            for target in section.get("targets", [])
        )
    if db_targets:
        result.environment["onprem_db"] = list({item["alias"]: item for item in db_targets}.values())
    result.resilience_tier_observed.update(derive_resilience_observations(result.evidence))
    bundle = build_bundle(config, result)
    key = load_key(args.encryption_key_file) if args.encryption_key_file else None
    run_dir = write_output(bundle, result, out_dir, encryption_key=key)
    print(run_dir)
    return result.exit_code


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        config = load_config(args.config)
        return execute(config, args)
    except (ConfigError, OciAuthError, OSError, ValueError) as exc:
        print(f"collector: {exc}", file=sys.stderr)
        return 1
