def evaluate(expected: str, actual: str, record_id: str) -> dict:
    return {'status': 'PASS' if expected == actual else 'FAIL', 'expected': expected,
            'actual': actual, 'comparator': 'literal_equals', 'verification_level': 'V2',
            'source': 'fresh-browser-record-by-id', 'record_id': record_id}

def verdict(steps: list[dict], assertions: list[dict], required_ids: tuple[str, ...] | None = None) -> str:
    statuses = {x['status'] for x in steps + assertions}
    for status in ('ERROR', 'BLOCKED', 'FAIL', 'INCONCLUSIVE', 'CANCELLED'):
        if status in statuses:
            return status
    if required_ids is not None and (len(assertions) != len(required_ids) or
            {a.get('assertion_id') for a in assertions} != set(required_ids)):
        return 'INCONCLUSIVE'
    if not assertions or 'NOT_RUN' in statuses or any(a['status'] != 'PASS' for a in assertions):
        return 'INCONCLUSIVE'
    return 'PASS' if all(s['status'] == 'EXECUTED' for s in steps) else 'ERROR'
