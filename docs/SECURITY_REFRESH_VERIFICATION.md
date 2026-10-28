# Dependency security refresh — 24 October 2026

GitHub CI run 40066707431 failed its dependency audit before executing tests. Its seven findings affected certifi 2026.7.22 (PYSEC-2026-4320) and filelock 4.2.0 (CVE-2026-112906, CVE-2026-112940, CVE-2026-112914, CVE-2026-112913, CVE-2026-112937, CVE-2026-112907). A fresh local audit reproduced all seven findings.

The lock now pins certifi 2026.10.19 and filelock 4.2.1, the fixed versions reported by the audit. No vulnerability exemptions or weakened CI gates were introduced. Other pins remain unchanged.

## Executed validation

- Installation succeeded and pip check reported no broken requirements.
- Fresh pip-audit: 87 packages, zero known vulnerabilities, exit 0. This is a point-in-time database result, not a guarantee that packages contain no vulnerabilities.
- Full Windows suite with real PostgreSQL and Chrome: **70 passed, zero failed/skipped, 224.42 seconds**, exit 0. One existing Starlette test-client deprecation warning remains.
- Bandit at the configured medium/high threshold: exit 0.
- CycloneDX environment SBOM regenerated successfully.

Raw before/after audits, the failing CI audit, JUnit, full test output, Bandit report and SBOM are retained in [evidence/security-refresh](evidence/security-refresh/). Earlier test and audit reports remain historical. GitHub CI for the new commit must be checked separately; local success does not establish remote success.

This repairs the dependency gate for the synthetic preview. It does not complete the enterprise blueprint. See [the requirements ledger](REQUIREMENTS_STATUS.md) for unimplemented controls, integrations and external signoffs.
