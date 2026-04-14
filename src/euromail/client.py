"""Synchronous EuroMail client."""

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
    AuditLog,
    BatchError,
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
    DnsRecord,
    VerificationCheck,
    Email,
    EmailValidation,
    GdprEraseResult,
    GdprExport,
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
    SubscriptionLimits,
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
    InsightFinding,
    AgentMailbox,
    MailboxMessage,
    LeasedMessage,
)

DEFAULT_BASE_URL = "https://api.euromail.dev"
DEFAULT_TIMEOUT = 30.0


class EuroMail:
    """Synchronous client for the EuroMail API."""

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
        self._client = httpx.Client(
            base_url=self._base_url,
            headers={
                "Authorization": f"Bearer {resolved_key}",
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
            timeout=timeout,
        )

    def __enter__(self) -> "EuroMail":
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

    def close(self) -> None:
        self._client.close()

    # ---- Account Methods ----

    def get_account(self) -> Account:
        data = self._get("/v1/account")
        return Account(**data["data"])

    def export_account(self) -> str:
        return self._get_raw("/v1/account/export")

    def delete_account(self) -> None:
        self._delete("/v1/account")

    # ---- Email Methods ----

    def send_email(
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
        )
        data = self._post("/v1/emails", params.to_dict())
        return SendEmailResponse(**data["data"])

    def send_batch(self, *, emails: list[SendEmailParams]) -> BatchResponse:
        payload = {"emails": [e.to_dict() for e in emails]}
        data = self._post("/v1/emails/batch", payload)
        return BatchResponse(
            data=[SendEmailResponse(**e) for e in data["data"]],
            errors=[BatchError(**e) for e in data.get("errors", [])],
        )

    def get_email(self, email_id: str) -> Email:
        data = self._get(f"/v1/emails/{email_id}")
        inner = data.get("data", data)
        email_data = inner.get("email", inner)
        return _parse_email(email_data)

    def list_emails(
        self,
        *,
        page: int = 1,
        per_page: int = 25,
        status: Optional[str] = None,
    ) -> PaginatedResponse[Email]:
        params: dict[str, Any] = {"page": page, "per_page": per_page}
        if status:
            params["status"] = status
        data = self._get("/v1/emails", params=params)
        pagination = data["pagination"]
        return PaginatedResponse(
            data=[_parse_email(e) for e in data["data"]],
            page=pagination["page"],
            per_page=pagination["per_page"],
            total=pagination["total"],
            total_pages=pagination["total_pages"],
        )

    def cancel_scheduled_email(self, email_id: str) -> SendEmailResponse:
        data = self._post(f"/v1/emails/{email_id}/cancel", {})
        return SendEmailResponse(**data["data"])

    def get_email_links(self, email_id: str) -> list[LinkClickStat]:
        """Return per-link click stats for a sent email."""
        data = self._get(f"/v1/emails/{quote(email_id)}/links")
        return [LinkClickStat(**item) for item in data["data"]]

    def send_broadcast(
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
        data = self._post("/v1/emails/broadcast", payload)
        return BroadcastResponse(**data["data"])

    # ---- Template Methods ----

    def create_template(
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
        data = self._post("/v1/templates", payload)
        return Template(**_unwrap(data))

    def get_template(self, template_id: str) -> Template:
        data = self._get(f"/v1/templates/{template_id}")
        return Template(**_unwrap(data))

    def update_template(self, template_id: str, **kwargs: Any) -> Template:
        data = self._put(f"/v1/templates/{template_id}", kwargs)
        return Template(**_unwrap(data))

    def delete_template(self, template_id: str) -> None:
        self._delete(f"/v1/templates/{template_id}")

    def list_templates(
        self, *, page: int = 1, per_page: int = 25
    ) -> PaginatedResponse[Template]:
        data = self._get("/v1/templates", params={"page": page, "per_page": per_page})
        pagination = data["pagination"]
        return PaginatedResponse(
            data=[Template(**t) for t in data["data"]],
            page=pagination["page"],
            per_page=pagination["per_page"],
            total=pagination["total"],
            total_pages=pagination["total_pages"],
        )

    # ---- Domain Methods ----

    def add_domain(self, domain: str) -> Domain:
        data = self._post("/v1/domains", {"domain": domain})
        return _parse_domain(data["data"])

    def get_domain(self, domain_id: str) -> Domain:
        data = self._get(f"/v1/domains/{domain_id}")
        return _parse_domain(data["data"])

    def verify_domain(self, domain_id: str) -> DomainVerificationResult:
        data = self._post(f"/v1/domains/{domain_id}/verify", {})
        inner = _unwrap(data)
        return DomainVerificationResult(
            domain=_parse_domain(inner["domain"]),
            checks={
                k: VerificationCheck(**v)
                for k, v in inner.get("checks", {}).items()
            },
        )

    def delete_domain(self, domain_id: str) -> None:
        self._delete(f"/v1/domains/{domain_id}")

    def list_domains(
        self, *, page: int = 1, per_page: int = 25
    ) -> PaginatedResponse[Domain]:
        data = self._get("/v1/domains", params={"page": page, "per_page": per_page})
        pagination = data["pagination"]
        return PaginatedResponse(
            data=[_parse_domain(d) for d in data["data"]],
            page=pagination["page"],
            per_page=pagination["per_page"],
            total=pagination["total"],
            total_pages=pagination["total_pages"],
        )

    def set_tracking_domain(
        self, domain_id: str, tracking_domain: str
    ) -> dict[str, Any]:
        data = self._put(
            f"/v1/domains/{domain_id}/tracking-domain",
            {"tracking_domain": tracking_domain},
        )
        return _unwrap(data)

    def verify_tracking_domain(self, domain_id: str) -> dict[str, Any]:
        data = self._post(f"/v1/domains/{domain_id}/verify-tracking", {})
        return _unwrap(data)

    def remove_tracking_domain(self, domain_id: str) -> Domain:
        data = self._client.delete(f"/v1/domains/{domain_id}/tracking-domain")
        result = self._handle_response(data)
        return _parse_domain(result["data"])

    # ---- Webhook Methods ----

    def create_webhook(
        self, *, url: str, events: list[str]
    ) -> Webhook:
        data = self._post("/v1/webhooks", {"url": url, "events": events})
        return Webhook(**_unwrap(data))

    def get_webhook(self, webhook_id: str) -> Webhook:
        data = self._get(f"/v1/webhooks/{webhook_id}")
        return Webhook(**_unwrap(data))

    def update_webhook(
        self,
        webhook_id: str,
        *,
        url: str,
        events: list[str],
        is_active: bool,
    ) -> Webhook:
        payload = {"url": url, "events": events, "is_active": is_active}
        data = self._put(f"/v1/webhooks/{webhook_id}", payload)
        return Webhook(**_unwrap(data))

    def test_webhook(self, webhook_id: str) -> WebhookTestResponse:
        data = self._post(f"/v1/webhooks/{webhook_id}/test", {})
        return WebhookTestResponse(**_unwrap(data))

    def delete_webhook(self, webhook_id: str) -> None:
        self._delete(f"/v1/webhooks/{webhook_id}")

    def list_webhooks(
        self, *, page: int = 1, per_page: int = 25
    ) -> PaginatedResponse[Webhook]:
        data = self._get("/v1/webhooks", params={"page": page, "per_page": per_page})
        pagination = data["pagination"]
        return PaginatedResponse(
            data=[Webhook(**w) for w in data["data"]],
            page=pagination["page"],
            per_page=pagination["per_page"],
            total=pagination["total"],
            total_pages=pagination["total_pages"],
        )

    # ---- Suppression Methods ----

    def add_suppression(
        self, email: str, reason: str = "manual"
    ) -> Suppression:
        data = self._post(
            "/v1/suppressions", {"email_address": email, "reason": reason}
        )
        return Suppression(**_unwrap(data))

    def delete_suppression(self, email: str) -> None:
        self._delete(f"/v1/suppressions/{quote(email, safe='')}")

    def list_suppressions(
        self, *, page: int = 1, per_page: int = 25
    ) -> PaginatedResponse[Suppression]:
        data = self._get(
            "/v1/suppressions", params={"page": page, "per_page": per_page}
        )
        pagination = data["pagination"]
        return PaginatedResponse(
            data=[Suppression(**s) for s in data["data"]],
            page=pagination["page"],
            per_page=pagination["per_page"],
            total=pagination["total"],
            total_pages=pagination["total_pages"],
        )

    # ---- Contact List Methods ----

    def create_contact_list(
        self,
        *,
        name: str,
        description: Optional[str] = None,
        double_opt_in: bool = False,
    ) -> ContactList:
        payload: dict[str, Any] = {"name": name, "double_opt_in": double_opt_in}
        if description is not None:
            payload["description"] = description
        data = self._post("/v1/contact-lists", payload)
        return ContactList(**_unwrap(data))

    def list_contact_lists(self) -> list[ContactList]:
        data = self._get("/v1/contact-lists")
        return [ContactList(**cl) for cl in data["data"]]

    def get_contact_list(self, list_id: str) -> ContactList:
        data = self._get(f"/v1/contact-lists/{list_id}")
        return ContactList(**_unwrap(data))

    def update_contact_list(
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
        data = self._put(f"/v1/contact-lists/{list_id}", payload)
        return ContactList(**_unwrap(data))

    def delete_contact_list(self, list_id: str) -> None:
        self._delete(f"/v1/contact-lists/{list_id}")

    def add_contact(
        self,
        list_id: str,
        *,
        email: str,
        metadata: Optional[dict[str, str]] = None,
    ) -> Contact:
        payload: dict[str, Any] = {"email": email}
        if metadata is not None:
            payload["metadata"] = metadata
        data = self._post(f"/v1/contact-lists/{list_id}/contacts", payload)
        return Contact(**_unwrap(data))

    def bulk_add_contacts(
        self,
        list_id: str,
        *,
        contacts: list[dict[str, Any]],
    ) -> BulkAddContactsResponse:
        data = self._post(
            f"/v1/contact-lists/{list_id}/contacts", {"contacts": contacts}
        )
        return BulkAddContactsResponse(**_unwrap(data))

    def list_contacts(
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
        data = self._get(f"/v1/contact-lists/{list_id}/contacts", params=params)
        pagination = data["pagination"]
        return PaginatedResponse(
            data=[Contact(**c) for c in data["data"]],
            page=pagination["page"],
            per_page=pagination["per_page"],
            total=pagination["total"],
            total_pages=pagination["total_pages"],
        )

    def remove_contact(self, list_id: str, email: str) -> None:
        self._delete(
            f"/v1/contact-lists/{list_id}/contacts/{quote(email, safe='')}"
        )

    # ---- Sub-Account Methods ----

    def create_sub_account(
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
        data = self._post("/v1/accounts", payload)
        return SubAccount(**data["data"])

    def list_sub_accounts(
        self, *, page: int = 1, per_page: int = 25
    ) -> PaginatedResponse[SubAccount]:
        data = self._get("/v1/accounts", params={"page": page, "per_page": per_page})
        pagination = data["pagination"]
        return PaginatedResponse(
            data=[SubAccount(**s) for s in data["data"]],
            page=pagination["page"],
            per_page=pagination["per_page"],
            total=pagination["total"],
            total_pages=pagination["total_pages"],
        )

    def get_sub_account(self, sub_account_id: str) -> SubAccount:
        data = self._get(f"/v1/accounts/{sub_account_id}")
        return SubAccount(**data["data"])

    def update_sub_account(
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
        data = self._patch(f"/v1/accounts/{sub_account_id}", payload)
        return SubAccount(**data["data"])

    def delete_sub_account(self, sub_account_id: str) -> None:
        self._delete(f"/v1/accounts/{sub_account_id}")

    def get_sub_account_analytics(
        self,
        sub_account_id: str,
        *,
        period: Optional[str] = None,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
    ) -> AnalyticsSummary:
        params = _analytics_params(period, from_date, to_date)
        data = self._get(
            f"/v1/accounts/{sub_account_id}/analytics", params=params or None
        )
        return AnalyticsSummary(**_unwrap(data))

    def get_aggregate_analytics(
        self,
        *,
        period: Optional[str] = None,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
    ) -> AnalyticsSummary:
        params = _analytics_params(period, from_date, to_date)
        data = self._get("/v1/analytics/aggregate", params=params or None)
        return AnalyticsSummary(**_unwrap(data))

    # ---- Analytics Methods ----

    def get_analytics_overview(
        self,
        *,
        period: Optional[str] = None,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
    ) -> AnalyticsSummary:
        params = _analytics_params(period, from_date, to_date)
        data = self._get("/v1/analytics/overview", params=params or None)
        return AnalyticsSummary(**_unwrap(data))

    def get_analytics_timeseries(
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
        data = self._get("/v1/analytics/timeseries", params=params or None)
        items = data["data"] if isinstance(data, dict) and "data" in data else data
        return [TimeseriesPoint(**p) for p in items]

    def get_analytics_domains(
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
        data = self._get("/v1/analytics/domains", params=params or None)
        items = data["data"] if isinstance(data, dict) and "data" in data else data
        return [DomainAnalytics(**d) for d in items]

    def export_analytics_csv(
        self,
        *,
        period: Optional[str] = None,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
    ) -> str:
        params = _analytics_params(period, from_date, to_date)
        return self._get_raw("/v1/analytics/export", params=params or None)

    # ---- Audit Log Methods ----

    def list_audit_logs(
        self, *, page: int = 1, per_page: int = 25
    ) -> PaginatedResponse[AuditLog]:
        data = self._get(
            "/v1/audit-logs", params={"page": page, "per_page": per_page}
        )
        pagination = data["pagination"]
        return PaginatedResponse(
            data=[AuditLog(**a) for a in data["data"]],
            page=pagination["page"],
            per_page=pagination["per_page"],
            total=pagination["total"],
            total_pages=pagination["total_pages"],
        )

    # ---- Dead Letter Methods ----

    def list_dead_letters(self, *, count: int = 50) -> list[DeadLetter]:
        data = self._get("/v1/dead-letters", params={"count": count})
        items = data["data"] if isinstance(data, dict) and "data" in data else data
        return [DeadLetter(**d) for d in items]

    def retry_dead_letter(self, dead_letter_id: str) -> None:
        self._post(f"/v1/dead-letters/{dead_letter_id}/retry", {})

    def delete_dead_letter(self, dead_letter_id: str) -> None:
        self._delete(f"/v1/dead-letters/{dead_letter_id}")

    # ---- Inbound Email Methods ----

    def list_inbound_emails(
        self, *, page: int = 1, per_page: int = 25
    ) -> PaginatedResponse[InboundEmail]:
        data = self._get(
            "/v1/inbound", params={"page": page, "per_page": per_page}
        )
        pagination = data["pagination"]
        return PaginatedResponse(
            data=[InboundEmail(**e) for e in data["data"]],
            page=pagination["page"],
            per_page=pagination["per_page"],
            total=pagination["total"],
            total_pages=pagination["total_pages"],
        )

    def get_inbound_email(self, inbound_id: str) -> InboundEmail:
        data = self._get(f"/v1/inbound/{inbound_id}")
        return InboundEmail(**_unwrap(data))

    def delete_inbound_email(self, inbound_id: str) -> None:
        self._delete(f"/v1/inbound/{inbound_id}")

    # ---- Inbound Route Methods ----

    def create_inbound_route(
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
        data = self._post("/v1/inbound-routes", payload)
        return InboundRoute(**_unwrap(data))

    def list_inbound_routes(
        self, *, page: int = 1, per_page: int = 25
    ) -> PaginatedResponse[InboundRoute]:
        data = self._get(
            "/v1/inbound-routes", params={"page": page, "per_page": per_page}
        )
        pagination = data["pagination"]
        return PaginatedResponse(
            data=[InboundRoute(**r) for r in data["data"]],
            page=pagination["page"],
            per_page=pagination["per_page"],
            total=pagination["total"],
            total_pages=pagination["total_pages"],
        )

    def get_inbound_route(self, route_id: str) -> InboundRoute:
        data = self._get(f"/v1/inbound-routes/{route_id}")
        return InboundRoute(**_unwrap(data))

    def update_inbound_route(self, route_id: str, **kwargs: Any) -> InboundRoute:
        data = self._put(f"/v1/inbound-routes/{route_id}", kwargs)
        return InboundRoute(**_unwrap(data))

    def delete_inbound_route(self, route_id: str) -> None:
        self._delete(f"/v1/inbound-routes/{route_id}")

    # ---- API Key Methods ----

    def create_api_key(
        self, *, name: str, scopes: Optional[list[str]] = None
    ) -> ApiKeyCreated:
        payload: dict[str, Any] = {"name": name}
        if scopes is not None:
            payload["scopes"] = scopes
        data = self._post("/v1/api-keys", payload)
        return ApiKeyCreated(**data["data"])

    def list_api_keys(self) -> list[ApiKey]:
        data = self._get("/v1/api-keys")
        return [ApiKey(**k) for k in data["data"]]

    def delete_api_key(self, api_key_id: str) -> None:
        self._delete(f"/v1/api-keys/{api_key_id}")

    def create_sub_account_api_key(
        self, sub_account_id: str, *, name: str, scopes: Optional[list[str]] = None
    ) -> ApiKeyCreated:
        payload: dict[str, Any] = {"name": name}
        if scopes is not None:
            payload["scopes"] = scopes
        data = self._post(f"/v1/accounts/{sub_account_id}/api-keys", payload)
        return ApiKeyCreated(**data["data"])

    # ---- Newsletter Methods ----

    def create_newsletter(
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
        data = self._post("/v1/newsletters", payload)
        return Newsletter(**data["data"])

    def list_newsletters(
        self, *, limit: int = 20, offset: int = 0
    ) -> list[Newsletter]:
        data = self._get(
            "/v1/newsletters", params={"limit": limit, "offset": offset}
        )
        return [Newsletter(**n) for n in data["data"]]

    def get_newsletter(self, newsletter_id: str) -> Newsletter:
        data = self._get(f"/v1/newsletters/{newsletter_id}")
        return Newsletter(**data["data"])

    def update_newsletter(self, newsletter_id: str, **kwargs: Any) -> Newsletter:
        data = self._put(f"/v1/newsletters/{newsletter_id}", kwargs)
        return Newsletter(**data["data"])

    def delete_newsletter(self, newsletter_id: str) -> None:
        self._delete(f"/v1/newsletters/{newsletter_id}")

    def send_newsletter(self, newsletter_id: str) -> NewsletterSendResponse:
        data = self._post(f"/v1/newsletters/{newsletter_id}/send", {})
        return NewsletterSendResponse(**data["data"])

    # ---- Email Validation Methods ----

    def validate_email(self, email: str) -> EmailValidation:
        data = self._post("/v1/validate", {"email": email})
        return EmailValidation(**(data["data"] if "data" in data else data))

    # ---- Operation Methods ----

    def list_operations(
        self, *, page: int = 1, per_page: int = 25
    ) -> PaginatedResponse[Operation]:
        data = self._get(
            "/v1/operations", params={"page": page, "per_page": per_page}
        )
        pagination = data["pagination"]
        return PaginatedResponse(
            data=[Operation(**o) for o in data["data"]],
            page=pagination["page"],
            per_page=pagination["per_page"],
            total=pagination["total"],
            total_pages=pagination["total_pages"],
        )

    def get_operation(self, operation_id: str) -> Operation:
        data = self._get(f"/v1/operations/{operation_id}")
        return Operation(**data["data"])

    # ---- Billing Methods ----

    def list_plans(self) -> list[BillingPlan]:
        data = self._get("/v1/billing/plans")
        return [BillingPlan(**p) for p in data["data"]]

    def get_subscription(self) -> Subscription:
        data = self._get("/v1/billing/subscription")
        raw = data["data"]
        raw["limits"] = SubscriptionLimits(**raw["limits"])
        return Subscription(**raw)

    def create_checkout(
        self, *, plan: str, success_url: str, cancel_url: str
    ) -> str:
        """Returns the Stripe checkout URL."""
        data = self._post(
            "/v1/billing/checkout",
            {"plan": plan, "success_url": success_url, "cancel_url": cancel_url},
        )
        return data["data"]["checkout_url"]

    def create_billing_portal(self, *, return_url: str) -> str:
        """Returns the Stripe billing portal URL."""
        data = self._post("/v1/billing/portal", {"return_url": return_url})
        return data["data"]["portal_url"]

    # ---- Signup Form Methods ----

    def create_signup_form(self, params: CreateSignupFormParams) -> SignupForm:
        data = self._post("/v1/signup-forms", params.to_dict())
        return SignupForm(**data["data"])

    def list_signup_forms(self) -> list[SignupForm]:
        data = self._get("/v1/signup-forms")
        return [SignupForm(**f) for f in data["data"]]

    def get_signup_form(self, form_id: str) -> SignupForm:
        data = self._get(f"/v1/signup-forms/{form_id}")
        return SignupForm(**data["data"])

    def update_signup_form(
        self, form_id: str, params: UpdateSignupFormParams
    ) -> SignupForm:
        data = self._put(f"/v1/signup-forms/{form_id}", params.to_dict())
        return SignupForm(**data["data"])

    def delete_signup_form(self, form_id: str) -> None:
        self._delete(f"/v1/signup-forms/{form_id}")

    def toggle_signup_form(self, form_id: str) -> SignupForm:
        data = self._post(f"/v1/signup-forms/{form_id}/toggle", {})
        return SignupForm(**data["data"])

    # ---- Insights Methods ----

    def generate_insights(self) -> InsightReport:
        """Trigger an AI-powered operational insights report for this account."""
        data = self._post("/v1/insights/generate", {})
        findings = [InsightFinding(**f) for f in data.get("findings", [])]
        return InsightReport(
            id=data["id"],
            account_id=data.get("account_id"),
            generated_at=data["generated_at"],
            period_start=data["period_start"],
            period_end=data["period_end"],
            model=data["model"],
            summary=data["summary"],
            findings=findings,
            raw_markdown=data.get("raw_markdown"),
            acknowledged_at=data.get("acknowledged_at"),
            input_tokens=data.get("input_tokens"),
            output_tokens=data.get("output_tokens"),
        )

    # ---- Agent Mailbox Methods ----

    def create_mailbox(
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
        data = self._post("/v1/agent-mailboxes", payload)
        return AgentMailbox(**data["data"])

    def list_mailboxes(
        self, *, limit: Optional[int] = None, offset: Optional[int] = None
    ) -> list[AgentMailbox]:
        params: dict[str, Any] = {}
        if limit is not None:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset
        data = self._get("/v1/agent-mailboxes", params=params or None)
        return [AgentMailbox(**m) for m in data["data"]]

    def get_mailbox(self, id: str) -> AgentMailbox:
        data = self._get(f"/v1/agent-mailboxes/{id}")
        return AgentMailbox(**data["data"])

    def delete_mailbox(self, id: str) -> None:
        self._delete(f"/v1/agent-mailboxes/{id}")

    def list_messages(
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
        data = self._get(
            f"/v1/agent-mailboxes/{mailbox_id}/messages",
            params=params or None,
        )
        return [MailboxMessage(**m) for m in data["data"]]

    def wait_for_next_message(
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
        response = self._client.get(
            f"/v1/agent-mailboxes/{mailbox_id}/messages/next",
            params=params or None,
        )
        if response.status_code == 408:
            return None
        data = self._handle_response(response)
        return LeasedMessage(
            data=MailboxMessage(**data["data"]),
            lease_token=data["lease_token"],
            lease_expires_at=data["lease_expires_at"],
        )

    def delete_message(self, mailbox_id: str, message_id: str) -> None:
        self._delete(f"/v1/agent-mailboxes/{mailbox_id}/messages/{message_id}")

    def ack_message(
        self, mailbox_id: str, message_id: str, lease_token: str
    ) -> None:
        self._post(
            f"/v1/agent-mailboxes/{mailbox_id}/messages/{message_id}/ack",
            {"lease_token": lease_token},
        )

    def nack_message(
        self, mailbox_id: str, message_id: str, lease_token: str
    ) -> None:
        self._post(
            f"/v1/agent-mailboxes/{mailbox_id}/messages/{message_id}/nack",
            {"lease_token": lease_token},
        )

    # ---- GDPR Methods ----

    def gdpr_export(self, email: str) -> dict[str, Any]:
        """Export all data for an email address (GDPR)."""
        return self._get(f"/v1/gdpr/export", params={"email": email})

    def gdpr_erase(self, email: str) -> GdprEraseResult:
        """Erase all data for an email address (GDPR)."""
        response = self._client.request(
            "DELETE", f"/v1/gdpr/erase", params={"email": email}
        )
        data = self._handle_response(response)
        return GdprEraseResult(**data["data"])

    # ---- HTTP Helpers ----

    def _get(self, path: str, params: Optional[dict[str, Any]] = None) -> Any:
        response = self._client.get(path, params=params)
        return self._handle_response(response)

    def _get_raw(self, path: str, params: Optional[dict[str, Any]] = None) -> str:
        response = self._client.get(path, params=params)
        if response.status_code >= 400:
            try:
                body = response.json()
            except Exception:
                body = {"code": "unknown", "message": response.text}
            raise EuroMailError.from_response(response.status_code, body)
        return response.text

    def _post(self, path: str, json: Any) -> Any:
        response = self._client.post(path, json=json)
        return self._handle_response(response)

    def _put(self, path: str, json: Any) -> Any:
        response = self._client.put(path, json=json)
        return self._handle_response(response)

    def _patch(self, path: str, json: Any) -> Any:
        response = self._client.patch(path, json=json)
        return self._handle_response(response)

    def _delete(self, path: str) -> None:
        response = self._client.delete(path)
        self._handle_response(response)

    def _handle_response(self, response: httpx.Response) -> Any:
        if response.status_code >= 400:
            try:
                body = response.json()
            except Exception:
                body = {"code": "unknown", "message": response.text}
            raise EuroMailError.from_response(response.status_code, body)

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


def _parse_email(data: dict[str, Any]) -> Email:
    return Email(
        id=data["id"],
        account_id=data["account_id"],
        message_id=data["message_id"],
        from_address=data["from_address"],
        to_address=data["to_address"],
        subject=data["subject"],
        status=data["status"],
        attempts=data["attempts"],
        max_attempts=data["max_attempts"],
        created_at=data["created_at"],
        updated_at=data["updated_at"],
        domain_id=data.get("domain_id"),
        cc=data.get("cc"),
        bcc=data.get("bcc"),
        reply_to=data.get("reply_to"),
        html_body=data.get("html_body"),
        text_body=data.get("text_body"),
        template_id=data.get("template_id"),
        template_data=data.get("template_data"),
        headers=data.get("headers", {}),
        tags=data.get("tags", []),
        metadata=data.get("metadata", {}),
        error_message=data.get("error_message"),
        smtp_response=data.get("smtp_response"),
        sent_at=data.get("sent_at"),
    )


def _unwrap(data: dict[str, Any]) -> dict[str, Any]:
    """Unwrap the `data` envelope if present."""
    if isinstance(data, dict) and "data" in data and len(data) <= 2:
        inner = data["data"]
        if isinstance(inner, dict):
            return inner
    return data


def _parse_dns_records(raw: Any) -> dict[str, DnsRecord]:
    if isinstance(raw, dict):
        result = {}
        for key, r in raw.items():
            rec = dict(r)
            result[key] = DnsRecord(**{k: v for k, v in rec.items() if k in ("type", "host", "value", "priority")})
        return result
    return {}


def _parse_domain(data: dict[str, Any]) -> Domain:
    dns_records = _parse_dns_records(data.get("dns_records", {}))
    return Domain(
        id=data["id"],
        account_id=data["account_id"],
        domain=data["domain"],
        dkim_selector=data["dkim_selector"],
        dkim_public_key=data.get("dkim_public_key", ""),
        spf_verified=data["spf_verified"],
        dkim_verified=data["dkim_verified"],
        dmarc_verified=data["dmarc_verified"],
        return_path_verified=data["return_path_verified"],
        mx_verified=data.get("mx_verified", False),
        inbound_enabled=data.get("inbound_enabled", False),
        dns_records=dns_records,
        created_at=data["created_at"],
        updated_at=data["updated_at"],
        mx_verified_at=data.get("mx_verified_at"),
        verified_at=data.get("verified_at"),
        tracking_domain=data.get("tracking_domain"),
        tracking_domain_verified=data.get("tracking_domain_verified", False),
        tracking_domain_verified_at=data.get("tracking_domain_verified_at"),
    )
