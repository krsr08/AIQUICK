from __future__ import annotations
import hashlib
import json
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

class Step(BaseModel):
    model_config = ConfigDict(frozen=True, extra='forbid')
    instruction: str
    kind: Literal['navigate', 'fill', 'click']
    target: str
    value: str = ''

class Plan(BaseModel):
    model_config = ConfigDict(frozen=True, extra='forbid')
    schema_version: Literal['0.1'] = '0.1'
    id: str
    title: str
    author: str
    steps: tuple[Step, ...]
    expected: str
    field: Literal['Customer Name', 'Email']
    value: str
    environment: Literal['synthetic-demo'] = 'synthetic-demo'
    risk: Literal['R1'] = 'R1'

    def digest(self) -> str:
        return hashlib.sha256(json.dumps(self.model_dump(), sort_keys=True, separators=(',', ':')).encode()).hexdigest()

class TestInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    title: str = Field(min_length=1, max_length=160)
    steps: list[str] = Field(min_length=1, max_length=12)
    expected: str = Field(min_length=1, max_length=300)
