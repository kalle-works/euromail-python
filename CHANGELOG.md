# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.5.0] - 2026-09-04

### Added

- `verify_signature()` (in `euromail.webhooks`, also exported from the
  top-level package alongside `DEFAULT_TOLERANCE_SECONDS`) verifies a
  webhook delivery's `X-Euromail-Signature` header against the raw request
  body: `t=<unix_timestamp>,v1=<hex_hmac_sha256>`, constant-time compared,
  with a default 300s timestamp tolerance and support for a secret-rotation
  window carrying more than one `v1` entry.
- `import_suppressions()` / `export_suppressions()` on both `EuroMail` and
  `AsyncEuroMail`: bulk-import up to 10,000 addresses in one call
  (`POST /v1/suppressions/import`) and export the full suppression list as
  CSV (`GET /v1/suppressions/export`). New `ImportSuppressionsResult` type.
- `ForbiddenError`, `NotFoundError`, `ConflictError`, and `ServerError`
  exception classes, so 403/404/409/5xx responses raise something more
  specific than the generic `EuroMailError`.

### Fixed

- `RateLimitError.retry_after` now reads the `Retry-After` HTTP response
  header. It previously read a `retry_after` field from the JSON error
  body, which the API has never sent — every `429` resolved to
  `retry_after=None` regardless of the real wait time.
- `ValidationError` now carries the actual response status (`400` or `422`
  — the API returns validation failures at both, depending on the
  endpoint) instead of assuming `422`.

## [0.4.0] - 2026-07-07

### Added

- Full agent-mailbox parity on both `EuroMail` and `AsyncEuroMail`:
  `reply_to_message`, `list_mailbox_threads`, `get_mailbox_thread`,
  `search_mailbox_messages`, `update_message_labels`,
  `get_message_attachment_urls`, `list_mailbox_contacts`,
  `get_mailbox_analytics`, and `update_auto_responder`.
- New dataclasses/types `MailboxReplyResult`, `MailboxAttachmentUrl`,
  `MailboxContact`, and `MailboxAnalytics` exported from the top-level
  `euromail` package.
- `MailboxMessage` gained `in_reply_to`, `references_header`,
  `attachments_stored`, `attachments_metadata`, `classification`,
  `classification_confidence`, `classified_at`, `leased_until`, and
  `lease_token` fields to match the current server response.
- `AgentMailbox` gained `auto_responder_enabled`, `auto_responder_rules`,
  and `webhook_filters` fields.

## [0.3.0] - 2026-07-07

### Added

- `send_email`/`send_batch` (sync + async): `attachments`, `send_at` (schedule
  delivery), `tracking` (per-email open/click override), `transactional`
  (opt out of the default `List-Unsubscribe`-suppressing behavior for
  marketing/newsletter sends), and `stream` (route through a named message
  stream) — brings the SDK up to date with the current `/v1/emails` API.
  Attachments were previously unsupported by this SDK entirely.
- `send_broadcast` (sync + async): `tracking` and `transactional` overrides.
- New `Attachment` dataclass exported from the top-level `euromail` package.

## [0.2.0] - 2026-04-13

### Added

- Native support for agent mailboxes on both `EuroMail` and `AsyncEuroMail`:
  `create_mailbox`, `list_mailboxes`, `get_mailbox`, `delete_mailbox`,
  `list_messages`, `wait_for_next_message` (long-poll), `delete_message`,
  `ack_message`, `nack_message`.
- New dataclasses `AgentMailbox`, `MailboxMessage`, and `LeasedMessage`
  exported from the top-level `euromail` package.
- `wait_for_next_message` returns `None` on HTTP 408 (no message available
  before the server-side long-poll timeout) instead of raising, so callers
  can simply loop.

## [0.1.0] - 2026-04-13

### Added

- Initial Python SDK for euromail transactional email API
- Synchronous `EuroMail` and asynchronous `AsyncEuroMail` clients
- `get_email_links` and `generate_insights` methods
- Full type definitions for all API resources (emails, domains, contacts, templates, webhooks, newsletters, and more)
- GDPR compliance helpers (`gdpr_export`, `gdpr_erase`)
- Domain verification and DNS record management
- Contact list and signup form management
- Analytics and audit log retrieval
- Suppression list management
- Dead letter queue inspection
- Inbound email routing
- Sub-account management
- `EUROMAIL_API_KEY` environment variable support for client initialization
- `EUROMAIL_API_URL` environment variable support for custom API base URL
