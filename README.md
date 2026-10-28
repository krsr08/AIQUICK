# AutoQA Enterprise — Sprint 0 engineering preview

A local, synthetic-data implementation of the **Describe → Review → independent Approve → Run → Verify** journey from [Implementation Blueprint v2.0](docs/specification/AUTOQA_ENTERPRISE_IMPLEMENTATION_BLUEPRINT_v2.md), now with PostgreSQL persistence and enforced tenant row policies. Sprint 0 signoffs and remaining Sprint 1/security gates are still open; this is **not an enterprise release**. The original repository MIT licence is preserved.

## Run on Windows

Prerequisites: Python 3.12, Node 24, installed Chrome and Edge for the full test suite, installed PostgreSQL binaries, and available loopback ports 8000, 8765, 8766, 8767. Windows defaults to `C:\Program Files\PostgreSQL\18\bin`; set `AUTOQA_POSTGRES_BIN` for another installation. The launcher creates its own loopback database cluster without touching an installed service. Selenium Manager obtains a matching driver on first use; subsequent offline operation requires its cached binary. Never use your normal browser profile for execution.

```powershell
py -3.12 -m venv .venv
.venv\Scripts\python.exe -m pip install -r config/requirements.lock
npm --prefix frontend ci
npm --prefix frontend run build
.venv\Scripts\python.exe scripts/run_demo.py
```

If Python 3.12 is not registered with `py`, use `uv venv --python 3.12 .venv` after installing that interpreter. The launcher privately prompts for two temporary passwords (12+ characters). It stores only scrypt hashes in the control-plane environment. Accounts are `author` (Author + Runner) and `reviewer` (Approver + Runner + Auditor).

On Windows, the launcher provisions a private persistent cluster under ignored `work/dev-postgres`, applies Alembic migrations, and stores generated database credentials as a user-bound Windows DPAPI ciphertext. It preserves plans, approvals and run history when stopped, while the synthetic target CRM remains disposable. Database files themselves are not encrypted by this feature: synthetic data only. No default passwords or plaintext credential files remain. A short-lived initdb password file is removed immediately after initialization. See [PostgreSQL operations](docs/POSTGRES.md) for separately managed databases and role boundaries.

Open [the local workspace](http://127.0.0.1:8000). Sign in as author, review the prefilled synthetic example, and create a plan. Sign out and sign in as reviewer, select the plan, confirm its exact expectation, approve and run. A different expected value should produce FAIL. Unsupported sentences are rejected with guidance. Every new draft creates a separate immutable plan; approval does not transfer.

This first slice supports exactly: open the synthetic CRM, fill Customer Name and Email once each, Save, then verify **one or two** linked literal field expectations by record ID in a separate browser session (V2). Enter one exact expectation per line; both must pass. `{run-id}` is expanded for unique run data. It does not yet implement CRM login, search/count assertions, full TC_CRM_001, suites or arbitrary sites.

Chrome is the default execution browser. To use Edge, set `$env:AUTOQA_BROWSER='edge'` before starting the launcher; use `'chrome'` to switch back. This is trusted server configuration, not a user-supplied executable or plan instruction. Unsupported values fail closed. The same engine runs both the action and fresh-session verification, and completed reports show the actual browser name/version. Existing plan hashes and approval semantics are unchanged. The browser that opens the dashboard is independent of the execution browser.

## Verify

```powershell
.venv\Scripts\python.exe -m pytest -c config/pytest.ini backend/tests -v --junitxml=work/tests.xml
.venv\Scripts\python.exe -m pip_audit
.venv\Scripts\python.exe -m bandit -r backend/src policy_service demo_apps deployment scripts -ll
```

Run browser tests serially with the demo stopped; fixtures own the fixed ports. The test session creates and removes a separate real PostgreSQL cluster with random credentials; it never uses the persistent demo database or SQLite. Browser workflow and process-cancellation tests require actual Chrome and Edge and do not silently skip missing browsers. Raw execution evidence is written into ignored `work/`; see the [original preview results](docs/VERIFICATION.md) and [PostgreSQL verification](docs/POSTGRES_VERIFICATION.md).

## Security boundary and limitations

The API checks authentication, roles, Host/Origin and CSRF. The login/bootstrap shell and static assets are necessarily public; API data is authenticated. Plans are immutable and hash-pinned, approvals expire after 15 minutes, and write-plan approver must differ from author. A separate loopback PDP authorizes each action and verification phase with short-lived ordered run grants. A worker subprocess receives no control-plane token or account hashes. Fresh Chrome profiles, bounded process trees and a fixed-destination HTTP proxy reduce exposure.

**Use synthetic data only on this local machine.** Processes currently share the same Windows user; proxy configuration is not an OS-enforced network sandbox. Local HTTP has no TLS. Neither the toy CRM nor this developer prototype is suitable for production data or hostile targets. The CRM has no authentication because it contains only throwaway synthetic records. The application accepts no target URLs or enterprise secrets.

Plans, approvals and runs persist in PostgreSQL behind a restricted runtime account and forced row-level security. Tenant identity comes from server-provisioned accounts; request bodies/headers cannot change it. Restored approvals retain their original expiry. Run idempotency and per-tenant active-run limits are database-enforced; expired worker leases become ERROR and are never automatically replayed. Demo CRM records and policy audit events remain volatile. Screenshots/DOM evidence capture is disabled in the execution product until masking, scanning and encryption are implemented. Tests may capture the known-synthetic dashboard after login. No Ollama/model or hosted model is used. No production writes, uploads, downloads, destructive actions, Salesforce or SAP workflows are supported.

Protected changes require independent human review before merge. CODEOWNERS is proposed; repository branch protection and signed-commit enforcement must be configured and verified by an administrator. See [readiness](docs/SPRINT0_READINESS.md), [threat model](docs/THREAT_MODEL.md), [dependency inventory](docs/dependencies.md), and [backlog](docs/BACKLOG.md).

Current full-scope gaps: [completion ledger](docs/REQUIREMENTS_STATUS.md). Selected deployment defaults: [self-hosted Keycloak/OpenBao reference](docs/REFERENCE_DEPLOYMENT.md). Latest linked-assertion evidence: [verification](docs/LINKED_ASSERTIONS_VERIFICATION.md).

Active runs can be stopped with **Cancel run** by a Runner/Admin in the same tenant. The UI shows Stopping until controller shutdown acknowledgement; cancellation does not undo records already saved. See [cancellation verification](docs/CANCELLATION_VERIFICATION.md).
