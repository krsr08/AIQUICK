# Architecture decisions baseline

2026-10-17. These decisions are inherited from the authoritative blueprint section 23. They are proposed implementation constraints; human owner signoff and achieved conformance remain pending. A local prototype deviation must be listed explicitly, not silently replace the baseline.

| ADR | Decision / rationale | Consequence / verification |
|---|---|---|
| 001 | Web dashboard; controlled English in R1, free-form in R2 | Publish supported sentences; unsupported text clarifies/BLOCKs; non-coder UAT |
| 002 | Python 3.12, FastAPI, Selenium 4 behind BrowserDriver | Inventory exact runtime/driver compatibility; any newer runtime needs recorded validation |
| 003 | Local Ollama only, pinned digest/prompt, strict closed-set output | No hosted model calls; benchmark/licence gate before model use |
| 004 | Human approves; PDP authorizes plan and every action; deterministic assertions judge | AI cannot approve or PASS; outage and mutation tests |
| 005 | Ephemeral RAM catalog; sanitized metadata in scoped DB, evidence separate | No raw DOM or sensitive locator persistence; poisoning tests |
| 006 | PostgreSQL with Alembic and RLS from Sprint 1 | SQLite restricted to unit tests; in-memory demonstration is not durable Sprint 1 persistence |
| 007 | Chrome first; Edge Sprint 3; certification per capability | Real runs per exact browser/driver version, no universal support claims |
| 008 | Extension optional and outside execution dependency | First workflow runs without installing an extension |
| 009 | Production writes denied; R0–R3 deterministic risk; sandbox writes only | Unknown semantics deny; R2/R3 require explicit scope; cleanup for R1 |
| 010 | Original English, literal expectations and approved hash authoritative | Edit creates new version and approval; runtime never recompiles |
| 011 | SSO/OIDC, roles, separation of duties by R1; dev accounts only in explicit dev mode | Strong password hashing, CSRF, short sessions; no shared default credentials |
| 012 | PDP/secrets/audit separate deployable and identity | Process split alone on one OS user does not prove isolation |
| 013 | Ephemeral non-root isolated workers, no durable credentials, network allowlisting | Clean profiles alone do not meet container/VM, firewall and resource-limit requirements |
| 014 | V1 same-session reread, V2 fresh session, V3 independent read-only channel | R1+ persistence at least V2; deterministic observations only |
| 015 | Protected paths require independent CODEOWNERS approval; agents do not merge | Remote required-review rules must be verified; file alone cannot enforce review |
| 016 | S0 + 18 sprints with shifted-left security and 20–30% contingency | Reforecast after Sprint 2; failed gates defer release |

Open choices: enterprise IdP, vault/KMS, named independent owners, target data regimes and classifications, approved MFA patterns, SAP Web GUI requirement, model shortlist after licence inspection and hardware measurements, second demo CRM implementation. These do not authorize enterprise access or model downloads.
