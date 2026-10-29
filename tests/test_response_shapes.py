"""The SDK reads what the API really sends.

Each fixture in `tests/fixtures/` is the full response body of one SDK call,
generated from the API's OpenAPI document by `tests/fixtures/generate.py`
(see its docstring to regenerate). For every one, the call must succeed and
every field the API sends must be readable on the returned model with the
value the API sent, or with the value in the fixture's `expect` where the SDK
reshapes it on purpose (a member named by `flatten` is read as fields of
the model itself). The same holds for what the envelope carries beside
`data`, except `pagination` (read into `PaginatedResponse`) and the keys the
fixture lists under `dropped`.
"""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path

import httpx
import pytest
import respx

from euromail import AsyncEuroMail, EuroMail, PaginatedResponse

BASE_URL = "https://api.euromail.test"
FIXTURES = sorted((Path(__file__).parent / "fixtures").glob("*.json"))


async def call(client_kind: str, spec: dict) -> object:
    method = spec["call"]
    if client_kind == "sync":
        with EuroMail(api_key="test", base_url=BASE_URL) as client:
            return getattr(client, method)(*spec["args"], **spec["kwargs"])
    async with AsyncEuroMail(api_key="test", base_url=BASE_URL) as client:
        return await getattr(client, method)(*spec["args"], **spec["kwargs"])


@pytest.mark.parametrize("client_kind", ["sync", "async"])
@pytest.mark.parametrize("fixture", FIXTURES, ids=lambda p: p.stem)
@respx.mock
async def test_call_exposes_every_field_the_api_sends(fixture, client_kind):
    spec = json.loads(fixture.read_text())
    method, path = spec["request"]
    body = spec["response"]
    respx.request(method, f"{BASE_URL}{path}").mock(
        return_value=httpx.Response(200, json=body)
    )

    result = await call(client_kind, spec)

    envelope = set(body) - {"data"} - set(spec["dropped"])
    if isinstance(result, PaginatedResponse):
        envelope.discard("pagination")
        result = result.data
    if envelope:
        assert not isinstance(result, list), f"a list cannot carry {sorted(envelope)}"
        readable = dataclasses.asdict(result)
        assert {k: readable.get(k) for k in envelope} == {k: body[k] for k in envelope}
    returned = result if isinstance(result, list) else [result]
    sent = body["data"] if isinstance(body["data"], list) else [body["data"]]
    if spec["flatten"]:
        sent = [{**obj.pop(spec["flatten"]), **obj} for obj in map(dict, sent)]
    assert len(returned) == len(sent)
    for model, obj in zip(returned, sent):
        readable = dataclasses.asdict(model)
        missing = sorted(set(obj) - set(readable))
        assert missing == [], f"{type(model).__name__} does not expose {missing}"
        expected = {**obj, **spec["expect"]}
        assert {k: readable[k] for k in expected} == expected
