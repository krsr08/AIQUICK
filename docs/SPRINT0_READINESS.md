# Sprint 0 readiness — 2026-10-17

Status: engineering baseline proposed; Sprint 0 exit and Release 1 signoff remain pending. A working local demonstrator is not an enterprise release. This document records required decisions, not observed test results. Executed results belong in the implementation verification report.

## Authority and scope

The authoritative user-uploaded [Implementation Blueprint v2.0](specification/AUTOQA_ENTERPRISE_IMPLEMENTATION_BLUEPRINT_v2.md) is copied without modification. SHA-256: `cf00892582ddfce680fa1394423a38f2ee75c6515ecd6c570361e504f8c8a504`.

Repository: https://github.com/krsr08/AIQUICK. Preserve existing files; propose changes on a feature branch and PR. No agent merge of protected code. Build only controlled synthetic local demonstrations until security and environment owners approve enterprise targets.

## Exit checklist

| Deliverable | Status / evidence needed | Accountable role |
|---|---|---|
| Supplied libraries, browser/driver and licence inventory | Inventory must record exact version, source, hash, compatibility, licence and scan outcome; discovery is not approval to reuse | Automation / DevOps |
| Hardware and Docker/Ollama readiness | Measure available RAM, CPU/GPU and runtime availability; worker density and model sizing remain unmeasured until benchmark | DevOps / AI |
| Runnable skeleton and first vertical slice | See execution evidence; do not infer completion from source files | Backend / QA |
| Threat model v1 and ADRs | Drafts in this directory; independent human review pending | Security / Architect |
| Golden acceptance and negatives | Defined below; PO acceptance pending | PO / QA |
| Baseline controls in CI | Require actual scan runs, SBOM and required-review configuration; workflow files alone are insufficient | DevOps / Security |
| Model benchmark skeleton and licensed shortlist | Harness contract defined; no model selected or benchmarked | AI / Legal |
| Enterprise access | Salesforce and SAP request package prepared below; no request sent and no access certified | PO / Adapter owners |

## Acceptance scenario and two demo candidates

Candidate A: deterministic server-rendered CRM using synthetic records, login and labelled customer form. Candidate B: independently implemented React SPA CRM with delayed rendering and alternate markup. They must eventually run the same English test; selection is proposed and Candidate B is not implied implemented.

Golden TC_CRM_001 follows blueprint section 1.2: unique run-scoped name/email, explicit author and approver, preview of literal expectations, approved immutable plan, create and capture record ID, search with exactly one result, then fresh-session V2 verification of that same record's name and email. A toast alone cannot establish persistence. No tester needs code or locators.

Minimum early slice may demonstrate a narrower controlled login or read-only scenario. Report its exact scope; it does not satisfy TC_CRM_001 or the complete section 17 demonstration.

Required negatives: changed expected email must FAIL; ambiguous target must clarify/BLOCK; unauthorized host/read-only write must deny before action; redirected subresources/popups must not escape egress policy; pre-existing matching records cannot satisfy created-record assertions; mutated plan/approval must refuse run; audit mutation must be detected; missing auth/cross-origin requests must reject; PDP outage must fail closed. Unsupported text must explain supported phrasing and cannot be skipped as success.

## Pending human decisions and access package

1. Name independent security/QA owners and eligible human approvers; enforce protected-path required reviews before merge.
2. Select enterprise OIDC provider, session policy and dev OS-vault integration. Never put passwords in chat or fixtures.
3. Confirm synthetic-only initial environment; identify privacy regime, retention and production-derived data constraints before real QA access.
4. Provide authorized Salesforce sandbox org ID, SAP Fiori system/client and whether SAP GUI for HTML is used; no native Windows SAP GUI support is promised.
5. Select approved dedicated test-account SSO/MFA approach; no bypass of MFA, CAPTCHA or bot protection.
6. Confirm two demo candidates, team capacity and 20–30% schedule contingency; hosted models remain disabled by default.

Sandbox request template: application/version, sandbox URL, tenant/org/system/client identifier, owner, data classification, permitted risk ceiling, external side-effect suppression, dedicated account secret reference, approved MFA pattern, read-only V3 integration identity, cleanup rules, access expiry, and security contact. This is a prepared request, not evidence of communication or approval.

The plan remains S0 plus 18 two-week sprints (38-week target; approximately 46–49 with contingency), not a delivery commitment. Reforecast after Sprint 2.
