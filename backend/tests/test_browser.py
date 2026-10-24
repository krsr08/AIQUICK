"""Real Chromium tests, never mocked or silently skipped."""
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import time

import httpx
import pytest

from autoqa.orchestration.service import Service
from scripts.run_demo import launch_services
from test_core import CASE

@pytest.fixture(scope='module')
def services():
    root = Path(__file__).resolve().parents[2]
    environment = dict(os.environ)
    environment['PYTHONPATH'] = str(root / 'backend' / 'src') + os.pathsep + str(root)
    environment['AUTOQA_POLICY_CONTROL_TOKEN'] = secrets.token_urlsafe(32)
    os.environ.update({k: environment[k] for k in ('PYTHONPATH', 'AUTOQA_POLICY_CONTROL_TOKEN')})
    processes = launch_services(environment)
    yield Service()
    for process in processes:
        process.terminate()
        process.wait(timeout=10)

@pytest.mark.browser
@pytest.mark.parametrize('expected,status', [('Email equals example@example.com', 'PASS'),
                                           ('Email equals deliberately-wrong@example.com', 'FAIL')])
def test_real_create_and_fresh_session_verification(services, expected, status):
    plan = services.compile(dict(CASE, expected=expected), 'author')
    with pytest.raises(PermissionError):
        services.start(plan['id'], 'author', secrets.token_hex(8))
    services.approve(plan['id'], 'reviewer', plan['hash'], True)
    key = secrets.token_hex(8)
    run = services.start(plan['id'], 'author', key)
    assert services.start(plan['id'], 'author', key)['id'] == run['id']
    deadline = time.monotonic() + 110
    while services.runs[run['id']]['status'] in ('QUEUED', 'RUNNING') and time.monotonic() < deadline:
        time.sleep(.2)
    result = services.runs[run['id']]
    output = Path('work')
    output.mkdir(exist_ok=True)
    (output / f'browser-{status.lower()}.json').write_text(json.dumps(result, indent=2))
    assert result['status'] == status, result
    assert result['assertions'][0]['verification_level'] == 'V2'
    assert all(s['status'] == 'EXECUTED' for s in result['steps'])

def test_proxy_denies_control_plane_and_external_host(services):
    with httpx.Client(proxy='http://127.0.0.1:8767', trust_env=False) as client:
        for target in ('http://127.0.0.1:8000/', 'http://example.com/', 'https://example.com/'):
            try:
                assert client.get(target).status_code == 403
            except httpx.ProxyError:
                assert target.startswith('https:')

def test_policy_refuses_missing_token(services):
    assert httpx.post('http://127.0.0.1:8766/action', json={'phase': 'execute'}, trust_env=False).status_code == 403
