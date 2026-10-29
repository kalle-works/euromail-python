"""Regenerate the response fixtures in this directory from the API's OpenAPI document.

Each fixture is the full body one SDK call receives, built from the 2xx
response schema the document declares for that operation: the envelope
(`{"data": …}`, a page, a period) and every property of the payload, with
nullable ones given a non-null value so the SDK's types see real data.
`tests/test_response_shapes.py` replays them.

Usage, with the published document:

    curl -s https://api.euromail.dev/api-docs/openapi.json > /tmp/openapi.json

or, for an unreleased API change, from a checkout of kalle-works/euromail.dev:

    cargo run --quiet --example dump_openapi -p euromail-api > /tmp/openapi.json

then from this repo:

    python tests/fixtures/generate.py /tmp/openapi.json
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
DATE = "2026-09-22"

# Values for properties whose schema is untyped (serde_json::Value), where a
# placeholder object would not look like what the API stores.
DNS_RECORDS = {
    "dkim": {"type": "TXT", "host": "em1._domainkey.em.example.com", "value": "v=DKIM1; k=rsa; p=MIIB"},
    "spf": {"type": "TXT", "host": "em.example.com", "value": "v=spf1 include:spf.euromail.dev ~all"},
    "return_path": {"type": "MX", "host": "em.example.com", "value": "bounce.euromail.dev", "priority": 10},
    "dmarc": {"type": "TXT", "host": "_dmarc.example.com", "value": "v=DMARC1; p=none"},
}
UNTYPED_EXAMPLES: dict[tuple[str, str], Any] = {("Domain", "dns_records"): DNS_RECORDS}

# Whole values for schemas whose fields only make sense together.
SCHEMA_EXAMPLES: dict[str, Any] = {
    "Pagination": {"page": 1, "per_page": 25, "total": 1, "total_pages": 1},
    "Period": {"from": "2026-08-23", "to": DATE, "days": 30},
}

# Model values that differ from the wire on purpose, per schema: a record
# without a priority reads as `priority=None`.
EXPECT: dict[str, dict[str, Any]] = {
    "Domain": {
        "dns_records": {k: {"priority": None, **v} for k, v in DNS_RECORDS.items()},
    },
}

ID = str(uuid.uuid5(UUID_NS, "path-id"))

# name -> (SDK method, positional args, keyword args, HTTP method, path as the
# document writes it). `{id}` in the path is filled with ID for the request.
ENDPOINTS: dict[str, tuple[str, list[str], dict[str, str], str, str]] = {
    "get_webhook": ("get_webhook", [ID], {}, "GET", "/v1/webhooks/{id}"),
    "list_webhooks": ("list_webhooks", [], {}, "GET", "/v1/webhooks"),
    "create_contact_list": (
        "create_contact_list", [], {"name": "Customers"}, "POST", "/v1/contact-lists",
    ),
    "get_analytics_overview": (
        "get_analytics_overview", [], {}, "GET", "/v1/analytics/overview",
    ),
    "get_inbound_route": ("get_inbound_route", [ID], {}, "GET", "/v1/inbound-routes/{id}"),
    "get_inbound_email": ("get_inbound_email", [ID], {}, "GET", "/v1/inbound/{id}"),
    "get_newsletter": ("get_newsletter", [ID], {}, "GET", "/v1/newsletters/{id}"),
    "list_api_keys": ("list_api_keys", [], {}, "GET", "/v1/api-keys"),
    "list_messages": (
        "list_messages", [ID], {}, "GET", "/v1/agent-mailboxes/{id}/messages",
    ),
    "get_email_links": ("get_email_links", [ID], {}, "GET", "/v1/emails/{id}/links"),
    "get_domain": ("get_domain", [ID], {}, "GET", "/v1/domains/{id}"),
    "get_mailbox_analytics": (
        "get_mailbox_analytics", [ID], {}, "GET", "/v1/agent-mailboxes/{id}/analytics",
    ),
}


def ref_name(schema: dict[str, Any]) -> str:
    return schema["$ref"].rsplit("/", 1)[1]


def example(
    name: str,
    schema: dict[str, Any],
    schemas: dict[str, Any],
    owner: str = "",
    type_name: str = "",
) -> Any:
    """An example value for `schema`, found as property `name` of schema `owner`."""
    if (owner, name) in UNTYPED_EXAMPLES:
        return UNTYPED_EXAMPLES[(owner, name)]
    if "$ref" in schema:
        ref = ref_name(schema)
        if ref in SCHEMA_EXAMPLES:
            return SCHEMA_EXAMPLES[ref]
        return example(name, schemas[ref], schemas, owner, type_name=ref)
    for key in ("oneOf", "anyOf", "allOf"):
        if key in schema:
            options = [s for s in schema[key] if s.get("type") != "null"]
            return example(name, options[0], schemas, owner, type_name)
    if "enum" in schema:
        return next(v for v in schema["enum"] if v is not None)
    kind = schema.get("type")
    if isinstance(kind, list):
        kind = next(k for k in kind if k != "null")
    fmt = schema.get("format")
    if kind == "string":
        if fmt == "uuid":
            return str(uuid.uuid5(UUID_NS, name))
        if fmt == "date-time":
            return TIMESTAMP
        if fmt == "date":
            return DATE
        return f"{name}-example"
    if kind == "integer":
        return 3
    if kind == "number":
        return 0.5
    if kind == "boolean":
        return True
    if kind == "array":
        return [example(name, schema.get("items", {}), schemas, owner)]
    if kind == "object" or "properties" in schema:
        return {
            prop: example(prop, sub, schemas, owner=type_name or name)
            for prop, sub in schema.get("properties", {}).items()
        }
    # An untyped schema (serde_json::Value on the Rust side).
    return {"example": name}


def success_schema(document: dict[str, Any], method: str, path: str) -> dict[str, Any]:
    """The JSON body schema of the operation's 2xx response."""
    operation = document["paths"][path][method.lower()]
    bodies = [
        response["content"]["application/json"]["schema"]
        for status, response in sorted(operation["responses"].items())
        if status.startswith("2") and "application/json" in response.get("content", {})
    ]
    if not bodies:
        sys.exit(f"{method} {path} declares no JSON body for its 2xx response")
    return bodies[0]


def payload_name(body: dict[str, Any], schemas: dict[str, Any]) -> str:
    """The schema of the object (or list item) under the envelope's `data`."""
    data = schemas[ref_name(body)]["properties"]["data"]
    return ref_name(data.get("items", data))


def main(openapi_path: str) -> None:
    document = json.loads(Path(openapi_path).read_text())
    schemas = document["components"]["schemas"]

    for name, (call, args, kwargs, method, path) in ENDPOINTS.items():
        body_schema = success_schema(document, method, path)
        schema = payload_name(body_schema, schemas)
        fixture = {
            "call": call,
            "args": args,
            "kwargs": kwargs,
            "request": [method, path.replace("{id}", ID)],
            "schema": schema,
            "response": example(name, body_schema, schemas),
            "expect": EXPECT.get(schema, {}),
        }
        (HERE / f"{name}.json").write_text(json.dumps(fixture, indent=2) + "\n")
        print(f"wrote {name}.json")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
