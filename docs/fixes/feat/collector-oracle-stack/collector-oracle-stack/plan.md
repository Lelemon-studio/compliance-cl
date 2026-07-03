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
| `/root` | Core models, CLI, orchestration, OCI, packaging, schemas, integration | Complete |
| `/root/onprem_collectors` | DBSAT, direct SQL, middleware, fixtures, focused tests | Complete; 32 focused tests passed |
| `/root/security_auditor` | Independent contract/security tests and verification | Complete; re-audit READY |

## File ownership

| Files/globs | Owner |
|---|---|
| `collector/src/oracle_collector/collectors/{dbsat,direct_sql,middleware}.py` | `/root/onprem_collectors` |
| `collector/tests/test_{dbsat,direct_sql,middleware}.py`, `collector/tests/fixtures/onprem/**` | `/root/onprem_collectors` |
| `collector/tests/test_security_contract.py` | `/root/security_auditor` |
| All remaining `collector/**` and `docs/fixes/**` | `/root` |

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

## Implementation status

- Core, on-prem, OCI, security, schema, packaging, and documentation work: complete.
- Full collector tests: 75 passed.
- Repository-wide pytest discovery: 75 passed.
- Wheel and sdist: built successfully with contract assets included.
- CLI dry-run and offline end-to-end smoke: passed.
- Evidence bundle schema validation: passed.
- Independent audit blockers remediated with exact-signature tests for Functions, Boot Volumes, Logging Analytics, and Notifications; final re-audit READY.

## Follow-up — Bash execution wrapper

Approved interface: add `collector/run-collector.sh` with `--config`, `--out`, repeatable `--only`/`--skip`, `--dry-run`, `--offline-only`, `--encryption-key-file`, `--collector-bin`, `--help`, and `--version`.

Execution resolution order:

1. Explicit `--collector-bin`.
2. Repository `.venv/bin/collector`.
3. `collector` available on `PATH`.
4. `python3 -m oracle_collector` with local `collector/src` in `PYTHONPATH`.

The wrapper will not install dependencies. It will validate option values and the configuration path, preserve all collector exit codes, avoid `eval`, and pass arguments as a Bash array.

### Follow-up plan

1. Add failing wrapper tests for help, defaults, forwarding, repeated filters, invalid/missing options, executable resolution, and exit-code preservation.
2. Implement the Bash wrapper with strict mode and portable long-option parsing.
3. Document wrapper examples in `collector/README.md`.
4. Run `bash -n`, focused wrapper tests, and the full collector/repository test suite.
5. Append final TDD, traceability, and validation results; commit and update PR #1.

### Follow-up agent roster and ownership

| Owner | Files/task | State |
|---|---|---|
| `/root/onprem_collectors` | `collector/run-collector.sh`, `collector/tests/test_bash_wrapper.py` | Complete; 30 focused tests passed |
| `/root/security_auditor` | Independent read-only shell safety and option-forwarding audit | Complete; READY |
| `/root` | README, SDD/TDD docs, integration, full validation | Complete |

Conflicts: none. No owner may edit another owner's files concurrently.

### Follow-up result

- Bash 3.2 syntax and executable mode: passed.
- Focused wrapper suite: 30 passed.
- Full collector and repository-wide suites: 105 passed.
- Wrapper-driven dry-run and offline end-to-end bundle: passed.
- Generated bundle schema validation: passed.
- Independent AC-12 shell-safety audit: READY.

## Follow-up — Canonical configuration profile matrix

Create a standalone, secret-free profile set under `collector/configs/` for every supported on-premises stack family, OCI layer, and a hybrid deployment. Profiles are composable examples, not an attempt to enumerate every environment permutation.

### Approved profile tree

- `onprem/database/{dbsat-only,direct-sql-only,database-full}.yaml`
- `onprem/middleware/{weblogic,ohs,oam,oaa,webgate,oag,avdf,middleware-full}.yaml`
- `oci/{full-stack,identity-governance,database-data-safe,compute-storage-oke,network-perimeter,observability-dr,object-storage}.yaml`
- `hybrid/onprem-oci-full.yaml`
- `configs/README.md` with copy/rename guidance for development, QA, and production environments.

### Config-matrix plan

1. Add failing tests that discover every expected profile, load each through `load_config`, assert a unique/safe `run.name`, verify intended enabled sections/services, and scan for embedded secret keys.
2. Create all standalone YAML profiles using replacement placeholders only for identifiers and paths.
3. Document profile selection, environment cloning, wrapper commands, and the current middleware filtering boundary.
4. Run every profile through parser validation and safe offline/dry-run checks where applicable.
5. Run the full collector and repository regression suites; update AC-13 and PR #1.

### Config-matrix roster and ownership

| Owner | Files/task | State |
|---|---|---|
| `/root/onprem_collectors` | `collector/configs/onprem/**`, `collector/tests/test_config_profiles.py` | Planned reactivation after tracking commit |
| `/root/security_auditor` | Independent read-only review for secret material, unsafe defaults, and misleading scopes | Planned reactivation after profiles exist |
| `/root` | `collector/configs/oci/**`, `collector/configs/hybrid/**`, config index, main README, integration | Active |

Conflicts: none.
