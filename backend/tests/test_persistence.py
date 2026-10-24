"""Real PostgreSQL enforcement tests. No SQLite or mocked database outcomes."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import json
import os
import secrets
import subprocess
import sys
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, delete, func, select, text, update
from sqlalchemy.exc import DBAPIError

from autoqa.api import create_app
from autoqa.api.auth import hash_password
from autoqa.natural_language.compiler import compile_test
from autoqa.orchestration.service import Service
from autoqa.persistence.repository import Repository
from autoqa.persistence.schema import approvals, plans, runs
from test_browser import services
from test_core import CASE


@pytest.fixture
def repo(database):
    value = Repository(database['runtime_url'])
    yield value
    value.engine.dispose()


def tenant():
    return 'test-' + uuid.uuid4().hex


def stored(repo, name):
    plan = compile_test(CASE, 'author').model_copy(update={'tenant_id': name})
    with repo.transaction(name) as conn:
        repo.save_plan(conn, plan)
    return plan


def insert_run(repo, name, plan, *, expired=False):
    run_id = uuid.uuid4().hex
    report = {'id': run_id, 'plan_hash': plan.digest(), 'status': 'RUNNING', 'steps': [], 'assertions': []}
    with repo.transaction(name) as conn:
        conn.execute(runs.insert().values(tenant_id=name, id=run_id, plan_id=plan.id, actor='runner',
            idempotency_key=uuid.uuid4().hex, status='RUNNING', result=report,
            lease_expires_at=datetime.now(timezone.utc) + timedelta(seconds=-10 if expired else 150)))
    return run_id


def test_runtime_role_and_forced_rls(repo):
    with repo.engine.connect() as conn:
        role = conn.execute(text('SELECT rolsuper, rolbypassrls, rolcreaterole, rolcreatedb FROM pg_roles WHERE rolname=current_user')).one()
        assert not any(role)
        flags = conn.execute(text("SELECT c.relname,c.relrowsecurity,c.relforcerowsecurity,pg_get_userbyid(c.relowner)=current_user AS owned FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='autoqa' AND c.relkind='r'")).all()
        assert {r.relname for r in flags} == {'plan_snapshots', 'approvals', 'test_runs'}
        assert all(r.relrowsecurity and r.relforcerowsecurity and not r.owned for r in flags)


def test_no_context_and_tenant_reads_with_check(repo):
    first, second = tenant(), tenant()
    a, b = stored(repo, first), stored(repo, second)
    with repo.engine.connect() as conn:
        for table in (plans, approvals, runs):
            assert conn.execute(select(func.count()).select_from(table)).scalar_one() == 0
    for name, own, foreign in ((first, a, b), (second, b, a)):
        with repo.transaction(name) as conn:
            assert set(conn.execute(select(plans.c.id)).scalars()) == {own.id}
            with pytest.raises(KeyError):
                repo.load_plan(conn, foreign.id)
    forged = compile_test(CASE, 'author').model_copy(update={'tenant_id': second})
    with pytest.raises(DBAPIError) as blocked:
        with repo.transaction(first) as conn:
            repo.save_plan(conn, forged)
    assert blocked.value.orig.sqlstate == '42501'


@pytest.mark.parametrize('mutation', ['update', 'delete'])
def test_runtime_plan_immutable(repo, mutation):
    name = tenant()
    plan = stored(repo, name)
    command = update(plans).where(plans.c.id == plan.id).values(plan_hash='tampered') if mutation == 'update' else delete(plans).where(plans.c.id == plan.id)
    with pytest.raises(DBAPIError) as blocked:
        with repo.transaction(name) as conn:
            conn.execute(command)
    assert blocked.value.orig.sqlstate == '42501'
    with repo.transaction(name) as conn:
        assert repo.load_plan(conn, plan.id).digest() == plan.digest()


def test_pooled_transaction_tenant_does_not_leak(repo):
    first, second = tenant(), tenant()
    stored(repo, first)
    for name in (first, second, first, second):
        with repo.transaction(name) as conn:
            assert conn.execute(text("SELECT current_setting('autoqa.tenant_id', true)")).scalar_one() == name
            assert conn.execute(select(func.count()).select_from(plans)).scalar_one() == (1 if name == first else 0)
        with repo.engine.connect() as conn:
            assert conn.execute(text("SELECT current_setting('autoqa.tenant_id', true)")).scalar_one() in ('', None)
            assert conn.execute(select(func.count()).select_from(plans)).scalar_one() == 0


def test_plan_survives_new_repository_and_process(repo, database):
    name = tenant()
    plan = stored(repo, name)
    other = Repository(database['runtime_url'])
    try:
        with other.transaction(name) as conn:
            assert other.load_plan(conn, plan.id).digest() == plan.digest()
    finally:
        other.engine.dispose()
    program = "import json,sys; from autoqa.persistence.repository import Repository; r=Repository(); t,p=json.load(sys.stdin);\nwith r.transaction(t) as c: print(r.load_plan(c,p).digest())\nr.engine.dispose()"
    result = subprocess.run([sys.executable, '-c', program], input=json.dumps([name, plan.id]),
                            text=True, capture_output=True, timeout=20, check=True)
    assert result.stdout.strip() == plan.digest()


def test_expired_approval_blocks_start(repo, monkeypatch):
    name = tenant()
    plan = stored(repo, name)
    with repo.transaction(name) as conn:
        repo.save_approval(conn, plan, 'reviewer', datetime.now(timezone.utc) - timedelta(seconds=1))
        assert repo.approval(conn, plan) is None
    monkeypatch.setenv('AUTOQA_POLICY_CONTROL_TOKEN', secrets.token_urlsafe(24))
    with pytest.raises(PermissionError, match='Unexpired approval required'):
        Service(repo, name).start(plan.id, 'runner', uuid.uuid4().hex)


def test_admin_corruption_is_refused(repo, database):
    name = tenant()
    plan = stored(repo, name)
    admin = create_engine(database['admin_url'], hide_parameters=True)
    try:
        with admin.begin() as conn:
            snapshot = plan.model_dump()
            snapshot['expected'] = 'Email equals forged@example.com'
            conn.execute(update(plans).where(plans.c.id == plan.id).values(snapshot=snapshot))
        with repo.transaction(name) as conn:
            with pytest.raises(PermissionError, match='integrity'):
                repo.load_plan(conn, plan.id)
    finally:
        admin.dispose()


def test_expired_lease_is_error_and_late_finish_cannot_overwrite(repo):
    name = tenant()
    plan = stored(repo, name)
    run_id = insert_run(repo, name, plan, expired=True)
    result = repo.read_runs(name)[run_id]
    assert result['status'] == 'ERROR'
    assert 'lease expired' in result['reason']
    assert repo.finish(name, run_id, dict(result, status='PASS')) is False
    assert repo.read_runs(name)[run_id] == result


def test_concurrent_idempotency_single_durable_run(services, repo, monkeypatch):
    name = tenant()
    service = services.for_tenant(name)
    plan = service.compile(CASE, 'author')
    service.approve(plan['id'], 'reviewer', plan['hash'], True)
    monkeypatch.setattr(Service, 'work', lambda self, payload: None)
    key = uuid.uuid4().hex
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda _: service.start(plan['id'], 'runner', key), range(4)))
    assert len({r['id'] for r in results}) == 1
    with repo.transaction(name) as conn:
        assert conn.execute(select(func.count()).select_from(runs)).scalar_one() == 1
    assert len(service.runs) == 1


def test_api_cross_tenant_objects_denied(repo, monkeypatch):
    first, second = tenant(), tenant()
    a, b = stored(repo, first), stored(repo, second)
    run_a, run_b = insert_run(repo, first, a), insert_run(repo, second, b)
    password = secrets.token_urlsafe(24)
    monkeypatch.setenv('AUTOQA_POLICY_CONTROL_TOKEN', secrets.token_urlsafe(24))
    monkeypatch.setenv('AUTOQA_USERS_JSON', json.dumps([
        {'username': 'tenant-user', 'tenant_id': first, 'password_hash': hash_password(password),
         'roles': ['Author', 'Approver', 'Runner', 'Auditor']}
    ]))
    with TestClient(create_app(Service(repo))) as client:
        response = client.post('/api/v1/login', json={'username': 'tenant-user', 'password': password}, headers={'Origin': 'http://testserver'})
        assert response.status_code == 200
        headers = {'Origin': 'http://testserver', 'X-CSRF-Token': response.json()['csrf']}
        assert {p['id'] for p in client.get('/api/v1/plans').json()} == {a.id}
        assert {r['id'] for r in client.get('/api/v1/runs').json()} == {run_a}
        assert client.get('/api/v1/runs/' + run_b).status_code == 404
        assert client.post('/api/v1/plans/' + b.id + '/approve', json={'plan_hash': b.digest(), 'confirm_expectation': True}, headers=headers).status_code == 404
        assert client.post('/api/v1/plans/' + b.id + '/runs', json={}, headers=dict(headers, **{'Idempotency-Key': uuid.uuid4().hex})).status_code == 404
        # A request body cannot override the session-bound tenant.
        assert client.post('/api/v1/plans', json=dict(CASE, tenant_id=second), headers=headers).status_code == 422
