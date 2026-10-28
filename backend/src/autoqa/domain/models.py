from __future__ import annotations
import hashlib
import json
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_serializer, model_validator

class Step(BaseModel):
    model_config = ConfigDict(frozen=True, extra='forbid')
    instruction: str
    kind: Literal['navigate', 'fill', 'click']
    target: str
    value: str = ''

class Assertion(BaseModel):
    model_config = ConfigDict(frozen=True, extra='forbid')
    id: Literal['final-1', 'final-2']
    phase: Literal['final'] = 'final'
    field: Literal['Customer Name', 'Email']
    value: str = Field(min_length=1, max_length=300)
    original: str = Field(min_length=1, max_length=330)
    comparator: Literal['literal_equals'] = 'literal_equals'
    required: Literal[True] = True

class Plan(BaseModel):
    model_config = ConfigDict(frozen=True, extra='forbid')
    schema_version: Literal['0.2', '0.3'] = '0.2'
    id: str
    title: str
    author: str
    tenant_id: str = Field(default='synthetic-demo', pattern=r'^[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}$')
    steps: tuple[Step, ...]
    expected: str
    field: Literal['Customer Name', 'Email']
    value: str
    assertions: tuple[Assertion, ...] = Field(default=(), max_length=2)
    environment: Literal['synthetic-demo'] = 'synthetic-demo'
    risk: Literal['R1'] = 'R1'

    @model_validator(mode='after')
    def validate_assertions(self):
        if self.schema_version == '0.2':
            if self.assertions:
                raise ValueError('Legacy plans cannot contain additional assertions')
        else:
            if any(len(a.value) > 200 for a in self.assertions):
                raise ValueError('New expectations must contain at most 200 value characters')
            if not self.assertions or len({a.field for a in self.assertions}) != len(self.assertions):
                raise ValueError('One or two distinct field expectations are required')
            if [a.id for a in self.assertions] != [f'final-{i + 1}' for i in range(len(self.assertions))]:
                raise ValueError('Assertion links must be ordered and unique')
            if self.expected != '\n'.join(a.original for a in self.assertions):
                raise ValueError('Original expectations must match linked assertions')
            if any(a.original != f'{a.field} equals {a.value}' for a in self.assertions):
                raise ValueError('Literal expectations must match original text')
            if (self.field, self.value) != (self.assertions[0].field, self.assertions[0].value):
                raise ValueError('Primary expectation differs from linked assertion')
        return self

    @model_serializer(mode='wrap')
    def serialize_snapshot(self, handler):
        snapshot = handler(self)
        if self.schema_version == '0.2':
            snapshot.pop('assertions', None)
        return snapshot

    def required_assertions(self) -> tuple[Assertion, ...]:
        return self.assertions or (Assertion(id='final-1', field=self.field, value=self.value, original=self.expected),)

    def digest(self) -> str:
        return hashlib.sha256(json.dumps(self.model_dump(), sort_keys=True, separators=(',', ':')).encode()).hexdigest()

class TestInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    title: str = Field(min_length=1, max_length=160)
    steps: list[str] = Field(min_length=1, max_length=12)
    expected: str = Field(min_length=1, max_length=461)
