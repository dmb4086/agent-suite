"""Custom exceptions for the Agent Suite SDK.

Provides a hierarchy of typed exceptions so callers can handle
specific failure modes (auth errors, rate limits, server errors)
without inspecting raw HTTP status codes.
"""

from typing import Optional


class AgentSuiteError(Exception):
    """Base exception for all Agent Suite SDK errors.

    Attributes:
        message: Human-readable error description.
        status_code: HTTP status code from the API, if available.
        detail: Raw detail string from the API error response.
    """

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        detail: Optional[str] = None,
    ) -> None:
        self.message = message
        self.status_code = status_code
        self.detail = detail
        super().__init__(message)


class AuthenticationError(AgentSuiteError):
    """Raised when the API key is invalid or missing (HTTP 401/403)."""

    def __init__(self, detail: Optional[str] = None) -> None:
        super().__init__(
            message=detail or "Invalid or missing API key",
            status_code=401,
            detail=detail,
        )


class NotFoundError(AgentSuiteError):
    """Raised when the requested resource is not found (HTTP 404)."""

    def __init__(self, detail: Optional[str] = None) -> None:
        super().__init__(
            message=detail or "Resource not found",
            status_code=404,
            detail=detail,
        )


class RateLimitError(AgentSuiteError):
    """Raised when rate limited by the API (HTTP 429)."""

    def __init__(self, detail: Optional[str] = None) -> None:
        super().__init__(
            message=detail or "Rate limit exceeded",
            status_code=429,
            detail=detail,
        )


class ServiceUnavailableError(AgentSuiteError):
    """Raised when a required service is unavailable (HTTP 503)."""

    def __init__(self, detail: Optional[str] = None) -> None:
        super().__init__(
            message=detail or "Service unavailable",
            status_code=503,
            detail=detail,
        )


class ServerError(AgentSuiteError):
    """Raised on unexpected server-side errors (HTTP 5xx)."""

    def __init__(
        self,
        detail: Optional[str] = None,
        status_code: int = 500,
    ) -> None:
        super().__init__(
            message=detail or "Internal server error",
            status_code=status_code,
            detail=detail,
        )
