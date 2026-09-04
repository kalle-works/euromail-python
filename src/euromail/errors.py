"""Error classes for the EuroMail SDK."""

from __future__ import annotations

from typing import Any, Mapping, Optional


def _parse_retry_after(headers: Optional[Mapping[str, str]]) -> Optional[int]:
    """Parse the `Retry-After` response header (seconds, as an integer).

    The API sends this as an HTTP header, not a JSON body field — see
    `retry-after` being set directly on the response in
    crates/euromail-api/src/errors.rs. Header lookups here are
    case-insensitive when `headers` is an `httpx.Headers` (or any other
    case-insensitive mapping); a plain `dict` would need exact-case keys.
    """
    if not headers:
        return None
    value = headers.get("retry-after")
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


class EuroMailError(Exception):
    """Base error for all EuroMail API errors."""

    def __init__(self, status: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(status={self.status}, code={self.code!r}, message={self.message!r})"

    @classmethod
    def from_response(
        cls,
        status: int,
        body: Any,
        headers: Optional[Mapping[str, str]] = None,
    ) -> "EuroMailError":
        # Every error response nests its details under an "error" key, e.g.
        # {"error": {"type": "validation_error", "code": "VALIDATION_ERROR",
        # "message": "..."}} — see the `json!({"error": {...}})` bodies built
        # in crates/euromail-api/src/errors.rs and
        # crates/euromail-common/src/errors.rs. A flat body (no wrapper) is
        # tolerated too, so a non-conforming response doesn't crash the SDK.
        err: dict[str, Any] = {}
        if isinstance(body, dict):
            candidate = body.get("error", body)
            if isinstance(candidate, dict):
                err = candidate

        code = str(err.get("code", "unknown"))
        message = str(err.get("message", "Unknown error"))
        error_type = err.get("type")

        if status == 401:
            return AuthenticationError(message)
        if status == 403:
            return ForbiddenError(code, message)
        if status == 404:
            return NotFoundError(code, message)
        if status == 409:
            return ConflictError(code, message)
        # Field/body validation is returned as 400 (AppError::Validation,
        # malformed JSON) as well as 422 (ApiError::UnprocessableEntity) —
        # both carry error_type "validation_error", so route on either signal
        # rather than assuming a single status code owns validation errors.
        if status in (400, 422) or error_type == "validation_error":
            return ValidationError(status, code, message)
        if status == 429:
            return RateLimitError(message, retry_after=_parse_retry_after(headers))
        if status >= 500:
            return ServerError(status, code, message)
        return cls(status, code, message)


class AuthenticationError(EuroMailError):
    """Raised when the API key is invalid or missing."""

    def __init__(self, message: str = "Invalid API key") -> None:
        super().__init__(401, "authentication_error", message)


class ForbiddenError(EuroMailError):
    """Raised when the API key is valid but lacks permission for the request."""

    def __init__(self, code: str = "forbidden", message: str = "Access denied") -> None:
        super().__init__(403, code, message)


class NotFoundError(EuroMailError):
    """Raised when the requested resource does not exist."""

    def __init__(self, code: str = "not_found", message: str = "Resource not found") -> None:
        super().__init__(404, code, message)


class ConflictError(EuroMailError):
    """Raised when the request conflicts with the current state of a resource."""

    def __init__(self, code: str = "conflict", message: str = "Conflict") -> None:
        super().__init__(409, code, message)


class ValidationError(EuroMailError):
    """Raised when request parameters fail validation.

    The API returns validation failures at both 400 (malformed JSON,
    `AppError::Validation`) and 422 (`ApiError::UnprocessableEntity`)
    depending on the endpoint, so `status` reflects whichever one actually
    came back rather than assuming 422.
    """

    def __init__(self, status: int, code: str, message: str) -> None:
        super().__init__(status, code, message)


class RateLimitError(EuroMailError):
    """Raised when the API rate limit is exceeded."""

    def __init__(
        self, message: str = "Rate limit exceeded", retry_after: Optional[int] = None
    ) -> None:
        super().__init__(429, "rate_limit_exceeded", message)
        self.retry_after = retry_after


class ServerError(EuroMailError):
    """Raised for 5xx responses (internal errors, service unavailable, etc.)."""

    def __init__(self, status: int, code: str, message: str) -> None:
        super().__init__(status, code, message)
