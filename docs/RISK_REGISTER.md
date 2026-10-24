# Risk and dependency register

All risks remain OPEN until linked evidence and independent review close them. Roles are proposed accountability; no person has accepted ownership merely because a role appears here.

| Risk | Severity | Owner | Mitigation / closure evidence |
|---|---|---|---|
| False PASS / assertion mis-compilation | Critical | QA lead | Immutable literals, deterministic V2/V3 observations, mutation/seeded-defect suite |
| Worker escapes policy/network boundary | Critical | Security / DevOps | Separate identity, constrained RPC, container/VM and firewall, redirect/subresource abuse tests |
| Unauthorized/CSRF local execution | Critical | Security / Backend | Auth, Host/Origin/CSRF, expiry, rate limits; real refusal tests |
| Credentials/PII in storage/evidence | Critical | Security | Vault references, masking/scanning, encryption, canaries; synthetic-only until verified |
| Wrong environment or externally visible actions | Critical | Security / PO | Live identity binding, deterministic risk and scoped approvals; deny R2/R3 absent grants |
| Protected code merged without independent review | Critical | Repository owner | CODEOWNERS and actual required review/branch rules; no agent merges |
| Audit truncation/tampering | High | DevOps | Separate writer and trusted external anchor; a self-contained hash chain cannot detect valid-prefix truncation alone |
| Browser/driver incompatibility | High | Automation | Exact-version inventory and real browser tests |
| Missing PostgreSQL/Docker runtime | High | DevOps | Provision approved runtime, migrations and RLS tests; no SQLite production substitute |
| Dependency CVEs/licence uncertainty | High | DevOps | Pins, scan result, SBOM and licence approval per added dependency |
| Model licence/hardware unknown | High | AI engineer | No model enablement until inspected licence, pinned digest and measured benchmark |
| Test-data collision / unsafe cleanup | High | QA / Automation | Run-unique values, recorded created IDs, journal-only cleanup and concurrency tests |
| Sandbox access / MFA unknown | High | PO / Adapter owners | Request package in readiness doc; no automated MFA bypass; no certification from demos |
| Schedule and staffing uncertainty | Medium | PO | Reforecast after Sprint 2; retain contingency and release gates |
| Accessibility, operational recovery and retention unmeasured | High | Frontend / DevOps | WCAG audit, restore drill, retention/deletion enforcement before enterprise release |

Pending dependencies: independent human security and QA reviewers; selected enterprise identity provider and secret manager; verified repository branch protections; approved Salesforce/SAP QA environments and accounts; data classifications; second demo implementation; model licence review; deployment TLS/KMS and external audit anchor. No external access request has been sent by this documentation task.
