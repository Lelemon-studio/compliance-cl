# Changes — Oracle Compliance Collector

## Root Cause Analysis

Observed gap: the repository contains a detailed Oracle collector specification but no executable collector, package metadata, schemas, or tests. The underlying cause is that the specification was added as design input before implementation. Existing repository guardrails focus on legal-content contributions and do not yet provide software test or packaging infrastructure for this component.

## How It Was Fixed

Created a Python package under `collector/` with a `collector` CLI, typed evidence/configuration models, partial-failure orchestration, normalization/mapping, resilience proposals, redaction, AES-256-GCM output, raw artifact writing, and JSON contracts. Added safe on-prem adapters for DBSAT, allowlisted Oracle catalog SQL, and exported middleware JSON. Added an extensible OCI registry covering every service family in the specification, with lazy SDK auth, pagination, throttling backoff, region/compartment aggregation, operation-level degradation, and IAM write-permission warnings.

The fix addresses the underlying gap by shipping runnable code, schemas, mocked fixtures, 65 automated tests, an example configuration, packaged contract assets, and operational/least-privilege documentation. The collector enforces technical signals only and leaves legal conclusions to the downstream GPT stage.

## Summary

- Added the complete collector package, CLI, configuration, schemas, remediation catalog, and README.
- Added read-only DBSAT, direct SQL, middleware, and OCI collectors.
- Added strict/minimal redaction, secret-safe logs/raw output, and optional AES-256-GCM encryption.
- Added registry-driven OCI coverage for all services named in §5.3.
- Added mocked tests and SDD traceability for AC-01 through AC-11.

## Validation

- `python -m pytest collector/tests -q` → 75 passed.
- `python -m pytest -q` → 75 passed.
- `python -m build collector` → wheel and sdist built successfully.
- `collector --help` and offline `--dry-run` → passed.
- Offline end-to-end bundle generation and JSON Schema validation → passed.
- Both JSON schemas pass Draft 2020-12 metaschema validation.
- Wheel contains the remediation catalog and both schemas.
- Production-source secret-pattern scan → no matches.
- `python -m compileall -q collector/src` and `git diff --check` → passed.
- Independent audit blockers were converted into 12 RED regressions and fixed; focused post-fix suite: 24 passed.
- Independent final re-audit → READY; no remaining blocker-level defects.
