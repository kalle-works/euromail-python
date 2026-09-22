"""Regenerate the response fixtures in this directory from the API's OpenAPI document.

Each fixture is the full body one SDK call receives: the envelope the API
handler wraps around the payload, with every property of the response
schema filled in (nullable ones with a non-null value, so the SDK's types
see real data). `tests/test_response_shapes.py` replays them.

Usage, from a checkout of the API repo (kalle-works/euromail.dev):

    cargo run --quiet --example dump_openapi -p euromail-api > /tmp/openapi.json

then from this repo:

    python tests/fixtures/generate.py /tmp/openapi.json

Schemas come from the document's `components.schemas`. A few responses are
not described there yet; their schemas live in SUPPLEMENT below, transcribed
from the Rust struct named in each entry's `x-source`. When the API starts
documenting one of them, delete its SUPPLEMENT entry — the script refuses to
run while both exist, so the spec always wins.
"""

from __future__ import annotations

import json
import sys
import uuid
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent

UUID_NS = uuid.UUID("6f1b8c5e-3d0a-4b8e-9c47-2a51f0e7d9b3")
TIMESTAMP = "2026-09-22T10:00:00Z"
PAGINATION = {"page": 1, "per_page": 25, "total": 1, "total_pages": 1}


def _nullable(t: str) -> dict[str, Any]:
    return {"type": [t, "null"]}


def _uuid(nullable: bool = False) -> dict[str, Any]:
    return {"type": ["string", "null"] if nullable else "string", "format": "uuid"}


def _ts(nullable: bool = False) -> dict[str, Any]:
    return {"type": ["string", "null"] if nullable else "string", "format": "date-time"}


_STR = {"type": "string"}
_INT = {"type": "integer"}
_BOOL = {"type": "boolean"}
_STRS = {"type": "array", "items": {"type": "string"}}

SUPPLEMENT: dict[str, dict[str, Any]] = {
    "AnalyticsSummary": {
        "x-source": "crates/euromail-common/src/db/models.rs AnalyticsSummary",
        "properties": {
            "total_sent": _INT,
            "total_delivered": _INT,
            "total_bounced": _INT,
            "total_failed": _INT,
            "total_opens": _INT,
            "total_unique_opens": _INT,
            "total_clicks": _INT,
            "total_unique_clicks": _INT,
            "total_unsubscribes": _INT,
            "total_proxy_opens": _INT,
            "delivery_rate_pct": {"type": "number"},
            "bounce_rate_pct": {"type": "number"},
            "open_rate_pct": {"type": "number"},
            "click_rate_pct": {"type": "number"},
        },
    },
    "InboundRoute": {
        "x-source": "crates/euromail-common/src/db/models.rs InboundRoute",
        "properties": {
            "id": _uuid(),
            "account_id": _uuid(),
            "domain_id": _uuid(),
            "pattern": _STR,
            "match_type": _STR,
            "priority": _INT,
            "webhook_url": _nullable("string"),
            "is_active": _BOOL,
            "created_at": _ts(),
            "updated_at": _ts(),
            "webhook_id": _uuid(nullable=True),
        },
    },
    "Newsletter": {
        "x-source": "crates/euromail-common/src/db/models.rs Newsletter",
        "properties": {
            "id": _uuid(),
            "account_id": _uuid(),
            "list_id": _uuid(nullable=True),
            "subject": _STR,
            "from_address": _STR,
            "html_body": _nullable("string"),
            "text_body": _nullable("string"),
            "template_id": _uuid(nullable=True),
            "template_data": {},
            "reply_to": _nullable("string"),
            "tags": _STRS,
            "status": _STR,
            "operation_id": _uuid(nullable=True),
            "scheduled_at": _ts(nullable=True),
            "sent_at": _ts(nullable=True),
            "total_recipients": _nullable("integer"),
            "created_at": _ts(),
            "updated_at": _ts(),
        },
    },
    "ApiKeyListItem": {
        "x-source": "crates/euromail-api/src/routes/api_keys.rs list_api_keys (json! body)",
        "properties": {
            "id": _uuid(),
            "name": _STR,
            "key_prefix": _STR,
            "scopes": _STRS,
            "is_active": _BOOL,
            "last_used_at": _ts(nullable=True),
            "created_at": _ts(),
        },
    },
    "MailboxMessage": {
        "x-source": "crates/euromail-common/src/db/models.rs MailboxMessage",
        "properties": {
            "id": _uuid(),
            "mailbox_id": _uuid(),
            "account_id": _uuid(),
            "message_id": _nullable("string"),
            "mail_from": _STR,
            "from_header": _nullable("string"),
            "reply_to": _nullable("string"),
            "subject": _nullable("string"),
            "text_body": _nullable("string"),
            "html_body": _nullable("string"),
            "raw_headers": {},
            "size_bytes": _INT,
            "in_reply_to": _nullable("string"),
            "references_header": _nullable("string"),
            "thread_id": _uuid(nullable=True),
            "attachments_stored": _BOOL,
            "attachments_metadata": {},
            "labels": _STRS,
            "read_at": _ts(nullable=True),
            "leased_until": _ts(nullable=True),
            "lease_token": _uuid(nullable=True),
            "classification": _nullable("string"),
            "classification_confidence": _nullable("number"),
            "classified_at": _ts(nullable=True),
            "direction": _STR,
            "to_addresses": _STRS,
            "email_id": _uuid(nullable=True),
            "created_at": _ts(),
        },
    },
    "MailboxAnalytics": {
        "x-source": "crates/euromail-common/src/db/queries/agent_mailboxes.rs MailboxAnalytics",
        "properties": {
            "total_messages": _INT,
            "unread_messages": _INT,
            "total_threads": _INT,
            "messages_today": _INT,
            "messages_this_week": _INT,
            "sent_messages": _INT,
        },
    },
}

# Values for properties whose schema is untyped (serde_json::Value), where a
# placeholder object would not look like what the API stores.
DNS_RECORDS = {
    "dkim": {"type": "TXT", "host": "em1._domainkey.em.example.com", "value": "v=DKIM1; k=rsa; p=MIIB"},
    "spf": {"type": "TXT", "host": "em.example.com", "value": "v=spf1 include:spf.euromail.dev ~all"},
    "return_path": {"type": "MX", "host": "em.example.com", "value": "bounce.euromail.dev", "priority": 10},
    "dmarc": {"type": "TXT", "host": "_dmarc.example.com", "value": "v=DMARC1; p=none"},
    # Written by the API's DNS provider detection
    # (crates/euromail-common/src/dns_verification.rs).
    "detected_provider": "cloudflare",
}
UNTYPED_EXAMPLES: dict[tuple[str, str], Any] = {("Domain", "dns_records"): DNS_RECORDS}

# Model values that differ from the wire on purpose, per schema: the SDK
# lifts `detected_provider` out of `dns_records`, and a record without a
# priority reads as `priority=None`.
EXPECT: dict[str, dict[str, Any]] = {
    "Domain": {
        "dns_records": {
            k: {"priority": None, **v}
            for k, v in DNS_RECORDS.items()
            if k != "detected_provider"
        },
        "detected_provider": "cloudflare",
    },
}

ID = str(uuid.uuid5(UUID_NS, "path-id"))

# name -> (SDK method, positional args, keyword args, HTTP method, path,
# envelope, schema).
# The envelope is what the API handler wraps around the schema's object:
# "object" = {"data": obj}, "list" = {"data": [obj]}, "paginated" adds a
# "pagination" block, "analytics" adds the overview's "period" block.
ENDPOINTS: dict[str, tuple[str, list[str], dict[str, str], str, str, str, str]] = {
    "get_webhook": (
        "get_webhook", [ID], {}, "GET", f"/v1/webhooks/{ID}", "object", "Webhook",
    ),
    "list_webhooks": (
        "list_webhooks", [], {}, "GET", "/v1/webhooks", "paginated", "Webhook",
    ),
    "create_contact_list": (
        "create_contact_list", [], {"name": "Customers"}, "POST", "/v1/contact-lists",
        "object", "ContactList",
    ),
    "get_analytics_overview": (
        "get_analytics_overview", [], {}, "GET", "/v1/analytics/overview",
        "analytics", "AnalyticsSummary",
    ),
    "get_inbound_route": (
        "get_inbound_route", [ID], {}, "GET", f"/v1/inbound-routes/{ID}",
        "object", "InboundRoute",
    ),
    "get_inbound_email": (
        "get_inbound_email", [ID], {}, "GET", f"/v1/inbound/{ID}", "object", "InboundEmail",
    ),
    "get_newsletter": (
        "get_newsletter", [ID], {}, "GET", f"/v1/newsletters/{ID}", "object", "Newsletter",
    ),
    "list_api_keys": (
        "list_api_keys", [], {}, "GET", "/v1/api-keys", "list", "ApiKeyListItem",
    ),
    "list_messages": (
        "list_messages", [ID], {}, "GET", f"/v1/agent-mailboxes/{ID}/messages",
        "list", "MailboxMessage",
    ),
    "get_email_links": (
        "get_email_links", [ID], {}, "GET", f"/v1/emails/{ID}/links", "list", "LinkClickStat",
    ),
    "get_domain": (
        "get_domain", [ID], {}, "GET", f"/v1/domains/{ID}", "object", "Domain",
    ),
    "get_mailbox_analytics": (
        "get_mailbox_analytics", [ID], {}, "GET", f"/v1/agent-mailboxes/{ID}/analytics",
        "object", "MailboxAnalytics",
    ),
}


def example(
    name: str, schema: dict[str, Any], schemas: dict[str, Any], owner: str = ""
) -> Any:
    if (owner, name) in UNTYPED_EXAMPLES:
        return UNTYPED_EXAMPLES[(owner, name)]
    if "$ref" in schema:
        return example(name, schemas[schema["$ref"].rsplit("/", 1)[1]], schemas)
    for key in ("oneOf", "anyOf", "allOf"):
        if key in schema:
            options = [s for s in schema[key] if s.get("type") != "null"]
            return example(name, options[0], schemas)
    kind = schema.get("type")
    if isinstance(kind, list):
        kind = next(k for k in kind if k != "null")
    fmt = schema.get("format")
    if kind == "string":
        if fmt == "uuid":
            return str(uuid.uuid5(UUID_NS, name))
        if fmt == "date-time":
            return TIMESTAMP
        return f"{name}-example"
    if kind == "integer":
        return 3
    if kind == "number":
        return 0.5
    if kind == "boolean":
        return True
    if kind == "array":
        return [example(name, schema.get("items", {}), schemas)]
    if kind == "object" or "properties" in schema:
        return {
            prop: example(prop, sub, schemas, owner=name)
            for prop, sub in schema.get("properties", {}).items()
        }
    # An untyped schema (serde_json::Value on the Rust side).
    return {"example": name}


def main(openapi_path: str) -> None:
    schemas = json.loads(Path(openapi_path).read_text())["components"]["schemas"]
    both = sorted(set(SUPPLEMENT) & set(schemas))
    if both:
        sys.exit(f"the API now documents {both}; delete their SUPPLEMENT entries")
    schemas = {**schemas, **SUPPLEMENT}

    for name, (call, args, kwargs, method, path, envelope, schema) in ENDPOINTS.items():
        obj = example(schema, schemas[schema], schemas)
        if envelope == "object":
            body: dict[str, Any] = {"data": obj}
        elif envelope == "list":
            body = {"data": [obj]}
        elif envelope == "paginated":
            body = {"data": [obj], "pagination": PAGINATION}
        elif envelope == "analytics":
            body = {"data": obj, "period": {"from": "2026-08-23", "to": "2026-09-22", "days": 30}}
        else:
            raise ValueError(envelope)
        fixture = {
            "call": call,
            "args": args,
            "kwargs": kwargs,
            "request": [method, path],
            "schema": schema,
            "response": body,
            "expect": EXPECT.get(schema, {}),
        }
        (HERE / f"{name}.json").write_text(json.dumps(fixture, indent=2) + "\n")
        print(f"wrote {name}.json")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
