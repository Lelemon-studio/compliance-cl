# Canonical Specification — Oracle Compliance Collector

## Source of truth

This SDD specification derives from `specs/collector-oracle-stack.spec.md` and the user's approved Phase 1 decisions. If this document conflicts with the source specification, the source specification wins unless a decision below explicitly resolves one of its open questions.

## Objective

Build a Python 3.9+ command-line collector under `collector/` that gathers read-only Oracle on-premises and OCI configuration evidence relevant to Chilean Law 21.719 controls, normalizes and redacts it, and writes an auditable evidence package for a downstream GPT assessment stage.

## Scope

- YAML configuration with CLI overrides.
- DBSAT 4.0+ execution and JSON parsing.
- Optional read-only Oracle catalog SQL using `python-oracledb`.
- Read-only WebLogic, OHS, OAM/OAA/WebGate, OAG, and AVDF adapters.
- OCI inventory and security signals across every service family named in §5.3 using a registry-driven, extensible design.
- Single-tenancy, multi-region, recursive-compartment OCI traversal.
- Partial-failure isolation, concurrency, pagination, throttling backoff, and resumable raw artifacts.
- Common evidence model, control mappings, remediation candidates, and proposed resilience tiers.
- Strict/minimal redaction, secret-safe logging, and optional AES-256-GCM output encryption.
- Evidence and downstream assessment JSON schemas.
- Mocked tests requiring no real Oracle database, middleware, or OCI tenant.
- Operations and least-privilege documentation.

## Non-goals

- No write, mutate, remediate, or deployment operations.
- No application-table or personal-data reads.
- No legal compliance verdict in collector output.
- No GPT execution or automatic `assessment.json` generation.
- No multi-tenancy federation in v1.
- No replacement of DBSAT or exploitation/vulnerability scanning.

## Security invariants

1. Database SQL is allowlisted catalog/configuration `SELECT` only.
2. SYSDBA and unsafe database sessions are rejected before collection.
3. OCI collectors invoke list/get/read-style SDK operations only.
4. Secret values, keys, tokens, passwords, and Vault material never enter output or logs.
5. Strict redaction hashes/truncates sensitive identifiers; minimal mode preserves only explicitly allowed local traceability.
6. Every evidence record references its raw source when a raw artifact exists.

## Acceptance criteria

- **AC-01:** The package installs on Python 3.9+ and exposes a `collector` CLI.
- **AC-02:** Config validation and CLI support full run, OCI-only/skip-DBSAT, dry-run, and offline-only modes plus `--only` service selection.
- **AC-03:** DBSAT, direct SQL, middleware, and OCI collectors emit normalized evidence without requiring live infrastructure in tests.
- **AC-04:** OCI traversal supports configured regions, compartment subtrees, pagination, service selection, and throttling backoff.
- **AC-05:** A collector failure does not abort unrelated collectors; exit 0 means complete, exit 2 means partial/skipped, and fatal configuration/authentication errors are nonzero.
- **AC-06:** Output contains inventory, evidence, remediation catalog, proposed resilience tiers, honest coverage, warnings, errors, raw artifacts, and a secret-safe log.
- **AC-07:** Evidence contains technical `signal` values only and never a legal `status` verdict.
- **AC-08:** Read-only guardrails reject unsafe DB access and prevent business-data or mutating operations.
- **AC-09:** Redaction removes credentials and secrets from structured output and logs; optional encryption uses AES-256-GCM.
- **AC-10:** `evidence-bundle.json` and documented `assessment.json` validate against shipped JSON schemas.
- **AC-11:** README documents setup, modes, minimum OCI policies, minimum DB role, security boundaries, and operational examples.

## Assumptions

- One OCI tenancy is processed per run.
- Optional OCI and Oracle DB libraries are imported lazily so offline fixture tests remain portable.
- Middleware adapters accept exported/read-only configuration or injectable clients; they do not require proprietary servers during tests.
- Resilience tiers are heuristic observations for downstream review, not compliance conclusions.

## Open questions

None. Phase 1 decisions resolved all source-spec implementation questions.

## Follow-up specification — Bash execution wrapper

Add an executable Bash wrapper at `collector/run-collector.sh` that exposes the Python collector's run options without duplicating collection logic.

### Scope

- Long options: `--config`, `--out`, `--only`, `--skip`, `--dry-run`, `--offline-only`, `--encryption-key-file`, `--collector-bin`, `--help`, and `--version`.
- Defaults: `--config ./collector.config.yaml` and `--out ./out`.
- Repeatable `--only` and `--skip` values forwarded in original order.
- Executable resolution: explicit binary, repository `.venv`, `PATH`, then local Python module fallback.
- Clear errors for missing values, unknown options, absent configuration files, and unusable executables.
- Exact propagation of the underlying collector exit status.

### Non-goals

- No dependency installation or virtual-environment creation.
- No configuration mutation.
- No reimplementation of Python CLI validation or collector behavior.

- **AC-12:** The Bash wrapper safely forwards every supported option, documents its resolution/default behavior, preserves exit codes, and passes syntax, focused wrapper, and full regression validation.

## Follow-up specification — Canonical configuration profiles

Create standalone YAML profiles under `collector/configs/` for supported Oracle stack slices:

- On-premises database: DBSAT only, direct SQL only, and combined database collection.
- On-premises middleware: WebLogic, OHS, OAM, OAA, WebGate, OAG, AVDF, and combined middleware.
- OCI: full stack plus identity/governance, database/Data Safe, compute/storage/OKE, network/perimeter, observability/DR, and Object Storage slices.
- Hybrid: combined on-premises database, middleware, and OCI.

Every profile must load through the production configuration parser, remain free of embedded secrets, use a unique safe `run.name`, enable only its intended stack sections, and contain explicit replacement placeholders for tenant-specific identifiers and filesystem paths. Profiles are copied and customized per environment; no YAML include/merge mechanism is introduced.

- **AC-13:** All canonical profiles exist, parse successfully, contain no embedded secret material, accurately select their documented stack slice, and are indexed with wrapper commands and environment-copy guidance.
