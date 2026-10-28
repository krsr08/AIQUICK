import re
import uuid
from autoqa.domain.models import Assertion, Plan, Step, TestInput

FIELDS = ('Customer Name', 'Email')

class CompilationError(ValueError):
    """Safe, authored business-language feedback; never raw browser exceptions."""

def compile_test(data: dict, author: str) -> Plan:
    case = TestInput.model_validate(data)
    steps = []
    for sentence in case.steps:
        if len(sentence) > 350:
            raise CompilationError('A step is too long.')
        if sentence == 'Open the demo CRM':
            steps.append(Step(instruction=sentence, kind='navigate', target='demo'))
        elif sentence == 'Click Save':
            steps.append(Step(instruction=sentence, kind='click', target='Save'))
        elif match := re.fullmatch(r'Enter (.+) in (Customer Name|Email)', sentence):
            value, field = match.groups()
            if len(value) > 200 or any(ord(c) < 32 for c in value):
                raise CompilationError('Use a short, single-line synthetic value.')
            steps.append(Step(instruction=sentence, kind='fill', target=field, value=value))
        else:
            raise CompilationError('Unsupported step. Try Open the demo CRM, Enter a value in Customer Name or Email, or Click Save.')
    clauses = case.expected.split('\n')
    if not 1 <= len(clauses) <= 2:
        raise CompilationError('Use one or two expectations, one per line.')
    assertions = []
    for index, clause in enumerate(clauses):
        expected = re.fullmatch(r'(Customer Name|Email) equals (.+)', clause)
        if not expected or not expected[2].strip() or len(expected[2]) > 200 or any(ord(c) < 32 for c in expected[2]):
            raise CompilationError('Each line must say Customer Name equals a value, or Email equals a value.')
        if any(a.field == expected[1] for a in assertions):
            raise CompilationError('Use only one expectation for each field.')
        if re.search(r'\{(?!run-id\})', expected[2]):
            raise CompilationError('Only the built-in run-id variable is supported.')
        assertions.append(Assertion(id=f'final-{index + 1}', field=expected[1], value=expected[2], original=clause))
    # Only a complete, known sandbox workflow is certified in this spike.
    if [s.kind for s in steps] != ['navigate', 'fill', 'fill', 'click'] or {s.target for s in steps[1:3]} != set(FIELDS):
        raise CompilationError('This demo supports opening the CRM, filling both customer fields once, then Save.')
    if any(re.search(r'\{(?!run-id\})', s.value) for s in steps):
        raise CompilationError('Only the built-in run-id variable is supported.')
    return Plan(schema_version='0.3', assertions=tuple(assertions), id=uuid.uuid4().hex, title=case.title, author=author, steps=tuple(steps), expected=case.expected, field=assertions[0].field, value=assertions[0].value)
