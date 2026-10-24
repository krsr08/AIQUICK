"""HTTP boundary for the single-tenant localhost demonstration."""
import json
import os
from pathlib import Path
import secrets
import time
from collections import defaultdict, deque

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, ConfigDict, Field, StrictBool
from .auth import hash_password, verify_password
from autoqa.natural_language.compiler import CompilationError
from autoqa.persistence.repository import tenant_name

ALLOWED_HOSTS = {'localhost:8000', '127.0.0.1:8000', 'testserver'}
ALLOWED_ORIGINS = {'http://localhost:8000', 'http://127.0.0.1:8000', 'http://testserver'}
SESSION_TTL = 1800


class Body(BaseModel):
    model_config = ConfigDict(extra='forbid')


class Login(Body):
    username: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=1, max_length=1024)


class Plan(Body):
    title: str = Field(min_length=1, max_length=200)
    steps: list[str] = Field(min_length=1, max_length=50)
    expected: str = Field(min_length=1, max_length=2000)


class Approval(Body):
    plan_hash: str = Field(min_length=1, max_length=128)
    confirm_expectation: StrictBool


def problem(status, detail):
    return JSONResponse({'type': 'about:blank', 'title': detail, 'status': status}, status_code=status, media_type='application/problem+json')


def create_app(service):
    users = json.loads(os.environ.get('AUTOQA_USERS_JSON', '[]'))
    known_roles = {'Author', 'Approver', 'Runner', 'Auditor', 'Admin'}
    if not isinstance(users, list) or not users:
        raise ValueError('Configure AUTOQA_USERS_JSON local accounts before startup')
    accounts = {}
    for user in users:
        if not isinstance(user, dict) or not isinstance(user.get('username'), str) or not user['username'] or not isinstance(user.get('roles'), list) or not user['roles'] or not set(user['roles']) <= known_roles or not isinstance(user.get('password_hash'), str) or not user['password_hash'].startswith('scrypt$') or user['username'] in accounts:
            raise ValueError('Invalid local account configuration')
        accounts[user['username']] = user
        user['tenant_id'] = tenant_name(user.get('tenant_id', 'synthetic-demo'))
    dummy_hash = hash_password(secrets.token_urlsafe(24))
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
    sessions = {}
    attempts = defaultdict(deque)
    app.state.sessions = sessions
    app.state.service = service

    @app.exception_handler(CompilationError)
    async def compilation_error(request, error):
        return problem(422, str(error))

    @app.exception_handler(HTTPException)
    async def http_error(request, error):
        return problem(error.status_code, str(error.detail))

    @app.exception_handler(RequestValidationError)
    async def validation_error(request, error):
        return problem(422, 'Invalid request')

    for exception, status, title in [(ValueError, 422, 'Invalid operation'), (PermissionError, 403, 'Operation forbidden'), (KeyError, 404, 'Resource not found')]:
        async def service_error(request, error, status=status, title=title):
            return problem(status, title)
        app.add_exception_handler(exception, service_error)

    @app.middleware('http')
    async def boundary(request, call_next):
        if request.headers.get('host') not in ALLOWED_HOSTS:
            return problem(400, 'Invalid host')
        origin = request.headers.get('origin')
        if origin is not None and origin not in ALLOWED_ORIGINS:
            return problem(403, 'Invalid origin')
        mutation = request.method not in {'GET', 'HEAD', 'OPTIONS'}
        if mutation and origin not in ALLOWED_ORIGINS:
            return problem(403, 'Origin required')
        token = request.cookies.get('autoqa_session', '')
        session = sessions.get(token)
        if session and session['expires'] <= time.monotonic():
            sessions.pop(token, None)
            session = None
        request.state.session = session
        if request.url.path.startswith('/api/') and request.url.path != '/api/v1/login':
            if not session:
                return problem(401, 'Authentication required')
            if mutation and not secrets.compare_digest(request.headers.get('x-csrf-token', ''), session['csrf']):
                return problem(403, 'Invalid CSRF token')
        try:
            response = await call_next(request)
        except Exception:
            response = problem(500, 'Internal server error')
        response.headers['Cache-Control'] = 'no-store'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"
        return response

    def actor(request, role=None):
        session = request.state.session
        if not session:
            raise HTTPException(401, 'Authentication required')
        if role and role not in session['roles'] and 'Admin' not in session['roles']:
            raise HTTPException(403, 'Role required')
        return session['username']

    def scoped_service(request):
        actor(request)
        return service.for_tenant(request.state.session['tenant_id'])

    @app.post('/api/v1/login')
    def login(body: Login, request: Request):
        now = time.monotonic()
        key = request.client.host if request.client else 'unknown'
        queue = attempts[key]
        while queue and queue[0] <= now - 60:
            queue.popleft()
        if len(queue) >= 5:
            raise HTTPException(429, 'Too many login attempts')
        queue.append(now)
        account = accounts.get(body.username)
        valid = verify_password(body.password, account['password_hash'] if account else dummy_hash)
        if not account or not valid:
            raise HTTPException(401, 'Invalid credentials')
        old = request.cookies.get('autoqa_session')
        sessions.pop(old, None)
        token = secrets.token_urlsafe(32)
        session = {'username': account['username'], 'roles': account['roles'], 'tenant_id': account['tenant_id'], 'csrf': secrets.token_urlsafe(32), 'expires': now + SESSION_TTL}
        sessions[token] = session
        response = JSONResponse({k: session[k] for k in ('username', 'roles', 'csrf')})
        response.set_cookie('autoqa_session', token, httponly=True, samesite='strict', max_age=SESSION_TTL, secure=request.url.scheme == 'https')
        return response

    @app.get('/api/v1/me')
    def me(request: Request):
        actor(request)
        return {k: request.state.session[k] for k in ('username', 'roles', 'csrf')}

    @app.post('/api/v1/logout')
    def logout(request: Request):
        sessions.pop(request.cookies.get('autoqa_session'), None)
        response = JSONResponse({'logged_out': True})
        response.delete_cookie('autoqa_session')
        return response

    @app.post('/api/v1/plans')
    def compile_plan(body: Plan, request: Request):
        return scoped_service(request).compile(body.model_dump(), actor(request, 'Author'))

    @app.get('/api/v1/plans')
    def plans(request: Request):
        actor(request)
        return scoped_service(request).list_plans()

    @app.post('/api/v1/plans/{plan_id}/approve')
    def approve(plan_id: str, body: Approval, request: Request):
        return scoped_service(request).approve(plan_id, actor(request, 'Approver'), body.plan_hash, body.confirm_expectation)

    @app.post('/api/v1/plans/{plan_id}/runs')
    def start(plan_id: str, body: Body, request: Request):
        username = actor(request, 'Runner')
        key = request.headers.get('idempotency-key', '')
        if not key or len(key) > 200:
            raise HTTPException(422, 'Idempotency-Key required')
        return scoped_service(request).start(plan_id, username, key)

    @app.get('/api/v1/runs')
    def runs(request: Request):
        actor(request)
        return list(scoped_service(request).runs.values())

    @app.get('/api/v1/runs/{run_id}')
    def run(run_id: str, request: Request):
        actor(request)
        return scoped_service(request).runs[run_id]

    @app.post('/api/v1/runs/{run_id}/cancel')
    def cancel(run_id: str, body: Body, request: Request):
        username = actor(request, 'Runner')
        return scoped_service(request).cancel(run_id, username)

    dist = Path(__file__).resolve().parents[4] / 'frontend' / 'dist'

    @app.get('/{path:path}')
    def frontend(path: str, request: Request):
        # Only the login/bootstrap SPA shell and immutable assets are public.
        if path and not path.startswith('assets/'):
            actor(request)
        candidate = (dist / (path or 'index.html')).resolve()
        if not candidate.is_relative_to(dist.resolve()) or not candidate.is_file():
            raise HTTPException(404, 'Resource not found')
        return FileResponse(candidate)

    return app
