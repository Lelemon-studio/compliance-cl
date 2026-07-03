# Requirements Traceability

| Criterion | Planned implementation | Planned tests/validation | Status |
|---|---|---|---|
| AC-01 | `collector/pyproject.toml`, package entry points | Package build/install and `collector --help` | Planned |
| AC-02 | `cli.py`, `config.py`, `orchestrator.py` | Config and CLI mode tests; smoke tests | Planned |
| AC-03 | On-prem and OCI collector modules | Mocked DBSAT, SQL, middleware, and OCI tests | Planned |
| AC-04 | OCI auth/traversal/registry/service modules | Pagination, region, compartment, retry tests | Planned |
| AC-05 | `orchestrator.py`, `models.py`, `cli.py` | Partial/fatal failure and exit-code tests | Planned |
| AC-06 | `writer.py`, collector raw artifacts, mapper/resilience modules | Bundle snapshot/schema and raw-path tests | Planned |
| AC-07 | `models.py`, `normalizer.py`, `mapper.py` | Reject legal `status`; allowed-signal tests | Planned |
| AC-08 | `direct_sql.py`, DBSAT/middleware/OCI guardrails | Unsafe-session and mutating-operation tests | Planned |
| AC-09 | `redaction.py`, `encryption.py`, logging filter | Secret corpus, strict/minimal, AES-GCM tests | Planned |
| AC-10 | Both JSON schemas | Automated `jsonschema` validation | Planned |
| AC-11 | `collector/README.md`, example config | Documentation review and example smoke test | Planned |

## Final validation matrix

Final commit hashes, exact test names, command results, and pass/fail status will be recorded here during Phases 3–4.
