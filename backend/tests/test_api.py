import json
import time

import pytest
from fastapi.testclient import TestClient
from autoqa.api import create_app
from autoqa.api.auth import hash_password, verify_password


class Service:
    runs = {'run1': {'id': 'run1', 'status': 'passed'}}

    def for_tenant(self, tenant_id):
        return self

    def compile(self, body, author):
        return {'id': 'plan1', 'author': author, **body}

    def list_plans(self):
        return []

    def approve(self, plan_id, actor, plan_hash, confirm_expectation):
        if not confirm_expectation:
            raise ValueError('secret internal failure')
        return {'id': plan_id, 'approved_by': actor}

    def start(self, plan_id, actor, idempotency_key):
        return {'id': 'run1', 'actor': actor}

    def cancel(self, run_id, actor):
        if run_id not in self.runs:
            raise KeyError(run_id)
        return {'id': run_id, 'actor': actor, 'status': 'RUNNING', 'cancel_requested': True}


@pytest.fixture
def client(monkeypatch):
    hashed = hash_password('test-password-123')
    monkeypatch.setenv('AUTOQA_USERS_JSON', json.dumps([
        {'username': role.lower(), 'password_hash': hashed, 'roles': [role]}
        for role in ['Author', 'Approver', 'Runner', 'Auditor', 'Admin']
    ]))
    return TestClient(create_app(Service()))


def login(client, role='author'):
    response = client.post('/api/v1/login', json={'username': role, 'password': 'test-password-123'}, headers={'Origin': 'http://testserver'})
    assert response.status_code == 200
    return {'Origin': 'http://testserver', 'X-CSRF-Token': response.json()['csrf']}


def test_password_hash():
    encoded = hash_password('test-password-123')
    assert verify_password('test-password-123', encoded)
    assert not verify_password('wrong-password', encoded)
    assert not verify_password('anything', 'malformed')
    with pytest.raises(ValueError):
        hash_password('short')


def test_no_default_accounts(monkeypatch):
    monkeypatch.delenv('AUTOQA_USERS_JSON', raising=False)
    with pytest.raises(ValueError):
        create_app(Service())


def test_auth_cookie_and_expiry(client):
    assert client.get('/api/v1/runs').status_code == 401
    headers = login(client)
    assert client.get('/api/v1/me').json()['username'] == 'author'
    cookie = client.cookies.get('autoqa_session')
    client.app.state.sessions[cookie]['expires'] = time.monotonic() - 1
    assert client.get('/api/v1/me').status_code == 401
    assert cookie not in client.app.state.sessions


def test_cookie_flags_and_logout(client):
    response = client.post('/api/v1/login', json={'username': 'author', 'password': 'test-password-123'}, headers={'Origin': 'http://testserver'})
    assert 'HttpOnly' in response.headers['set-cookie']
    assert 'SameSite=strict' in response.headers['set-cookie']
    headers = {'Origin': 'http://testserver', 'X-CSRF-Token': response.json()['csrf']}
    assert client.post('/api/v1/logout', headers=headers).status_code == 200
    assert client.get('/api/v1/me').status_code == 401


def test_host_origin_and_csrf(client):
    assert client.get('/api/v1/me', headers={'Host': 'evil.example'}).status_code == 400
    assert client.get('/api/v1/me', headers={'Origin': 'https://evil.example'}).status_code == 403
    assert client.post('/api/v1/login', json={}).status_code == 403
    headers = login(client)
    body = {'title': 'Test', 'steps': ['Open fixture'], 'expected': 'Visible'}
    assert client.post('/api/v1/plans', json=body, headers={'Origin': 'http://testserver'}).status_code == 403
    assert client.post('/api/v1/plans', json=body, headers=headers).status_code == 200
    assert client.post('/api/v1/plans', json={**body, 'extra': 'bad'}, headers=headers).status_code == 422


def test_roles_and_safe_errors(client):
    headers = login(client, 'auditor')
    assert client.get('/api/v1/runs').status_code == 200
    assert client.post('/api/v1/plans', json={'title': 'Test', 'steps': ['Open fixture'], 'expected': 'Visible'}, headers=headers).status_code == 403
    assert client.post('/api/v1/plans/p/approve', json={'plan_hash': 'hash', 'confirm_expectation': True}, headers=headers).status_code == 403
    headers = login(client, 'approver')
    response = client.post('/api/v1/plans/p/approve', json={'plan_hash': 'hash', 'confirm_expectation': False}, headers=headers)
    assert response.status_code == 422
    assert response.headers['content-type'] == 'application/problem+json'
    assert 'secret' not in response.text
    assert client.get('/api/v1/runs/missing').status_code == 404


def test_runner_idempotency_required(client):
    headers = login(client, 'runner')
    assert client.post('/api/v1/plans/p/runs', json={}, headers=headers).status_code == 422
    headers['Idempotency-Key'] = 'unique-run-1'
    assert client.post('/api/v1/plans/p/runs', json={}, headers=headers).status_code == 200


def test_login_rate_limit(client):
    for _ in range(5):
        assert client.post('/api/v1/login', json={'username': 'missing', 'password': 'incorrect'}, headers={'Origin': 'http://testserver'}).status_code == 401
    assert client.post('/api/v1/login', json={'username': 'missing', 'password': 'incorrect'}, headers={'Origin': 'http://testserver'}).status_code == 429


@pytest.mark.parametrize('role', ['author', 'approver', 'auditor'])
def test_cancel_requires_runner_role(client, role):
    headers = login(client, role)
    assert client.post('/api/v1/runs/run1/cancel', json={}, headers=headers).status_code == 403


@pytest.mark.parametrize('role', ['runner', 'admin'])
def test_cancel_requires_csrf_and_empty_body(client, role):
    assert client.post('/api/v1/runs/run1/cancel', json={}, headers={'Origin': 'http://testserver'}).status_code == 401
    headers = login(client, role)
    assert client.post('/api/v1/runs/run1/cancel', json={}, headers={'Origin': 'http://testserver'}).status_code == 403
    assert client.post('/api/v1/runs/run1/cancel', json={'tenant_id': 'other'}, headers=headers).status_code == 422
    response = client.post('/api/v1/runs/run1/cancel', json={}, headers=headers)
    assert response.status_code == 200
    assert response.json() == {'id': 'run1', 'actor': role, 'status': 'RUNNING', 'cancel_requested': True}
    assert client.post('/api/v1/runs/missing/cancel', json={}, headers=headers).status_code == 404


def test_cancel_uses_authenticated_tenant(client, monkeypatch):
    headers = login(client, 'runner')
    scoped_tenants = []
    service = client.app.state.service

    def scoped(tenant_id):
        scoped_tenants.append(tenant_id)
        return service

    monkeypatch.setattr(service, 'for_tenant', scoped)
    assert client.post('/api/v1/runs/run1/cancel', json={}, headers=headers).status_code == 200
    assert scoped_tenants == ['synthetic-demo']
