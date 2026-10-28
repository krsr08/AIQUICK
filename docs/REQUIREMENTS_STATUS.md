# Blueprint completion ledger — 28 October 2026

The authoritative scope spans Sprint 0 through Sprint 18. The product is **not complete** and is not approved for production data. This ledger distinguishes shipped engineering work from release signoff. Earlier evidence remains historical; a passing local run does not imply passing CI or enterprise readiness.

## Security requirements

| Requirement | Current implementation | Remaining acceptance work |
|---|---|---|
| SR-01 identity | Local scrypt accounts; authenticated API; public login/bootstrap | Enterprise OIDC/SAML, lifecycle and access review |
| SR-02 local boundary | Loopback, Host/Origin checks, cookie CSRF, expiry and login rate limit | TLS deployment, distributed rate limits and production identity testing |
| SR-03 action authorization | Separate PDP, ordered scoped grants and pre/post checks | Hardened sole dispatcher boundary and compromised-worker testing |
| SR-04 egress | Browser allowlisting proxy, control-plane/external-host denial | OS-enforced mandatory proxy; direct bypass, DNS, redirects, popup and subresource fault matrix |
| SR-05 immutable approval | Hash-bound persisted snapshots; expiry and author/reviewer separation | Independent review of new schema and broader mutation tests |
| SR-06 roles | Author, Approver, Runner, Admin, Auditor account roles | Complete per-environment role administration and authorization matrix |
| SR-07 secrets | Generated DB credentials protected with Windows DPAPI; worker excludes DB credentials | Target secret handles, external vault, rotation and canary leak tests |
| SR-08 evidence | Synthetic text observations; synthetic UI screenshots only | Pre-capture masking, post-scan quarantine and retention enforcement |
| SR-09 encryption/TLS | No general at-rest or transport encryption claim | Per-tenant envelope encryption, key lifecycle, TLS/mTLS, backup encryption |
| SR-10 worker containment | Fresh profiles, process deadline, Windows Job Object descendant cleanup | Separate restricted identity/container/VM, read-only filesystem and network/resource limits |
| SR-11 files | Downloads disabled; no upload workflow | Quarantine/type/size/malware gates before enabling file workflows |
| SR-12 audit | Volatile policy hash chain | Durable append-only independent writer, verification, trusted time and external anchoring |
| SR-13 supply chain | Pinned packages/actions, scans and SBOM | CI green on current commit; licence clearance, container scanner when deployed |
| SR-14 human control | Draft feature PR and CODEOWNERS | Named independent human reviewer, enforced branch protection and signing; agent does not merge |
| SR-15 classification | Fixed synthetic local environment | Classified environment registry, production-derived controls and explicit grants |

## Functional roadmap

| Scope | Current position | Remaining work |
|---|---|---|
| Sprint 0 | Inventory, threat model, ADRs, repository and CI proposal exist | Human security/QA signatures, operational ownership and long-lead sandbox access |
| Sprint 1 | Describe/review/approve/run/result UI, PostgreSQL/RLS, controlled English, Chrome create workflow | Demo CRM login/list, full acceptance and security review |
| Sprint 2 | Durable plans, approvals and run state | Suites/history UX, evidence masking, durable audit, full role and egress controls |
| Sprint 3 | Fresh-session record-by-ID verification; linked assertions; Chrome/Edge execution and verified local cancellation | Cleanup journal, full TC_CRM_001 and fault/escape matrix; see EDGE_VERIFICATION.md and CANCELLATION_VERIFICATION.md |
| Sprints 4–6 | Not implemented | Licensed pinned local model, page discovery/mappings, poisoning/injection defence, healing and evaluation |
| Sprints 7–8 | Not implemented | Certified advanced web controls and browser capability matrix |
| Sprints 9–11 | Not implemented | Authorized Salesforce QA adapter and real certification evidence |
| Sprints 12–14 | Not implemented | Authorized SAP Fiori/Web GUI QA adapters and certification evidence |
| Sprints 15–16 | Not implemented | Cross-system orchestration and team operations |
| Sprints 17–18 | Not implemented | Scale, recovery, penetration testing, operational readiness and release signoff |

## External decisions and access still needed

The user delegated vendor choice: self-hosted Linux, Keycloak OIDC and OpenBao are selected (REFERENCE_DEPLOYMENT.md). A working container engine is required for integration execution. Name an independent security/QA reviewer and plan approvers; provide approved Salesforce and SAP QA environment references and dedicated test identities through a secret store, never chat. Confirm dependency licences and production data classification. These cannot be replaced by synthetic tests or invented signoff.

## Measurable release gates

The blueprint's 300 seeded-defect and 300 ambiguous-target trials, reported abstention, reliability/performance targets, backup/restore, penetration tests and enterprise adapter certification have not been completed. A two-field local browser journey is only part of TC_CRM_001. No full-requirements completion claim is permitted until these entries have actual evidence and required independent approvals.
