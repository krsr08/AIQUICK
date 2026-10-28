"""Resolve browser tools once in the trusted control plane, before worker startup."""
from functools import lru_cache
import os
from pathlib import Path
from selenium.webdriver.common.selenium_manager import SeleniumManager

def browser_tools():
    # Only the trusted control plane chooses the engine; never take this from a plan.
    selected = os.environ.get('AUTOQA_BROWSER', 'chrome')
    if selected not in ('chrome', 'edge'):
        raise ValueError('AUTOQA_BROWSER must be chrome or edge')
    browser, driver = _resolve_tools(selected)
    environment = {'AUTOQA_BROWSER': selected, 'AUTOQA_BROWSER_BINARY': browser,
                   'AUTOQA_DRIVER_BINARY': driver}
    if selected == 'chrome':
        # Existing local dashboard clients still consume these names.
        environment.update(AUTOQA_CHROME_BINARY=browser, AUTOQA_CHROMEDRIVER_BINARY=driver)
    return environment


@lru_cache(maxsize=2)
def _resolve_tools(selected):
    result = SeleniumManager().binary_paths(['--browser', selected, '--avoid-stats'])
    browser = Path(result['browser_path']).resolve()
    driver = Path(result['driver_path']).resolve()
    if not browser.is_file() or not driver.is_file():
        raise RuntimeError('Selected browser or driver setup is incomplete')
    return str(browser), str(driver)
