import os
import subprocess
import sys
import threading
import uuid

import httpx

from autoqa.natural_language.compiler import compile_test
from autoqa.orchestration.processes import bounded_worker

class Service:
    """Volatile Sprint 0 store. No SQLite; durable PostgreSQL is a release gate."""
    def __init__(self):
        self.plans = {}
        self.runs = {}
        self.approvals = set()
        self.keys = {}
        self.lock = threading.RLock()
        self.control = os.environ['AUTOQA_POLICY_CONTROL_TOKEN']

    def policy(self, path, data):
        try:
            response = httpx.post('http://127.0.0.1:8766' + path, json=data,
                headers={'Authorization': 'Bearer ' + self.control}, timeout=3, trust_env=False)
            if response.status_code != 200:
                raise PermissionError('Policy denied')
            return response.json()
        except httpx.HTTPError as exc:
            raise PermissionError('Policy unavailable') from exc

    def view(self, plan):
        return dict(plan.model_dump(), hash=plan.digest(), approved=plan.digest() in self.approvals)

    def compile(self, data, author):
        plan = compile_test(data, author)
        with self.lock:
            if len(self.plans) >= 100:
                raise ValueError('Demo plan limit reached; restart clears volatile state')
            self.plans[plan.id] = plan
        return self.view(plan)

    def list_plans(self):
        with self.lock:
            return [self.view(p) for p in self.plans.values()]

    def approve(self, plan_id, actor, plan_hash, confirm_expectation):
        with self.lock:
            plan = self.plans[plan_id]
            if actor == plan.author or not confirm_expectation or plan.digest() != plan_hash:
                raise PermissionError('Independent confirmation of exact plan required')
            self.policy('/approve', {'plan': plan.model_dump(), 'hash': plan_hash, 'approver': actor})
            self.approvals.add(plan_hash)
            return self.view(plan)

    def start(self, plan_id, actor, idempotency_key):
        with self.lock:
            plan = self.plans[plan_id]
            key = (actor, idempotency_key)
            if key in self.keys:
                old_plan, run_id = self.keys[key]
                if old_plan != plan_id:
                    raise ValueError('Idempotency key already used for another plan')
                return self.runs[run_id]
            if any(r['status'] in ('QUEUED', 'RUNNING') for r in self.runs.values()):
                raise ValueError('One synthetic demo run at a time')
            if plan.digest() not in self.approvals:
                raise PermissionError('Approval required')
            if len(self.runs) >= 100:
                raise ValueError('Demo run limit reached')
            grant = self.policy('/grant', {'hash': plan.digest(), 'actor': actor})
            run_id = uuid.uuid4().hex
            self.runs[run_id] = {'id': run_id, 'plan_hash': plan.digest(), 'status': 'QUEUED', 'steps': [], 'assertions': []}
            self.keys[key] = (plan_id, run_id)
            payload = dict(id=run_id, plan=plan.model_dump(), hash=plan.digest(), token=grant['token'])
            threading.Thread(target=self.work, args=(payload,), daemon=True).start()
            return self.runs[run_id]

    def work(self, payload):
        import json
        run_id = payload['id']
        self.runs[run_id]['status'] = 'RUNNING'
        # Deliberately do not pass control-plane credentials or user hashes to worker.
        allowed = ('PATH', 'SYSTEMROOT', 'SYSTEMDRIVE', 'WINDIR', 'TEMP', 'TMP', 'USERPROFILE',
                   'LOCALAPPDATA', 'APPDATA', 'PYTHONPATH', 'PROGRAMFILES', 'PROGRAMFILES(X86)', 'PROGRAMW6432')
        environment = {k: v for k, v in os.environ.items() if k.upper() in allowed}
        try:
            result = bounded_worker([sys.executable, '-m', 'autoqa.selenium_engine.worker'],
                payload=json.dumps(payload), environment=environment, timeout=100)
            report = json.loads(result)
            if report.get('id') != run_id or report.get('plan_hash') != payload['hash']:
                raise ValueError('Invalid report')
            self.runs[run_id] = report
        except (subprocess.SubprocessError, ValueError, OSError):
            self.runs[run_id] = {'id': run_id, 'status': 'ERROR', 'reason': 'Worker failed or exceeded time budget',
                                 'steps': [], 'assertions': []}
