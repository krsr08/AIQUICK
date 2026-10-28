# PostgreSQL slice — verified results, 18 October 2026

This extends draft PR #1 with S1-03 persistence and tenant isolation. It is a review proposal, not full Sprint 1 completion or enterprise certification. The original LICENSE and previous verification evidence are preserved.

## Implemented behavior

- PostgreSQL-only SQLAlchemy repository and Alembic migration for immutable plan snapshots, expiring approvals and run history. Schema v0.2 includes tenant identity in the approved hash. No SQLite or in-memory persistence fallback.
- Separate migration/runtime roles; runtime startup refuses privileged/owner memberships or missing forced-RLS flags. Tenant context comes from provisioned accounts and the authenticated session, never request parameters; transaction-local settings prevent pool leakage.
- Database-enforced composite tenant keys, immutable plan permissions, durable idempotency and one active run per tenant. Expired worker leases become ERROR; a stale completion cannot overwrite the terminal outcome, and execution is never automatically repeated.
- Rehydration of stored approvals preserves the original expiry and records APPROVAL_RESTORED rather than pretending a human approved again.
- Windows private persistent PostgreSQL cluster with generated credentials protected by user-bound DPAPI, bounded startup/shutdown, directory ownership checks and a concurrent-launch lock. Existing PostgreSQL services/databases are untouched.
- Browser/driver discovery now occurs once in the trusted controller; the restricted browser worker receives only the resolved binary paths and its scoped policy token, not database or control-plane credentials.

## Execution evidence

**Final local result: 44 passed, zero failed/skipped, in 194.49 seconds.** One Starlette test-client deprecation warning remains. Full output and JUnit: [test output](evidence/postgres/postgres-test-output.txt), [JUnit](evidence/postgres/postgres-tests.xml). Both the real browser and dashboard produced PASS for correct expectations and FAIL for deliberately wrong expectations.

Real targeted checks already executed during implementation: PostgreSQL persistence/security suite 11 passed; migration roundtrip/DDL-denial 1 passed; persistent launcher suite 3 passed before the additional startup-failure scenario (covered by the final suite); browser/dashboard regression after driver-path correction 5 passed in 123.01 seconds. These are development runs, not additional independent reliability samples.

Environment: Windows 11, PostgreSQL 18.2, Python 3.12.13, Selenium 4.51.0, Chrome 153.0.8010.53, ChromeDriver 153.0.8010.52. The test fixture initialized a separate password-authenticated, loopback-only cluster and removed it after shutdown. The persistent-launcher test used a separate owned test directory, stopped and restarted the database, then re-read the same plan hash. It also checked encrypted credential material, concurrent-launch denial, refusal to adopt unrelated directories and cleanup after a simulated failure following actual PostgreSQL startup.

The migration test performed upgrade → downgrade → upgrade in a separate disposable database and confirmed runtime schema changes/TRUNCATE/migration attempts fail. RLS tests exercised missing tenant context, wrong-tenant reads/writes, cross-tenant API object IDs, pooled connections, immutable plans, corruption rejection, approval expiry, concurrent duplicate run requests and late worker completion.

Intermediate failures were retained: a full development run had 41 passing and 2 failing tests due to Chrome initialization producing ERROR, including a captured NoSuchDriverException; an earlier dashboard preview timeout was also observed. The controller-resolved driver-path change removed repeated discovery from the restricted worker, and the targeted real-browser regression subsequently passed. A subsequent full run passed 43 and failed one dashboard preview check. The dashboard test now replaces controlled-input text using keyboard selection/backspace and asserts the resulting values before submission; the final full run passed. Earlier failure logs are retained in evidence/postgres. No expected values were changed, tests skipped or failed runs silently relabelled. Product runs are not automatically retried.

## Supply chain and CI

The expanded dependency audit examined 87 distributions with zero reported known vulnerabilities. Bandit reported no medium/high findings; reviewed low-severity process-launch findings remain visible. A refreshed CycloneDX SBOM and exact pins are included. PostgreSQL dependency licences, including Psycopg LGPL-3.0-only terms, are documented in POSTGRES_DEPENDENCIES.md; enterprise redistribution approval remains pending.

The previous PR commit's GitHub workflow [completed successfully](https://github.com/krsr08/AIQUICK/actions/runs/39054321711). That does not establish CI success for this new commit. Updated CI locates installed PostgreSQL binaries and runs the real database suite without a skip fallback.

## Remaining gates and next work

PostgreSQL state now persists, but database files are not encrypted by this feature; synthetic data only. DPAPI protects database credentials, not database contents. RLS protects against missing tenant filters, not a compromised control-plane database login capable of changing its tenant setting. Processes still share a Windows identity; enforce network/OS isolation before expanding targets.

Still required: TLS, enterprise identity/vault, durable signed and externally anchored audit, encrypted/masked/scanned evidence with retention and backups, complete TC_CRM_001 (CRM login, multiple linked assertions, search/count, cleanup and cancellation), Edge, full escape/fault matrix, legal dependency clearance, signed commits, branch protection and independent human signoff. Demo CRM records and policy audit events remain volatile. No Salesforce/SAP support or enterprise certification is claimed.
