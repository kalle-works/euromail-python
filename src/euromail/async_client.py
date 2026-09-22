"""Asynchronous EuroMail client."""

from __future__ import annotations

import os
from typing import Any, Optional

import httpx

from euromail.errors import EuroMailError
from urllib.parse import quote

from euromail.types import (
    Account,
    AnalyticsSummary,
    ApiKey,
    ApiKeyCreated,
    Attachment,
    AuditLog,
    BatchResponse,
    BillingPlan,
    BroadcastResponse,
    BulkAddContactsResponse,
    Contact,
    ContactList,
    DeadLetter,
    Domain,
    DomainAnalytics,
    DomainVerificationResult,
    Email,
    EmailValidation,
    GdprEraseResult,
    GdprExport,
    ImportSuppressionsResult,
    InboundEmail,
    InboundRoute,
    Newsletter,
    NewsletterSendResponse,
    Operation,
    PaginatedResponse,
    SendEmailParams,
    SendEmailResponse,
    SubAccount,
    Subscription,
    Suppression,
    Template,
    TimeseriesPoint,
    Webhook,
    WebhookTestResponse,
    SignupForm,
    CreateSignupFormParams,
    UpdateSignupFormParams,
    LinkClickStat,
    InsightReport,
    AgentMailbox,
    MailboxMessage,
    LeasedMessage,
    MailboxReplyResult,
    MailboxAttachmentUrl,
    MailboxContact,
    MailboxAnalytics,
    from_dict,
)

DEFAULT_BASE_URL = "https://api.euromail.dev"
DEFAULT_TIMEOUT = 30.0


class AsyncEuroMail:
    """Asynchronous client for the EuroMail API."""

    def __init__(
        self,
        *,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        resolved_key = api_key or os.environ.get("EUROMAIL_API_KEY")
        if not resolved_key:
            raise ValueError(
                "api_key is required. Either pass it explicitly or set the "
                "EUROMAIL_API_KEY environment variable."
            )
        self._api_key = resolved_key
        resolved_url = base_url or os.environ.get("EUROMAIL_API_URL") or DEFAULT_BASE_URL
        self._base_url = resolved_url.rstrip("/")
        if not self._base_url.startswith("https://") and not self._base_url.startswith(("http://localhost", "http://127.0.0.1")):
            import warnings
            warnings.warn("EuroMail base URL does not use HTTPS. API keys will be sent in cleartext.", stacklevel=2)
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            headers={
                "Authorization": f"Bearer {resolved_key}",
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
            timeout=timeout,
        )

    async def __aenter__(self) -> "AsyncEuroMail":
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()

    async def close(self) -> None:
        await self._client.aclose()

    # ---- Account Methods ----

    async def get_account(self) -> Account:
        data = await self._get("/v1/account")
        return from_dict(Account, data["data"])

    async def export_account(self) -> str:
        return await self._get_raw("/v1/account/export")

    async def delete_account(self) -> None:
        await self._delete("/v1/account")

    # ---- Email Methods ----

    async def send_email(
        self,
        *,
        from_address: str,
        to: "str | list[str]",
        subject: Optional[str] = None,
        cc: Optional[list[str]] = None,
        bcc: Optional[list[str]] = None,
        reply_to: Optional[str] = None,
        html_body: Optional[str] = None,
        text_body: Optional[str] = None,
        template_alias: Optional[str] = None,
        template_data: Optional[dict[str, Any]] = None,
        headers: Optional[dict[str, str]] = None,
        tags: Optional[list[str]] = None,
        metadata: Optional[dict[str, str]] = None,
        idempotency_key: Optional[str] = None,
        attachments: Optional[list[Attachment]] = None,
        send_at: Optional[str] = None,
        tracking: Optional[bool] = None,
        transactional: Optional[bool] = None,
        stream: Optional[str] = None,
    ) -> SendEmailResponse:
        params = SendEmailParams(
            from_address=from_address,
            to=to,
            subject=subject,
            cc=cc,
            bcc=bcc,
            reply_to=reply_to,
            html_body=html_body,
            text_body=text_body,
            template_alias=template_alias,
            template_data=template_data,
            headers=headers,
            tags=tags,
            metadata=metadata,
            idempotency_key=idempotency_key,
            attachments=attachments,
            send_at=send_at,
            tracking=tracking,
            transactional=transactional,
            stream=stream,
        )
        data = await self._post("/v1/emails", params.to_dict())
        return from_dict(SendEmailResponse, data["data"])

    async def send_batch(self, *, emails: list[SendEmailParams]) -> BatchResponse:
        payload = {"emails": [e.to_dict() for e in emails]}
        data = await self._post("/v1/emails/batch", payload)
        return from_dict(BatchResponse, data)

    async def get_email(self, email_id: str) -> Email:
        data = await self._get(f"/v1/emails/{email_id}")
        inner = data.get("data", data)
        email_data = inner.get("email", inner)
        return from_dict(Email, email_data)

    async def list_emails(
        self,
        *,
        page: int = 1,
        per_page: int = 25,
        status: Optional[str] = None,
    ) -> PaginatedResponse[Email]:
        params: dict[str, Any] = {"page": page, "per_page": per_page}
        if status:
            params["status"] = status
        data = await self._get("/v1/emails", params=params)
        pagination = data["pagination"]
        return PaginatedResponse(
            data=[from_dict(Email, e) for e in data["data"]],
            page=pagination["page"],
            per_page=pagination["per_page"],
            total=pagination["total"],
            total_pages=pagination["total_pages"],
        )

    async def cancel_scheduled_email(self, email_id: str) -> SendEmailResponse:
        data = await self._post(f"/v1/emails/{email_id}/cancel", {})
        return from_dict(SendEmailResponse, data["data"])

    async def get_email_links(self, email_id: str) -> list[LinkClickStat]:
        """Return per-link click stats for a sent email."""
        data = await self._get(f"/v1/emails/{quote(email_id)}/links")
        return [from_dict(LinkClickStat, item) for item in data["data"]]

    async def send_broadcast(
        self,
        *,
        contact_list_id: str,
        from_address: str,
        subject: Optional[str] = None,
        html_body: Optional[str] = None,
        text_body: Optional[str] = None,
        template_alias: Optional[str] = None,
        template_data: Optional[dict[str, Any]] = None,
        reply_to: Optional[str] = None,
        headers: Optional[dict[str, str]] = None,
        tags: Optional[list[str]] = None,
        send_at: Optional[str] = None,
        tracking: Optional[bool] = None,
        transactional: Optional[bool] = None,
    ) -> BroadcastResponse:
        payload: dict[str, Any] = {
            "contact_list_id": contact_list_id,
            "from_address": from_address,
        }
        if subject is not None:
            payload["subject"] = subject
        if html_body is not None:
            payload["html_body"] = html_body
        if text_body is not None:
            payload["text_body"] = text_body
        if template_alias is not None:
            payload["template_alias"] = template_alias
        if template_data is not None:
            payload["template_data"] = template_data
        if reply_to is not None:
            payload["reply_to"] = reply_to
        if headers is not None:
            payload["headers"] = headers
        if tags is not None:
            payload["tags"] = tags
        if send_at is not None:
            payload["send_at"] = send_at
        if tracking is not None:
            payload["tracking"] = tracking
        if transactional is not None:
            payload["transactional"] = transactional
        data = await self._post("/v1/emails/broadcast", payload)
        return from_dict(BroadcastResponse, data["data"])

    # ---- Template Methods ----

    async def create_template(
        self,
        *,
        alias: str,
        name: str,
        subject: str,
        html_body: Optional[str] = None,
        text_body: Optional[str] = None,
    ) -> Template:
        payload: dict[str, Any] = {"alias": alias, "name": name, "subject": subject}
        if html_body is not None:
            payload["html_body"] = html_body
        if text_body is not None:
            payload["text_body"] = text_body
        data = await self._post("/v1/templates", payload)
        return from_dict(Template, _unwrap(data))

    async def get_template(self, template_id: str) -> Template:
        data = await self._get(f"/v1/templates/{template_id}")
        return from_dict(Template, _unwrap(data))

    async def update_template(self, template_id: str, **kwargs: Any) -> Template:
        data = await self._put(f"/v1/templates/{template_id}", kwargs)
        return from_dict(Template, _unwrap(data))

    async def delete_template(self, template_id: str) -> None:
        await self._delete(f"/v1/templates/{template_id}")

    async def list_templates(
        self, *, page: int = 1, per_page: int = 25
    ) -> PaginatedResponse[Template]:
        data = await self._get(
            "/v1/templates", params={"page": page, "per_page": per_page}
        )
        pagination = data["pagination"]
        return PaginatedResponse(
            data=[from_dict(Template, t) for t in data["data"]],
            page=pagination["page"],
            per_page=pagination["per_page"],
            total=pagination["total"],
            total_pages=pagination["total_pages"],
        )

    # ---- Domain Methods ----

    async def add_domain(self, domain: str) -> Domain:
        data = await self._post("/v1/domains", {"domain": domain})
        return from_dict(Domain, data["data"])

    async def get_domain(self, domain_id: str) -> Domain:
        data = await self._get(f"/v1/domains/{domain_id}")
        return from_dict(Domain, data["data"])

    async def verify_domain(self, domain_id: str) -> DomainVerificationResult:
        data = await self._post(f"/v1/domains/{domain_id}/verify", {})
        inner = _unwrap(data)
        return from_dict(DomainVerificationResult, inner)

    async def delete_domain(self, domain_id: str) -> None:
        await self._delete(f"/v1/domains/{domain_id}")

    async def list_domains(
        self, *, page: int = 1, per_page: int = 25
    ) -> PaginatedResponse[Domain]:
        data = await self._get(
            "/v1/domains", params={"page": page, "per_page": per_page}
        )
        pagination = data["pagination"]
        return PaginatedResponse(
            data=[from_dict(Domain, d) for d in data["data"]],
            page=pagination["page"],
            per_page=pagination["per_page"],
            total=pagination["total"],
            total_pages=pagination["total_pages"],
        )

    async def set_tracking_domain(
        self, domain_id: str, tracking_domain: str
    ) -> dict[str, Any]:
        data = await self._put(
            f"/v1/domains/{domain_id}/tracking-domain",
            {"tracking_domain": tracking_domain},
        )
        return _unwrap(data)

    async def verify_tracking_domain(self, domain_id: str) -> dict[str, Any]:
        data = await self._post(f"/v1/domains/{domain_id}/verify-tracking", {})
        return _unwrap(data)

    async def remove_tracking_domain(self, domain_id: str) -> Domain:
        response = await self._client.delete(
            f"/v1/domains/{domain_id}/tracking-domain"
        )
        result = self._handle_response(response)
        return from_dict(Domain, result["data"])

    # ---- Webhook Methods ----

    async def create_webhook(
        self, *, url: str, events: list[str]
    ) -> Webhook:
        data = await self._post("/v1/webhooks", {"url": url, "events": events})
        return from_dict(Webhook, _unwrap(data))

    async def get_webhook(self, webhook_id: str) -> Webhook:
        data = await self._get(f"/v1/webhooks/{webhook_id}")
        return from_dict(Webhook, _unwrap(data))

    async def update_webhook(
        self,
        webhook_id: str,
        *,
        url: str,
        events: list[str],
        is_active: bool,
    ) -> Webhook:
        payload = {"url": url, "events": events, "is_active": is_active}
        data = await self._put(f"/v1/webhooks/{webhook_id}", payload)
        return from_dict(Webhook, _unwrap(data))

    async def test_webhook(self, webhook_id: str) -> WebhookTestResponse:
        data = await self._post(f"/v1/webhooks/{webhook_id}/test", {})
        return from_dict(WebhookTestResponse, _unwrap(data))

    async def delete_webhook(self, webhook_id: str) -> None:
        await self._delete(f"/v1/webhooks/{webhook_id}")

    async def list_webhooks(
        self, *, page: int = 1, per_page: int = 25
    ) -> PaginatedResponse[Webhook]:
        data = await self._get(
            "/v1/webhooks", params={"page": page, "per_page": per_page}
        )
        pagination = data["pagination"]
        return PaginatedResponse(
            data=[from_dict(Webhook, w) for w in data["data"]],
            page=pagination["page"],
            per_page=pagination["per_page"],
            total=pagination["total"],
            total_pages=pagination["total_pages"],
        )

    # ---- Suppression Methods ----

    async def add_suppression(
        self, email: str, reason: str = "manual"
    ) -> Suppression:
        data = await self._post(
            "/v1/suppressions", {"email_address": email, "reason": reason}
        )
        return from_dict(Suppression, _unwrap(data))

    async def delete_suppression(self, email: str) -> None:
        await self._delete(f"/v1/suppressions/{quote(email, safe='')}")

    async def list_suppressions(
        self, *, page: int = 1, per_page: int = 25
    ) -> PaginatedResponse[Suppression]:
        data = await self._get(
            "/v1/suppressions", params={"page": page, "per_page": per_page}
        )
        pagination = data["pagination"]
        return PaginatedResponse(
            data=[from_dict(Suppression, s) for s in data["data"]],
            page=pagination["page"],
            per_page=pagination["per_page"],
            total=pagination["total"],
            total_pages=pagination["total_pages"],
        )

    async def import_suppressions(
        self, emails: list[str], *, reason: Optional[str] = None
    ) -> ImportSuppressionsResult:
        """Bulk-import up to 10,000 addresses in one call."""
        payload: dict[str, Any] = {"emails": emails}
        if reason is not None:
            payload["reason"] = reason
        data = _unwrap(await self._post("/v1/suppressions/import", payload))
        return from_dict(ImportSuppressionsResult, data)

    async def export_suppressions(self) -> str:
        """Export the full suppression list as CSV."""
        return await self._get_raw("/v1/suppressions/export")

    # ---- Contact List Methods ----

    async def create_contact_list(
        self,
        *,
        name: str,
        description: Optional[str] = None,
        double_opt_in: bool = False,
    ) -> ContactList:
        payload: dict[str, Any] = {"name": name, "double_opt_in": double_opt_in}
        if description is not None:
            payload["description"] = description
        data = await self._post("/v1/contact-lists", payload)
        return from_dict(ContactList, _unwrap(data))

    async def list_contact_lists(self) -> list[ContactList]:
        data = await self._get("/v1/contact-lists")
        return [from_dict(ContactList, cl) for cl in data["data"]]

    async def get_contact_list(self, list_id: str) -> ContactList:
        data = await self._get(f"/v1/contact-lists/{list_id}")
        return from_dict(ContactList, _unwrap(data))

    async def update_contact_list(
        self,
        list_id: str,
        *,
        name: str,
        double_opt_in: bool,
        description: Optional[str] = None,
    ) -> ContactList:
        payload: dict[str, Any] = {"name": name, "double_opt_in": double_opt_in}
        if description is not None:
            payload["description"] = description
        data = await self._put(f"/v1/contact-lists/{list_id}", payload)
        return from_dict(ContactList, _unwrap(data))

    async def delete_contact_list(self, list_id: str) -> None:
        await self._delete(f"/v1/contact-lists/{list_id}")

    async def add_contact(
        self,
        list_id: str,
        *,
        email: str,
        metadata: Optional[dict[str, str]] = None,
    ) -> Contact:
        payload: dict[str, Any] = {"email": email}
        if metadata is not None:
            payload["metadata"] = metadata
        data = await self._post(f"/v1/contact-lists/{list_id}/contacts", payload)
        return from_dict(Contact, _unwrap(data))

    async def bulk_add_contacts(
        self,
        list_id: str,
        *,
        contacts: list[dict[str, Any]],
    ) -> BulkAddContactsResponse:
        data = await self._post(
            f"/v1/contact-lists/{list_id}/contacts", {"contacts": contacts}
        )
        return from_dict(BulkAddContactsResponse, _unwrap(data))

    async def list_contacts(
        self,
        list_id: str,
        *,
        page: int = 1,
        per_page: int = 25,
        status: Optional[str] = None,
    ) -> PaginatedResponse[Contact]:
        params: dict[str, Any] = {"page": page, "per_page": per_page}
        if status:
            params["status"] = status
        data = await self._get(
            f"/v1/contact-lists/{list_id}/contacts", params=params
        )
        pagination = data["pagination"]
        return PaginatedResponse(
            data=[from_dict(Contact, c) for c in data["data"]],
            page=pagination["page"],
            per_page=pagination["per_page"],
            total=pagination["total"],
            total_pages=pagination["total_pages"],
        )

    async def remove_contact(self, list_id: str, email: str) -> None:
        await self._delete(
            f"/v1/contact-lists/{list_id}/contacts/{quote(email, safe='')}"
        )

    # ---- Analytics Methods ----

    async def get_analytics_overview(
        self,
        *,
        period: Optional[str] = None,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
    ) -> AnalyticsSummary:
        params = _analytics_params(period, from_date, to_date)
        data = await self._get("/v1/analytics/overview", params=params or None)
        return from_dict(AnalyticsSummary, _unwrap(data))

    async def get_analytics_timeseries(
        self,
        *,
        period: Optional[str] = None,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        metrics: Optional[list[str]] = None,
    ) -> list[TimeseriesPoint]:
        params = _analytics_params(period, from_date, to_date)
        if metrics:
            params["metrics"] = ",".join(metrics)
        data = await self._get("/v1/analytics/timeseries", params=params or None)
        return [from_dict(TimeseriesPoint, p) for p in data]

    async def get_analytics_domains(
        self,
        *,
        period: Optional[str] = None,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> list[DomainAnalytics]:
        params = _analytics_params(period, from_date, to_date)
        if limit is not None:
            params["limit"] = limit
        data = await self._get("/v1/analytics/domains", params=params or None)
        return [from_dict(DomainAnalytics, d) for d in data]

    async def export_analytics_csv(
        self,
        *,
        period: Optional[str] = None,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
    ) -> str:
        params = _analytics_params(period, from_date, to_date)
        return await self._get_raw("/v1/analytics/export", params=params or None)

    # ---- Audit Log Methods ----

    async def list_audit_logs(
        self, *, page: int = 1, per_page: int = 25
    ) -> PaginatedResponse[AuditLog]:
        data = await self._get(
            "/v1/audit-logs", params={"page": page, "per_page": per_page}
        )
        pagination = data["pagination"]
        return PaginatedResponse(
            data=[from_dict(AuditLog, a) for a in data["data"]],
            page=pagination["page"],
            per_page=pagination["per_page"],
            total=pagination["total"],
            total_pages=pagination["total_pages"],
        )

    # ---- Dead Letter Methods ----

    async def list_dead_letters(self, *, count: int = 50) -> list[DeadLetter]:
        data = await self._get("/v1/dead-letters", params={"count": count})
        return [from_dict(DeadLetter, d) for d in data]

    async def retry_dead_letter(self, dead_letter_id: str) -> None:
        await self._post(f"/v1/dead-letters/{dead_letter_id}/retry", {})

    async def delete_dead_letter(self, dead_letter_id: str) -> None:
        await self._delete(f"/v1/dead-letters/{dead_letter_id}")

    # ---- Inbound Email Methods ----

    async def list_inbound_emails(
        self, *, page: int = 1, per_page: int = 25
    ) -> PaginatedResponse[InboundEmail]:
        data = await self._get(
            "/v1/inbound", params={"page": page, "per_page": per_page}
        )
        pagination = data["pagination"]
        return PaginatedResponse(
            data=[from_dict(InboundEmail, e) for e in data["data"]],
            page=pagination["page"],
            per_page=pagination["per_page"],
            total=pagination["total"],
            total_pages=pagination["total_pages"],
        )

    async def get_inbound_email(self, inbound_id: str) -> InboundEmail:
        data = await self._get(f"/v1/inbound/{inbound_id}")
        return from_dict(InboundEmail, _unwrap(data))

    async def delete_inbound_email(self, inbound_id: str) -> None:
        await self._delete(f"/v1/inbound/{inbound_id}")

    # ---- Inbound Route Methods ----

    async def create_inbound_route(
        self,
        *,
        domain_id: str,
        pattern: str,
        match_type: str,
        priority: Optional[int] = None,
        webhook_url: Optional[str] = None,
    ) -> InboundRoute:
        payload: dict[str, Any] = {
            "domain_id": domain_id,
            "pattern": pattern,
            "match_type": match_type,
        }
        if priority is not None:
            payload["priority"] = priority
        if webhook_url is not None:
            payload["webhook_url"] = webhook_url
        data = await self._post("/v1/inbound-routes", payload)
        return from_dict(InboundRoute, _unwrap(data))

    async def list_inbound_routes(
        self, *, page: int = 1, per_page: int = 25
    ) -> PaginatedResponse[InboundRoute]:
        data = await self._get(
            "/v1/inbound-routes", params={"page": page, "per_page": per_page}
        )
        pagination = data["pagination"]
        return PaginatedResponse(
            data=[from_dict(InboundRoute, r) for r in data["data"]],
            page=pagination["page"],
            per_page=pagination["per_page"],
            total=pagination["total"],
            total_pages=pagination["total_pages"],
        )

    async def get_inbound_route(self, route_id: str) -> InboundRoute:
        data = await self._get(f"/v1/inbound-routes/{route_id}")
        return from_dict(InboundRoute, _unwrap(data))

    async def update_inbound_route(self, route_id: str, **kwargs: Any) -> InboundRoute:
        data = await self._put(f"/v1/inbound-routes/{route_id}", kwargs)
        return from_dict(InboundRoute, _unwrap(data))

    async def delete_inbound_route(self, route_id: str) -> None:
        await self._delete(f"/v1/inbound-routes/{route_id}")

    # ---- Sub-Account Methods ----

    async def create_sub_account(
        self,
        *,
        name: str,
        email: str,
        password: str,
        monthly_quota: int,
    ) -> SubAccount:
        payload = {
            "name": name,
            "email": email,
            "password": password,
            "monthly_quota": monthly_quota,
        }
        data = await self._post("/v1/accounts", payload)
        return from_dict(SubAccount, data["data"])

    async def list_sub_accounts(
        self, *, page: int = 1, per_page: int = 25
    ) -> PaginatedResponse[SubAccount]:
        data = await self._get(
            "/v1/accounts", params={"page": page, "per_page": per_page}
        )
        pagination = data["pagination"]
        return PaginatedResponse(
            data=[from_dict(SubAccount, s) for s in data["data"]],
            page=pagination["page"],
            per_page=pagination["per_page"],
            total=pagination["total"],
            total_pages=pagination["total_pages"],
        )

    async def get_sub_account(self, sub_account_id: str) -> SubAccount:
        data = await self._get(f"/v1/accounts/{sub_account_id}")
        return from_dict(SubAccount, data["data"])

    async def update_sub_account(
        self,
        sub_account_id: str,
        *,
        name: Optional[str] = None,
        monthly_quota: Optional[int] = None,
        is_active: Optional[bool] = None,
    ) -> SubAccount:
        payload: dict[str, Any] = {}
        if name is not None:
            payload["name"] = name
        if monthly_quota is not None:
            payload["monthly_quota"] = monthly_quota
        if is_active is not None:
            payload["is_active"] = is_active
        data = await self._patch(f"/v1/accounts/{sub_account_id}", payload)
        return from_dict(SubAccount, data["data"])

    async def delete_sub_account(self, sub_account_id: str) -> None:
        await self._delete(f"/v1/accounts/{sub_account_id}")

    async def get_sub_account_analytics(
        self,
        sub_account_id: str,
        *,
        period: Optional[str] = None,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
    ) -> AnalyticsSummary:
        params = _analytics_params(period, from_date, to_date)
        data = await self._get(
            f"/v1/accounts/{sub_account_id}/analytics", params=params or None
        )
        return from_dict(AnalyticsSummary, _unwrap(data))

    async def get_aggregate_analytics(
        self,
        *,
        period: Optional[str] = None,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
    ) -> AnalyticsSummary:
        params = _analytics_params(period, from_date, to_date)
        data = await self._get("/v1/analytics/aggregate", params=params or None)
        return from_dict(AnalyticsSummary, _unwrap(data))

    # ---- API Key Methods ----

    async def create_api_key(
        self, *, name: str, scopes: Optional[list[str]] = None
    ) -> ApiKeyCreated:
        payload: dict[str, Any] = {"name": name}
        if scopes is not None:
            payload["scopes"] = scopes
        data = await self._post("/v1/api-keys", payload)
        return from_dict(ApiKeyCreated, data["data"])

    async def list_api_keys(self) -> list[ApiKey]:
        data = await self._get("/v1/api-keys")
        return [from_dict(ApiKey, k) for k in data["data"]]

    async def delete_api_key(self, api_key_id: str) -> None:
        await self._delete(f"/v1/api-keys/{api_key_id}")

    async def create_sub_account_api_key(
        self, sub_account_id: str, *, name: str, scopes: Optional[list[str]] = None
    ) -> ApiKeyCreated:
        payload: dict[str, Any] = {"name": name}
        if scopes is not None:
            payload["scopes"] = scopes
        data = await self._post(
            f"/v1/accounts/{sub_account_id}/api-keys", payload
        )
        return from_dict(ApiKeyCreated, data["data"])

    # ---- Newsletter Methods ----

    async def create_newsletter(
        self,
        *,
        list_id: str,
        subject: str,
        from_address: str,
        html_body: Optional[str] = None,
        text_body: Optional[str] = None,
        template_id: Optional[str] = None,
        template_data: Optional[dict[str, Any]] = None,
        reply_to: Optional[str] = None,
    ) -> Newsletter:
        payload: dict[str, Any] = {
            "list_id": list_id,
            "subject": subject,
            "from_address": from_address,
        }
        if html_body is not None:
            payload["html_body"] = html_body
        if text_body is not None:
            payload["text_body"] = text_body
        if template_id is not None:
            payload["template_id"] = template_id
        if template_data is not None:
            payload["template_data"] = template_data
        if reply_to is not None:
            payload["reply_to"] = reply_to
        data = await self._post("/v1/newsletters", payload)
        return from_dict(Newsletter, data["data"])

    async def list_newsletters(
        self, *, limit: int = 20, offset: int = 0
    ) -> list[Newsletter]:
        data = await self._get(
            "/v1/newsletters", params={"limit": limit, "offset": offset}
        )
        return [from_dict(Newsletter, n) for n in data["data"]]

    async def get_newsletter(self, newsletter_id: str) -> Newsletter:
        data = await self._get(f"/v1/newsletters/{newsletter_id}")
        return from_dict(Newsletter, data["data"])

    async def update_newsletter(
        self, newsletter_id: str, **kwargs: Any
    ) -> Newsletter:
        data = await self._put(f"/v1/newsletters/{newsletter_id}", kwargs)
        return from_dict(Newsletter, data["data"])

    async def delete_newsletter(self, newsletter_id: str) -> None:
        await self._delete(f"/v1/newsletters/{newsletter_id}")

    async def send_newsletter(self, newsletter_id: str) -> NewsletterSendResponse:
        data = await self._post(f"/v1/newsletters/{newsletter_id}/send", {})
        return from_dict(NewsletterSendResponse, data["data"])

    # ---- Email Validation Methods ----

    async def validate_email(self, email: str) -> EmailValidation:
        data = await self._post("/v1/validate", {"email": email})
        return from_dict(EmailValidation, (data["data"] if "data" in data else data))

    # ---- Operation Methods ----

    async def list_operations(
        self, *, page: int = 1, per_page: int = 25
    ) -> PaginatedResponse[Operation]:
        data = await self._get(
            "/v1/operations", params={"page": page, "per_page": per_page}
        )
        pagination = data["pagination"]
        return PaginatedResponse(
            data=[from_dict(Operation, o) for o in data["data"]],
            page=pagination["page"],
            per_page=pagination["per_page"],
            total=pagination["total"],
            total_pages=pagination["total_pages"],
        )

    async def get_operation(self, operation_id: str) -> Operation:
        data = await self._get(f"/v1/operations/{operation_id}")
        return from_dict(Operation, data["data"])

    # ---- Billing Methods ----

    async def list_plans(self) -> list[BillingPlan]:
        data = await self._get("/v1/billing/plans")
        return [from_dict(BillingPlan, p) for p in data["data"]]

    async def get_subscription(self) -> Subscription:
        data = await self._get("/v1/billing/subscription")
        return from_dict(Subscription, data["data"])

    async def create_checkout(
        self, *, plan: str, success_url: str, cancel_url: str
    ) -> str:
        """Returns the Stripe checkout URL."""
        data = await self._post(
            "/v1/billing/checkout",
            {"plan": plan, "success_url": success_url, "cancel_url": cancel_url},
        )
        return data["data"]["checkout_url"]

    async def create_billing_portal(self, *, return_url: str) -> str:
        """Returns the Stripe billing portal URL."""
        data = await self._post("/v1/billing/portal", {"return_url": return_url})
        return data["data"]["portal_url"]

    # ---- Signup Form Methods ----

    async def create_signup_form(self, params: CreateSignupFormParams) -> SignupForm:
        data = await self._post("/v1/signup-forms", params.to_dict())
        return from_dict(SignupForm, data["data"])

    async def list_signup_forms(self) -> list[SignupForm]:
        data = await self._get("/v1/signup-forms")
        return [from_dict(SignupForm, f) for f in data["data"]]

    async def get_signup_form(self, form_id: str) -> SignupForm:
        data = await self._get(f"/v1/signup-forms/{form_id}")
        return from_dict(SignupForm, data["data"])

    async def update_signup_form(
        self, form_id: str, params: UpdateSignupFormParams
    ) -> SignupForm:
        data = await self._put(f"/v1/signup-forms/{form_id}", params.to_dict())
        return from_dict(SignupForm, data["data"])

    async def delete_signup_form(self, form_id: str) -> None:
        await self._delete(f"/v1/signup-forms/{form_id}")

    async def toggle_signup_form(self, form_id: str) -> SignupForm:
        data = await self._post(f"/v1/signup-forms/{form_id}/toggle", {})
        return from_dict(SignupForm, data["data"])

    # ---- Insights Methods ----

    async def generate_insights(self) -> InsightReport:
        """Trigger an AI-powered operational insights report for this account."""
        data = await self._post("/v1/insights/generate", {})
        return from_dict(InsightReport, data)

    # ---- Agent Mailbox Methods ----

    async def create_mailbox(
        self,
        *,
        display_name: Optional[str] = None,
        local_part: Optional[str] = None,
        domain_id: Optional[str] = None,
    ) -> AgentMailbox:
        payload: dict[str, Any] = {}
        if display_name is not None:
            payload["display_name"] = display_name
        if local_part is not None:
            payload["local_part"] = local_part
        if domain_id is not None:
            payload["domain_id"] = domain_id
        data = await self._post("/v1/agent-mailboxes", payload)
        return from_dict(AgentMailbox, data["data"])

    async def list_mailboxes(
        self, *, limit: Optional[int] = None, offset: Optional[int] = None
    ) -> list[AgentMailbox]:
        params: dict[str, Any] = {}
        if limit is not None:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset
        data = await self._get("/v1/agent-mailboxes", params=params or None)
        return [from_dict(AgentMailbox, m) for m in data["data"]]

    async def get_mailbox(self, id: str) -> AgentMailbox:
        data = await self._get(f"/v1/agent-mailboxes/{id}")
        return from_dict(AgentMailbox, data["data"])

    async def delete_mailbox(self, id: str) -> None:
        await self._delete(f"/v1/agent-mailboxes/{id}")

    async def list_messages(
        self,
        mailbox_id: str,
        *,
        status: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> list[MailboxMessage]:
        params: dict[str, Any] = {}
        if status is not None:
            params["status"] = status
        if limit is not None:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset
        data = await self._get(
            f"/v1/agent-mailboxes/{mailbox_id}/messages",
            params=params or None,
        )
        return [from_dict(MailboxMessage, m) for m in data["data"]]

    async def wait_for_next_message(
        self, mailbox_id: str, *, timeout: Optional[int] = None
    ) -> Optional[LeasedMessage]:
        """Long-poll for the next unread message.

        Returns ``None`` when the server returns HTTP 408 (no message became
        available before the server-side poll timeout elapsed). Note that the
        HTTP client timeout should exceed ``timeout`` seconds, otherwise the
        underlying httpx call will raise before the server responds.
        """
        params: dict[str, Any] = {}
        if timeout is not None:
            params["timeout"] = timeout
        response = await self._client.get(
            f"/v1/agent-mailboxes/{mailbox_id}/messages/next",
            params=params or None,
        )
        if response.status_code == 408:
            return None
        data = self._handle_response(response)
        return from_dict(LeasedMessage, data)

    async def delete_message(self, mailbox_id: str, message_id: str) -> None:
        await self._delete(f"/v1/agent-mailboxes/{mailbox_id}/messages/{message_id}")

    async def ack_message(
        self, mailbox_id: str, message_id: str, lease_token: str
    ) -> None:
        await self._post(
            f"/v1/agent-mailboxes/{mailbox_id}/messages/{message_id}/ack",
            {"lease_token": lease_token},
        )

    async def nack_message(
        self, mailbox_id: str, message_id: str, lease_token: str
    ) -> None:
        await self._post(
            f"/v1/agent-mailboxes/{mailbox_id}/messages/{message_id}/nack",
            {"lease_token": lease_token},
        )

    async def reply_to_message(
        self,
        mailbox_id: str,
        message_id: str,
        *,
        text_body: Optional[str] = None,
        html_body: Optional[str] = None,
    ) -> MailboxReplyResult:
        payload: dict[str, Any] = {}
        if text_body is not None:
            payload["text_body"] = text_body
        if html_body is not None:
            payload["html_body"] = html_body
        data = await self._post(
            f"/v1/agent-mailboxes/{mailbox_id}/messages/{message_id}/reply",
            payload,
        )
        return from_dict(MailboxReplyResult, data["data"])

    async def list_mailbox_threads(
        self,
        mailbox_id: str,
        *,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> list[MailboxMessage]:
        params: dict[str, Any] = {}
        if limit is not None:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset
        data = await self._get(
            f"/v1/agent-mailboxes/{mailbox_id}/threads",
            params=params or None,
        )
        return [from_dict(MailboxMessage, m) for m in data["data"]]

    async def get_mailbox_thread(
        self,
        mailbox_id: str,
        thread_id: str,
        *,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> list[MailboxMessage]:
        params: dict[str, Any] = {}
        if limit is not None:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset
        data = await self._get(
            f"/v1/agent-mailboxes/{mailbox_id}/threads/{thread_id}",
            params=params or None,
        )
        return [from_dict(MailboxMessage, m) for m in data["data"]]

    async def search_mailbox_messages(
        self,
        mailbox_id: str,
        query: str,
        *,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> list[MailboxMessage]:
        params: dict[str, Any] = {"q": query}
        if limit is not None:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset
        data = await self._get(
            f"/v1/agent-mailboxes/{mailbox_id}/messages/search",
            params=params,
        )
        return [from_dict(MailboxMessage, m) for m in data["data"]]

    async def update_message_labels(
        self, mailbox_id: str, message_id: str, labels: list[str]
    ) -> list[str]:
        data = await self._put(
            f"/v1/agent-mailboxes/{mailbox_id}/messages/{message_id}/labels",
            {"labels": labels},
        )
        return data["data"]["labels"]

    async def get_message_attachment_urls(
        self, mailbox_id: str, message_id: str
    ) -> list[MailboxAttachmentUrl]:
        data = await self._get(
            f"/v1/agent-mailboxes/{mailbox_id}/messages/{message_id}/attachments"
        )
        return data["data"]

    async def list_mailbox_contacts(
        self,
        mailbox_id: str,
        *,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> list[MailboxContact]:
        params: dict[str, Any] = {}
        if limit is not None:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset
        data = await self._get(
            f"/v1/agent-mailboxes/{mailbox_id}/contacts",
            params=params or None,
        )
        return [from_dict(MailboxContact, c) for c in data["data"]]

    async def get_mailbox_analytics(self, mailbox_id: str) -> MailboxAnalytics:
        data = await self._get(f"/v1/agent-mailboxes/{mailbox_id}/analytics")
        return from_dict(MailboxAnalytics, data["data"])

    async def update_auto_responder(
        self,
        mailbox_id: str,
        *,
        enabled: Optional[bool] = None,
        rules: Optional[Any] = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {}
        if enabled is not None:
            payload["enabled"] = enabled
        if rules is not None:
            payload["rules"] = rules
        data = await self._patch(
            f"/v1/agent-mailboxes/{mailbox_id}/auto-responder",
            payload,
        )
        return data["data"]

    # ---- GDPR Methods ----

    async def gdpr_export(self, email: str) -> dict[str, Any]:
        """Export all data for an email address (GDPR)."""
        return await self._get("/v1/gdpr/export", params={"email": email})

    async def gdpr_erase(self, email: str) -> GdprEraseResult:
        """Erase all data for an email address (GDPR)."""
        response = await self._client.request(
            "DELETE", "/v1/gdpr/erase", params={"email": email}
        )
        data = self._handle_response(response)
        return from_dict(GdprEraseResult, data["data"])

    # ---- HTTP Helpers ----

    async def _get(self, path: str, params: Optional[dict[str, Any]] = None) -> Any:
        response = await self._client.get(path, params=params)
        return self._handle_response(response)

    async def _get_raw(
        self, path: str, params: Optional[dict[str, Any]] = None
    ) -> str:
        response = await self._client.get(path, params=params)
        if response.status_code >= 400:
            try:
                body = response.json()
            except Exception:
                body = {"code": "unknown", "message": response.text}
            raise EuroMailError.from_response(response.status_code, body, headers=response.headers)
        return response.text

    async def _post(self, path: str, json: Any) -> Any:
        response = await self._client.post(path, json=json)
        return self._handle_response(response)

    async def _put(self, path: str, json: Any) -> Any:
        response = await self._client.put(path, json=json)
        return self._handle_response(response)

    async def _patch(self, path: str, json: Any) -> Any:
        response = await self._client.patch(path, json=json)
        return self._handle_response(response)

    async def _delete(self, path: str) -> None:
        response = await self._client.delete(path)
        self._handle_response(response)

    def _handle_response(self, response: httpx.Response) -> Any:
        if response.status_code >= 400:
            try:
                body = response.json()
            except Exception:
                body = {"code": "unknown", "message": response.text}
            raise EuroMailError.from_response(response.status_code, body, headers=response.headers)

        if response.status_code == 204:
            return None

        return response.json()


def _analytics_params(
    period: Optional[str],
    from_date: Optional[str],
    to_date: Optional[str],
) -> dict[str, Any]:
    params: dict[str, Any] = {}
    if period:
        params["period"] = period
    if from_date:
        params["from"] = from_date
    if to_date:
        params["to"] = to_date
    return params


def _unwrap(data: dict[str, Any]) -> dict[str, Any]:
    """Unwrap the `data` envelope if present."""
    if isinstance(data, dict) and "data" in data and len(data) <= 2:
        inner = data["data"]
        if isinstance(inner, dict):
            return inner
    return data
