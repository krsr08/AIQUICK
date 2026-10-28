# Capability baseline

This is the planning baseline, not a certification report. A capability moves to VERIFIED only with a recorded real test, exact browser/driver/application version and evidence link. Implementation alone is PROPOSED/IMPLEMENTED-UNVERIFIED. Consult the execution report for current demonstrated scope.

| Capability | Baseline state | Required evidence / scope |
|---|---|---|
| Chrome controlled synthetic workflow | Demonstrated locally | Chrome 153.0.8010.53 / ChromeDriver 153.0.8010.52; navigate, two fills, Save; fresh-session single-field V2 assertion (historical baseline); linked-field continuation in LINKED_ASSERTIONS_VERIFICATION.md; [evidence](VERIFICATION.md) |
| Guided English, review and hash-bound approval | Demonstrated locally | Real dashboard author/reviewer journey; hash mutation and self-approval negatives; [evidence](VERIFICATION.md) |
| Policy deny-by-default and action-time checks | Partially verified | Separate PDP, ordered grants, replay/expiry and host negatives tested; compromised-worker containment and full outage/escape matrix not certified |
| Deterministic PASS/FAIL | Demonstrated locally | Real correct-value PASS and intentionally wrong email/name FAIL; missing assertion rejection; [evidence](VERIFICATION.md) |
| Full TC_CRM_001 with V2 persistence | Not certified | Fresh browser reopening created record by ID; four linked expectations |
| Request-level network containment | Not certified | Redirect/popup/subresource plus direct-network bypass denial |
| Edge | Not certified | Real Edge capability suite; Sprint 3 target |
| PostgreSQL tenant isolation | Demonstrated locally | Forced RLS, missing-context denial, forged tenant write denial, cross-tenant API denial, immutable plans and process persistence tested against PostgreSQL 18.2; see POSTGRES_VERIFICATION.md; no enterprise certification |
| Enterprise SSO, vault, TLS, encrypted evidence | Not certified | Deployment/security verification |
| Local model free-form English | Not implemented by this baseline | Model licence/digest, hardware and closed-set evaluation |
| Salesforce, SAP Fiori, SAP GUI for HTML | Not certified | Authorized real sandbox/version/workflow evidence |
| Native Windows SAP GUI, Firefox/Safari/mobile | Out of scope | New approved scope/adapter decision required |
| Closed shadow/canvas/custom controls | Unsupported unless certified adapter | BLOCK rather than silent success |

No universal English understanding, enterprise readiness, privacy certification, performance guarantee or universal browser/application compatibility is claimed.
