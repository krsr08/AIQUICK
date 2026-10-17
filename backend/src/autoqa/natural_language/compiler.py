import re
import uuid
from autoqa.domain.models import Plan, Step, TestInput

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
    expected = re.fullmatch(r'(Customer Name|Email) equals (.+)', case.expected)
    if not expected:
        raise CompilationError('Add an explicit expectation: Customer Name equals a value, or Email equals a value.')
    # Only a complete, known sandbox workflow is certified in this spike.
    if [s.kind for s in steps] != ['navigate', 'fill', 'fill', 'click'] or {s.target for s in steps[1:3]} != set(FIELDS):
        raise CompilationError('This demo supports opening the CRM, filling both customer fields once, then Save.')
    if any(re.search(r'\{(?!run-id\})', s.value) for s in steps):
        raise CompilationError('Only the built-in run-id variable is supported.')
    return Plan(id=uuid.uuid4().hex, title=case.title, author=author, steps=tuple(steps), expected=case.expected, field=expected[1], value=expected[2])
