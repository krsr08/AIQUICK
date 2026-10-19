"""Section 17 pre-existing record negative, exercised through real Chromium."""
import json
import secrets
import time
from pathlib import Path
import httpx
import pytest
from test_browser import services

@pytest.mark.browser
def test_preexisting_same_name_cannot_satisfy_new_record_assertions(services):
    name = 'Identity collision ' + secrets.token_hex(8)
    with httpx.Client(trust_env=False,follow_redirects=False) as client:
        prior = client.post('http://127.0.0.1:8765/customers',data={'name':name,'email':'old@example.com'})
    assert prior.status_code == 303
    old_id = prior.headers['location'].split('/')[-1]
    plan = services.compile({'title':'Created record identity', 'steps':['Open the demo CRM',
        'Enter '+name+' in Customer Name','Enter new@example.com in Email','Click Save'],
        'expected':'Customer Name equals '+name+'\nEmail equals old@example.com'}, 'identity-author')
    services.approve(plan['id'],'identity-reviewer',plan['hash'],True)
    run = services.start(plan['id'],'identity-author',secrets.token_hex(16))
    deadline=time.monotonic()+110
    while time.monotonic()<deadline:
        result=services.runs[run['id']]
        if result['status'] not in ('QUEUED','RUNNING'): break
        time.sleep(.2)
    Path('work/created-record-identity.json').write_text(json.dumps(result,indent=2))
    assert result['status']=='FAIL', result
    assert result['record_id'] != old_id
    assert [a['status'] for a in result['assertions']]==['PASS','FAIL']
    assert all(a['record_id']==result['record_id'] for a in result['assertions'])
    assert result['assertions'][1]['actual']=='new@example.com'
