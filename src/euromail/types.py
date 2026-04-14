"""Type definitions for the EuroMail SDK."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Generic, Literal, Optional, TypeVar

EmailStatus = Literal[
    "queued", "processing", "sent", "delivered", "bounced", "failed", "rejected"
]

EmailEventType = Literal[
    "queued",
    "processing",
    "sent",
    "delivered",
    "bounced",
    "deferred",
    "opened",
    "clicked",
    "complained",
    "unsubscribed",
]

WebhookEventType = Literal[
    "sent",
    "delivered",
    "bounced",
    "opened",
    "clicked",
    "complained",
    "email.inbound",
    "account.auto_paused",
    "insights.generated",
]

SuppressionReason = Literal["hard_bounce", "complaint", "manual", "unsubscribe", "fbl"]

T = TypeVar("T")


@dataclass
class SendEmailParams:
    from_address: str
    to: "str | list[str]"
    subject: Optional[str] = None
    cc: Optional[list[str]] = None
    bcc: Optional[list[str]] = None
    reply_to: Optional[str] = None
    html_body: Optional[str] = None
    text_body: Optional[str] = None
    template_alias: Optional[str] = None
    template_data: Optional[dict[str, Any]] = None
    headers: Optional[dict[str, str]] = None
    tags: Optional[list[str]] = None
    metadata: Optional[dict[str, str]] = None
    idempotency_key: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "from": self.from_address,
            "to": self.to,
        }
        if self.subject is not None:
            d["subject"] = self.subject
        if self.cc is not None:
            d["cc"] = self.cc
        if self.bcc is not None:
            d["bcc"] = self.bcc
        if self.reply_to is not None:
            d["reply_to"] = self.reply_to
        if self.html_body is not None:
            d["html_body"] = self.html_body
        if self.text_body is not None:
            d["text_body"] = self.text_body
        if self.template_alias is not None:
            d["template_alias"] = self.template_alias
        if self.template_data is not None:
            d["template_data"] = self.template_data
        if self.headers is not None:
            d["headers"] = self.headers
        if self.tags is not None:
            d["tags"] = self.tags
        if self.metadata is not None:
            d["metadata"] = self.metadata
        if self.idempotency_key is not None:
            d["idempotency_key"] = self.idempotency_key
        return d


@dataclass
class Email:
    id: str
    account_id: str
    message_id: str
    from_address: str
    to_address: str
    subject: str
    status: EmailStatus
    attempts: int
    max_attempts: int
    created_at: str
    updated_at: str
    domain_id: Optional[str] = None
    cc: Optional[list[str]] = None
    bcc: Optional[list[str]] = None
    reply_to: Optional[str] = None
    html_body: Optional[str] = None
    text_body: Optional[str] = None
    template_id: Optional[str] = None
    template_data: Optional[dict[str, Any]] = None
    headers: dict[str, str] = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, str] = field(default_factory=dict)
    error_message: Optional[str] = None
    smtp_response: Optional[str] = None
    sent_at: Optional[str] = None


@dataclass
class EmailEvent:
    id: str
    email_id: str
    account_id: str
    event_type: EmailEventType
    created_at: str
    bounce_type: Optional[str] = None
    bounce_category: Optional[str] = None
    remote_mta: Optional[str] = None
    diagnostic_code: Optional[str] = None
    user_agent: Optional[str] = None
    ip_address: Optional[str] = None
    link_url: Optional[str] = None
    raw_payload: Optional[dict[str, Any]] = None


@dataclass
class SendEmailResponse:
    id: str
    message_id: str
    status: EmailStatus
    to: str
    created_at: str
    sandbox: bool = False
    scheduled_at: Optional[str] = None


@dataclass
class BatchError:
    index: int
    error: str


@dataclass
class BatchResponse:
    data: list[SendEmailResponse]
    errors: list[BatchError]


@dataclass
class Template:
    id: str
    account_id: str
    alias: str
    name: str
    subject: str
    created_at: str
    updated_at: str
    html_body: Optional[str] = None
    text_body: Optional[str] = None


@dataclass
class DnsRecord:
    type: str
    host: str
    value: str
    priority: Optional[int] = None


@dataclass
class Domain:
    id: str
    account_id: str
    domain: str
    dkim_selector: str
    dkim_public_key: str
    spf_verified: bool
    dkim_verified: bool
    dmarc_verified: bool
    return_path_verified: bool
    mx_verified: bool
    inbound_enabled: bool
    dns_records: dict[str, DnsRecord]
    created_at: str
    updated_at: str
    mx_verified_at: Optional[str] = None
    verified_at: Optional[str] = None
    tracking_domain: Optional[str] = None
    tracking_domain_verified: bool = False
    tracking_domain_verified_at: Optional[str] = None


@dataclass
class VerificationCheck:
    verified: bool
    detail: str


@dataclass
class DomainVerificationResult:
    domain: Domain
    checks: dict[str, VerificationCheck]


@dataclass
class Webhook:
    id: str
    account_id: str
    url: str
    events: list[WebhookEventType]
    is_active: bool
    created_at: str
    updated_at: str
    failure_count: int = 0
    secret: Optional[str] = None
    last_success_at: Optional[str] = None
    last_failure_at: Optional[str] = None
    last_failure_reason: Optional[str] = None


@dataclass
class Suppression:
    id: str
    account_id: str
    email_address: str
    reason: SuppressionReason
    created_at: str
    source_email_id: Optional[str] = None


@dataclass
class Account:
    id: str
    name: str
    email: str
    plan: str
    monthly_quota: int
    emails_sent_this_month: int
    quota_reset_at: str
    created_at: str


@dataclass
class SubAccount:
    id: str
    name: str
    email: str
    plan: str
    monthly_quota: int
    emails_sent_this_month: int
    parent_account_id: str
    is_active: bool
    created_at: str


@dataclass
class PaginatedResponse(Generic[T]):
    data: list[T]
    page: int
    per_page: int
    total: int
    total_pages: int


@dataclass
class ContactList:
    id: str
    account_id: str
    name: str
    double_opt_in: bool
    created_at: str
    updated_at: str
    contact_count: int = 0
    description: Optional[str] = None


@dataclass
class Contact:
    id: str
    list_id: str
    email: str
    status: str
    created_at: str
    account_id: Optional[str] = None
    metadata: Optional[dict[str, str]] = None
    subscribed_at: Optional[str] = None
    unsubscribed_at: Optional[str] = None


@dataclass
class BulkAddContactsResponse:
    inserted: int
    total_requested: int


@dataclass
class AnalyticsPeriod:
    from_date: str
    to_date: str
    period: str


@dataclass
class AnalyticsSummary:
    total_sent: int
    total_delivered: int
    total_bounced: int
    total_opens: int
    total_clicks: int
    total_unsubscribes: int
    delivery_rate_pct: float
    open_rate_pct: float
    click_rate_pct: float
    bounce_rate_pct: float


@dataclass
class TimeseriesPoint:
    date: str
    sent: Optional[int] = None
    delivered: Optional[int] = None
    bounced: Optional[int] = None
    opens: Optional[int] = None
    clicks: Optional[int] = None


@dataclass
class DomainAnalytics:
    domain: str
    sent: int
    delivered: int
    bounced: int
    open_rate: float
    click_rate: float


@dataclass
class AuditLog:
    id: str
    account_id: str
    action: str
    resource_type: str
    created_at: str
    resource_id: Optional[str] = None
    actor_id: Optional[str] = None
    actor_type: Optional[str] = None
    ip_address: Optional[str] = None
    metadata: Optional[dict[str, Any]] = None


@dataclass
class WebhookTestResponse:
    message: str
    payload: dict[str, Any]


@dataclass
class DeadLetter:
    stream_id: str
    original_stream: str
    email_id: str
    account_id: str
    failure_reason: str
    attempt_count: int
    last_error: str
    failed_at: str
    payload: dict[str, Any]


@dataclass
class InboundEmail:
    id: str
    account_id: str
    domain_id: str
    from_address: str
    to_addresses: list[str]
    subject: str
    raw_size: int
    created_at: str
    text_body: Optional[str] = None
    html_body: Optional[str] = None


@dataclass
class InboundRoute:
    id: str
    account_id: str
    domain_id: str
    pattern: str
    match_type: str
    priority: int
    is_active: bool
    created_at: str
    updated_at: str
    webhook_url: Optional[str] = None


# ---- API Key Types ----

@dataclass
class ApiKey:
    id: str
    name: str
    key_prefix: str
    scopes: list[str]
    is_active: bool
    created_at: str
    last_used_at: Optional[str] = None


@dataclass
class ApiKeyCreated(ApiKey):
    """Returned only at creation time. Store `key` securely."""
    key: str = ""


# ---- Newsletter Types ----

@dataclass
class Newsletter:
    id: str
    account_id: str
    subject: str
    from_address: str
    status: str
    created_at: str
    updated_at: str
    list_id: Optional[str] = None
    html_body: Optional[str] = None
    text_body: Optional[str] = None
    template_id: Optional[str] = None
    template_data: Optional[dict[str, Any]] = None
    reply_to: Optional[str] = None
    operation_id: Optional[str] = None
    scheduled_at: Optional[str] = None
    sent_at: Optional[str] = None
    total_recipients: Optional[int] = None


@dataclass
class NewsletterSendResponse:
    operation_id: str
    total_recipients: int
    message: str


# ---- Broadcast Types ----

@dataclass
class BroadcastResponse:
    operation_id: str
    total_recipients: int
    message: str


# ---- Email Validation Types ----

Deliverable = Literal["yes", "no", "unknown"]


@dataclass
class EmailValidation:
    email: str
    valid: bool
    deliverable: str
    is_disposable: bool
    is_role: bool
    is_free: bool
    mx_found: bool
    reason: Optional[str] = None


# ---- Operation Types ----

OperationType = Literal["broadcast", "newsletter_send", "bulk_import"]
OperationStatus = Literal["pending", "processing", "completed", "failed"]


@dataclass
class Operation:
    id: str
    account_id: str
    operation_type: str
    status: str
    total_items: int
    completed_items: int
    failed_items: int
    created_at: str
    updated_at: str
    expires_at: str
    error_summary: Optional[dict[str, Any]] = None
    metadata: Optional[dict[str, Any]] = None
    completed_at: Optional[str] = None


# ---- Billing Types ----

@dataclass
class BillingPlan:
    plan: str
    monthly_quota: int
    max_domains: int
    max_templates: int
    max_webhooks: int
    max_contact_lists: int
    max_sub_accounts: int
    tracking_enabled: bool
    price_cents: int
    stripe_price_id: Optional[str] = None


@dataclass
class SubscriptionLimits:
    max_domains: int
    max_templates: int
    max_webhooks: int
    tracking_enabled: bool
    price_cents: int


@dataclass
class Subscription:
    plan: str
    subscription_status: str
    billing_email: str
    monthly_quota: int
    emails_sent_this_month: int
    limits: SubscriptionLimits
    stripe_subscription_id: Optional[str] = None
    trial_ends_at: Optional[str] = None


# ---- GDPR Types ----

@dataclass
class GdprExport:
    email_address: str
    emails: list[dict[str, Any]]
    events: list[dict[str, Any]]
    suppressions: list[dict[str, Any]]
    unsubscribe_events: list[dict[str, Any]]
    inbound_emails: list[dict[str, Any]]


@dataclass
class GdprEraseResult:
    email_address: str
    rows_deleted: int
    message: str


# ---- Signup Form Types ----

@dataclass
class SignupForm:
    id: str
    account_id: str
    list_id: str
    slug: str
    title: str
    custom_fields: list[dict[str, Any]]
    theme: dict[str, Any]
    is_active: bool
    form_url: str
    embed_code: str
    created_at: str
    updated_at: str
    description: Optional[str] = None
    success_message: Optional[str] = None
    redirect_url: Optional[str] = None


@dataclass
class CreateSignupFormParams:
    list_id: str
    title: str
    description: Optional[str] = None
    success_message: Optional[str] = None
    redirect_url: Optional[str] = None
    custom_fields: Optional[list[dict[str, Any]]] = None
    theme: Optional[dict[str, Any]] = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "list_id": self.list_id,
            "title": self.title,
        }
        if self.description is not None:
            d["description"] = self.description
        if self.success_message is not None:
            d["success_message"] = self.success_message
        if self.redirect_url is not None:
            d["redirect_url"] = self.redirect_url
        if self.custom_fields is not None:
            d["custom_fields"] = self.custom_fields
        if self.theme is not None:
            d["theme"] = self.theme
        return d


# ---- Link Click Stats ----

@dataclass
class LinkClickStat:
    url: str
    clicks: int
    unique_clicks: int


# ---- Insight Types ----

InsightSeverity = Literal["info", "warn", "critical"]
InsightArea = Literal["deliverability", "reputation", "performance", "security"]


@dataclass
class InsightFinding:
    severity: str
    area: str
    observation: str
    recommendation: str


@dataclass
class InsightReport:
    id: str
    account_id: Optional[str]
    generated_at: str
    period_start: str
    period_end: str
    model: str
    summary: str
    findings: list[InsightFinding]
    raw_markdown: Optional[str] = None
    acknowledged_at: Optional[str] = None
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None


# ---- Agent Mailboxes ----


@dataclass
class AgentMailbox:
    id: str
    account_id: str
    local_part: str
    domain: str
    address: str
    display_name: Optional[str]
    created_at: str


@dataclass
class MailboxMessage:
    id: str
    mailbox_id: str
    account_id: str
    mail_from: str
    size_bytes: int
    created_at: str
    message_id: Optional[str] = None
    from_header: Optional[str] = None
    reply_to: Optional[str] = None
    subject: Optional[str] = None
    text_body: Optional[str] = None
    html_body: Optional[str] = None
    thread_id: Optional[str] = None
    labels: list[str] = field(default_factory=list)
    read_at: Optional[str] = None


@dataclass
class LeasedMessage:
    data: MailboxMessage
    lease_token: str
    lease_expires_at: str


@dataclass
class UpdateSignupFormParams:
    title: Optional[str] = None
    description: Optional[str] = None
    success_message: Optional[str] = None
    redirect_url: Optional[str] = None
    custom_fields: Optional[list[dict[str, Any]]] = None
    theme: Optional[dict[str, Any]] = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {}
        if self.title is not None:
            d["title"] = self.title
        if self.description is not None:
            d["description"] = self.description
        if self.success_message is not None:
            d["success_message"] = self.success_message
        if self.redirect_url is not None:
            d["redirect_url"] = self.redirect_url
        if self.custom_fields is not None:
            d["custom_fields"] = self.custom_fields
        if self.theme is not None:
            d["theme"] = self.theme
        return d
