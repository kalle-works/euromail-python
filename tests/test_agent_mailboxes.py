"""Tests for agent mailbox support on sync + async clients."""

from __future__ import annotations

import httpx
import pytest
import respx

import json as _json

from euromail import (
    AgentMailbox,
    AsyncEuroMail,
    EuroMail,
    LeasedMessage,
    MailboxAnalytics,
    MailboxContact,
    MailboxMessage,
    MailboxReplyResult,
)


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


# ---- Parity methods (sync) ----


REPLY_PAYLOAD = {
    "id": "eml_1",
    "status": "queued",
    "message_id": "<reply@agents.example.com>",
    "to": "sender@example.com",
    "subject": "Re: hello",
}


@respx.mock
def test_reply_to_message(sync_client):
    route = respx.post(
        f"{BASE_URL}/v1/agent-mailboxes/mb_123/messages/msg_1/reply"
    ).mock(return_value=httpx.Response(201, json={"data": REPLY_PAYLOAD}))
    result = sync_client.reply_to_message(
        "mb_123", "msg_1", text_body="thanks!"
    )
    assert route.called
    assert _json.loads(route.calls.last.request.content) == {"text_body": "thanks!"}
    assert isinstance(result, MailboxReplyResult)
    assert result.id == "eml_1"
    assert result.subject == "Re: hello"


@respx.mock
def test_reply_to_message_html_only(sync_client):
    route = respx.post(
        f"{BASE_URL}/v1/agent-mailboxes/mb_123/messages/msg_1/reply"
    ).mock(return_value=httpx.Response(201, json={"data": REPLY_PAYLOAD}))
    sync_client.reply_to_message("mb_123", "msg_1", html_body="<p>hi</p>")
    assert _json.loads(route.calls.last.request.content) == {"html_body": "<p>hi</p>"}


@respx.mock
def test_list_mailbox_threads(sync_client):
    route = respx.get(f"{BASE_URL}/v1/agent-mailboxes/mb_123/threads").mock(
        return_value=httpx.Response(200, json={"data": [MESSAGE_PAYLOAD]})
    )
    threads = sync_client.list_mailbox_threads("mb_123", limit=5, offset=10)
    assert threads[0].id == "msg_1"
    assert route.calls.last.request.url.params["limit"] == "5"
    assert route.calls.last.request.url.params["offset"] == "10"


@respx.mock
def test_get_mailbox_thread(sync_client):
    respx.get(f"{BASE_URL}/v1/agent-mailboxes/mb_123/threads/thr_1").mock(
        return_value=httpx.Response(200, json={"data": [MESSAGE_PAYLOAD]})
    )
    thread = sync_client.get_mailbox_thread("mb_123", "thr_1")
    assert len(thread) == 1
    assert isinstance(thread[0], MailboxMessage)


@respx.mock
def test_search_mailbox_messages(sync_client):
    route = respx.get(f"{BASE_URL}/v1/agent-mailboxes/mb_123/messages/search").mock(
        return_value=httpx.Response(200, json={"data": [MESSAGE_PAYLOAD]})
    )
    results = sync_client.search_mailbox_messages("mb_123", "invoice", limit=3)
    assert results[0].id == "msg_1"
    assert route.calls.last.request.url.params["q"] == "invoice"
    assert route.calls.last.request.url.params["limit"] == "3"


@respx.mock
def test_update_message_labels(sync_client):
    route = respx.put(
        f"{BASE_URL}/v1/agent-mailboxes/mb_123/messages/msg_1/labels"
    ).mock(
        return_value=httpx.Response(
            200, json={"data": {"labels": ["urgent", "billing"]}}
        )
    )
    labels = sync_client.update_message_labels("mb_123", "msg_1", ["urgent", "billing"])
    assert labels == ["urgent", "billing"]
    assert _json.loads(route.calls.last.request.content) == {
        "labels": ["urgent", "billing"]
    }


@respx.mock
def test_get_message_attachment_urls(sync_client):
    payload = [
        {
            "filename": "invoice.pdf",
            "content_type": "application/pdf",
            "size": 1024,
            "url": "https://storage.example/invoice.pdf?sig=abc",
            "expires_in_seconds": 3600,
        }
    ]
    respx.get(
        f"{BASE_URL}/v1/agent-mailboxes/mb_123/messages/msg_1/attachments"
    ).mock(return_value=httpx.Response(200, json={"data": payload}))
    urls = sync_client.get_message_attachment_urls("mb_123", "msg_1")
    assert urls[0]["url"].startswith("https://storage.example")
    assert urls[0]["expires_in_seconds"] == 3600


@respx.mock
def test_get_message_attachment_urls_fallback_metadata(sync_client):
    # When attachments were never persisted to storage, the server returns the
    # raw stored metadata array, which may lack url/expires_in_seconds.
    payload = [{"filename": "note.txt", "content_type": "text/plain"}]
    respx.get(
        f"{BASE_URL}/v1/agent-mailboxes/mb_123/messages/msg_1/attachments"
    ).mock(return_value=httpx.Response(200, json={"data": payload}))
    urls = sync_client.get_message_attachment_urls("mb_123", "msg_1")
    assert urls[0]["filename"] == "note.txt"
    assert "url" not in urls[0]


@respx.mock
def test_list_mailbox_contacts(sync_client):
    payload = [
        {
            "email": "sender@example.com",
            "display_name": "Sender",
            "message_count": 3,
            "last_seen": "2026-04-13T12:01:00Z",
        }
    ]
    respx.get(f"{BASE_URL}/v1/agent-mailboxes/mb_123/contacts").mock(
        return_value=httpx.Response(200, json={"data": payload})
    )
    contacts = sync_client.list_mailbox_contacts("mb_123")
    assert isinstance(contacts[0], MailboxContact)
    assert contacts[0].message_count == 3


@respx.mock
def test_get_mailbox_analytics(sync_client):
    payload = {
        "total_messages": 10,
        "unread_messages": 2,
        "total_threads": 4,
        "messages_today": 1,
        "messages_this_week": 5,
    }
    respx.get(f"{BASE_URL}/v1/agent-mailboxes/mb_123/analytics").mock(
        return_value=httpx.Response(200, json={"data": payload})
    )
    analytics = sync_client.get_mailbox_analytics("mb_123")
    assert isinstance(analytics, MailboxAnalytics)
    assert analytics.total_messages == 10
    assert analytics.unread_messages == 2


@respx.mock
def test_update_auto_responder(sync_client):
    rules = [{"match": "*", "action": {"reply_text": "Out of office"}}]
    route = respx.patch(
        f"{BASE_URL}/v1/agent-mailboxes/mb_123/auto-responder"
    ).mock(
        return_value=httpx.Response(
            200,
            json={
                "data": {
                    "auto_responder_enabled": True,
                    "auto_responder_rules": rules,
                }
            },
        )
    )
    result = sync_client.update_auto_responder("mb_123", enabled=True, rules=rules)
    assert result["auto_responder_enabled"] is True
    assert _json.loads(route.calls.last.request.content) == {
        "enabled": True,
        "rules": rules,
    }


# ---- Parity methods (async) ----


@respx.mock
async def test_async_reply_to_message(async_client):
    respx.post(
        f"{BASE_URL}/v1/agent-mailboxes/mb_123/messages/msg_1/reply"
    ).mock(return_value=httpx.Response(201, json={"data": REPLY_PAYLOAD}))
    result = await async_client.reply_to_message(
        "mb_123", "msg_1", text_body="thanks!"
    )
    assert result.id == "eml_1"


@respx.mock
async def test_async_list_mailbox_threads(async_client):
    respx.get(f"{BASE_URL}/v1/agent-mailboxes/mb_123/threads").mock(
        return_value=httpx.Response(200, json={"data": [MESSAGE_PAYLOAD]})
    )
    threads = await async_client.list_mailbox_threads("mb_123")
    assert threads[0].id == "msg_1"


@respx.mock
async def test_async_get_mailbox_thread(async_client):
    respx.get(f"{BASE_URL}/v1/agent-mailboxes/mb_123/threads/thr_1").mock(
        return_value=httpx.Response(200, json={"data": [MESSAGE_PAYLOAD]})
    )
    thread = await async_client.get_mailbox_thread("mb_123", "thr_1")
    assert len(thread) == 1


@respx.mock
async def test_async_search_mailbox_messages(async_client):
    route = respx.get(
        f"{BASE_URL}/v1/agent-mailboxes/mb_123/messages/search"
    ).mock(return_value=httpx.Response(200, json={"data": [MESSAGE_PAYLOAD]}))
    results = await async_client.search_mailbox_messages("mb_123", "invoice")
    assert results[0].id == "msg_1"
    assert route.calls.last.request.url.params["q"] == "invoice"


@respx.mock
async def test_async_update_message_labels(async_client):
    respx.put(
        f"{BASE_URL}/v1/agent-mailboxes/mb_123/messages/msg_1/labels"
    ).mock(return_value=httpx.Response(200, json={"data": {"labels": ["a"]}}))
    labels = await async_client.update_message_labels("mb_123", "msg_1", ["a"])
    assert labels == ["a"]


@respx.mock
async def test_async_get_message_attachment_urls_fallback(async_client):
    payload = [{"filename": "note.txt", "content_type": "text/plain"}]
    respx.get(
        f"{BASE_URL}/v1/agent-mailboxes/mb_123/messages/msg_1/attachments"
    ).mock(return_value=httpx.Response(200, json={"data": payload}))
    urls = await async_client.get_message_attachment_urls("mb_123", "msg_1")
    assert urls[0]["filename"] == "note.txt"
    assert "url" not in urls[0]


@respx.mock
async def test_async_list_mailbox_contacts(async_client):
    payload = [
        {
            "email": "sender@example.com",
            "display_name": None,
            "message_count": 1,
            "last_seen": "2026-04-13T12:01:00Z",
        }
    ]
    respx.get(f"{BASE_URL}/v1/agent-mailboxes/mb_123/contacts").mock(
        return_value=httpx.Response(200, json={"data": payload})
    )
    contacts = await async_client.list_mailbox_contacts("mb_123")
    assert contacts[0].display_name is None


@respx.mock
async def test_async_get_mailbox_analytics(async_client):
    payload = {
        "total_messages": 0,
        "unread_messages": 0,
        "total_threads": 0,
        "messages_today": 0,
        "messages_this_week": 0,
    }
    respx.get(f"{BASE_URL}/v1/agent-mailboxes/mb_123/analytics").mock(
        return_value=httpx.Response(200, json={"data": payload})
    )
    analytics = await async_client.get_mailbox_analytics("mb_123")
    assert analytics.total_messages == 0


@respx.mock
async def test_async_update_auto_responder(async_client):
    route = respx.patch(
        f"{BASE_URL}/v1/agent-mailboxes/mb_123/auto-responder"
    ).mock(
        return_value=httpx.Response(
            200,
            json={
                "data": {
                    "auto_responder_enabled": False,
                    "auto_responder_rules": None,
                }
            },
        )
    )
    result = await async_client.update_auto_responder("mb_123", enabled=False)
    assert result["auto_responder_enabled"] is False
    assert _json.loads(route.calls.last.request.content) == {"enabled": False}
