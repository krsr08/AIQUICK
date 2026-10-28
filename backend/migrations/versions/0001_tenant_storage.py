"""Immutable plans, renewable approvals and idempotent runs with forced tenant RLS."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001_tenant_storage"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Provision autoqa_app separately: it must not own these objects or bypass RLS.
    op.execute("""DO $$ BEGIN
      IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'autoqa_app') THEN
        RAISE EXCEPTION 'Provision autoqa_app before applying this migration';
      END IF;
      IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'autoqa_app' AND (rolsuper OR rolbypassrls OR rolcreaterole OR rolcreatedb)) THEN
        RAISE EXCEPTION 'autoqa_app must be a restricted runtime role';
      END IF;
      IF current_user = 'autoqa_app' THEN
        RAISE EXCEPTION 'Runtime role cannot own the migration';
      END IF;
    END $$""")
    op.execute("CREATE SCHEMA autoqa")
    op.execute("REVOKE CREATE ON SCHEMA public FROM PUBLIC")
    op.execute("REVOKE ALL ON SCHEMA autoqa FROM PUBLIC")
    op.execute("GRANT USAGE ON SCHEMA autoqa TO autoqa_app")
    op.create_table(
        "plan_snapshots",
        sa.Column("tenant_id", sa.Text(), primary_key=True),
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("plan_hash", sa.Text(), nullable=False),
        sa.Column("snapshot", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        schema="autoqa",
    )
    op.create_table(
        "approvals",
        sa.Column("tenant_id", sa.Text(), primary_key=True),
        sa.Column("plan_id", sa.Text(), primary_key=True),
        sa.Column("plan_hash", sa.Text(), nullable=False),
        sa.Column("approver", sa.Text(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["tenant_id", "plan_id"], ["autoqa.plan_snapshots.tenant_id", "autoqa.plan_snapshots.id"], name="fk_approvals_plan"),
        schema="autoqa",
    )
    op.create_table(
        "test_runs",
        sa.Column("tenant_id", sa.Text(), primary_key=True),
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("plan_id", sa.Text(), nullable=False),
        sa.Column("actor", sa.Text(), nullable=False),
        sa.Column("idempotency_key", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("status IN ('QUEUED','RUNNING','PASS','FAIL','ERROR','BLOCKED','INCONCLUSIVE','CANCELLED')", name="ck_runs_status"),
        sa.Column("result", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["tenant_id", "plan_id"], ["autoqa.plan_snapshots.tenant_id", "autoqa.plan_snapshots.id"], name="fk_runs_plan"),
        sa.UniqueConstraint("tenant_id", "actor", "idempotency_key", name="uq_runs_idempotency"),
        schema="autoqa",
    )
    op.create_index("uq_runs_active_tenant", "test_runs", ["tenant_id"], unique=True, schema="autoqa", postgresql_where=sa.text("status IN ('QUEUED', 'RUNNING')"))
    # Names are migration-owned constants, never user input.
    for table in ("plan_snapshots", "approvals", "test_runs"):
        op.execute(f"ALTER TABLE autoqa.{table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE autoqa.{table} FORCE ROW LEVEL SECURITY")
        op.execute(f"CREATE POLICY tenant_isolation ON autoqa.{table} TO autoqa_app USING (tenant_id = current_setting('autoqa.tenant_id', true)) WITH CHECK (tenant_id = current_setting('autoqa.tenant_id', true))")
        op.execute(f"REVOKE ALL ON TABLE autoqa.{table} FROM PUBLIC, autoqa_app")
    op.execute("GRANT SELECT, INSERT ON autoqa.plan_snapshots TO autoqa_app")
    op.execute("GRANT SELECT, INSERT, UPDATE ON autoqa.approvals, autoqa.test_runs TO autoqa_app")


def downgrade():
    op.drop_table("test_runs", schema="autoqa")
    op.drop_table("approvals", schema="autoqa")
    op.drop_table("plan_snapshots", schema="autoqa")
    op.execute("DROP SCHEMA autoqa")
    # Intentionally retain public CREATE hardening; restoring broad privilege is unsafe.
