"""Tests for agent mailbox support on sync + async clients."""

from __future__ import annotations

import httpx
import pytest
import respx

from euromail import AgentMailbox, AsyncEuroMail, EuroMail, LeasedMessage, MailboxMessage


BASE_URL = "https://api.euromail.test"


MAILBOX_PAYLOAD = {
    "id": "mb_123",
    "account_id": "acc_1",
    "local_part": "agent",
    "domain": "agents.example.com",
    "address": "agent@agents.example.com",
    "display_name": "Support Agent",
    "created_at": "2026-04-13T12:00:00Z",
}


MESSAGE_PAYLOAD = {
    "id": "msg_1",
    "mailbox_id": "mb_123",
    "account_id": "acc_1",
    "message_id": "<abc@example.com>",
    "mail_from": "sender@example.com",
    "from_header": "Sender <sender@example.com>",
    "reply_to": None,
    "subject": "hello",
    "text_body": "hi",
    "html_body": None,
    "size_bytes": 42,
    "thread_id": None,
    "labels": [],
    "read_at": None,
    "created_at": "2026-04-13T12:01:00Z",
}


def _sync_client() -> EuroMail:
    return EuroMail(api_key="test", base_url=BASE_URL)


@pytest.fixture
def sync_client():
    client = _sync_client()
    yield client
    client.close()


@pytest.fixture
async def async_client():
    client = AsyncEuroMail(api_key="test", base_url=BASE_URL)
    yield client
    await client.close()


@respx.mock
def test_create_mailbox(sync_client):
    route = respx.post(f"{BASE_URL}/v1/agent-mailboxes").mock(
        return_value=httpx.Response(200, json={"data": MAILBOX_PAYLOAD})
    )
    mailbox = sync_client.create_mailbox(display_name="Support Agent")
    assert route.called
    import json as _json
    assert _json.loads(route.calls.last.request.content) == {
        "display_name": "Support Agent"
    }
    assert isinstance(mailbox, AgentMailbox)
    assert mailbox.id == "mb_123"
    assert mailbox.address == "agent@agents.example.com"


@respx.mock
def test_list_mailboxes(sync_client):
    respx.get(f"{BASE_URL}/v1/agent-mailboxes").mock(
        return_value=httpx.Response(200, json={"data": [MAILBOX_PAYLOAD]})
    )
    mailboxes = sync_client.list_mailboxes(limit=10)
    assert len(mailboxes) == 1
    assert mailboxes[0].id == "mb_123"


@respx.mock
def test_wait_for_next_message_200(sync_client):
    respx.get(f"{BASE_URL}/v1/agent-mailboxes/mb_123/messages/next").mock(
        return_value=httpx.Response(
            200,
            json={
                "data": MESSAGE_PAYLOAD,
                "lease_token": "tok_abc",
                "lease_expires_at": "2026-04-13T12:06:00Z",
            },
        )
    )
    leased = sync_client.wait_for_next_message("mb_123", timeout=30)
    assert isinstance(leased, LeasedMessage)
    assert leased.lease_token == "tok_abc"
    assert isinstance(leased.data, MailboxMessage)
    assert leased.data.subject == "hello"


@respx.mock
def test_wait_for_next_message_408_returns_none(sync_client):
    respx.get(f"{BASE_URL}/v1/agent-mailboxes/mb_123/messages/next").mock(
        return_value=httpx.Response(408)
    )
    result = sync_client.wait_for_next_message("mb_123", timeout=30)
    assert result is None


@respx.mock
def test_ack_message(sync_client):
    route = respx.post(
        f"{BASE_URL}/v1/agent-mailboxes/mb_123/messages/msg_1/ack"
    ).mock(return_value=httpx.Response(204))
    sync_client.ack_message("mb_123", "msg_1", "tok_abc")
    assert route.called
    assert b"tok_abc" in route.calls.last.request.content


@respx.mock
def test_nack_message(sync_client):
    route = respx.post(
        f"{BASE_URL}/v1/agent-mailboxes/mb_123/messages/msg_1/nack"
    ).mock(return_value=httpx.Response(204))
    sync_client.nack_message("mb_123", "msg_1", "tok_abc")
    assert route.called


@respx.mock
def test_delete_mailbox(sync_client):
    route = respx.delete(f"{BASE_URL}/v1/agent-mailboxes/mb_123").mock(
        return_value=httpx.Response(204)
    )
    sync_client.delete_mailbox("mb_123")
    assert route.called


# ---- Async parity ----


@respx.mock
async def test_async_create_mailbox(async_client):
    respx.post(f"{BASE_URL}/v1/agent-mailboxes").mock(
        return_value=httpx.Response(200, json={"data": MAILBOX_PAYLOAD})
    )
    mailbox = await async_client.create_mailbox(display_name="Support Agent")
    assert mailbox.id == "mb_123"


@respx.mock
async def test_async_wait_for_next_message_200(async_client):
    respx.get(f"{BASE_URL}/v1/agent-mailboxes/mb_123/messages/next").mock(
        return_value=httpx.Response(
            200,
            json={
                "data": MESSAGE_PAYLOAD,
                "lease_token": "tok_abc",
                "lease_expires_at": "2026-04-13T12:06:00Z",
            },
        )
    )
    leased = await async_client.wait_for_next_message("mb_123", timeout=30)
    assert leased is not None
    assert leased.lease_token == "tok_abc"


@respx.mock
async def test_async_wait_for_next_message_408(async_client):
    respx.get(f"{BASE_URL}/v1/agent-mailboxes/mb_123/messages/next").mock(
        return_value=httpx.Response(408)
    )
    result = await async_client.wait_for_next_message("mb_123", timeout=30)
    assert result is None


@respx.mock
async def test_async_ack_message(async_client):
    route = respx.post(
        f"{BASE_URL}/v1/agent-mailboxes/mb_123/messages/msg_1/ack"
    ).mock(return_value=httpx.Response(204))
    await async_client.ack_message("mb_123", "msg_1", "tok_abc")
    assert route.called
