"""Tests for send_email/send_batch/send_broadcast on sync + async clients."""

from __future__ import annotations

import json

import httpx
import respx

from euromail import Attachment, AsyncEuroMail, EuroMail

BASE_URL = "https://api.euromail.test"

EMAIL_RESPONSE = {
    "id": "email_001",
    "message_id": "<msg@euromail.dev>",
    "status": "queued",
    "to": "user@example.com",
    "sandbox": False,
    "scheduled_at": None,
    "created_at": "2026-07-07T00:00:00Z",
}


def _sync_client() -> EuroMail:
    return EuroMail(api_key="test", base_url=BASE_URL)


@respx.mock
def test_send_email_includes_new_fields():
    client = _sync_client()
    route = respx.post(f"{BASE_URL}/v1/emails").mock(
        return_value=httpx.Response(200, json={"data": EMAIL_RESPONSE})
    )
    client.send_email(
        from_address="news@example.com",
        to="user@example.com",
        subject="Weekly update",
        text_body="News",
        transactional=False,
        stream="marketing",
        send_at="2026-08-01T00:00:00Z",
        tracking=True,
        attachments=[
            Attachment(filename="test.pdf", content="base64data", content_type="application/pdf")
        ],
    )
    body = json.loads(route.calls.last.request.content)
    assert body["transactional"] is False
    assert body["stream"] == "marketing"
    assert body["send_at"] == "2026-08-01T00:00:00Z"
    assert body["tracking"] is True
    assert body["attachments"] == [
        {"filename": "test.pdf", "content": "base64data", "content_type": "application/pdf"}
    ]
    client.close()


@respx.mock
def test_send_email_omits_unset_fields():
    client = _sync_client()
    route = respx.post(f"{BASE_URL}/v1/emails").mock(
        return_value=httpx.Response(200, json={"data": EMAIL_RESPONSE})
    )
    client.send_email(from_address="a@b.com", to="c@d.com", subject="Hi", text_body="Hello")
    body = json.loads(route.calls.last.request.content)
    for field in ("transactional", "stream", "send_at", "tracking", "attachments"):
        assert field not in body
    client.close()


@respx.mock
def test_send_broadcast_includes_tracking_and_transactional():
    client = _sync_client()
    route = respx.post(f"{BASE_URL}/v1/emails/broadcast").mock(
        return_value=httpx.Response(
            200,
            json={"data": {"operation_id": "op_1", "total_recipients": 3, "message": "queued"}},
        )
    )
    client.send_broadcast(
        contact_list_id="cl_001",
        from_address="sender@example.com",
        subject="Migration notice",
        text_body="We moved!",
        transactional=True,
        tracking=False,
    )
    body = json.loads(route.calls.last.request.content)
    assert body["transactional"] is True
    assert body["tracking"] is False
    client.close()


@respx.mock
async def test_async_send_email_includes_new_fields():
    client = AsyncEuroMail(api_key="test", base_url=BASE_URL)
    route = respx.post(f"{BASE_URL}/v1/emails").mock(
        return_value=httpx.Response(200, json={"data": EMAIL_RESPONSE})
    )
    await client.send_email(
        from_address="news@example.com",
        to="user@example.com",
        subject="Weekly update",
        text_body="News",
        transactional=False,
        stream="marketing",
    )
    body = json.loads(route.calls.last.request.content)
    assert body["transactional"] is False
    assert body["stream"] == "marketing"
    await client.close()
