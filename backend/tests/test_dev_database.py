"""Actual private PostgreSQL stop/restart and Windows credential protection checks."""
import json
import shutil
import tempfile
from pathlib import Path

import pytest

from autoqa.natural_language.compiler import compile_test
from autoqa.persistence.repository import Repository
from scripts.dev_database import ROOT, dev_database, protect


@pytest.fixture
def owned_directory():
    work = (ROOT / 'work').resolve()
    directory = Path(tempfile.mkdtemp(prefix='autoqa-dev-test-', dir=work)).resolve()
    try:
        yield directory
    finally:
        assert directory.parent == work and directory.name.startswith('autoqa-dev-test-')
        assert not (directory / 'data' / 'postmaster.pid').exists(), 'Refusing cleanup of running cluster'
        shutil.rmtree(directory)


def test_persistent_plan_survives_server_restart_and_credentials_are_protected(owned_directory, monkeypatch):
    plan = compile_test({'title': 'Persistent restart proof', 'steps': [
        'Open the demo CRM', 'Enter Synthetic Customer in Customer Name',
        'Enter synthetic@example.invalid in Email', 'Click Save'],
        'expected': 'Customer Name equals Synthetic Customer'}, 'author')
    with dev_database(owned_directory) as first_url:
        repository = Repository(first_url)
        try:
            with repository.transaction(plan.tenant_id) as connection:
                repository.save_plan(connection, plan)
            with pytest.raises(RuntimeError, match='already active'):
                with dev_database(owned_directory):
                    pytest.fail('Concurrent launcher acquired cluster')
            blob = (owned_directory / 'credentials.dpapi').read_bytes()
            credentials = json.loads(protect(blob, decrypt=True))
            if any(value.encode() in blob for value in credentials.values()) or first_url.encode() in blob:
                pytest.fail('Protected credential blob contains plaintext credential material', pytrace=False)
            assert not (owned_directory / 'init-password').exists()
        finally:
            repository.engine.dispose()
    assert not (owned_directory / 'launcher.lock').exists()
    assert not (owned_directory / 'data' / 'postmaster.pid').exists()
    with dev_database(owned_directory) as second_url:
        assert (owned_directory / 'credentials.dpapi').read_bytes() == blob
        repository = Repository(second_url)
        try:
            with repository.transaction(plan.tenant_id) as connection:
                restored = repository.load_plan(connection, plan.id)
            assert restored.digest() == plan.digest()
            assert restored.title == 'Persistent restart proof'
        finally:
            repository.engine.dispose()

    # A process launcher can time out after the server becomes ready; own and stop it.
    import scripts.dev_database as module
    original_run = module._run
    def start_then_fail(arguments, **kwargs):
        result = original_run(arguments, **kwargs)
        if arguments[-1] == 'start':
            raise RuntimeError('Simulated launcher timeout after server startup')
        return result
    monkeypatch.setattr(module, '_run', start_then_fail)
    with pytest.raises(RuntimeError, match='Simulated launcher timeout'):
        with dev_database(owned_directory):
            pytest.fail('Simulated startup failure was ignored')
    assert not (owned_directory / 'data' / 'postmaster.pid').exists()
    assert not (owned_directory / 'launcher.lock').exists()


def test_unrelated_directory_is_not_adopted(owned_directory):
    sentinel = owned_directory / 'unrelated.txt'
    sentinel.write_text('Preserve this content', encoding='utf-8')
    with pytest.raises(RuntimeError, match='unrelated data'):
        with dev_database(owned_directory):
            pytest.fail('Unrelated directory adopted')
    assert sentinel.read_text(encoding='utf-8') == 'Preserve this content'
    assert not (owned_directory / 'launcher.lock').exists()
    assert not (owned_directory / 'credentials.dpapi').exists()


def test_directory_outside_owned_work_is_rejected(tmp_path):
    with pytest.raises(ValueError, match='owned direct child'):
        with dev_database(tmp_path):
            pytest.fail('Unowned directory accepted')
