# PostgreSQL dependency addendum

Observed 2026-10-18 (Asia/Calcutta). This addendum preserves the original 81-package inventory as historical evidence. Six additional installed versions are now pinned for PostgreSQL persistence and migrations, bringing the audit inventory to 87 dependencies.

| Dependency | Installed pin | Local declared licence | Justification |
|---|---|---|---|
| SQLAlchemy | 2.1.5 | MIT | Typed Core statements, PostgreSQL JSONB metadata, safe parameter binding and pooled transactions |
| alembic | 1.20.0 | MIT | Versioned PostgreSQL schema upgrade/downgrade, isolated administrator migration identity |
| Mako | 1.4.3 | MIT | Alembic transitive migration-template dependency |
| MarkupSafe | 3.0.4 | BSD-3-Clause | Mako transitive escaping dependency |
| psycopg | 3.3.6 | LGPL-3.0-only | PostgreSQL 3 driver API and safe SQL composables for isolated test provisioning |
| psycopg-binary | 3.3.6 | LGPL-3.0-only | Packaged native PostgreSQL driver implementation for Windows development |

## Local licence evidence

- SQLAlchemy: `sqlalchemy-2.1.5.dist-info/licenses/LICENSE`; SHA-256 `9bb754071e711cf75728b9051b170bfb8f9e3b879c08386c96a36989c42cd5f1`. Metadata and licence header inspected.
- alembic: `alembic-1.20.0.dist-info/licenses/LICENSE`; SHA-256 `6e68d94a03a0e3e327ddf3e86d1ebedc14eece3922022618fc246a36296fd0cc`. Metadata and licence header inspected.
- Mako: `mako-1.4.3.dist-info/licenses/LICENSE`; SHA-256 `8c1d171bc5d341ad9cd33d5e2c39b96a82c7bd49b3ae89a470c37e5822232054`. Metadata and licence header inspected.
- MarkupSafe: `markupsafe-3.0.4.dist-info/licenses/LICENSE.txt`; SHA-256 `4631ec0db5fd90a547e336817264c6798214338146f8ac94b4a57f96ee8c9ec4`. Metadata and licence header inspected.
- psycopg: `psycopg-3.3.6.dist-info/licenses/LICENSE.txt`; SHA-256 `e3a994d82e644b03a792a930f574002658412f62407f5fee083f2555c5f23118`. Metadata and licence header inspected.
- psycopg-binary: `psycopg_binary-3.3.6.dist-info/licenses/LICENSE.txt`; SHA-256 `7d3a95e5e06978064ed3f8e2b7c8f845e7fd8a405294727cc708f94cb83b8059`. Metadata and licence header inspected.

Psycopg and psycopg-binary declare LGPL-3.0-only. This inventory does not establish enterprise redistribution clearance or waive the project's licence approval requirement. Before distributing packaged binaries, obtain the owner/legal review of applicable obligations and the binary wheel's bundled component notices. Mako and MarkupSafe are migration-tool dependencies; keep tooling separate from production runtime where practical. Preserve required licence notices. No dependency licence was silently relabelled as permissive.

## Observed vulnerability audit

Existing `work/postgres-dependency-audit.json` contains 87 packages, with 0 reported known vulnerabilities and 0 fixes. Result SHA-256: `c0618c9bd4d48e892673830c374abf40e4d0dc59cf8fbb8cf5c93513dccf1e46`. The implementation owner ran this audit; the documentation task inspected its output rather than claiming a new scan. This is a point-in-time known-vulnerability result, not a guarantee of safety or licence approval.

The existing lock remains version-pinned without package artifact hashes; fully hash-locked builds and distribution review remain follow-up requirements. See [POSTGRES.md](POSTGRES.md) for migration roles and execution evidence.
