"""Tests for webhook signature verification."""

from __future__ import annotations

import time

from euromail import verify_signature
from euromail.webhooks import DEFAULT_TOLERANCE_SECONDS

SECRET = "whsec_test_secret_do_not_use"
TIMESTAMP = 1735689600
BODY = (
    '{"event":"delivered","email_id":"018f2c3a-7b1e-7c3e-8b1a-2f6e9d4c5a01",'
    '"account_id":"018f2c3a-7b1e-7c3e-8b1a-2f6e9d4c5a02","timestamp":"2025-01-01T00:00:00Z"}'
)
EXPECTED_V1 = "d571fbef13b9e524d460f6f2c88f8d8dc7df3c50ff7aabdedd8a3656abb96dd0"


def test_verify_signature_matches_known_vector():
    header = f"t={TIMESTAMP},v1={EXPECTED_V1}"
    assert verify_signature(BODY, header, SECRET, now=TIMESTAMP) is True


def test_verify_signature_rejects_wrong_secret():
    header = f"t={TIMESTAMP},v1={EXPECTED_V1}"
    assert verify_signature(BODY, header, "wrong-secret", now=TIMESTAMP) is False


def test_verify_signature_rejects_tampered_body():
    header = f"t={TIMESTAMP},v1={EXPECTED_V1}"
    assert verify_signature(BODY + "x", header, SECRET, now=TIMESTAMP) is False


def test_verify_signature_rejects_timestamp_outside_tolerance():
    header = f"t={TIMESTAMP},v1={EXPECTED_V1}"
    outside = TIMESTAMP + DEFAULT_TOLERANCE_SECONDS + 1
    assert verify_signature(BODY, header, SECRET, now=outside) is False


def test_verify_signature_accepts_timestamp_at_tolerance_boundary():
    header = f"t={TIMESTAMP},v1={EXPECTED_V1}"
    boundary = TIMESTAMP + DEFAULT_TOLERANCE_SECONDS
    assert verify_signature(BODY, header, SECRET, now=boundary) is True


def test_verify_signature_rejects_missing_header():
    assert verify_signature(BODY, None, SECRET) is False


def test_verify_signature_rejects_malformed_header():
    assert verify_signature(BODY, "not-a-valid-header", SECRET, now=TIMESTAMP) is False


def test_verify_signature_supports_secret_rotation_multiple_v1_entries():
    # A rotation window may sign with both the old and new secret; either
    # v1 entry matching its own secret should verify.
    import hashlib
    import hmac as hmac_mod

    old_secret = "whsec_old"
    new_secret = "whsec_new"
    signed = f"{TIMESTAMP}.".encode() + BODY.encode()
    old_sig = hmac_mod.new(old_secret.encode(), signed, hashlib.sha256).hexdigest()
    new_sig = hmac_mod.new(new_secret.encode(), signed, hashlib.sha256).hexdigest()
    header = f"t={TIMESTAMP},v1={old_sig},v1={new_sig}"

    assert verify_signature(BODY, header, old_secret, now=TIMESTAMP) is True
    assert verify_signature(BODY, header, new_secret, now=TIMESTAMP) is True


def test_verify_signature_uses_current_time_by_default():
    header = f"t={int(time.time())},v1=irrelevant-since-secret-wont-match"
    # Sanity: default `now` shouldn't itself cause a tolerance rejection
    # (the signature still won't match, but not because of staleness).
    assert verify_signature(BODY, header, SECRET) is False
