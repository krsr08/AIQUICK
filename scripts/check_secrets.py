"""Minimal tracked-file secret patterns; not a replacement for enterprise scanning."""
from pathlib import Path
import re
import subprocess
import sys

patterns = [re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----'),
            re.compile(r'gh[pousr]_[A-Za-z0-9]{30,}'), re.compile(r'AKIA[A-Z0-9]{16}')]
paths = subprocess.check_output(['git', 'ls-files'], text=True).splitlines()
findings = []
for name in paths:
    path = Path(name)
    if path.suffix in ('.png', '.zip') or not path.is_file():
        continue
    text = path.read_text(encoding='utf-8', errors='replace')
    if any(pattern.search(text) for pattern in patterns):
        findings.append(name)
print('Secret pattern scan:', 'FAIL: ' + ', '.join(findings) if findings else f'PASS ({len(paths)} tracked files)')
sys.exit(bool(findings))
