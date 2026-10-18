"""Run from repository root. Credentials are entered privately, never printed or stored."""
import getpass
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import time
from contextlib import nullcontext

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend' / 'src'))
sys.path.insert(0, str(ROOT))
from autoqa.api.auth import hash_password
from scripts.dev_database import dev_database

def launch_services(environment):
    processes = []
    try:
        for module in ('demo_apps.crm', 'deployment.egress_proxy', 'policy_service.server'):
            child_environment = {k: v for k, v in environment.items() if not k.startswith('AUTOQA_')}
            if module == 'policy_service.server':
                child_environment['AUTOQA_POLICY_CONTROL_TOKEN'] = environment['AUTOQA_POLICY_CONTROL_TOKEN']
            process = subprocess.Popen([sys.executable, '-m', module], cwd=ROOT, env=child_environment,
                                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            processes.append(process)
        time.sleep(1)
        if any(p.poll() is not None for p in processes):
            raise RuntimeError('A service could not start; ensure demo ports 8765–8767 are free')
        return processes
    except Exception:
        stop_services(processes)
        raise

def stop_services(processes):
    for process in processes:
        if process.poll() is None:
            process.terminate()
    for process in processes:
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=10)

def main():
    environment = dict(os.environ)
    environment['PYTHONPATH'] = str(ROOT / 'backend' / 'src') + os.pathsep + str(ROOT)
    environment['AUTOQA_POLICY_CONTROL_TOKEN'] = secrets.token_urlsafe(32)
    users = []
    for username, roles in [('author', ['Author', 'Runner']), ('reviewer', ['Approver', 'Runner', 'Auditor'])]:
        password = getpass.getpass(f'Choose a temporary {username} password (12+ characters): ')
        users.append(dict(username=username, password_hash=hash_password(password), roles=roles))
    environment['AUTOQA_USERS_JSON'] = json.dumps(users)
    database = nullcontext(environment['AUTOQA_DATABASE_URL']) if environment.get('AUTOQA_DATABASE_URL') else dev_database()
    with database as runtime_url:
        environment['AUTOQA_DATABASE_URL'] = runtime_url
        processes = launch_services(environment)
        try:
            print('Synthetic demo ready at http://127.0.0.1:8000. Plans and run history persist in PostgreSQL.')
            subprocess.run([sys.executable, '-m', 'autoqa.main'], cwd=ROOT, env=environment, check=True)
        finally:
            stop_services(processes)

if __name__ == '__main__':
    main()
