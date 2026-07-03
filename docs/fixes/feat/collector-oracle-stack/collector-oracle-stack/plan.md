# Collector Oracle Stack — Implementation Plan

## Context

Implement `specs/collector-oracle-stack.spec.md` as a new Python 3.9+ project under `collector/`. The collector gathers read-only Oracle on-premises and OCI security configuration evidence and emits an auditable, redacted `evidence-bundle.json`. It never makes a legal compliance determination.

Branch: `feat/collector-oracle-stack`  
Base: `main`  
Task: `collector-oracle-stack`  
Tracking PR: https://github.com/oracletechcl/compliance-cl/pull/1

## Approved decisions

1. Use SDD and treat `specs/collector-oracle-stack.spec.md` as the source of truth.
2. Include WebLogic, OHS, OAM/OAA/WebGate, OAG, and AVDF read-only middleware adapters in v1.
3. Include optional `python-oracledb` catalog queries; reject SYSDBA and unsafe sessions.
4. Support one OCI tenancy per run; defer federated multi-tenancy.
5. Let the collector propose a resilience tier from observed signals; downstream GPT owns the final assessment.
6. Keep GPT execution out of scope; publish its input/output contract and assessment schema.

## Implementation plan

1. Establish package metadata, dependency groups, CLI entry point, example configuration, and typed models.
2. Write failing tests for configuration, execution modes, evidence contracts, read-only restrictions, redaction, partial failures, and schema validation.
3. Implement shared configuration, models, normalization, control mapping, remediation catalog loading, resilience heuristics, redaction, encryption, writing, and orchestration.
4. Implement DBSAT invocation/parsing, safe direct SQL, and read-only middleware configuration adapters.
5. Implement OCI authentication, pagination, region/compartment traversal, throttling backoff, and registry-driven service adapters covering §5.3.
6. Implement resumable raw artifacts, dry-run/offline/only/skip modes, partial-error aggregation, and exit codes 0/2/fatal.
7. Add JSON schemas, mocked fixtures, operational documentation, and least-privilege policy/role guidance.
8. Run targeted tests, full repository discovery, package build, install/CLI smoke tests, and schema validation.
9. Complete TDD/SDD evidence, commit task files, push, and mark the draft PR ready.

## Planned files

- `collector/pyproject.toml`
- `collector/README.md`
- `collector/collector.config.example.yaml`
- `collector/remediation_catalog.json`
- `collector/schema/evidence-bundle.schema.json`
- `collector/schema/assessment.schema.json`
- `collector/src/oracle_collector/{__init__,__main__,cli,config,models,orchestrator,normalizer,mapper,writer,redaction,encryption,resilience}.py`
- `collector/src/oracle_collector/collectors/{__init__,base,dbsat,direct_sql,middleware}.py`
- `collector/src/oracle_collector/collectors/oci/{__init__,auth,traversal,registry,identity_governance,database,compute,network,observability}.py`
- `collector/tests/` unit tests and mocked DBSAT/OCI/middleware fixtures
- This task directory's `plan.md`, `spec.md`, `traceability.md`, `tdd.md`, and `changes.md`

## Agent roster

| Owner | Task | State |
|---|---|---|
| Root integration owner | Core models, CLI, orchestration, OCI, packaging, schemas, integration | Planned |
| On-prem implementation agent | DBSAT, direct SQL, middleware, fixtures, focused tests | Planned; spawn after tracking PR |
| TDD/security auditor | Independent contract/security review and verification | Planned; spawn after tracking PR |

## File ownership

| Files/globs | Owner |
|---|---|
| `collector/src/oracle_collector/collectors/{dbsat,direct_sql,middleware}.py` | On-prem implementation agent |
| `collector/tests/test_{dbsat,direct_sql,middleware}.py`, matching fixtures | On-prem implementation agent |
| Independent review; auditor-authored tests in separately agreed files | TDD/security auditor |
| All remaining `collector/**` and `docs/fixes/**` | Root integration owner |

No concurrent overlap is permitted. Conflicts: none.

## TDD sequence

### Red

Create failing tests that prove configuration/CLI behavior, safe query restrictions, evidence normalization, registry degradation, redaction, output contracts, and partial-error exit semantics.

### Green

Implement the smallest cohesive modules needed to satisfy each focused test group.

### Refactor

Consolidate registry metadata, mappings, serialization, error handling, and fixtures while keeping all tests green.

## Validation commands

- `python3 -m pytest collector/tests`
- `python3 -m pytest`
- `python3 -m build collector`
- Installed `collector --help` smoke test
- Example-config `--dry-run`, `--offline-only`, and invalid-config smoke tests
- JSON Schema validation through automated tests

`python3 -m pytest` is the approved full-regression command because the repository had no pre-existing root `tests/` directory or test manifest when planning began.

## Pull request tracking

Draft PR: https://github.com/oracletechcl/compliance-cl/pull/1

Initial tracking commit: `ca30eba`
