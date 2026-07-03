# TDD Log — Oracle Compliance Collector

## Red — planned first cycle

The first implementation cycle will begin with failing tests for:

1. Configuration validation and CLI mode resolution.
2. Evidence schema constraints, especially `signal` without legal `status`.
3. Strict/minimal redaction and secret-safe logging.
4. Safe direct-SQL allowlisting and SYSDBA rejection.
5. Partial collector failure isolation and exit code 2.
6. OCI pagination/backoff and unsupported-service degradation.

No test has been run yet. Tracking artifacts and the mandatory draft PR precede implementation.

### Red execution 1 — 2026-07-03

Command:

`python3 -m pytest collector/tests/test_config_cli.py collector/tests/test_models_mapping.py collector/tests/test_orchestrator.py collector/tests/test_oci_registry.py collector/tests/test_writer_schema.py collector/tests/test_resilience.py -q`

Result: expected RED during collection. Six test modules failed to import because the planned `oracle_collector` production modules did not exist yet (`cli`, `config`, `models`, `mapper`, `orchestrator`, OCI registry/traversal, writer, and resilience). This confirms the first tests precede implementation.

## Green

### On-prem cycle

- RED: three collection errors because `dbsat`, `direct_sql`, and `middleware` modules did not exist.
- GREEN: 32 focused tests passed after implementing safe DBSAT invocation/parsing, catalog SQL allowlisting, privileged-session rejection, and exported middleware JSON adapters.

### Integrated cycle

- Initial integrated GREEN: 56 tests passed.
- OCI aggregation RED: missing `collect_service_across_compartments` caused collection failure.
- OCI aggregation GREEN: five focused OCI tests passed; full suite reached 58 passed.
- Security/coverage RED: three failures exposed incomplete IAM operation traversal, minimal-mode OCID leakage, and URI/Oracle DSN credential leakage.
- Security/coverage GREEN: targeted suite passed; full suite reached 61 passed.
- Resilience RED: missing evidence-to-tier derivation API.
- Serialization RED: OCI SDK `datetime` values were not JSON serializable.
- Final GREEN: 65 tests passed after resilience derivation, recursive JSON-safe conversion, OCI session-token signer coverage, and AES-256-GCM verification.

### Independent audit remediation cycle

- Audit verdict: not ready. Concrete blockers were parent-specific OCI parameters, Notifications client selection, dishonest scanned coverage after total failure, secret-key suffixes, and quoted/incomplete log secret forms.
- RED: 12 failures across exact SDK-signature, coverage-honesty, config-secret, and log-redaction tests.
- GREEN: 24 focused tests passed after adding Functions application traversal, Boot Volume availability-domain context, Logging Analytics namespace discovery, Notifications control-plane client mapping, scan-success accounting, secret suffix rejection, and hardened log patterns.
- Full GREEN: 75 tests passed collector-wide and repository-wide.

## Refactor

- Consolidated OCI service definitions into a registry spanning every §5.3 service family.
- Aggregated compartments into one raw artifact per service/region to avoid overwrites.
- Added all supported list operations per service rather than stopping at the first operation.
- Added final-boundary redaction for bundles and raw artifacts.
- Included remediation catalog and both JSON schemas in built wheel data.
- Added least-privilege, operation, security, and limitation documentation.

## Final validation

- `python -m pytest collector/tests -q` → 75 passed.
- `python -m pytest -q` → 75 passed repository-wide.
- `python -m build collector` → wheel and sdist built successfully.
- CLI help and offline dry-run → passed.
- Offline end-to-end bundle generation → passed.
- Draft 2020-12 metaschema checks and generated bundle validation → passed.
- `python -m compileall -q collector/src` → passed.
- `git diff --check` → passed.

## Follow-up TDD — Bash execution wrapper

### Red — planned

Add tests before the wrapper exists for help output, default config/output forwarding, repeatable `--only` and `--skip`, boolean/encryption options, explicit binary resolution, malformed arguments, missing configuration, and underlying exit-code preservation.

### Green

- RED command: `python3 -m pytest collector/tests/test_bash_wrapper.py -q`.
- RED result: 22 failures because `collector/run-collector.sh` did not exist.
- GREEN result: 30 focused wrapper tests passed on GNU Bash 3.2.57.
- Implementation uses strict mode, Bash arrays, exact long-option parsing, repository-root virtualenv resolution, explicit executable validation, local Python fallback, and `exec` for exact status propagation.

### Refactor

- Corrected virtualenv discovery to `$SCRIPT_DIR/../.venv/bin/collector`.
- Added adversarial literal-argument tests for spaces, glob characters, semicolons, and `$()`.
- Added missing/next-option value tests, config/key validation, precedence tests, and exit-code cases `0`, `1`, `2`, and `23`.
- Documented wrapper operation and stack-selection examples in `collector/README.md`.

### Follow-up validation

- `bash -n collector/run-collector.sh` → passed.
- Executable mode → `-rwxr-xr-x`.
- `python -m pytest collector/tests/test_bash_wrapper.py -q` → 30 passed.
- `python -m pytest collector/tests -q` → 105 passed.
- `python -m pytest -q` → 105 passed repository-wide.
- Wrapper help, version, and offline dry-run → passed.
- Wrapper-driven offline end-to-end output and JSON Schema validation → passed.
- `git diff --check` → passed.
- Independent AC-12 audit → READY; no remaining blocker.

## Follow-up TDD — Canonical configuration profiles

### Red — planned

Add discovery and validation tests before the profile tree exists. Tests will require all approved filenames, parse each YAML through `load_config`, verify unique run names and intended source/service selection, and reject embedded secret keys or unsafe placeholder values.

### Green

Pending.

### Refactor

Pending.
