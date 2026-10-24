# Safe cancellation â€” 20 October 2026

`POST /api/v1/runs/{id}/cancel` accepts an empty body and requires an authenticated Runner/Admin, the existing Origin/Host/CSRF checks, and the session's tenant scope. A different tenant cannot discover or cancel the run. Repeated cancellation is idempotent. Cancelling an already terminal run returns that result unchanged.

Cancellation is a durable request in the run record. QUEUED/RUNNING remains active, retaining the database's one-active-run constraint, while the UI shows Stopping. The controller polls for cancellation, lease expiry and terminal status between bounded process waits; the same check runs before process launch. Windows API failures and shutdown-verification deadlines fail closed. A prelaunch request prevents browser startup; an active request explicitly terminates the Windows Job Object and checks ActiveProcesses reaches zero (or terminates and checks the POSIX process group), reaps the worker, and removes parent-owned browser profile storage. Only after that path returns does the controller acknowledge CANCELLED. Row locks serialize cancellation with completion; a requested cancellation prevents late PASS/result writes. Reusing the original idempotency key returns the same cancelled run rather than rerunning it.

Cancellation is not a database rollback or a cleanup journal for the target application. An in-flight browser action may complete before shutdown. The UI explicitly states that already-saved target data is not undone. If process cleanup or database access fails, cancellation is not falsely acknowledged; the active lease expires to ERROR. This implementation does not claim distributed cancellation across untrusted worker hosts, an external audit anchor, or OS-level network confinement.

## Validation

**Final full suite: 70 passed, zero failed/skipped, 296.94 seconds, one existing Starlette test-client deprecation warning.** Executed against real PostgreSQL and Chrome on Windows. Frontend TypeScript/Vite build, Bandit (no medium/high findings) and tracked secret-pattern scan passed. [Full output](evidence/cancellation/cancellation-test-output.txt) and [JUnit](evidence/cancellation/cancellation-tests.xml). Executed checks: API role/tenant/CSRF boundaries; durable cross-connection request; prelaunch refusal; late-PASS fencing; terminal idempotency; descendant delayed-write suppression; real Chrome and ChromeDriver process termination; browser profile removal; service-level idempotency; cleanup-failure lease expiry to ERROR.

The linked-assertion baseline commit adfba23 passed GitHub CI run 39305087824. That success does not establish CI success for this cancellation change.

An independent agent review identified missing process-tree shutdown confirmation and missing live lease checks. Both were corrected and re-reviewed before final tests; this agent review is not the blueprint’s required independent human signoff. POSIX code is implemented but this Windows run does not certify Linux behavior.

An intermediate full run passed 67 checks and failed an existing wrong-email browser case with a lease-expiry ERROR, not false PASS. Its output and result are retained. A subsequent 69-test run passed before the last review changes; final 70-test execution includes those changes. This does not establish a flake-free reliability rate.
