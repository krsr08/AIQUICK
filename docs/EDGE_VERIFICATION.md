# Chrome and Edge execution — 28 October 2026

The existing synthetic approved create-and-verify workflow now runs on Chrome (default) or Edge. Set `AUTOQA_BROWSER=edge` in the trusted server environment before launching; use `chrome` to switch back. Unsupported names fail before driver resolution. Selenium Manager resolves explicit local executable paths in the control plane, not inside the worker. Resolution is cached by browser, and workers receive no database credentials. Plans, hashes, approval separation and PDP scope are unchanged.

Both engines use the same proxy, disabled downloads/password storage, ephemeral profiles and bounded worker process tree. Each fresh browser opens the fixed empty `data:,` page and checks one window before policy-controlled navigation. This fixes Edge's different startup page without widening the policy allowlist. Results include the actual browser name/version, also shown in the dashboard. Browser choice is deployment configuration, not a per-plan browser selector or an enterprise capability certification.

The launcher now rejects occupied service ports and waits up to 30 seconds for all three local listeners while checking child liveness. It cleans up failed launches. This fixes an observed policy connection-refused startup race; it is not an OS isolation boundary.

## Executed evidence

Full Windows suite: **74 passed, zero failed/skipped, 384.64 seconds**, exit 0. One existing Starlette test-client deprecation warning remains. Command: `.venv\Scripts\python.exe -m pytest -c config/pytest.ini backend/tests -v --tb=short --junitxml=work/edge-final-tests.xml` with `PYTHONPATH=backend/src;.`.

- Actual Chrome 153.0.8010.53 and MicrosoftEdge 154.0.4258.37 produced PASS for the matching expectation and FAIL for the deliberately wrong expectation. Verification reopened the created record by ID in a separate browser session.
- Both real browsers and drivers were alive before cancellation, then their retained Windows process handles signalled termination. Profile directories were removed. Holding handles before cancellation avoids confusing a reused process ID with the original process. Both installed drivers expose `goog:processID`; Edge does not expose `ms:processID`.
- Legacy hashes, approval/tenant/CSRF checks, idempotency, late-result fencing, lease expiry, database migrations and the dashboard journey passed in the full suite.
- Frontend TypeScript/Vite build passed. Python and npm dependency audits reported zero known vulnerabilities. Bandit passed the medium/high gate. CycloneDX SBOM regenerated.

See [raw evidence](evidence/edge/). Intermediate failures are retained: the first suite had 70 passing and four failing tests (Edge startup twice, process termination observation and policy readiness). A subsequent two-case cancellation check failed before correcting the capability key and holding process handles before shutdown. These failures are not omitted from the record and this run does not establish a flake-free reliability rate. GitHub verification for the commit must be checked separately.

## Remaining requirements

Full TC_CRM_001, target-record cleanup, CRM login/search/count, durable anchored audit, enterprise identity/vault integration, mandatory OS/network isolation, TLS/encryption, model intelligence, Salesforce/SAP certification, quantitative release gates and independent human signoff remain open. Cancellation does not undo saved target data. See [completion ledger](REQUIREMENTS_STATUS.md). Agent review is not an independent human release approval.
