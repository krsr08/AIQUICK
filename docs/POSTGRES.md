# PostgreSQL storage and migration

Migration `0001_tenant_storage` creates the `autoqa` schema with plan_snapshots, approvals and test_runs. SQLAlchemy Core exports `metadata`, `plans`, `approvals`, `runs` from `autoqa.persistence.schema`. All timestamps are timezone-aware PostgreSQL timestamps; JSON payloads use JSONB. The repository must explicitly update `updated_at` when a run changes.

## Roles and tenant boundaries

An administrator provisions a dedicated non-superuser runtime login `autoqa_app` before migration. It must be NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE, must not own the database/schema/tables, and must not inherit administrator or object-owner memberships. Never use the migration identity for normal requests. The migration rejects a missing, privileged or current-user runtime role; provisioning must additionally ensure role memberships and database-level grants do not expand its rights.

Apply migrations using a separate infrastructure identity with the necessary schema/role grant permissions. The migration grants runtime schema USAGE and only SELECT/INSERT on immutable plan snapshots; approvals and runs additionally get UPDATE. No DELETE/TRUNCATE/schema CREATE/DDL rights are granted. Public schema CREATE is revoked from PUBLIC. Check pre-existing direct grants, inherited roles and database privileges as part of provisioning: a migration cannot safely remove unrelated administrators' policies.

Every table enables and forces row-level security. The policy compares tenant_id with `current_setting('autoqa.tenant_id', true)` for both USING and WITH CHECK; a missing setting yields NULL and denies access. The authenticated control-plane repository must derive a non-empty tenant ID from trusted identity, then call parameterized `set_config('autoqa.tenant_id', tenant_id, true)` inside each transaction. Never accept an arbitrary tenant header as authorization. The setting is transaction-local to prevent connection-pool reuse leaking tenant context. RLS is defense against missing filters, not protection from a compromised runtime identity that can set arbitrary tenant settings; the worker must not possess this identity.

Composite tenant/entity primary and foreign keys prevent cross-tenant plan associations. Runs have unique `(tenant_id, actor, idempotency_key)` and a partial unique index permitting at most one QUEUED/RUNNING run per tenant. The repository also takes a per-tenant transaction advisory lock for deterministic quota/idempotency decisions. A run must transition to a terminal status to release the active index slot. Each run has a non-null lease_expires_at; the repository assigns an initial 150-second lease. Expired active runs become ERROR, never automatically retried. Terminal updates must condition on an active, unexpired lease to fence a stale worker. The schema constrains status to QUEUED, RUNNING, PASS, FAIL, ERROR, BLOCKED, INCONCLUSIVE or CANCELLED.

## Applying and rolling back

From the repository root, set `AUTOQA_MIGRATION_URL` in the process environment through an approved secret source, then run:

```powershell
.\.venv\Scripts\python.exe -m alembic -c backend/alembic.ini upgrade head
```

Do not paste database passwords into commands, logs, chat or Git. The migration code does not log the URL or configure SQL echo. Test harnesses may instead supply an already-open SQLAlchemy connection through `Config.attributes['connection']`; the caller controls its transaction. Offline SQL generation is disabled so role validation cannot be bypassed unintentionally. Alembic's version table is infrastructure state in public, not tenant application data.

Rollback command:

```powershell
.\.venv\Scripts\python.exe -m alembic -c backend/alembic.ini downgrade base
```

Rollback drops application tables and their data, then the schema. Use only a disposable test database or an explicitly approved migration recovery procedure with backup. It intentionally does not restore broad public CREATE privileges and does not delete the separately provisioned runtime role. Re-upgrade reconstructs the empty application schema; it does not restore lost data.

## Required real database verification

Verify migration up/down/up on disposable PostgreSQL; runtime is not owner/superuser/BYPASSRLS; missing/wrong tenant reads return no rows; cross-tenant inserts and updates reject; plan UPDATE/DELETE/TRUNCATE and schema CREATE reject; same tenant/actor/key cannot duplicate a run; concurrent active runs violate the partial unique index; terminal completion permits a new active run; connection reuse does not retain tenant context. Record actual executed commands/results in the verification report. This document itself makes no claim that those tests ran.

## Executed migration roundtrip — 2026-10-18

Executed from the project Python 3.12 virtual environment with backend/src on PYTHONPATH:

```powershell
.\.venv\Scripts\python.exe -m pytest backend/tests/test_migrations.py -q
```

Observed result: **1 passed in 36.95s**, exit code 0. The test used actual PostgreSQL from the isolated local harness and created a separate randomly named `test_migrations_...` database. It verified upgrade, administrator downgrade removing all application tables/schema, preservation of public CREATE hardening, re-upgrade to revision 0001_tenant_storage, and runtime refusal of schema/public CREATE TABLE, ALTER TABLE, TRUNCATE and Alembic downgrade. Runtime refusals had PostgreSQL SQLSTATE 42501. Its temporary database was removed; the fixture database was not downgraded. This single test does not establish enterprise recovery/backup readiness or substitute for the separate RLS/data-integrity suite.

Alembic path_separator is explicitly set to os to remove the configuration deprecation. PostgreSQL dependency and licence additions are recorded separately in [POSTGRES_DEPENDENCIES.md](POSTGRES_DEPENDENCIES.md).
