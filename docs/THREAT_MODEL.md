# Threat model v1

Status: draft for independent security/QA review. Controls below are requirements; implementation and test results must be linked separately. Scope is the local synthetic demo and its transition to enterprise deployment.

## Assets, boundaries and data flow

Protect original expectations, immutable approved plan snapshots, credentials/cookies, tenant data, evidence, audit integrity and worker hosts. Z0 tester sends untrusted text to authenticated Z1 control plane. Z1 compiles typed actions, presents literal assertions, stores a hash-bound snapshot and sends a scoped job to Z4. Z2 separately authorizes plan/run/every action and writes audit. Z4 reads hostile Z5 pages only through egress restrictions. Z3 local AI, when introduced, has no credentials, network or tools and returns closed-set proposals only. Evidence is masked and scanned before leaving Z4. Workers cannot access policy/database stores directly.

Loopback binding reduces network exposure but does not replace authentication, CSRF, Host checking, TLS, process identity or OS-level isolation. A separate process under the same OS user is not a hardened trust boundary against compromise.

## Abuse cases and verification

| ID / STRIDE | Attack path | Required control and requirement | Negative evidence needed | Owner |
|---|---|---|---|---|
| T01 Spoofing | Hostile web page calls local API or forges Host | Auth on routes, strict Host/Origin, CSRF, expiry, rate limits; SR-01/02 | Missing auth, foreign Origin, DNS-rebinding Host all reject | Security |
| T02 Tampering | Plan changes after review; token replay | Immutable version+hash, signed scoped expiring approvals, run binding; SR-05/06 | Alter step, expected literal, tenant or environment; reject | Backend / QA |
| T03 Elevation | Worker bypasses PDP or replays authorized action | Sole dispatcher, action sequence/scope binding, separate PDP identity, fail closed; SR-03 | PDP down, stale grant, extra action and direct driver route denied | Security |
| T04 Elevation | Redirect, popup, fetch or subresource reaches unauthorized host | Request-level egress enforcement, redirect/window checks, OS firewall/container boundary; SR-04/10 | Escape attempts denied including browser proxy bypass | DevOps |
| T05 Tampering | Wrong element or malicious page changes assertion | Deterministic unique semantic target, immutable expected literal, no AI assertion resolver | Duplicate controls BLOCK; mutated expected value FAIL; no-assertion compile reject | QA |
| T06 Disclosure | Secret/PII enters DOM dumps, screenshots or prompts | Broker handles, pre-capture masking, post-scan quarantine, no raw DOM persistence; SR-07/08/15 | Canary absent from all allowed artifacts/logs/prompts | Security |
| T07 Disclosure | Evidence/store stolen or cross-tenant query | TLS, envelope encryption, RLS, tenant authorization, signed expiring artifact URLs; SR-09 | Cross-tenant deny; storage/TLS inspection | Backend |
| T08 Repudiation | Audit deletion/reordering, forged approval | Separate append-only hash-chain writer, external anchor, identity/time; SR-12 | Alter/reorder/remove event; detect against trusted anchor | DevOps |
| T09 Denial | Infinite wait, runaway browser/model or retry loop | Bounded waits/run quotas, cancellation, resource limits; NFR-05 | Timeout/cancel ends with explicit non-PASS and cleaned profile | Automation |
| T10 Elevation | Prompt injection adds tools or changes expected results | No model execution; enums/closed candidates, schema validation, PDP | Malicious DOM/test/dataset cannot authorize actions | AI / Security |
| T11 Tampering | Cached locator poisoned across environments | Semantic keys, trust tiers, environment scope, live revalidation | Poisoned/cross-tenant mapping cannot be reused | Automation |
| T12 Supply chain | Malicious package or agent weakens safety | Pins, licence review, SBOM/scanners, protected owners and review; SR-13/14 | CI enforcement plus remote branch-rule verification | DevOps |
| T13 Elevation | Wrong tenant or external write side effect | Live tenant binding, deterministic risk, default deny, side-effect suppression | QA/production mismatch, R2/R3 without grant deny | Security |
| T14 Disclosure | Download path abuse or hostile upload | Approved dataset store, per-run quarantine, type/size/AV; SR-11 | Unsupported file handling BLOCK; malicious paths rejected | Security |

## Risk and policy vocabulary

R0: reads/navigation; R1: reversible sandbox writes with cleanup journal; R2: modification/deletion requiring scoped approval; R3: financial/irreversible/external effects requiring explicit environment grant and verified suppression. Unknown semantics default upward and deny. A label is not proof a click is read-only.

Policy input must bind principal/role, tenant/environment, plan hash/version, action index/type, semantic target/live identity, current URL, risk, expiry, capability and budget. Denial is default; unreachability is denial. Approval is not a blanket permission to execute arbitrary actions. Post-action checks cannot undo an already leaked request, hence independent network enforcement is mandatory.

## Residual risks and release gate

### PostgreSQL change, 2026-10-18

Control-plane plans, approvals and runs now cross a PostgreSQL boundary. Migration and runtime identities are separate; the runtime refuses superuser/BYPASSRLS/owner memberships and missing forced-RLS flags. Tenant context comes from the server-owned account/session and is set only for each transaction. Immutable plans are SELECT/INSERT-only to the runtime, and reads verify the snapshot hash and tenant binding. Cross-tenant foreign keys and RLS WITH CHECK prevent accidental foreign-tenant writes. Idempotency is durable; advisory locks and a partial unique index serialize one active run per tenant. Expired leases become ERROR, and stale worker completion cannot replace that status.

The browser worker receives no database connection URL. The Windows local launcher stores database credentials under user-bound DPAPI and retains its own private cluster; it never adopts an unrelated directory or installed service. RLS does not contain a compromised control-plane database login able to change its tenant setting. DPAPI protects credentials at rest, not database contents, and the same-user process boundary remains a residual risk. Database backup/restore, disk encryption, production identity and tenant lifecycle administration remain open gates. See POSTGRES_VERIFICATION.md for executed evidence.

Synthetic local demos may use narrower controls; any absent TLS, OS isolation, external audit anchoring, encrypted storage, secret vault, RLS or network containment remains an open requirement rather than an implicit waiver. No production-derived data or enterprise credentials until these are verified. Human signoff: security owner PENDING; QA owner PENDING; date PENDING. Reassess with each changed trust boundary.
