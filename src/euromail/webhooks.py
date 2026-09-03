"""Webhook signature verification for the EuroMail SDK."""

from __future__ import annotations

import hashlib
import hmac
import time
from typing import Optional, Union

# Matches the server's tolerance guidance (see the worker's signing comment
# and the PHP SDK's `WebhookSignature::verify` default) and guards against a
# captured request being replayed long after the fact. It does not (and
# can't) prevent replay within the window.
DEFAULT_TOLERANCE_SECONDS = 300


def verify_signature(
    payload: Union[bytes, str],
    signature_header: Optional[str],
    secret: str,
    tolerance: int = DEFAULT_TOLERANCE_SECONDS,
    now: Optional[int] = None,
) -> bool:
    """Verify a webhook delivery's `X-Euromail-Signature` header.

    Every webhook payload is signed with HMAC-SHA256 over
    `"{timestamp}.{raw_body}"` using the webhook's signing secret, and sent
    in a Stripe-style header: `t=<unix_timestamp>,v1=<hex_hmac_sha256>`
    (see `crates/euromail-worker/src/processors/fire_webhook.rs`). Verify
    against the *raw* request body bytes, before any JSON parsing — a
    round-tripped/re-serialized payload will not reproduce the same bytes
    and the signature will not match.

    Returns `True` only if the header parses, at least one `v1` entry
    matches (supports secret rotation, where the header may briefly carry
    signatures for both the old and new secret), and the timestamp is
    within `tolerance` seconds of `now` (defaults to the current time).
    Malformed input returns `False` rather than raising, so a webhook
    receiver can always treat a `False` result as "reject the request"
    without a try/except.
    """
    if not signature_header:
        return False
    if isinstance(payload, str):
        payload = payload.encode("utf-8")

    timestamp: Optional[str] = None
    signatures: list[str] = []
    for part in signature_header.split(","):
        part = part.strip()
        if "=" not in part:
            continue
        key, _, value = part.partition("=")
        if key == "t":
            timestamp = value
        elif key == "v1":
            signatures.append(value)

    if timestamp is None or not signatures or not timestamp.isdigit():
        return False

    ts = int(timestamp)
    current = int(time.time()) if now is None else now
    if abs(current - ts) > tolerance:
        return False

    signed_payload = f"{ts}.".encode("utf-8") + payload
    expected = hmac.new(secret.encode("utf-8"), signed_payload, hashlib.sha256).hexdigest()

    return any(hmac.compare_digest(expected, sig) for sig in signatures)
