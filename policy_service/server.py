"""Separate, loopback-only PDP. In-memory synthetic-demo spike; no durable audit claim."""
import hashlib
import hmac
import json
import os
import secrets
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit

from autoqa.domain.models import Plan

TARGET = 'http://127.0.0.1:8765'
FRESH_PAGES = ('data:,', 'chrome://new-tab-page/', 'chrome://newtab/')

def allowed_url(url):
    parsed = urlsplit(url)
    return (parsed.scheme == 'http' and parsed.netloc == '127.0.0.1:8765'
            and not parsed.username and not parsed.fragment
            and (parsed.path in ('/', '/customers') or
                 (parsed.path.startswith('/records/') and len(parsed.path) == 41)))

class Policy:
    def __init__(self):
        self.plans = {}
        self.grants = {}
        self.events = []
        self.lock = threading.RLock()

    def event(self, kind, digest, **data):
        event = dict(kind=kind, plan_hash=digest, timestamp=time.time(),
                     previous=self.events[-1]['hash'] if self.events else '0' * 64, **data)
        event['hash'] = hashlib.sha256(json.dumps(event, sort_keys=True).encode()).hexdigest()
        self.events.append(event)

    def register(self, data):
        plan = Plan.model_validate(data['plan'])
        if plan.digest() != data['hash'] or data['approver'] == plan.author:
            raise PermissionError('Independent approval and exact plan hash required')
        # Validate the closed demo action sequence independently from the compiler.
        if ([s.kind for s in plan.steps] != ['navigate', 'fill', 'fill', 'click']
            or plan.steps[0].target != 'demo' or plan.steps[-1].target != 'Save'
            or {s.target for s in plan.steps[1:3]} != {'Customer Name', 'Email'}):
            raise PermissionError('Uncertified plan')
        self.plans[plan.digest()] = (plan, time.time() + 900)
        self.event('APPROVED', plan.digest(), actor=data['approver'])
        return {'approved': True}

    def grant(self, data):
        digest = data['hash']
        plan, expiry = self.plans[digest]
        if expiry < time.time():
            raise PermissionError('Approval expired')
        token = secrets.token_urlsafe(32)
        self.grants[token] = dict(hash=digest, expiry=min(expiry, time.time() + 120), next=0,
                                  record=None, pending=None, verification=0)
        self.event('RUN_STARTED', digest, actor=data['actor'])
        return {'token': token}

    def action(self, token, data):
        grant = self.grants[token]
        plan, _ = self.plans[grant['hash']]
        if grant['expiry'] < time.time() or data['hash'] != grant['hash']:
            raise PermissionError('Expired or altered run')
        if grant['pending'] is not None:
            raise PermissionError('Previous action requires post-check')
        phase = data['phase']
        if phase == 'execute':
            index = grant['next']
            if index >= len(plan.steps) or data['index'] != index:
                raise PermissionError('Action replay or order mismatch')
            step = plan.steps[index]
            if data['step'] != step.model_dump():
                raise PermissionError('Action differs from approved snapshot')
            if index == 0:
                if data['url'] not in FRESH_PAGES:
                    raise PermissionError('Session must be fresh')
            elif data['url'] != TARGET + '/':
                raise PermissionError('Unexpected live page')
            grant['next'] += 1
        elif phase == 'verify':
            if grant['next'] != len(plan.steps) or grant['record'] is None:
                raise PermissionError('Cannot verify before completed creation')
            if data['record'] != grant['record'] or grant['verification'] >= 2:
                raise PermissionError('Verification scope mismatch')
            valid_urls = FRESH_PAGES if grant['verification'] == 0 else (TARGET + '/records/' + grant['record'],)
            if data['url'] not in valid_urls:
                raise PermissionError('Verification URL mismatch')
            grant['verification'] += 1
        else:
            raise PermissionError('Unknown phase')
        grant['pending'] = phase
        self.event('ACTION_ALLOWED', grant['hash'], phase=phase)
        return {'allowed': True}

    def post(self, token, data):
        grant = self.grants[token]
        if grant['expiry'] < time.time() or grant['pending'] is None or not allowed_url(data['url']) or data['windows'] != 1:
            raise PermissionError('Post-action scope violation')
        if grant['pending'] == 'verify' and data['url'] != TARGET + '/records/' + grant['record']:
            raise PermissionError('Verification changed record identity')
        if grant['pending'] == 'execute' and grant['next'] == 4:
            record = data['url'].removeprefix(TARGET + '/records/')
            if len(record) != 32 or any(c not in '0123456789abcdef' for c in record):
                raise PermissionError('Save did not produce a record identity')
            grant['record'] = record
        grant['pending'] = None
        self.event('POST_CHECK', grant['hash'])
        return {'allowed': True}

def serve():
    policy = Policy()
    control = os.environ['AUTOQA_POLICY_CONTROL_TOKEN']

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass  # Never log credentials, bodies, URLs or synthetic input values.

        def do_POST(self):
            try:
                size = int(self.headers.get('Content-Length', '0'))
                if not 0 < size <= 20000:
                    raise ValueError()
                data = json.loads(self.rfile.read(size))
                token = self.headers.get('Authorization', '').removeprefix('Bearer ')
                with policy.lock:
                    if self.path in ('/approve', '/grant', '/audit'):
                        if not hmac.compare_digest(token, control):
                            raise PermissionError()
                        if self.path == '/audit':
                            result = {'events': policy.events}
                        else:
                            result = policy.register(data) if self.path == '/approve' else policy.grant(data)
                    elif self.path == '/action':
                        result = policy.action(token, data)
                    elif self.path == '/post':
                        result = policy.post(token, data)
                    else:
                        raise PermissionError()
                payload = json.dumps(result).encode()
                self.send_response(200)
            except (ValueError, KeyError, TypeError, PermissionError):
                payload = b'{"error":"Policy denied request"}'
                self.send_response(403)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
    ThreadingHTTPServer(('127.0.0.1', 8766), Handler).serve_forever()

if __name__ == '__main__':
    serve()
