# Prioritized backlog and acceptance evidence

Baseline 2026-10-17. Status below is planning, not test execution. Preserve safety tests; never skip or weaken one to turn a result green. Every delivered story needs commands, exact observed outcomes, environment, artifact references, limitations and independent review.

| Priority / story | Scope | Acceptance gate | Dependencies |
|---|---|---|---|
| P0 S0-01 | Environment/library/dependency inventory | Source, version, hash, licence, scan outcome and compatibility recorded | Supplied Downloads assets |
| P0 S0-02 | Threat model/ADRs/risk owners | Security and QA independent signatures | Named humans |
| P0 S0-03 | Baseline CI/protected paths | Actual scanner results + SBOM; required reviews verified remotely | CI and repository administration |
| P0 S1-02 | Authenticated UI/API and CSRF/Host/Origin controls | Unauthorized and cross-origin requests refused | Dev identity/vault decision |
| P0 S1-05/06 | Typed schemas, controlled English, preview, immutable approval | Literal assertions preserved; zero-assertion and tamper reject | Human approver workflow |
| P0 S1-09 | Separate PDP and sole dispatcher | Each action authorized; outage and off-plan scope fail closed | Policy identity and transport |
| P0 S1-12 | Real positive, negative and abuse tests | Actual browser PASS plus deliberately wrong expectation FAIL | Browser/driver and controlled fixture |
| P1 S1-03 | PostgreSQL/Alembic/RLS | Migration + real PostgreSQL cross-tenant integration tests | PostgreSQL/Docker availability |
| P1 S1-04/07/08/10/11 | Editor, browser actions, independent assertions, result UI, CRM | Human can describe/review/approve/run without code; exact supported workflow evidenced | Above safety foundations |
| P1 S2 | History, suites, masking, audit, role completeness and egress | Approver differs from author; masked evidence; request-level escapes deny | Encrypted stores, audit identity, proxy/firewall |
| P1 S3 | Edge, TC_CRM_001, fresh-session verification and cleanup | Section 17 steps 1–9 and 13–15 on Chrome and Edge | Demo persistence/identity, cleanup journal |
| P2 S4–6 | Local-model compiler/discovery/healing | Schema benchmark, mutation suite, injection/poisoning safe failures | Licensed pinned model; measured hardware |
| P2 S7–18 | Advanced controls, enterprise adapters and hardening | Blueprint release gates; real approved QA environments | Access approvals and capacity |

## Evidence record format

### 2026-10-18 progress

S1-03 is implemented as a review proposal: PostgreSQL/Alembic/forced RLS, immutable plans, persisted approvals/runs, durable idempotency and expiring worker leases. Windows development now has a private persistent cluster with DPAPI-protected database credentials. Real PostgreSQL tests include tenant denial, migration rollback/re-upgrade, plan persistence across process/server restarts and stale-worker fencing. See POSTGRES_VERIFICATION.md for final counts and CI status; no story or release is signed off by this entry.

Next engineering priorities: enforce worker network/OS isolation; durable signed/anchored audit and encrypted evidence; expand full TC_CRM_001 with login, multiple linked expectations/search/cleanup/cancellation and Edge. Human review, legal dependency clearance, branch protection and commit signing remain prerequisites before merge/release.

For every execution: date/time with zone, commit/tree identifier, OS/runtime/browser/driver versions, exact command, exit code, test counts including skips, positive and negative expected/actual verdicts, artifact locations, redaction results, observed blockers. CI configuration is not a successful CI run. Browser smoke is not enterprise certification. Automated fixtures exercising approval are not a human product/security signoff.

## Release targets remain unmeasured

Blueprint targets: zero observed false PASS in at least 300 independent seeded defects and zero wrong-target writes in at least 300 ambiguous-target trials, plus reported abstention; approximately 1% upper 95% bound for zero events in 300 trials. A handful of successful local runs cannot establish those rates. Required assertions need evidence; missing evidence prohibits PASS. Never treat model self-evaluation as proof.

### 2026-10-20 continuation

Linked immutable name/email assertions and a multiline review editor extend section 17 verification; see LINKED_ASSERTIONS_VERIFICATION.md for executed results. Full status is tracked in REQUIREMENTS_STATUS.md. Under the user's delegated choice, the reference deployment uses self-hosted Linux, Keycloak OIDC and OpenBao; actual integration remains gated by a working container engine and verification, not by a further vendor-choice question. Independent human signoff and authorized enterprise QA access remain external gates.
