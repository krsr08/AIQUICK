"""PostgreSQL-only repository. Tenant context is transaction-local."""
from contextlib import contextmanager
from datetime import datetime, timezone
import os
import re
from sqlalchemy import create_engine, select, text, update
from sqlalchemy.dialects.postgresql import insert
from autoqa.domain.models import Plan
from autoqa.persistence.schema import approvals, plans, runs

def tenant_name(value):
    if not isinstance(value, str) or not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}', value):
        raise ValueError('Invalid tenant identity')
    return value

class Repository:
    def __init__(self, url=None):
        url = url or os.environ.get('AUTOQA_DATABASE_URL')
        if not url or not url.startswith('postgresql+psycopg://'):
            raise RuntimeError('A PostgreSQL runtime connection is required')
        self.engine = create_engine(url, pool_pre_ping=True, hide_parameters=True,
            connect_args={'connect_timeout': 5}, pool_size=5, max_overflow=2)
        try:
            with self.engine.connect() as conn:
                role = conn.execute(text('SELECT rolsuper, rolbypassrls, rolcreaterole, rolcreatedb FROM pg_roles WHERE rolname=current_user')).one()
                owner = conn.execute(text("SELECT count(*) FROM pg_tables WHERE schemaname='autoqa' AND pg_has_role(current_user, tableowner, 'MEMBER')")).scalar_one()
                privileged_membership = conn.execute(text("SELECT count(*) FROM pg_roles WHERE (rolsuper OR rolbypassrls) AND pg_has_role(current_user, oid, 'MEMBER')")).scalar_one()
                policies = conn.execute(text("SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='autoqa' AND c.relname IN ('plan_snapshots','approvals','test_runs') AND c.relrowsecurity AND c.relforcerowsecurity")).scalar_one()
                if any(role) or owner or privileged_membership or policies != 3:
                    raise PermissionError('Runtime database must enforce tenant policies with a restricted identity')
        except Exception:
            self.engine.dispose()
            raise

    @contextmanager
    def transaction(self, tenant, *, serialize=False):
        tenant = tenant_name(tenant)
        with self.engine.begin() as conn:
            conn.execute(text("SELECT set_config('autoqa.tenant_id', :tenant, true)"), {'tenant': tenant})
            conn.execute(text("SET LOCAL statement_timeout = '8s'"))
            conn.execute(text("SET LOCAL lock_timeout = '5s'"))
            if serialize:
                conn.execute(text('SELECT pg_advisory_xact_lock(hashtextextended(:tenant, 20261017))'), {'tenant': tenant})
            yield conn

    def load_plan(self, conn, plan_id):
        row = conn.execute(select(plans).where(plans.c.id == plan_id)).mappings().first()
        if row is None:
            raise KeyError(plan_id)
        try:
            plan = Plan.model_validate(row['snapshot'])
        except ValueError:
            raise PermissionError('Stored plan integrity check failed') from None
        if plan.digest() != row['plan_hash'] or plan.id != row['id'] or plan.tenant_id != row['tenant_id']:
            raise PermissionError('Stored plan integrity check failed')
        return plan

    def save_plan(self, conn, plan):
        conn.execute(plans.insert().values(tenant_id=plan.tenant_id, id=plan.id,
            plan_hash=plan.digest(), snapshot=plan.model_dump()))

    def approval(self, conn, plan):
        row = conn.execute(select(approvals).where(approvals.c.plan_id == plan.id)).mappings().first()
        if (row is None or row['plan_hash'] != plan.digest() or row['approver'] == plan.author
                or row['expires_at'] <= datetime.now(timezone.utc)):
            return None
        return dict(row)

    def save_approval(self, conn, plan, actor, expires):
        values = dict(tenant_id=plan.tenant_id, plan_id=plan.id, plan_hash=plan.digest(), approver=actor,
            expires_at=expires, approved_at=datetime.now(timezone.utc))
        conn.execute(insert(approvals).values(**values).on_conflict_do_update(
            index_elements=['tenant_id', 'plan_id'], set_=values))

    def expire_runs(self, conn):
        rows = conn.execute(select(runs.c.id, runs.c.result).where(
            runs.c.status.in_(('QUEUED', 'RUNNING')), runs.c.lease_expires_at <= datetime.now(timezone.utc))).all()
        for run_id, result in rows:
            report = dict(result, status='ERROR', reason='Worker lease expired; execution was not retried')
            conn.execute(update(runs).where(runs.c.id == run_id, runs.c.status.in_(('QUEUED', 'RUNNING'))).values(
                status='ERROR', result=report, updated_at=datetime.now(timezone.utc)))

    def read_runs(self, tenant):
        with self.transaction(tenant) as conn:
            self.expire_runs(conn)
            return {row.id: row.result for row in conn.execute(select(runs.c.id, runs.c.result))}

    def finish(self, tenant, run_id, report):
        with self.transaction(tenant) as conn:
            row = conn.execute(select(runs).where(runs.c.id == run_id).with_for_update()).mappings().first()
            if row is not None and (row['result'] or {}).get('cancel_requested'):
                return False
            changed = conn.execute(update(runs).where(runs.c.id == run_id,
                runs.c.status.in_(('QUEUED', 'RUNNING')),
                runs.c.lease_expires_at > datetime.now(timezone.utc)).values(
                    status=report['status'], result=report, updated_at=datetime.now(timezone.utc))).rowcount
            if not changed:
                self.expire_runs(conn)
            return bool(changed)

    def request_cancel(self, tenant, run_id, actor):
        with self.transaction(tenant) as conn:
            row = conn.execute(select(runs).where(runs.c.id == run_id).with_for_update()).mappings().first()
            if row is None:
                raise KeyError(run_id)
            report = dict(row['result'])
            if row['status'] in ('QUEUED', 'RUNNING') and not report.get('cancel_requested'):
                report.update(cancel_requested=True, cancelled_by=actor,
                              reason='Stopping execution; saved data is not rolled back')
                conn.execute(update(runs).where(runs.c.id == run_id).values(
                    result=report, updated_at=datetime.now(timezone.utc)))
            return report

    def cancellation_requested(self, tenant, run_id):
        with self.transaction(tenant) as conn:
            row = conn.execute(select(runs.c.result).where(runs.c.id == run_id)).first()
            if row is None:
                raise KeyError(run_id)
            return bool((row.result or {}).get('cancel_requested'))

    def worker_should_stop(self, tenant, run_id):
        with self.transaction(tenant) as conn:
            row = conn.execute(select(runs).where(runs.c.id == run_id)).mappings().first()
            return (row is None or row['status'] not in ('QUEUED', 'RUNNING') or
                    row['lease_expires_at'] <= datetime.now(timezone.utc) or
                    bool((row['result'] or {}).get('cancel_requested')))

    def acknowledge_cancel(self, tenant, run_id):
        """Controller calls only after no worker was launched or process cleanup returned."""
        with self.transaction(tenant) as conn:
            self.expire_runs(conn)
            row = conn.execute(select(runs).where(runs.c.id == run_id).with_for_update()).mappings().first()
            if row is None:
                raise KeyError(run_id)
            if row['status'] not in ('QUEUED', 'RUNNING') or not row['result'].get('cancel_requested'):
                return False
            report = dict(row['result'], status='CANCELLED',
                          reason='Execution stopped; saved data is not rolled back')
            conn.execute(update(runs).where(runs.c.id == run_id).values(
                status='CANCELLED', result=report, updated_at=datetime.now(timezone.utc)))
            return True
