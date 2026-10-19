import hashlib
import json
import uuid
import pytest
from autoqa.domain.models import Plan
from autoqa.natural_language.compiler import compile_test
from autoqa.assertions.evaluator import verdict
from autoqa.persistence.repository import Repository
from test_core import CASE

BOTH = 'Customer Name equals Example {run-id}\nEmail equals example@example.com'

def test_linked_expectations_are_literal_immutable_and_hash_bound():
    plan = compile_test(dict(CASE, expected=BOTH), 'author')
    assert plan.schema_version == '0.3'
    assert tuple(a.original for a in plan.assertions) == tuple(BOTH.splitlines())
    with pytest.raises(ValueError):
        plan.assertions[1].value = 'changed'
    changed = plan.model_dump()
    changed['assertions'][1]['value'] = 'changed'
    with pytest.raises(ValueError):
        Plan.model_validate(changed)
    assert compile_test(dict(CASE, expected=BOTH.replace('example@example.com','wrong@example.com')), 'author').digest() != plan.digest()

@pytest.mark.parametrize('expected', [BOTH+'\nEmail equals x', BOTH+'\n', '\n'+BOTH,
    'Email equals x\nEmail equals y', 'Email equals ', 'Email equals {secret}', 'Email equals x\r'])
def test_invalid_linked_expectations_are_rejected(expected):
    with pytest.raises(ValueError):
        compile_test(dict(CASE, expected=expected), 'author')

def test_missing_or_duplicate_link_never_passes():
    steps = [{'status':'EXECUTED'}]
    a = {'status':'PASS','assertion_id':'final-1'}
    required = ('final-1','final-2')
    assert verdict(steps,[a],required) == 'INCONCLUSIVE'
    assert verdict(steps,[a,a],required) == 'INCONCLUSIVE'
    assert verdict(steps,[a,{'status':'FAIL','assertion_id':'final-2'}],required) == 'FAIL'

def test_legacy_snapshot_survives_database_reload_with_original_hash(database):
    snapshot = compile_test(CASE,'author').model_dump()
    snapshot.pop('assertions')
    snapshot['schema_version'] = '0.2'
    snapshot['tenant_id'] = 'legacy-' + uuid.uuid4().hex
    original = hashlib.sha256(json.dumps(snapshot,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    plan = Plan.model_validate(snapshot)
    assert plan.model_dump() == snapshot
    assert plan.digest() == original
    repo = Repository(database['runtime_url'])
    try:
        with repo.transaction(plan.tenant_id) as conn:
            repo.save_plan(conn,plan)
        with repo.transaction(plan.tenant_id) as conn:
            restored = repo.load_plan(conn,plan.id)
        assert restored.digest() == original
        assert len(restored.required_assertions()) == 1
    finally:
        repo.engine.dispose()
