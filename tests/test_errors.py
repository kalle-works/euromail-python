"""Tests for error mapping: status/type -> exception class, and the
Retry-After header fix (the API has never sent a `retry_after` body field —
see crates/euromail-api/src/errors.rs — so the client must read the HTTP
header instead)."""

from __future__ import annotations

import httpx
import pytest
import respx

from euromail import (
    AuthenticationError,
    ConflictError,
    EuroMail,
    ForbiddenError,
    NotFoundError,
    RateLimitError,
    ServerError,
    ValidationError,
)

BASE_URL = "https://api.euromail.test"


def _client() -> EuroMail:
    return EuroMail(api_key="test", base_url=BASE_URL)


@respx.mock
def test_429_reads_retry_after_from_header_not_body():
    client = _client()
    respx.get(f"{BASE_URL}/v1/account").mock(
        return_value=httpx.Response(
            429,
            headers={"retry-after": "42"},
            json={"error": {"type": "rate_limited", "code": "RATE_LIMIT_EXCEEDED", "message": "slow down"}},
        )
    )
    with pytest.raises(RateLimitError) as exc_info:
        client.get_account()
    assert exc_info.value.retry_after == 42
    client.close()


@respx.mock
def test_429_without_retry_after_header_leaves_it_none():
    client = _client()
    respx.get(f"{BASE_URL}/v1/account").mock(
        return_value=httpx.Response(
            429,
            json={"error": {"type": "rate_limited", "code": "RATE_LIMIT_EXCEEDED", "message": "slow down"}},
        )
    )
    with pytest.raises(RateLimitError) as exc_info:
        client.get_account()
    assert exc_info.value.retry_after is None
    client.close()


@respx.mock
def test_a_retry_after_body_field_is_ignored():
    # Regression guard: the API has never sent this field. If a future
    # response body happened to include one, the client must still prefer
    # the header — trusting the body field here would silently reintroduce
    # the original bug for any caller who *does* get a body field for some
    # unrelated reason (e.g. a proxy echoing it back).
    client = _client()
    respx.get(f"{BASE_URL}/v1/account").mock(
        return_value=httpx.Response(
            429,
            headers={"retry-after": "7"},
            json={
                "error": {"type": "rate_limited", "code": "RATE_LIMIT_EXCEEDED", "message": "slow down"},
                "retry_after": 9999,
            },
        )
    )
    with pytest.raises(RateLimitError) as exc_info:
        client.get_account()
    assert exc_info.value.retry_after == 7
    client.close()


@pytest.mark.parametrize(
    ("status", "exc_class"),
    [
        (401, AuthenticationError),
        (403, ForbiddenError),
        (404, NotFoundError),
        (409, ConflictError),
        (422, ValidationError),
        (500, ServerError),
    ],
)
@respx.mock
def test_status_code_maps_to_expected_exception_class(status, exc_class):
    client = _client()
    respx.get(f"{BASE_URL}/v1/account").mock(
        return_value=httpx.Response(
            status,
            json={"error": {"type": "x", "code": "X", "message": "boom"}},
        )
    )
    with pytest.raises(exc_class):
        client.get_account()
    client.close()
