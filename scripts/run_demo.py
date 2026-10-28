"""Run from repository root. Credentials are entered privately, never printed or stored."""
import getpass
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import sys
import time
import threading
import webbrowser
from contextlib import ExitStack, nullcontext

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend' / 'src'))
sys.path.insert(0, str(ROOT))
from autoqa.api.auth import hash_password
from scripts.dev_database import dev_database

def open_when_ready():
    """Open only the fixed local UI after the backend is serving its login page."""
    import httpx
    for _ in range(60):
        try:
            with httpx.Client(trust_env=False, timeout=1) as client:
                if client.get('http://127.0.0.1:8000/').status_code == 200:
                    webbrowser.open('http://127.0.0.1:8000/')
                    return
        except httpx.HTTPError:
            pass
        time.sleep(1)

def launch_services(environment):
    processes = []
    ports = (8765, 8767, 8766)
    try:
        # Refuse an existing listener before spawning anything. On Windows an
        # exclusive bind also rejects listeners that permit address sharing.
        with ExitStack() as reservations:
            for port in ports:
                probe = reservations.enter_context(socket.socket())
                if os.name == 'nt':
                    probe.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
                try:
                    probe.bind(('127.0.0.1', port))
                except OSError:
                    raise RuntimeError('A demo port is occupied; ports 8765–8767 must be free') from None
        for module in ('demo_apps.crm', 'deployment.egress_proxy', 'policy_service.server'):
            child_environment = {k: v for k, v in environment.items() if not k.startswith('AUTOQA_')}
            if module == 'policy_service.server':
                child_environment['AUTOQA_POLICY_CONTROL_TOKEN'] = environment['AUTOQA_POLICY_CONTROL_TOKEN']
            process = subprocess.Popen([sys.executable, '-m', module], cwd=ROOT, env=child_environment,
                                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            processes.append(process)
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            if any(p.poll() is not None for p in processes):
                raise RuntimeError('A demo service exited before becoming ready')
            ready = True
            for port in ports:
                try:
                    with socket.create_connection(('127.0.0.1', port), timeout=.2):
                        pass
                except OSError:
                    ready = False
            if ready:
                # Recheck child liveness after all listener checks so a failed
                # child cannot be reported as ready just because a port opens.
                if any(p.poll() is not None for p in processes):
                    raise RuntimeError('A demo service exited during startup')
                return processes
            time.sleep(.1)
        raise RuntimeError('Demo services did not become ready within 30 seconds')
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
            if '--open-browser' in sys.argv:
                threading.Thread(target=open_when_ready, daemon=True).start()
            subprocess.run([sys.executable, '-m', 'autoqa.main'], cwd=ROOT, env=environment, check=True)
        finally:
            stop_services(processes)

if __name__ == '__main__':
    main()
