"""Disposable subprocess with a run-scoped PDP token and fresh browser sessions."""
import json
import os
import sys
import tempfile
from contextlib import contextmanager
from urllib.parse import urlsplit

import httpx
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

from autoqa.assertions.evaluator import evaluate, verdict
from autoqa.domain.models import Plan

TARGET = 'http://127.0.0.1:8765'

class Denied(Exception):
    pass

class PDPClient:
    def __init__(self, token):
        self.token = token

    def call(self, path, data):
        try:
            response = httpx.post('http://127.0.0.1:8766' + path, json=data,
                headers={'Authorization': 'Bearer ' + self.token}, timeout=3, trust_env=False)
            if response.status_code != 200:
                raise Denied()
        except httpx.HTTPError as exc:
            raise Denied() from exc

@contextmanager
def browser():
    with tempfile.TemporaryDirectory(prefix='autoqa-profile-') as profile:
        options = webdriver.ChromeOptions()
        options.binary_location = os.environ['AUTOQA_CHROME_BINARY']
        for arg in ('--headless=new', '--disable-extensions', '--disable-background-networking',
                    '--disable-sync', '--no-first-run', '--disable-quic',
                    '--proxy-server=http://127.0.0.1:8767', '--proxy-bypass-list=<-loopback>',
                    '--remote-debugging-pipe', '--window-size=1280,900'):
            options.add_argument(arg)
        options.add_argument('--user-data-dir=' + profile)
        options.add_experimental_option('prefs', {'download_restrictions': 3,
            'profile.default_content_setting_values.notifications': 2,
            'credentials_enable_service': False, 'profile.password_manager_enabled': False})
        driver = webdriver.Chrome(options=options, service=ChromeService(os.environ['AUTOQA_CHROMEDRIVER_BINARY']))
        try:
            driver.set_page_load_timeout(15)
            driver.set_script_timeout(3)
            yield driver
        finally:
            driver.quit()

def unique(driver, by, selector):
    elements = [e for e in driver.find_elements(by, selector) if e.is_displayed() and e.is_enabled()]
    if len(elements) != 1:
        raise Denied('Ambiguous or missing target')
    return elements[0]

def execute(payload):
    plan = Plan.model_validate(payload['plan'])
    if plan.digest() != payload['hash']:
        raise Denied('Snapshot mismatch')
    client = PDPClient(payload['token'])
    results = [{'instruction': s.instruction, 'status': 'NOT_RUN'} for s in plan.steps]
    assertions = []
    record = None
    browser_version = None
    error_code = None
    index = 0
    try:
        with browser() as driver:
            browser_version = driver.capabilities['browserVersion']
            for index, step in enumerate(plan.steps):
                element = None
                if step.kind == 'fill':
                    element = unique(driver, By.CSS_SELECTOR, 'input[aria-label="' + step.target + '"]')
                elif step.kind == 'click':
                    element = unique(driver, By.TAG_NAME, 'button')
                    if element.text != step.target:
                        raise Denied('Target identity mismatch')
                client.call('/action', {'hash': plan.digest(), 'phase': 'execute', 'index': index,
                                       'step': step.model_dump(), 'url': driver.current_url})
                if step.kind == 'navigate':
                    driver.get(TARGET + '/')
                elif step.kind == 'fill':
                    element.clear()
                    element.send_keys(step.value.replace('{run-id}', payload['id']))
                elif step.kind == 'click':
                    element.click()
                    WebDriverWait(driver, 10).until(lambda d: '/records/' in d.current_url)
                client.call('/post', {'url': driver.current_url, 'windows': len(driver.window_handles)})
                results[index]['status'] = 'EXECUTED'
            record = urlsplit(driver.current_url).path.removeprefix('/records/')
        # Separate profile/session, no action resolver and no AI for assertions.
        with browser() as verifier:
            client.call('/action', {'hash': plan.digest(), 'phase': 'verify', 'record': record,
                                   'url': verifier.current_url})
            verifier.get(TARGET + '/records/' + record)
            client.call('/post', {'url': verifier.current_url, 'windows': len(verifier.window_handles)})
            client.call('/action', {'hash': plan.digest(), 'phase': 'verify', 'record': record,
                                   'url': verifier.current_url})
            for assertion in plan.required_assertions():
                selector = '[data-testid="customer-name"]' if assertion.field == 'Customer Name' else '[data-testid="customer-email"]'
                observations = verifier.find_elements(By.CSS_SELECTOR, selector)
                if len(observations) != 1 or not observations[0].is_displayed():
                    observed = {'status': 'INCONCLUSIVE', 'reason': 'Unique observation unavailable'}
                else:
                    observed = evaluate(assertion.value.replace('{run-id}', payload['id']), observations[0].text, record)
                assertions.append(dict(observed, assertion_id=assertion.id, field=assertion.field, phase=assertion.phase))
            client.call('/post', {'url': verifier.current_url, 'windows': len(verifier.window_handles)})
    except Denied:
        results[index]['status'] = 'BLOCKED'
        error_code = 'PolicyOrTargetDenied'
    except Exception as exc:
        # WebDriver exceptions may contain page content; never export raw exceptions.
        results[index]['status'] = 'ERROR'
        error_code = type(exc).__name__
    return {'id': payload['id'], 'plan_hash': plan.digest(), 'status': verdict(results, assertions, tuple(a.id for a in plan.required_assertions())),
            'steps': results, 'assertions': assertions, 'record_id': record,
            'browser_version': browser_version, 'error_code': error_code, 'evidence_mode': 'synthetic-text-only',
            'cleanup': 'ephemeral-demo-records-discarded-at-service-stop'}

if __name__ == '__main__':
    try:
        result = execute(json.load(sys.stdin))
    except Exception:
        result = {'status': 'ERROR', 'reason': 'Invalid worker request'}
    print(json.dumps(result))
