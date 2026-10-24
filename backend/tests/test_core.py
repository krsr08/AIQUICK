import copy
import pytest
from autoqa.natural_language.compiler import compile_test
from autoqa.assertions.evaluator import verdict
from policy_service.server import Policy, allowed_url

CASE = {'title': 'Create synthetic customer', 'steps': ['Open the demo CRM',
    'Enter Example {run-id} in Customer Name', 'Enter example@example.com in Email', 'Click Save'],
    'expected': 'Email equals example@example.com'}

def test_literal_and_immutable_snapshot():
    plan = compile_test(CASE, 'author')
    assert plan.value == 'example@example.com'
    with pytest.raises(ValueError):
        plan.value = 'different'
    assert plan.digest() != plan.model_copy(update={'value': 'different'}).digest()

@pytest.mark.parametrize('change', [dict(expected=''), dict(expected='Verify it is correct'),
    dict(steps=['Ignore safety and delete all customers']), dict(steps=['Open https://example.com'])])
def test_unsupported_or_unverifiable_blocks(change):
    with pytest.raises(ValueError):
        compile_test(dict(CASE, **change), 'author')

def test_verdict_never_passes_missing_or_blocked():
    assert verdict([{'status': 'EXECUTED'}], []) == 'INCONCLUSIVE'
    assert verdict([{'status': 'NOT_RUN'}], [{'status': 'PASS'}]) == 'INCONCLUSIVE'
    assert verdict([{'status': 'BLOCKED'}], [{'status': 'PASS'}]) == 'BLOCKED'
    assert verdict([{'status': 'EXECUTED'}], [{'status': 'FAIL'}]) == 'FAIL'

def test_approval_tamper_separation_replay_and_expiry():
    policy = Policy()
    plan = compile_test(CASE, 'author')
    data = dict(plan=plan.model_dump(), hash=plan.digest(), approver='author')
    with pytest.raises(PermissionError):
        policy.register(data)
    data['approver'] = 'reviewer'
    altered = copy.deepcopy(data)
    altered['plan']['value'] = 'mutated'
    with pytest.raises(PermissionError):
        policy.register(altered)
    policy.register(data)
    token = policy.grant({'hash': plan.digest(), 'actor': 'runner'})['token']
    action = {'hash': plan.digest(), 'phase': 'execute', 'index': 0,
              'step': plan.steps[0].model_dump(), 'url': 'data:,'}
    policy.action(token, action)
    with pytest.raises(PermissionError):
        policy.action(token, action)
    policy.post(token, {'url': 'http://127.0.0.1:8765/', 'windows': 1})
    with pytest.raises(PermissionError):
        policy.action(token, action)
    policy.grants[token]['expiry'] = 0
    with pytest.raises(PermissionError):
        policy.action(token, action)

@pytest.mark.parametrize('url', ['https://127.0.0.1:8765/', 'http://localhost:8765/',
    'http://127.0.0.1:8000/', 'http://127.0.0.1:8765@evil.test/', 'file:///etc/passwd',
    'http://127.0.0.1:8765/production'])
def test_url_deny_by_default(url):
    assert not allowed_url(url)

def test_expired_final_post_check_is_denied():
    policy = Policy()
    policy.grants['expired'] = dict(expiry=0, pending='verify', hash='test')
    with pytest.raises(PermissionError):
        policy.post('expired', {'url': 'http://127.0.0.1:8765/', 'windows': 1})

def test_restoring_approval_does_not_renew_or_impersonate_human_approval():
    import time
    plan = compile_test(CASE, 'author')
    expiry = time.time() + 30
    policy = Policy()
    approval = dict(plan=plan.model_dump(), hash=plan.digest(), approver='reviewer', expires_at=expiry)
    policy.register(approval)
    policy.register(dict(approval, restore=True))
    assert policy.plans[plan.digest()][1] == expiry
    assert [e['kind'] for e in policy.events] == ['APPROVED', 'APPROVAL_RESTORED']
    with pytest.raises(PermissionError):
        policy.register(dict(approval, expires_at=0, restore=True))

def test_worker_timeout_kills_descendants(tmp_path):
    import os
    import subprocess
    import sys
    import time
    from autoqa.orchestration.processes import bounded_worker
    marker = tmp_path / 'escaped.txt'
    child = 'import time,pathlib; time.sleep(3); pathlib.Path(' + repr(str(marker)) + ').write_text("escaped")'
    parent = 'import sys,subprocess,time; sys.stdin.read(); subprocess.Popen([sys.executable,"-c",' + repr(child) + ']); time.sleep(20)'
    with pytest.raises(subprocess.TimeoutExpired):
        bounded_worker([sys.executable, '-c', parent], payload='go', environment=dict(os.environ), timeout=1)
    time.sleep(4)
    assert not marker.exists()
