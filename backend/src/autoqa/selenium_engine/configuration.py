"""Resolve browser tools once in the trusted control plane, before worker startup."""
from functools import lru_cache
from pathlib import Path
from selenium.webdriver.common.selenium_manager import SeleniumManager

@lru_cache(maxsize=1)
def browser_tools():
    result = SeleniumManager().binary_paths(['--browser', 'chrome', '--avoid-stats'])
    browser = Path(result['browser_path']).resolve()
    driver = Path(result['driver_path']).resolve()
    if not browser.is_file() or not driver.is_file():
        raise RuntimeError('Chrome or ChromeDriver setup is incomplete')
    return {'AUTOQA_CHROME_BINARY': str(browser), 'AUTOQA_CHROMEDRIVER_BINARY': str(driver)}
