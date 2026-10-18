from datetime import datetime, timedelta, timezone
import os
import subprocess
import sys
import threading
import uuid
import httpx
from selenium.common.exceptions import WebDriverException
from sqlalchemy import select, func
from sqlalchemy.exc import SQLAlchemyError
from autoqa.natural_language.compiler import compile_test
from autoqa.orchestration.processes import bounded_worker
from autoqa.selenium_engine.configuration import browser_tools
from autoqa.persistence.repository import Repository, tenant_name
from autoqa.persistence.schema import plans, runs

class Service:
    """Durable control-plane state, scoped to the authenticated tenant."""
    def __init__(self, repository=None, tenant_id='synthetic-demo'):
        self.repository = repository if repository is not None else Repository()
        self.tenant_id = tenant_name(tenant_id)
        self.control = os.environ['AUTOQA_POLICY_CONTROL_TOKEN']

    def for_tenant(self, tenant_id):
        return Service(self.repository, tenant_id)

    @property
    def runs(self):
        return self.repository.read_runs(self.tenant_id)

    def policy(self, path, data):
        try:
            response = httpx.post('http://127.0.0.1:8766' + path, json=data,
                headers={'Authorization': 'Bearer ' + self.control}, timeout=3, trust_env=False)
            if response.status_code != 200:
                raise PermissionError('Policy denied')
            return response.json()
        except httpx.HTTPError as exc:
            raise PermissionError('Policy unavailable') from exc

    def view(self, conn, plan):
        return dict(plan.model_dump(), hash=plan.digest(), approved=self.repository.approval(conn, plan) is not None)

    def compile(self, data, author):
        plan = compile_test(data, author).model_copy(update={'tenant_id': self.tenant_id})
        with self.repository.transaction(self.tenant_id, serialize=True) as conn:
            if conn.execute(select(func.count()).select_from(plans)).scalar_one() >= 100:
                raise ValueError('Demo tenant plan limit reached')
            self.repository.save_plan(conn, plan)
            return self.view(conn, plan)

    def list_plans(self):
        with self.repository.transaction(self.tenant_id) as conn:
            return [self.view(conn, self.repository.load_plan(conn, row.id))
                    for row in conn.execute(select(plans.c.id).order_by(plans.c.created_at))]

    def approve(self, plan_id, actor, plan_hash, confirm_expectation):
        with self.repository.transaction(self.tenant_id, serialize=True) as conn:
            plan = self.repository.load_plan(conn, plan_id)
            if actor == plan.author or not confirm_expectation or plan.digest() != plan_hash:
                raise PermissionError('Independent confirmation of exact plan required')
            expires = datetime.now(timezone.utc) + timedelta(minutes=15)
            self.policy('/approve', {'plan': plan.model_dump(), 'hash': plan_hash, 'approver': actor,
                                     'expires_at': expires.timestamp()})
            self.repository.save_approval(conn, plan, actor, expires)
            return self.view(conn, plan)

    def start(self, plan_id, actor, idempotency_key):
        with self.repository.transaction(self.tenant_id, serialize=True) as conn:
            plan = self.repository.load_plan(conn, plan_id)
            self.repository.expire_runs(conn)
            prior = conn.execute(select(runs).where(runs.c.actor == actor,
                                runs.c.idempotency_key == idempotency_key)).mappings().first()
            if prior:
                if prior['plan_id'] != plan_id:
                    raise ValueError('Idempotency key already used for another plan')
                return prior['result']
            if conn.execute(select(func.count()).select_from(runs).where(runs.c.status.in_(('QUEUED', 'RUNNING')))).scalar_one():
                raise ValueError('One synthetic demo run per tenant at a time')
            approval = self.repository.approval(conn, plan)
            if approval is None:
                raise PermissionError('Unexpired approval required')
            if conn.execute(select(func.count()).select_from(runs)).scalar_one() >= 100:
                raise ValueError('Demo tenant run limit reached')
            self.policy('/approve', {'plan': plan.model_dump(), 'hash': plan.digest(),
                'approver': approval['approver'], 'expires_at': approval['expires_at'].timestamp(), 'restore': True})
            grant = self.policy('/grant', {'hash': plan.digest(), 'actor': actor})
            run_id = uuid.uuid4().hex
            report = {'id': run_id, 'plan_hash': plan.digest(), 'status': 'QUEUED', 'steps': [], 'assertions': []}
            conn.execute(runs.insert().values(tenant_id=self.tenant_id, id=run_id, plan_id=plan.id,
                actor=actor, idempotency_key=idempotency_key, status='QUEUED', result=report,
                lease_expires_at=datetime.now(timezone.utc) + timedelta(seconds=150)))
            payload = dict(id=run_id, plan=plan.model_dump(), hash=plan.digest(), token=grant['token'])
        threading.Thread(target=self.work, args=(payload,), daemon=True).start()
        return report

    def work(self, payload):
        import json
        run_id = payload['id']
        initial = {'id': run_id, 'plan_hash': payload['hash'], 'status': 'RUNNING', 'steps': [], 'assertions': []}
        try:
            if not self.repository.finish(self.tenant_id, run_id, initial):
                return
            allowed = ('PATH', 'SYSTEMROOT', 'SYSTEMDRIVE', 'WINDIR', 'TEMP', 'TMP', 'USERPROFILE',
                       'LOCALAPPDATA', 'APPDATA', 'PYTHONPATH', 'PROGRAMFILES', 'PROGRAMFILES(X86)', 'PROGRAMW6432')
            environment = {k: v for k, v in os.environ.items() if k.upper() in allowed}
            environment.update(browser_tools())
            result = bounded_worker([sys.executable, '-m', 'autoqa.selenium_engine.worker'],
                payload=json.dumps(payload), environment=environment, timeout=100)
            report = json.loads(result)
            if report.get('id') != run_id or report.get('plan_hash') != payload['hash']:
                raise ValueError('Invalid report')
            self.repository.finish(self.tenant_id, run_id, report)
        except (subprocess.SubprocessError, ValueError, OSError, RuntimeError, WebDriverException, SQLAlchemyError):
            try:
                self.repository.finish(self.tenant_id, run_id, dict(initial, status='ERROR',
                    reason='Worker or storage failed; execution was not retried'))
            except SQLAlchemyError:
                pass  # Expired lease becomes ERROR when the database returns.
