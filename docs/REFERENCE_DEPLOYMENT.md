# Reference deployment decision — 20 October 2026

Status: selected by engineering under the user's instruction to choose appropriate defaults and proceed; not deployed or certified.

Use a self-hosted Linux deployment, initially local containers for development, with PostgreSQL for application/identity persistence, Keycloak for OpenID Connect identity, and OpenBao for secret handles and key operations. This avoids an unrequested paid-cloud commitment and keeps adapters standards-based. Production topology and capacity must follow measured load/recovery requirements rather than a single-machine demo.

Keycloak integration must use authorization code + PKCE, state/nonce validation, exact issuer/audience/redirect matching, bounded key retrieval, server-side sessions and server-provisioned tenant/role mapping. Never trust arbitrary token claims as tenant grants. Local accounts remain development-only.

OpenBao must run with persistent storage and TLS, scoped short-lived workload identities, audited access and an operator-managed initialization/unseal/recovery procedure. No dev-mode server, fixed root token or checked-in secret is acceptable as enterprise evidence. Resolve target credentials by approved handle inside the policy boundary; keep them out of plans, logs, prompts and evidence.

Workers require separate identities, read-only base filesystems, bounded resources, private authenticated control channels, and a network policy that forces all browser traffic through the allowlisting proxy. A browser proxy setting alone does not meet SR-04/SR-10.

Validation blocker observed: Docker server version query exceeded a 15-second deadline; its Windows service was stopped. Attempting to start that service failed with an OS access error. Docker Desktop launch was requested using a hidden window. No container deployment or SSO/vault verification is claimed until the engine responds and the integration is actually exercised. Existing Windows/PostgreSQL/browser tests remain available independently.

Independent security/QA review still requires a named human. Authorized Salesforce and SAP QA environments and their test identities cannot be manufactured locally. These remain release gates, not inferred approvals.

Primary references consulted:
- https://www.keycloak.org/server/configuration-production
- https://www.keycloak.org/guides
- https://openbao.org/docs/commands/server/
- https://openbao.org/docs/configuration/listener/tcp/
