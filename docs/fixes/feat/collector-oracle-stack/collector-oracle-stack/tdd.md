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

## Green

Pending.

## Refactor

Pending.
