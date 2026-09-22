"""The SDK reads what the API really sends.

Each fixture in `tests/fixtures/` is the full response body of one SDK call,
generated from the API's OpenAPI document by `tests/fixtures/generate.py`
(see its docstring to regenerate). For every one, the call must succeed and
every field the API sends must be readable on the returned model with the
value the API sent.
"""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path

import httpx
import pytest
import respx

from euromail import EuroMail, PaginatedResponse

BASE_URL = "https://api.euromail.test"
FIXTURES = sorted((Path(__file__).parent / "fixtures").glob("*.json"))


@pytest.mark.parametrize("fixture", FIXTURES, ids=lambda p: p.stem)
@respx.mock
def test_call_exposes_every_field_the_api_sends(fixture):
    spec = json.loads(fixture.read_text())
    method, path = spec["request"]
    body = spec["response"]
    respx.request(method, f"{BASE_URL}{path}").mock(
        return_value=httpx.Response(200, json=body)
    )

    with EuroMail(api_key="test", base_url=BASE_URL) as client:
        result = getattr(client, spec["call"])(*spec["args"], **spec["kwargs"])

    if isinstance(result, PaginatedResponse):
        result = result.data
    returned = result if isinstance(result, list) else [result]
    sent = body["data"] if isinstance(body["data"], list) else [body["data"]]
    assert len(returned) == len(sent)
    for model, obj in zip(returned, sent):
        readable = dataclasses.asdict(model)
        missing = sorted(set(obj) - set(readable))
        assert missing == [], f"{type(model).__name__} does not expose {missing}"
        assert {k: readable[k] for k in obj} == obj
