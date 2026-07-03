# Requirements Traceability

| Criterion | Planned implementation | Planned tests/validation | Status |
|---|---|---|---|
| AC-01 | `collector/pyproject.toml`, package entry points | Wheel/sdist build and `collector --help` | Passed |
| AC-02 | `cli.py`, `config.py`, `orchestrator.py` | Config/CLI tests plus dry-run/offline smoke | Passed |
| AC-03 | On-prem and OCI collector modules | Mocked DBSAT, SQL, middleware, and OCI tests | Passed |
| AC-04 | OCI auth/traversal/registry/service modules | Pagination, compartments, multi-operation, aggregation, auth tests | Passed |
| AC-05 | `orchestrator.py`, `models.py`, `cli.py` | Partial failure and exit-code tests | Passed |
| AC-06 | `writer.py`, raw artifacts, mapper/resilience modules | Bundle, raw, catalog, resilience, and schema tests | Passed |
| AC-07 | `models.py`, `normalizer.py`, `mapper.py` | Allowed-signal and legal-status rejection tests | Passed |
| AC-08 | `direct_sql.py`, DBSAT/middleware/OCI guardrails | Allowlist, SYS/SYSTEM/privileged, credential, endpoint tests | Passed |
| AC-09 | `redaction.py`, `encryption.py` | Secret corpus, OCID, URI/DSN, log, and AES-GCM tests | Passed |
| AC-10 | Both JSON schemas | Metaschema checks and generated bundle validation | Passed |
| AC-11 | `collector/README.md`, example config | Documentation review and CLI smoke | Passed |
| AC-12 | `collector/run-collector.sh`, README wrapper section | Bash syntax, forwarding/error/exit tests, full regression | Planned follow-up |

## Final validation matrix

Validation environment: isolated temporary Python 3.14 environment for core tests and packaging. OCI deployment documentation recommends Python 3.9–3.11, matching Oracle's currently documented SDK support range.

- Collector suite: 75 passed.
- Repository-wide discovery: 75 passed.
- Build: `oracle_compliance_collector-0.1.0.tar.gz` and `oracle_compliance_collector-0.1.0-py3-none-any.whl` created.
- Wheel inspection: remediation catalog and both JSON schemas present.
- Offline generated bundle: valid against `evidence-bundle.schema.json`.
- OCI parent-specific signature tests: Functions, Boot Volumes, Logging Analytics, and Notifications passed.
- Coverage honesty: a service with no successful operation is skipped and never marked scanned.
- Independent re-audit: READY; AC-03, AC-04, AC-06, and prior security findings passed.
