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

## Follow-up — Bash execution wrapper

### Root Cause Analysis

Observed gap: the collector is runnable through its installed Python entry point, but operators do not have a repository-local shell entry point with discoverable long options. Existing README commands assume activation or installation of the console script, and no shell tests protect argument forwarding or exit-code behavior.

### How It Was Fixed

Added an executable Bash 3.2-compatible wrapper that parses only the approved long options, validates required values and files, resolves the collector executable by documented precedence, forwards values through arrays without evaluation, and uses `exec` to preserve the underlying status. Added 30 focused pytest cases covering defaults, every option, repeated filters, hostile literal values, malformed input, executable precedence/fallback, readable configuration/key files, and exit codes.

### Summary

- Added `collector/run-collector.sh` and `collector/tests/test_bash_wrapper.py`.
- Added wrapper installation, option, resolution, and example commands to `collector/README.md`.
- Preserved all Python collector behavior; the shell layer performs no install or configuration mutation.

### Validation

- `bash -n collector/run-collector.sh` → passed on GNU Bash 3.2.57.
- Focused wrapper tests → 30 passed.
- Full collector and repository-wide suites → 105 passed each.
- Wrapper dry-run/offline end-to-end/schema smoke → passed.
- Independent shell-safety audit → READY.

## Follow-up — Canonical configuration profiles

### Root Cause Analysis

Observed gap: the project has one broad example configuration, but operators need clear, independently runnable profiles for database, middleware, OCI layer, and hybrid collection. Without canonical profiles, environment-specific copies can accidentally enable unrelated collectors or mix incompatible targets.

### How It Was Fixed

Added 19 standalone YAML profiles: three database, seven single middleware plus one combined middleware, seven OCI slices, and one hybrid profile. Added a profile index with stack/environment-copy guidance and wrapper examples. Added automated discovery, production-parser, scope, service-subset, unique-name, replacement-marker, read-only middleware, and secret-material checks.

### Summary

- Added `collector/configs/onprem/database/` profiles for DBSAT, direct SQL, and combined collection.
- Added `collector/configs/onprem/middleware/` profiles for every supported middleware type and the combined stack.
- Added seven OCI layer profiles and one hybrid profile.
- Added `collector/configs/README.md` and linked it from the main collector README.
- Categorized the configuration index by deployment model: `On-premises`, `OCI`, and `Hybrid`.
- Added `collector/tests/test_config_profiles.py`.
- Expanded `collector/README.md` with a product-by-product operator guide covering every supported Oracle/OCI service, its evidence, profile, prerequisites, and execution command.
- Added `collector/tests/test_readme_products.py` to keep product and profile documentation complete.

### Validation

- Focused profile tests → 68 passed.
- Wrapper dry-run matrix → 19 of 19 profiles passed.
- Product-guide and deployment-category documentation tests → 4 passed.
- Full collector and repository-wide suites → 177 passed each.
- Independent profile safety/scope audit → READY.
- Independent product-scope and profile-category re-audit → READY.
