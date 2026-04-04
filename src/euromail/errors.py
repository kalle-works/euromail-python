"""Error classes for the EuroMail SDK."""

from __future__ import annotations

from typing import Any, Optional


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
    def from_response(cls, status: int, body: dict[str, Any]) -> "EuroMailError":
        code = body.get("code", "unknown")
        message = body.get("message", "Unknown error")

        if status == 401:
            return AuthenticationError(message)
        if status == 422:
            return ValidationError(code, message)
        if status == 429:
            return RateLimitError(message, retry_after=body.get("retry_after"))
        return cls(status, code, message)


class AuthenticationError(EuroMailError):
    """Raised when the API key is invalid or missing."""

    def __init__(self, message: str = "Invalid API key") -> None:
        super().__init__(401, "authentication_error", message)


class ValidationError(EuroMailError):
    """Raised when request parameters fail validation."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(422, code, message)


class RateLimitError(EuroMailError):
    """Raised when the API rate limit is exceeded."""

    def __init__(
        self, message: str = "Rate limit exceeded", retry_after: Optional[int] = None
    ) -> None:
        super().__init__(429, "rate_limit_exceeded", message)
        self.retry_after = retry_after
