# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
