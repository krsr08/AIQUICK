# Security review record — engineering preview

Independent agent review found three defects during implementation; this is not a substitute for independent human owner review:

1. A timed-out Python worker could leave Chrome descendants. Worker launch now attaches a Windows Job Object before writing the payload; closing it kills the process tree. POSIX uses a process group. A regression launches a delayed marker-writing child and proves it cannot survive timeout.
2. Browser timeout configuration could fail before cleanup was established. Configuration is now inside the browser `try/finally`.
3. PDP post-check accepted expired authorization. Both pre-action and post-action checks now reject expiry; a regression covers expiry at the final observation.

Chrome 153 starts a fresh profile on `chrome://new-tab-page/`, not always `data:,`. The PDP permits only those explicit browser-owned initial blank pages for the first navigation and first verification navigation; subsequent URLs remain bound to the synthetic host and record identity. The worker environment allowlist includes Windows browser-discovery directories but excludes all control-plane credentials.

Bandit reports low-severity B404/B603 subprocess findings. Invocations use fixed interpreter/module argument arrays, `shell=False`, and no tester-controlled commands. The CI gate rejects medium/high findings; low findings remain visible in the scan artifact and require human review. No scanner suppression hides them. The included secret-pattern check is intentionally narrow and does not replace a full enterprise secret-scanning service.

Open release blockers: PostgreSQL/Alembic/RLS, separate OS identities and enforced network isolation, TLS, encrypted durable storage, OS-vault/broker integration, durable signed and externally anchored audit, evidence masking/scanning, deletion/retention, enterprise identity, negative browser escape matrix, full supply-chain/container/licence gates, required branch protection and signed commits. The current proxy permits only HTTP to the fixed synthetic app and denies CONNECT; its browser use does not establish compromised-worker containment.

Verbose diagnostics must never include raw WebDriver exceptions, request bodies, passwords or session tokens. Worker failures deliberately return generic ERROR/BLOCKED. Test logs and synthetic assertion observations provide diagnostic evidence without logging credentials.
