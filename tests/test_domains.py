"""Tests for changing a domain's settings."""

from __future__ import annotations

import json

import httpx
import respx

from euromail import AsyncEuroMail, EuroMail

BASE_URL = "https://api.euromail.test"
DOMAIN_ID = "c8e8c5a3-8050-506c-a5fb-de56aceb0032"


def _domain_body(require_tls: bool) -> dict:
    return {
        "data": {
            "id": DOMAIN_ID,
            "account_id": "fc406502-93f9-5e5c-a566-f83d4aa924f2",
            "domain": "mail.example.com",
            "dkim_selector": "em1",
            "dkim_public_key": None,
            "spf_verified": True,
            "dkim_verified": True,
            "dmarc_verified": True,
            "return_path_verified": True,
            "mx_verified": False,
            "inbound_enabled": False,
            "dns_records": {},
            "created_at": "2026-09-22T10:00:00Z",
            "updated_at": "2026-09-22T10:00:00Z",
            "require_tls": require_tls,
        }
    }


@respx.mock
def test_update_domain_patches_only_the_given_settings():
    route = respx.patch(f"{BASE_URL}/v1/domains/{DOMAIN_ID}").mock(
        return_value=httpx.Response(200, json=_domain_body(True))
    )
    with EuroMail(api_key="test", base_url=BASE_URL) as client:
        domain = client.update_domain(DOMAIN_ID, require_tls=True)

    assert json.loads(route.calls.last.request.content) == {"require_tls": True}
    assert domain.require_tls is True


@respx.mock
async def test_async_update_domain_patches_only_the_given_settings():
    route = respx.patch(f"{BASE_URL}/v1/domains/{DOMAIN_ID}").mock(
        return_value=httpx.Response(200, json=_domain_body(False))
    )
    async with AsyncEuroMail(api_key="test", base_url=BASE_URL) as client:
        domain = await client.update_domain(DOMAIN_ID, require_tls=False)

    assert json.loads(route.calls.last.request.content) == {"require_tls": False}
    assert domain.require_tls is False
