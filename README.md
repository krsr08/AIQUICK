# AutoQA Enterprise — Sprint 0 engineering preview

A local, synthetic-data proof of the **Describe → Review → independent Approve → Run → Verify** journey from [Implementation Blueprint v2.0](docs/specification/AUTOQA_ENTERPRISE_IMPLEMENTATION_BLUEPRINT_v2.md). This is a proposed Sprint 0 implementation and early vertical slice, **not a completed Sprint 1 or enterprise release**. The original repository MIT licence is preserved.

## Run on Windows

Prerequisites: Python 3.12, Node 24, installed Chrome, and available loopback ports 8000, 8765, 8766, 8767. Selenium Manager obtains a matching driver on first use; subsequent offline operation requires its cached binary. Never use your normal browser profile for execution.

```powershell
py -3.12 -m venv .venv
.venv\Scripts\python.exe -m pip install -r config/requirements.lock
npm --prefix frontend ci
npm --prefix frontend run build
.venv\Scripts\python.exe scripts/run_demo.py
```

If Python 3.12 is not registered with `py`, use `uv venv --python 3.12 .venv` after installing that interpreter. The launcher privately prompts for two temporary passwords (12+ characters). It stores only scrypt hashes in the control-plane environment. No default passwords, secrets in files, or credentials in chat are needed. Accounts are `author` (Author + Runner) and `reviewer` (Approver + Runner + Auditor).

Open [the local workspace](http://127.0.0.1:8000). Sign in as author, review the prefilled synthetic example, and create a plan. Sign out and sign in as reviewer, select the plan, confirm its exact expectation, approve and run. A different expected value should produce FAIL. Unsupported sentences are rejected with guidance. Every new draft creates a separate immutable plan; approval does not transfer.

This first slice supports exactly: open the synthetic CRM, fill Customer Name and Email once each, Save, then verify **one** literal field expectation by record ID in a separate Chrome session (V2). `{run-id}` is expanded for unique run data. It does not yet implement CRM login, search/count assertions, two simultaneous expectations, full TC_CRM_001, suites or arbitrary sites.

## Verify

```powershell
.venv\Scripts\python.exe -m pytest -c config/pytest.ini backend/tests -v --junitxml=work/tests.xml
.venv\Scripts\python.exe -m pip_audit
.venv\Scripts\python.exe -m bandit -r backend/src policy_service demo_apps deployment scripts -ll
```

Run browser tests serially with the demo stopped; fixtures own the fixed ports. Tests create random in-memory credentials and run actual Chrome. Raw execution evidence is written into ignored `work/`; selected synthetic evidence and the exact verified results are in [the verification report](docs/VERIFICATION.md).

## Security boundary and limitations

The API checks authentication, roles, Host/Origin and CSRF. The login/bootstrap shell and static assets are necessarily public; API data is authenticated. Plans are immutable and hash-pinned, approvals expire after 15 minutes, and write-plan approver must differ from author. A separate loopback PDP authorizes each action and verification phase with short-lived ordered run grants. A worker subprocess receives no control-plane token or account hashes. Fresh Chrome profiles, bounded process trees and a fixed-destination HTTP proxy reduce exposure.

**Use synthetic data only on this local machine.** Processes currently share the same Windows user; proxy configuration is not an OS-enforced network sandbox. Local HTTP has no TLS. Neither the toy CRM nor this developer prototype is suitable for production data or hostile targets. The CRM has no authentication because it contains only throwaway synthetic records. The application accepts no target URLs or enterprise secrets.

Plans, approvals, runs, demo records and hash-chain events are volatile RAM state; restarting discards them. This is explicitly a Sprint 0 spike, not a SQLite replacement for the required PostgreSQL baseline. Screenshots/DOM evidence capture is disabled in the execution product until masking, scanning and encryption are implemented. Tests may capture the known-synthetic dashboard after login. No Ollama/model or hosted model is used. No production writes, uploads, downloads, destructive actions, Salesforce or SAP workflows are supported.

Protected changes require independent human review before merge. CODEOWNERS is proposed; repository branch protection and signed-commit enforcement must be configured and verified by an administrator. See [readiness](docs/SPRINT0_READINESS.md), [threat model](docs/THREAT_MODEL.md), [dependency inventory](docs/dependencies.md), and [backlog](docs/BACKLOG.md).
