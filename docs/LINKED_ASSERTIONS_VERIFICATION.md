# Linked assertion change — 20 October 2026

New v0.3 plans carry one or two ordered, immutable final assertions. Each exact sentence is retained, rendered separately for approval, included in the plan hash, and checked against the same created record in a fresh browser. Supported sentences are `Customer Name equals …` and `Email equals …`, one per line. Duplicate fields, empty clauses, unsupported variables and overlong expectations are rejected. A missing or duplicated required observation cannot produce PASS. The schema deliberately retains v0.2 serialization unchanged so stored approvals do not silently change their content hash.

This extends section 17's paired-field verification; it does not complete CRM login, search/count assertions, cleanup/cancellation, Edge or the full acceptance script. See REQUIREMENTS_STATUS.md for all release gaps and REFERENCE_DEPLOYMENT.md for selected deployment defaults and execution blockers.

## Verification

**Final local full suite: 55 passed, zero failed/skipped, 247.09 seconds; one Starlette test-client deprecation warning.** Windows/Python 3.12.13/PostgreSQL 18.2/Chrome 153.0.8010.53. Command: `.venv\Scripts\python.exe -m pytest -c config/pytest.ini backend/tests -v --tb=short --junitxml=work/linked-tests.xml`. [JUnit](evidence/linked/linked-tests.xml), [full output](evidence/linked/linked-test-output.txt). Real dashboard cases verified two assertions with correct-value PASS and wrong-email FAIL. A separate real browser case seeded a same-name record with the expected old email, created another record, and correctly returned FAIL using the new record ID. Legacy v0.2 snapshot hash/serialization survived real database storage/reload. Frontend TypeScript/Vite build completed successfully. Bandit reported no medium/high findings. No new third-party package was added.

## CI investigation

Run 39140464464 failed all 44 tests during shared PostgreSQL fixture initialization, before test bodies. Follow-up 39303289548 confirmed initdb permission denial with exit 1. Diagnostic output is restricted to fixed categories and exit codes, never database output or credentials. A separate fix grants only the current hosted runner identity inheritable access to its own checkout for PostgreSQL's restricted process token; it does not grant Everyone access or change local installed database services. That checkout-only grant was insufficient. Explicit current-user access on the private cluster directory fixed initialization: [run 39304217464](https://github.com/krsr08/AIQUICK/actions/runs/39304217464) completed successfully for infrastructure commit 25741fb. This is not evidence for the later linked-assertion commit.

An intermediate local diagnostic run encountered inherited stderr-pipe handles from the PostgreSQL server and failed fixture startup. Capture is now restricted to initdb; long-lived server launch retains discarded stderr and its private server log. The affected cluster was explicitly stopped before rerunning tests. The failed output is retained rather than counted as test success.

The first expanded suite passed 53 and failed one test because invalid stored snapshots raised schema validation instead of the repository integrity error. This handling was corrected without weakening the corruption test; intermediate output is retained.
