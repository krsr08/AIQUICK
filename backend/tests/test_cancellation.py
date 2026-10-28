"""Real database fencing and OS process-tree cancellation regressions."""
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import time
import uuid
import pytest
from sqlalchemy import select
from autoqa.orchestration.processes import bounded_worker, WorkerCancelled
from autoqa.orchestration.service import Service
from autoqa.persistence.repository import Repository
from autoqa.persistence.schema import runs
from test_persistence import stored, insert_run

def test_cancel_persists_and_fences_completion_until_acknowledged(database):
    repo=Repository(database['runtime_url'])
    tenant='cancel-'+uuid.uuid4().hex
    try:
        plan=stored(repo,tenant)
        run_id=insert_run(repo,tenant,plan)
        request=repo.request_cancel(tenant,run_id,'runner')
        assert request['cancel_requested'] and request['status']=='RUNNING'
        assert repo.request_cancel(tenant,run_id,'other')==request
        assert not repo.finish(tenant,run_id,dict(request,status='PASS'))
        other=Repository(database['runtime_url'])
        try:
            assert other.cancellation_requested(tenant,run_id)
            with pytest.raises(KeyError): other.request_cancel('other-tenant',run_id,'runner')
        finally: other.engine.dispose()
        with repo.transaction(tenant) as conn:
            assert conn.execute(select(runs.c.status).where(runs.c.id==run_id)).scalar_one()=='RUNNING'
        assert repo.acknowledge_cancel(tenant,run_id)
        assert repo.read_runs(tenant)[run_id]['status']=='CANCELLED'
        assert not repo.finish(tenant,run_id,dict(request,status='PASS'))
        assert not repo.acknowledge_cancel(tenant,run_id)
    finally: repo.engine.dispose()

def test_prelaunch_cancel_never_starts_process(tmp_path):
    marker=tmp_path/'launched'
    with pytest.raises(WorkerCancelled):
        bounded_worker([sys.executable,'-c','from pathlib import Path; Path('+repr(str(marker))+').touch()'],
            payload='',environment=dict(os.environ),timeout=10,cancelled=lambda:True)
    assert not marker.exists()

def test_cancellation_kills_descendant_before_delayed_write(tmp_path):
    marker=tmp_path/'escaped'
    ready=tmp_path/'ready'
    child='import time,pathlib; time.sleep(3); pathlib.Path('+repr(str(marker))+').touch()'
    parent='import sys,subprocess,time,pathlib; sys.stdin.read(); subprocess.Popen([sys.executable,"-c",'+repr(child)+']); pathlib.Path('+repr(str(ready))+').touch(); time.sleep(20)'
    with pytest.raises(WorkerCancelled):
        bounded_worker([sys.executable,'-c',parent],payload='go',environment=dict(os.environ),timeout=15,cancelled=ready.exists)
    time.sleep(4)
    assert ready.exists() and not marker.exists()

def test_cancel_after_terminal_result_is_noop(database):
    repo=Repository(database['runtime_url']);tenant='terminal-'+uuid.uuid4().hex
    try:
        plan=stored(repo,tenant);run_id=insert_run(repo,tenant,plan)
        report={'id':run_id,'status':'PASS','steps':[],'assertions':[]}
        assert repo.finish(tenant,run_id,report)
        assert repo.request_cancel(tenant,run_id,'runner')==report
    finally: repo.engine.dispose()

@pytest.mark.browser
@pytest.mark.parametrize('browser_name', ['chrome', 'edge'])
def test_cancel_stops_real_browser_and_driver(tmp_path, monkeypatch, browser_name):
    import ctypes
    from autoqa.selenium_engine.configuration import browser_tools
    monkeypatch.setenv('AUTOQA_BROWSER', browser_name)
    ready=tmp_path/f'{browser_name}-ready.json'
    profile_root=tmp_path/'profiles';profile_root.mkdir()
    environment={k:v for k,v in os.environ.items() if not k.startswith('AUTOQA_')}
    environment.update(browser_tools());environment['AUTOQA_PROFILE_ROOT']=str(profile_root)
    script='''import sys,json,time
from pathlib import Path
from autoqa.selenium_engine.worker import browser
payload=json.loads(sys.stdin.read())
ready=Path(payload['ready'])
with browser() as driver:
    assert driver.capabilities['browserName']=={'chrome':'chrome','edge':'MicrosoftEdge'}[payload['browser_name']]
    driver.get('data:text/html,<title>Cancellation fixture</title>')
    assert driver.title=='Cancellation fixture'
    capability = 'goog:processID'  # Both installed Chromium drivers expose this key.
    staging=ready.with_suffix('.tmp')
    staging.write_text(json.dumps({'driver':driver.service.process.pid,'browser':driver.capabilities[capability]}))
    staging.replace(ready)
    time.sleep(60)
'''
    handles=[]
    pids={}
    if os.name=='nt':
        from ctypes import wintypes
        kernel=ctypes.WinDLL('kernel32',use_last_error=True)
        kernel.OpenProcess.argtypes=[wintypes.DWORD,wintypes.BOOL,wintypes.DWORD]
        kernel.OpenProcess.restype=wintypes.HANDLE
        kernel.WaitForSingleObject.argtypes=[wintypes.HANDLE,wintypes.DWORD]
        kernel.WaitForSingleObject.restype=wintypes.DWORD
        kernel.CloseHandle.argtypes=[wintypes.HANDLE]
    def pin_processes_then_cancel():
        if not ready.exists():
            return False
        pids.update(json.loads(ready.read_text()))
        if os.name=='nt':
            for pid in pids.values():
                handle=kernel.OpenProcess(0x00100000,False,pid)
                assert handle, f'Cannot pin live process {pid}: Windows error {ctypes.get_last_error()}'
                handles.append(handle)
                assert kernel.WaitForSingleObject(handle,0)==258, 'Process exited before cancellation'
        return True
    try:
        with pytest.raises(WorkerCancelled):
            bounded_worker([sys.executable,'-c',script],payload=json.dumps({'ready':str(ready),'browser_name':browser_name}),
                environment=environment,timeout=40,cancelled=pin_processes_then_cancel)
        assert set(pids)=={'driver','browser'}
        if os.name=='nt':
            assert len(handles)==2
            for handle in handles:
                assert kernel.WaitForSingleObject(handle,5000)==0, 'Cancelled process did not terminate'
        else:
            for pid in pids.values():
                with pytest.raises(ProcessLookupError): os.kill(pid,0)
    finally:
        for handle in handles:
            kernel.CloseHandle(handle)
    import shutil
    shutil.rmtree(profile_root)
    assert not profile_root.exists()
    Path(f'work/cancellation-{browser_name}.json').write_text(json.dumps({'browser_name':browser_name,'real_browser_started':True,
        'driver_and_browser_stopped':True,'profiles_removed':True,'status':'CANCELLED'},indent=2))

def test_queued_cancellation_acknowledged_without_launch(database,monkeypatch):
    repo=Repository(database['runtime_url']);tenant='queued-'+uuid.uuid4().hex
    monkeypatch.setenv('AUTOQA_POLICY_CONTROL_TOKEN','test-control')
    try:
        plan=stored(repo,tenant);run_id=insert_run(repo,tenant,plan)
        repo.request_cancel(tenant,run_id,'runner')
        def forbidden(): raise AssertionError('Cancelled run must not resolve or launch a browser')
        monkeypatch.setattr('autoqa.orchestration.service.browser_tools',forbidden)
        Service(repo,tenant).work({'id':run_id,'hash':plan.digest()})
        assert repo.read_runs(tenant)[run_id]['status']=='CANCELLED'
    finally: repo.engine.dispose()

@pytest.mark.browser
def test_service_cancellation_is_durable_and_idempotent(services):
    from test_core import CASE
    plan=services.compile(CASE,'cancel-author')
    services.approve(plan['id'],'cancel-reviewer',plan['hash'],True)
    key=secrets.token_hex(16)
    run=services.start(plan['id'],'cancel-author',key)
    requested=services.cancel(run['id'],'cancel-author')
    assert requested['cancel_requested']
    deadline=time.monotonic()+110
    while time.monotonic()<deadline:
        result=services.runs[run['id']]
        if result['status'] not in ('QUEUED','RUNNING'): break
        time.sleep(.2)
    assert result['status']=='CANCELLED',result
    assert services.start(plan['id'],'cancel-author',key)['status']=='CANCELLED'
    assert services.cancel(run['id'],'cancel-author')['status']=='CANCELLED'
    Path('work/cancellation-service.json').write_text(json.dumps(result,indent=2))

from test_browser import services

def test_cleanup_failure_does_not_acknowledge_cancellation(database,monkeypatch):
    repo=Repository(database['runtime_url']);tenant='cleanup-'+uuid.uuid4().hex
    monkeypatch.setenv('AUTOQA_POLICY_CONTROL_TOKEN','test-control')
    try:
        plan=stored(repo,tenant);run_id=insert_run(repo,tenant,plan)
        monkeypatch.setattr('autoqa.orchestration.service.browser_tools',lambda:{})
        def failed(*args,**kwargs):
            repo.request_cancel(tenant,run_id,'runner')
            raise OSError('simulated process cleanup failure')
        monkeypatch.setattr('autoqa.orchestration.service.bounded_worker',failed)
        Service(repo,tenant).work({'id':run_id,'hash':plan.digest()})
        result=repo.read_runs(tenant)[run_id]
        assert result['status']=='RUNNING' and result['cancel_requested']
        from sqlalchemy import update
        from datetime import datetime,timedelta,timezone
        with repo.transaction(tenant) as conn:
            conn.execute(update(runs).where(runs.c.id==run_id).values(lease_expires_at=datetime.now(timezone.utc)-timedelta(seconds=1)))
        assert repo.read_runs(tenant)[run_id]['status']=='ERROR'
    finally: repo.engine.dispose()

def test_expired_lease_stops_before_worker_launch(database,monkeypatch):
    from sqlalchemy import update
    from datetime import datetime,timedelta,timezone
    repo=Repository(database['runtime_url']);tenant='expired-'+uuid.uuid4().hex
    monkeypatch.setenv('AUTOQA_POLICY_CONTROL_TOKEN','test-control')
    try:
        plan=stored(repo,tenant);run_id=insert_run(repo,tenant,plan)
        def delayed_setup():
            with repo.transaction(tenant) as conn:
                conn.execute(update(runs).where(runs.c.id==run_id).values(lease_expires_at=datetime.now(timezone.utc)-timedelta(seconds=1)))
            return {}
        def forbidden(*args,**kwargs): raise AssertionError('Expired lease launched a process')
        monkeypatch.setattr('autoqa.orchestration.service.browser_tools',delayed_setup)
        monkeypatch.setattr('autoqa.orchestration.processes.subprocess.Popen',forbidden)
        Service(repo,tenant).work({'id':run_id,'hash':plan.digest()})
        assert repo.worker_should_stop(tenant,run_id)
        assert repo.read_runs(tenant)[run_id]['status']=='ERROR'
    finally: repo.engine.dispose()
