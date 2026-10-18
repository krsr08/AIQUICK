"""Real dashboard interaction; credentials remain in memory and never in evidence."""
import json
import secrets
import tempfile
import threading
import time
from pathlib import Path

import pytest
import uvicorn
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from autoqa.api import create_app
from autoqa.api.auth import hash_password
from test_browser import services  # Shared real demo/proxy/PDP lifecycle fixture.


@pytest.mark.browser
def test_dashboard_describe_approve_run_and_mutated_expectation(services, monkeypatch):
    passwords = {name: secrets.token_urlsafe(24) for name in ('ui-author', 'ui-reviewer')}
    monkeypatch.setenv('AUTOQA_USERS_JSON', json.dumps([
        {'username': name, 'password_hash': hash_password(passwords[name]), 'roles': roles}
        for name, roles in [('ui-author', ['Author', 'Runner']), ('ui-reviewer', ['Approver', 'Runner'])]
    ]))
    server = uvicorn.Server(uvicorn.Config(create_app(services), host='127.0.0.1', port=8000,
                                         access_log=False, log_level='error'))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    deadline = time.monotonic() + 10
    while not server.started and thread.is_alive() and time.monotonic() < deadline:
        time.sleep(.05)
    assert server.started, 'UI server did not start'
    evidence = {'test': 'real Selenium dashboard journey', 'cases': []}
    output = Path('work')
    output.mkdir(exist_ok=True)
    try:
        with tempfile.TemporaryDirectory(prefix='autoqa-ui-profile-') as profile:
            options = webdriver.ChromeOptions()
            for arg in ('--headless=new', '--disable-extensions', '--disable-background-networking',
                        '--no-first-run', '--window-size=1440,1100', '--remote-debugging-pipe',
                        '--user-data-dir=' + profile):
                options.add_argument(arg)
            driver = webdriver.Chrome(options=options)
            try:
                driver.set_page_load_timeout(20)
                wait = WebDriverWait(driver, 25)
                evidence['browser_version'] = driver.capabilities['browserVersion']

                def button(text):
                    return wait.until(EC.element_to_be_clickable((By.XPATH, '//button[normalize-space(.)="' + text + '"]')))

                def login(name):
                    field = wait.until(EC.visibility_of_element_located((By.NAME, 'username')))
                    field.send_keys(name)
                    driver.find_element(By.NAME, 'password').send_keys(passwords[name])
                    button('Sign in').click()
                    wait.until(EC.visibility_of_element_located((By.XPATH, '//h1[text()="From intent to evidence."]')))

                def input_label(label):
                    return driver.find_element(By.XPATH, '//label[starts-with(normalize-space(.),"' + label + '")]/input')

                driver.get('http://127.0.0.1:8000/')
                for expected_status, expected in [('PASS', 'Customer Name equals ABC Technologies {run-id}'),
                                                  ('FAIL', 'Customer Name equals deliberately incorrect')]:
                    login('ui-author')
                    title = 'UI verification ' + expected_status
                    field = input_label('Test title')
                    field.send_keys(Keys.CONTROL, 'a', Keys.NULL, Keys.BACKSPACE)
                    field.send_keys(title)
                    assert field.get_attribute('value') == title
                    field = input_label('Expected result')
                    field.send_keys(Keys.CONTROL, 'a', Keys.NULL, Keys.BACKSPACE)
                    field.send_keys(expected)
                    assert field.get_attribute('value') == expected
                    button('Create plan for review').click()
                    try:
                        wait.until(EC.visibility_of_element_located((By.XPATH, '//h3[text()="' + title + '"]')))
                    except TimeoutException:
                        alerts = [e.text for e in driver.find_elements(By.CSS_SELECTOR, '[role="alert"]')]
                        headings = [e.text for e in driver.find_elements(By.CSS_SELECTOR, 'h3')]
                        raise AssertionError('Plan preview did not appear; UI feedback: ' + repr(alerts) + '; headings: ' + repr(headings)) from None
                    assert not driver.find_element(By.XPATH, '//button[text()="Run approved test"]').is_enabled()
                    assert not driver.find_element(By.XPATH, '//button[text()="Approve this plan"]').is_enabled()
                    button('Sign out').click()
                    login('ui-reviewer')
                    saved = wait.until(EC.element_to_be_clickable((By.XPATH, '//button[contains(@class,"plan-item")][strong[text()="' + title + '"]]')))
                    saved.click()
                    checkbox = driver.find_element(By.CSS_SELECTOR, 'input[type="checkbox"]')
                    checkbox.click()
                    button('Approve this plan').click()
                    button('Run approved test').click()
                    status_element = WebDriverWait(driver, 110).until(lambda d: next((e for e in d.find_elements(By.CSS_SELECTOR, '[data-testid="run-status"]') if e.text not in ('QUEUED', 'RUNNING')), False))
                    observed = status_element.text
                    matching_plan = next(p for p in services.list_plans() if p['title'] == title)
                    matching_run = next(r for r in services.runs.values() if r.get('plan_hash') == matching_plan['hash'])
                    evidence['cases'].append({'expected_verdict': expected_status, 'observed_verdict': observed,
                                              'plan_id': matching_plan['id'], 'run': matching_run})
                    (output / 'dashboard-result.json').write_text(json.dumps(evidence, indent=2), encoding='utf-8')
                    assert observed == expected_status, 'Dashboard verdict ' + observed + ' did not match ' + expected_status
                    assert matching_run['assertions'][0]['verification_level'] == 'V2'
                    # Capture only the authenticated synthetic result, never the login form or credentials.
                    driver.save_screenshot(str(output / ('dashboard-' + expected_status.lower() + '.png')))
                    if expected_status == 'PASS':
                        button('Sign out').click()
            finally:
                driver.quit()
    finally:
        server.should_exit = True
        thread.join(timeout=10)
