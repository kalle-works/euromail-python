"""Tests for bulk suppression import/export."""

from __future__ import annotations

import json

import httpx
import respx

from euromail import AsyncEuroMail, EuroMail
from euromail.types import ImportSuppressionsResult

BASE_URL = "https://api.euromail.test"


def _client() -> EuroMail:
    return EuroMail(api_key="test", base_url=BASE_URL)


@respx.mock
def test_import_suppressions_sends_emails_and_reason():
    client = _client()
    route = respx.post(f"{BASE_URL}/v1/suppressions/import").mock(
        return_value=httpx.Response(
            200,
            json={
                "data": {
                    "inserted": 2,
                    "total_requested": 3,
                    "invalid_addresses": ["not-an-email"],
                }
            },
        )
    )
    result = client.import_suppressions(
        ["a@example.com", "b@example.com", "not-an-email"], reason="bulk-cleanup"
    )
    body = json.loads(route.calls.last.request.content)
    assert body == {
        "emails": ["a@example.com", "b@example.com", "not-an-email"],
        "reason": "bulk-cleanup",
    }
    assert result == ImportSuppressionsResult(
        inserted=2, total_requested=3, invalid_addresses=["not-an-email"]
    )
    client.close()


@respx.mock
def test_import_suppressions_omits_reason_when_not_given():
    client = _client()
    route = respx.post(f"{BASE_URL}/v1/suppressions/import").mock(
        return_value=httpx.Response(
            200,
            json={"data": {"inserted": 1, "total_requested": 1, "invalid_addresses": []}},
        )
    )
    client.import_suppressions(["a@example.com"])
    body = json.loads(route.calls.last.request.content)
    assert "reason" not in body
    client.close()


@respx.mock
def test_export_suppressions_returns_raw_csv_body():
    client = _client()
    csv_body = "email_address,reason,created_at\na@example.com,manual,2026-01-01T00:00:00Z\n"
    respx.get(f"{BASE_URL}/v1/suppressions/export").mock(
        return_value=httpx.Response(200, text=csv_body, headers={"content-type": "text/csv"})
    )
    result = client.export_suppressions()
    assert result == csv_body
    client.close()


@respx.mock
async def test_async_import_and_export_suppressions():
    client = AsyncEuroMail(api_key="test", base_url=BASE_URL)
    import_route = respx.post(f"{BASE_URL}/v1/suppressions/import").mock(
        return_value=httpx.Response(
            200,
            json={"data": {"inserted": 1, "total_requested": 1, "invalid_addresses": []}},
        )
    )
    csv_body = "email_address,reason,created_at\n"
    respx.get(f"{BASE_URL}/v1/suppressions/export").mock(
        return_value=httpx.Response(200, text=csv_body)
    )

    result = await client.import_suppressions(["a@example.com"], reason="import")
    assert result == ImportSuppressionsResult(
        inserted=1, total_requested=1, invalid_addresses=[]
    )
    body = json.loads(import_route.calls.last.request.content)
    assert body == {"emails": ["a@example.com"], "reason": "import"}

    exported = await client.export_suppressions()
    assert exported == csv_body

    await client.close()
