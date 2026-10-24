"""PostgreSQL tenant-scoped storage contracts; runtime access is RLS-enforced."""
from sqlalchemy import (
    CheckConstraint, Column, DateTime, ForeignKeyConstraint, Index, MetaData, Table, Text,
    UniqueConstraint, func,
)
from sqlalchemy.dialects.postgresql import JSONB

metadata = MetaData(schema="autoqa")
plans = Table(
    "plan_snapshots", metadata,
    Column("tenant_id", Text, primary_key=True),
    Column("id", Text, primary_key=True),
    Column("plan_hash", Text, nullable=False),
    Column("snapshot", JSONB, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
)
approvals = Table(
    "approvals", metadata,
    Column("tenant_id", Text, primary_key=True),
    Column("plan_id", Text, primary_key=True),
    Column("plan_hash", Text, nullable=False),
    Column("approver", Text, nullable=False),
    Column("expires_at", DateTime(timezone=True), nullable=False),
    Column("approved_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    ForeignKeyConstraint(["tenant_id", "plan_id"], ["autoqa.plan_snapshots.tenant_id", "autoqa.plan_snapshots.id"], name="fk_approvals_plan"),
)
runs = Table(
    "test_runs", metadata,
    Column("tenant_id", Text, primary_key=True),
    Column("id", Text, primary_key=True),
    Column("plan_id", Text, nullable=False),
    Column("actor", Text, nullable=False),
    Column("idempotency_key", Text, nullable=False),
    Column("status", Text, nullable=False),
    Column("lease_expires_at", DateTime(timezone=True), nullable=False),
    CheckConstraint("status IN ('QUEUED','RUNNING','PASS','FAIL','ERROR','BLOCKED','INCONCLUSIVE','CANCELLED')", name="ck_runs_status"),
    Column("result", JSONB, nullable=True),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("updated_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    ForeignKeyConstraint(["tenant_id", "plan_id"], ["autoqa.plan_snapshots.tenant_id", "autoqa.plan_snapshots.id"], name="fk_runs_plan"),
    UniqueConstraint("tenant_id", "actor", "idempotency_key", name="uq_runs_idempotency"),
)

Index("uq_runs_active_tenant", runs.c.tenant_id, unique=True, postgresql_where=runs.c.status.in_(("QUEUED", "RUNNING")))
