# Verified implementation results — 17 October 2026 (Asia/Kolkata)

## Scope and provenance

Repository baseline `2e4ce570d3ebf9c03c0945ffd3733ec0cda36784` contained LICENSE only; that file is unchanged. Implementation is proposed on `feat/autoqa-sprint0-secured-slice` for independent review. This report describes a runnable synthetic Sprint 0 preview and early browser-testing vertical slice. **Sprint 0 signoff, Sprint 1 completion and enterprise readiness are not claimed.**

The uploaded blueprint was retrieved through the referenced conversation and matched the Downloads copy by SHA-256. See the [exact specification](specification/AUTOQA_ENTERPRISE_IMPLEMENTATION_BLUEPRINT_v2.md) and [dependency/browser inventory](dependencies.md). Implementation ran under `C:\Users\ANIRUDH\Documents\autoqa-enterprise`.

Environment: Windows 11; Python 3.12.13; Selenium 4.51.0; Chrome 153.0.8010.53; ChromeDriver 153.0.8010.52; Node 24.13.0. The source ZIP and supplied driver archives were inspected, not installed. Selenium Manager selected the compatible installed Chrome driver. Browser sessions used fresh temporary profiles and were headless.

## Executed checks

| Check / exact command | Observed result |
|---|---|
| `.venv\Scripts\python.exe -m pytest -c config/pytest.ini backend/tests -v --junitxml=work/tests.xml` | **28 passed, 0 failed, 0 skipped**, 1 deprecation warning; final run 104.81 s; [log](evidence/test-output.txt), [JUnit](evidence/tests.xml) |
| `npm --prefix frontend run build` | TypeScript check and Vite production build succeeded |
| `npm --prefix frontend audit --json` | 0 reported vulnerabilities; [JSON](evidence/frontend-audit.json) |
| `.venv\Scripts\python.exe -m pip_audit --format json --output work/dependency-audit.json` | 81 distributions, 0 reported known vulnerabilities; [JSON](evidence/dependency-audit.json) |
| `.venv\Scripts\python.exe -m bandit -r backend/src policy_service demo_apps deployment scripts -ll -f json -o work/bandit-gate.json` | No medium/high findings; low subprocess findings remain for review; [JSON](evidence/bandit-gate.json), [review rationale](SECURITY_REVIEW.md) |
| `.venv\Scripts\python.exe -m cyclonedx_py environment --of JSON -o work/sbom.json` | Generated [CycloneDX SBOM](evidence/sbom.json) |
| `.venv\Scripts\python.exe scripts/check_secrets.py` | Tracked-file pattern scan passed; narrow coverage, not an enterprise secret audit |

The warning is Starlette's deprecation of its httpx-based TestClient. It did not skip or fail tests. CI is configured but **a remote green CI run has not been verified in this report**. No penetration test, container scan, licence approval or enterprise certification was executed.

## What the real browser tests demonstrated

1. Service-level approved plan: open CRM, fill both fields, Save, capture new record ID; a **fresh** Chrome session reopens that ID and compares literal Email. Correct expectation produced PASS. Deliberately wrong email produced FAIL. [Positive](evidence/browser-pass.json) / [negative](evidence/browser-fail.json).
2. Actual React dashboard: sign in as author, create plain-English plan, observe that self-approval and unapproved execution are disabled, sign out, sign in as independent reviewer, confirm expectation, approve, Run and see PASS. Repeat with a newly authored incorrect Customer Name expectation: FAIL. Four real target-browser runs total across service and dashboard scenarios; each includes separate execution and verification sessions. [Machine-readable UI evidence](evidence/dashboard-result.json), [PASS screenshot](evidence/dashboard-pass.png), [FAIL screenshot](evidence/dashboard-fail.png).
3. Unit/API negatives: no default accounts; password hashing; unauthenticated API; session expiry/logout; Host/Origin/CSRF; role denial; login throttling; missing idempotency key; immutable/hash-changed plans; self-approval; action replay/order; expiry; unsupported language; unverifiable expectations; missing assertions; prohibited URLs; and worker process-tree cleanup after timeout.
4. Real HTTP negatives: proxy rejected control-plane and external destinations including CONNECT; PDP rejected absent run authorization. These are narrower than the blueprint's full browser redirect/popup/subresource and compromised-worker escape suite.

Earlier runs exposed browser-discovery and initial-page mismatches, returning ERROR/BLOCKED rather than false PASS. Those failures were fixed and the entire suite rerun. Expected values and negative tests were not weakened. Separate review also found expiry and process-cleanup defects; fixes and regressions are recorded in [security review](SECURITY_REVIEW.md).

## Remaining blockers and next sprint

- **PostgreSQL / Alembic / RLS:** Docker engine query hung. The spike uses volatile memory, never SQLite. Durable multi-tenant storage and real PostgreSQL isolation tests are still required for Sprint 1.
- **Isolation/security:** separate processes currently share a Windows identity. Add ephemeral non-root containers/VMs, enforced outbound firewall/proxy, separate service identities, TLS and vault integration before any non-synthetic target. No default production access exists.
- **Evidence/audit:** current observations contain synthetic text only. Product screenshots are disabled. Implement masking, post-scan quarantine, encrypted retention, signed durable approvals and externally anchored append-only audit. Current in-memory chain is not a durable compliance audit.
- **Workflow breadth:** one controlled four-step creation flow and one field assertion per plan. CRM login, linked multiple assertions, search/count, cleanup journal, cancellation, Edge, full TC_CRM_001 and all section 17 variants remain unimplemented/unverified.
- **Human/governance gates:** independent human security/QA review, PO acceptance, named approvers/IdP, branch protection and signed commits remain pending. CODEOWNERS does not itself enforce repository rules. No signing key was configured locally; review the proposed commit-signing requirement before merge.
- **Enterprise/model readiness:** Salesforce/SAP accounts and approved MFA patterns are not available; no sandbox requests were sent. No local model was installed, licence-approved or benchmarked. Free-form English and enterprise adapters are not supported.

Next: resolve PostgreSQL/Docker, implement migrations/RLS and durable versioned plans; strengthen deployment identities/network containment; extend the acceptance flow and negative matrix; obtain independent human signoffs. The current results do not meet the blueprint's 300-defect reliability targets and do not measure performance or compliance.
