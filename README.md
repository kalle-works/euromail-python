# euromail

Official Python SDK for the [EuroMail](https://euromail.dev) transactional email service.

[![PyPI](https://img.shields.io/pypi/v/euromail.svg)](https://pypi.org/project/euromail/)

## Installation

```bash
pip install euromail
```

## Quick Start

```python
from euromail import EuroMail

client = EuroMail(api_key="em_live_your_api_key_here")

result = client.send_email(
    from_address="sender@yourdomain.com",
    to="recipient@example.com",
    subject="Hello from EuroMail",
    html_body="<h1>Welcome!</h1><p>Your account is ready.</p>",
)
print(f"Email queued: {result.id}")
```

## Configuration

```python
client = EuroMail(
    api_key="em_live_...",                      # Required
    timeout=30.0,                               # Default: 30 seconds
)
```

### Context manager

The client can be used as a context manager to ensure the HTTP connection is properly closed:

```python
with EuroMail(api_key="em_live_...") as client:
    client.send_email(
        from_address="noreply@yourdomain.com",
        to="user@example.com",
        subject="Hello",
        text_body="Welcome aboard!",
    )
```

### Async client

For async/await applications, use `AsyncEuroMail`:

```python
from euromail import AsyncEuroMail

async with AsyncEuroMail(api_key="em_live_...") as client:
    result = await client.send_email(
        from_address="noreply@yourdomain.com",
        to="user@example.com",
        subject="Hello",
        text_body="Welcome aboard!",
    )
```

The async client has the same API as the sync client, with all methods being `async`.

## Sending Emails

### Direct send

```python
result = client.send_email(
    from_address="noreply@yourdomain.com",
    to="user@example.com",
    subject="Order Confirmation",
    html_body="<h1>Thanks for your order!</h1>",
    text_body="Thanks for your order!",
    reply_to="support@yourdomain.com",
    cc=["manager@yourdomain.com"],
    tags=["order", "confirmation"],
    metadata={"order_id": "12345"},
)
```

### Send with template

```python
result = client.send_email(
    from_address="noreply@yourdomain.com",
    to="user@example.com",
    template_alias="welcome-email",
    template_data={
        "name": "John",
        "activation_url": "https://example.com/activate/abc123",
    },
)
```

### Batch send

```python
from euromail import SendEmailParams

batch = client.send_batch(
    emails=[
        SendEmailParams(
            from_address="noreply@yourdomain.com",
            to="user1@example.com",
            subject="Hello User 1",
            text_body="Welcome aboard!",
        ),
        SendEmailParams(
            from_address="noreply@yourdomain.com",
            to="user2@example.com",
            subject="Hello User 2",
            text_body="Welcome aboard!",
        ),
    ]
)
print(f"Sent: {len(batch.data)}, Errors: {len(batch.errors)}")
```

### Idempotent sends

```python
client.send_email(
    from_address="noreply@yourdomain.com",
    to="user@example.com",
    subject="Payment Receipt",
    html_body="<p>Payment received.</p>",
    idempotency_key="payment-receipt-12345",
)
```

### Retrieve and list emails

```python
email = client.get_email("email-uuid")

emails = client.list_emails(page=1, per_page=50, status="delivered")
for e in emails.data:
    print(f"{e.to_address}: {e.status}")
```

## Domains

```python
# Add a sending domain
domain = client.add_domain("mail.yourdomain.com")
print("Configure DNS records:", domain.dns_records)

# Trigger verification
verification = client.verify_domain(domain.id)
if verification.fully_verified:
    print("Domain verified! SPF, DKIM, DMARC, and return-path all confirmed.")

# List all domains
domains = client.list_domains(page=1, per_page=25)

# Remove a domain
client.delete_domain(domain.id)
```

## Templates

```python
# Create a template with Jinja2-style variables
template = client.create_template(
    alias="welcome-email",
    name="Welcome Email",
    subject="Welcome, {{ name }}!",
    html_body="<h1>Hello {{ name }}</h1><p>Welcome to {{ company }}.</p>",
    text_body="Hello {{ name }}, welcome to {{ company }}.",
)

# Update a template
client.update_template(template.id, subject="Welcome to {{ company }}, {{ name }}!")

# List and delete
templates = client.list_templates(page=1, per_page=25)
client.delete_template(template.id)
```

## Webhooks

```python
# Subscribe to delivery events
webhook = client.create_webhook(
    url="https://yourdomain.com/webhooks/euromail",
    events=["delivered", "bounced", "complained", "email.inbound"],
)

# Update webhook
client.update_webhook(
    webhook.id,
    url="https://yourdomain.com/webhooks/v2",
    events=["delivered", "bounced"],
    is_active=True,
)

# Send a test event
test = client.test_webhook(webhook.id)

# List and delete
webhooks = client.list_webhooks()
client.delete_webhook(webhook.id)
```

Supported events: `sent`, `delivered`, `bounced`, `opened`, `clicked`, `complained`, `email.inbound`

## Suppressions

```python
# Suppress an address manually
client.add_suppression("bounced@example.com", reason="hard_bounce")

# List all suppressions
suppressions = client.list_suppressions(page=1, per_page=50)

# Remove a suppression
client.delete_suppression("bounced@example.com")
```

## Contact Lists

```python
# Create a list with double opt-in
contact_list = client.create_contact_list(
    name="Newsletter",
    description="Monthly product updates",
    double_opt_in=True,
)

# Add a single contact
contact = client.add_contact(
    contact_list.id,
    email="user@example.com",
    metadata={"first_name": "Jane", "source": "signup"},
)

# Bulk add contacts
result = client.bulk_add_contacts(
    contact_list.id,
    contacts=[
        {"email": "a@example.com", "metadata": {"name": "Alice"}},
        {"email": "b@example.com", "metadata": {"name": "Bob"}},
    ],
)
print(f"Inserted: {result.inserted} of {result.total_requested}")

# List contacts with filters
contacts = client.list_contacts(contact_list.id, page=1, per_page=50, status="active")

# Remove contact and delete list
client.remove_contact(contact_list.id, "user@example.com")
client.delete_contact_list(contact_list.id)
```

## Inbound Email

```python
# List received emails
inbound = client.list_inbound_emails(page=1, per_page=25)

# Get details
email = client.get_inbound_email("inbound-uuid")
print(f"From: {email.from_address}, Subject: {email.subject}")

# Delete
client.delete_inbound_email("inbound-uuid")
```

## Inbound Routes

```python
# Route incoming email to a webhook
route = client.create_inbound_route(
    domain_id="domain-uuid",
    pattern="support@",
    match_type="prefix",
    priority=10,
    webhook_url="https://yourdomain.com/inbound/support",
)

# Update a route
client.update_inbound_route(route.id, webhook_url="https://yourdomain.com/inbound/v2", is_active=True)

# Catch-all route
client.create_inbound_route(
    domain_id="domain-uuid",
    pattern="*",
    match_type="catch_all",
    priority=100,
)

# List and delete
routes = client.list_inbound_routes()
client.delete_inbound_route(route.id)
```

## Analytics

```python
# Overview for the last 30 days
overview = client.get_analytics_overview(period="30d")
print(f"Delivery rate: {overview.delivery_rate}%")

# Custom date range
custom = client.get_analytics_overview(from_date="2025-01-01", to_date="2025-01-31")

# Time series data
timeseries = client.get_analytics_timeseries(period="7d", metrics=["sent", "delivered", "bounced"])

# Per-domain breakdown
domains = client.get_analytics_domains(period="30d", limit=10)

# Export as CSV
csv_data = client.export_analytics_csv(period="30d")
```

## Account

```python
account = client.get_account()
print(f"Plan: {account.plan}, Used: {account.emails_sent_this_month}/{account.monthly_quota}")

# Export all account data (GDPR)
export_data = client.export_account()

# Delete account permanently
client.delete_account()
```

## Audit Logs

```python
logs = client.list_audit_logs(page=1, per_page=50)
for log in logs.data:
    print(f"{log.created_at}: {log.action} on {log.resource_type}")
```

## Dead Letters

```python
# List failed emails
dead_letters = client.list_dead_letters(count=20)

# Retry delivery
client.retry_dead_letter("dead-letter-uuid")

# Remove permanently
client.delete_dead_letter("dead-letter-uuid")
```

## Error Handling

All API errors raise typed exceptions:

```python
from euromail import (
    EuroMail,
    EuroMailError,
    AuthenticationError,
    RateLimitError,
    ValidationError,
)

try:
    client.send_email(...)
except AuthenticationError:
    # Invalid or missing API key (401)
    print("Check your API key")
except ValidationError as e:
    # Invalid request parameters (422)
    print(f"{e.code}: {e.message}")
except RateLimitError as e:
    # Too many requests (429)
    print(f"Retry after {e.retry_after} seconds")
except EuroMailError as e:
    # Other API errors (4xx/5xx)
    print(f"[{e.status}] {e.code}: {e.message}")
```

| Exception | HTTP Status | Description |
|---|---|---|
| `AuthenticationError` | 401 | Invalid or missing API key |
| `ValidationError` | 422 | Invalid request parameters |
| `RateLimitError` | 429 | Too many requests (includes `retry_after`) |
| `EuroMailError` | 4xx/5xx | Base class for all API errors |

## API Reference

| Category | Method | Description |
|---|---|---|
| **Emails** | `send_email(...)` | Send a single email |
| | `send_batch(emails=...)` | Send up to 500 emails in one request |
| | `get_email(id)` | Get email details and status |
| | `list_emails(...)` | List emails with pagination and status filter |
| **Templates** | `create_template(...)` | Create an email template |
| | `get_template(id)` | Get template by ID |
| | `update_template(id, ...)` | Update template fields |
| | `delete_template(id)` | Delete a template |
| | `list_templates(...)` | List templates with pagination |
| **Domains** | `add_domain(domain)` | Register a sending domain |
| | `get_domain(id)` | Get domain details and DNS records |
| | `verify_domain(id)` | Trigger DNS verification |
| | `delete_domain(id)` | Remove a domain |
| | `list_domains(...)` | List domains with pagination |
| **Webhooks** | `create_webhook(...)` | Subscribe to events |
| | `get_webhook(id)` | Get webhook details |
| | `update_webhook(id, ...)` | Update URL, events, or status |
| | `test_webhook(id)` | Send a test event |
| | `delete_webhook(id)` | Remove a webhook |
| | `list_webhooks(...)` | List webhooks with pagination |
| **Suppressions** | `add_suppression(email, ...)` | Suppress an email address |
| | `delete_suppression(email)` | Remove a suppression |
| | `list_suppressions(...)` | List suppressions with pagination |
| **Contact Lists** | `create_contact_list(...)` | Create a contact list |
| | `get_contact_list(id)` | Get list details |
| | `update_contact_list(id, ...)` | Update list settings |
| | `delete_contact_list(id)` | Delete a list |
| | `list_contact_lists()` | List all contact lists |
| | `add_contact(list_id, ...)` | Add a contact to a list |
| | `bulk_add_contacts(list_id, ...)` | Add multiple contacts |
| | `list_contacts(list_id, ...)` | List contacts with filters |
| | `remove_contact(list_id, email)` | Remove a contact |
| **Inbound** | `list_inbound_emails(...)` | List received emails |
| | `get_inbound_email(id)` | Get inbound email details |
| | `delete_inbound_email(id)` | Delete an inbound email |
| **Inbound Routes** | `create_inbound_route(...)` | Create a routing rule |
| | `get_inbound_route(id)` | Get route details |
| | `update_inbound_route(id, ...)` | Update a route |
| | `delete_inbound_route(id)` | Delete a route |
| | `list_inbound_routes(...)` | List routes with pagination |
| **Analytics** | `get_analytics_overview(...)` | Aggregated delivery stats |
| | `get_analytics_timeseries(...)` | Daily metrics over time |
| | `get_analytics_domains(...)` | Per-domain breakdown |
| | `export_analytics_csv(...)` | Export stats as CSV |
| **Audit Logs** | `list_audit_logs(...)` | List account activity |
| **Dead Letters** | `list_dead_letters(...)` | List permanently failed emails |
| | `retry_dead_letter(id)` | Retry delivery |
| | `delete_dead_letter(id)` | Remove from dead letter queue |
| **Account** | `get_account()` | Get account info and quota |
| | `export_account()` | Export all account data |
| | `delete_account()` | Permanently delete account |

## Requirements

- Python 3.9+
- httpx >= 0.27

## License

MIT

