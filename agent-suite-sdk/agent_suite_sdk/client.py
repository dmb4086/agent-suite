"""Synchronous and asynchronous HTTP clients for the Agent Suite API.

Both clients share the same interface and support:
- Automatic Bearer token authentication
- Configurable retry with exponential backoff
- Typed Pydantic responses
- Custom timeout settings

Usage (sync):
    client = AgentSuiteClient(base_url="http://localhost:8000", api_key="as_...")
    messages = client.list_messages(limit=10)

Usage (async):
    async with AsyncAgentSuiteClient(base_url="http://localhost:8000", api_key="as_...") as client:
        messages = await client.list_messages(limit=10)
"""

from __future__ import annotations

import time
from typing import Any, Dict, Optional

import httpx

from agent_suite_sdk.exceptions import (
    AgentSuiteError,
    AuthenticationError,
    NotFoundError,
    RateLimitError,
    ServerError,
    ServiceUnavailableError,
)
from agent_suite_sdk.models import (
    Inbox,
    InboxPublic,
    MessageCreate,
    MessageList,
    SendResponse,
    WebhookPayload,
    WebhookResponse,
)

_DEFAULT_TIMEOUT = 30.0
_DEFAULT_MAX_RETRIES = 3
_DEFAULT_BACKOFF_FACTOR = 0.5
_RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}


def _build_headers(api_key: Optional[str] = None) -> Dict[str, str]:
    """Build default request headers."""
    headers: Dict[str, str] = {"Accept": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    return headers


def _handle_error(response: httpx.Response) -> None:
    """Raise a typed exception based on HTTP status code."""
    if response.status_code < 400:
        return

    detail = None
    try:
        body = response.json()
        detail = body.get("detail")
    except Exception:
        detail = response.text or None

    status = response.status_code

    if status == 401 or status == 403:
        raise AuthenticationError(detail=detail)
    elif status == 404:
        raise NotFoundError(detail=detail)
    elif status == 429:
        raise RateLimitError(detail=detail)
    elif status == 503:
        raise ServiceUnavailableError(detail=detail)
    elif status >= 500:
        raise ServerError(detail=detail, status_code=status)
    else:
        raise AgentSuiteError(
            message=detail or f"HTTP {status}",
            status_code=status,
            detail=detail,
        )


class AgentSuiteClient:
    """Synchronous client for the Agent Suite API.

    Args:
        base_url: API server URL (e.g. ``http://localhost:8000``).
        api_key: Optional Bearer token for authenticated endpoints.
        timeout: Request timeout in seconds. Default 30.
        max_retries: Max retry attempts for transient failures. Default 3.
        backoff_factor: Multiplier for exponential backoff between retries.
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        api_key: Optional[str] = None,
        timeout: float = _DEFAULT_TIMEOUT,
        max_retries: int = _DEFAULT_MAX_RETRIES,
        backoff_factor: float = _DEFAULT_BACKOFF_FACTOR,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self._client = httpx.Client(
            base_url=self.base_url,
            headers=_build_headers(api_key),
            timeout=timeout,
        )

    def close(self) -> None:
        """Close the underlying HTTP connection pool."""
        self._client.close()

    def __enter__(self) -> "AgentSuiteClient":
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

    # ── Internal helpers ──────────────────────────────────────────

    def _request(
        self,
        method: str,
        path: str,
        *,
        json: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> httpx.Response:
        """Execute an HTTP request with retry logic.

        Retries on transient errors (429, 5xx) with exponential backoff.
        Non-retryable errors are raised immediately.
        """
        last_exception: Optional[Exception] = None

        for attempt in range(self.max_retries + 1):
            try:
                response = self._client.request(
                    method,
                    path,
                    json=json,
                    data=data,
                    params=params,
                )

                if response.status_code in _RETRYABLE_STATUS_CODES:
                    if attempt < self.max_retries:
                        self._sleep_backoff(attempt, response)
                        continue

                _handle_error(response)
                return response

            except (httpx.ConnectError, httpx.TimeoutException) as exc:
                last_exception = exc
                if attempt < self.max_retries:
                    self._sleep_backoff(attempt)
                    continue
                raise AgentSuiteError(
                    message=f"Connection failed after {self.max_retries + 1} attempts: {exc}",
                ) from exc

        # Should not reach here, but satisfy type checker
        raise last_exception or AgentSuiteError("Request failed")  # type: ignore[arg-type]

    def _sleep_backoff(
        self,
        attempt: int,
        response: Optional[httpx.Response] = None,
    ) -> None:
        """Sleep with exponential backoff, respecting Retry-After header."""
        if response is not None:
            retry_after = response.headers.get("Retry-After")
            if retry_after:
                try:
                    time.sleep(float(retry_after))
                    return
                except ValueError:
                    pass

        delay = self.backoff_factor * (2 ** attempt)
        time.sleep(delay)

    # ── Public API ────────────────────────────────────────────────

    def health_check(self) -> Dict[str, str]:
        """Check API health status.

        Returns:
            Dict with ``status`` and ``service`` keys.
        """
        response = self._request("GET", "/health")
        return response.json()

    def create_inbox(self) -> Inbox:
        """Create a new inbox with a unique email address and API key.

        Returns:
            Inbox object containing id, email_address, api_key, and created_at.

        Note:
            The ``api_key`` is only returned on creation. Store it securely.
        """
        response = self._request("POST", "/v1/inboxes")
        return Inbox.model_validate(response.json())

    def get_inbox(self) -> InboxPublic:
        """Get the current authenticated inbox details.

        Returns:
            InboxPublic object (no api_key).

        Raises:
            AuthenticationError: If no api_key is set or it is invalid.
        """
        response = self._request("GET", "/v1/inboxes/me")
        return InboxPublic.model_validate(response.json())

    def send_email(
        self,
        to: str,
        subject: str,
        body: str,
        html_body: Optional[str] = None,
    ) -> SendResponse:
        """Send an email via AWS SES.

        Args:
            to: Recipient email address.
            subject: Email subject line.
            body: Plain text email body.
            html_body: Optional HTML email body.

        Returns:
            SendResponse with status, message_id, and recipient.

        Raises:
            AuthenticationError: If api_key is invalid.
            ServiceUnavailableError: If AWS SES is not configured.
            ServerError: If SES delivery fails.
        """
        message = MessageCreate(
            to=to,
            subject=subject,
            body=body,
            html_body=html_body,
        )
        response = self._request(
            "POST",
            "/v1/inboxes/me/send",
            json=message.model_dump(exclude_none=True),
        )
        return SendResponse.model_validate(response.json())

    def list_messages(
        self,
        skip: int = 0,
        limit: int = 50,
        unread_only: bool = False,
    ) -> MessageList:
        """List received messages for the authenticated inbox.

        Args:
            skip: Number of messages to skip (pagination offset).
            limit: Maximum number of messages to return.
            unread_only: If True, return only unread messages.

        Returns:
            MessageList with total count and list of MessageResponse objects.

        Raises:
            AuthenticationError: If api_key is invalid.
        """
        params: Dict[str, Any] = {
            "skip": skip,
            "limit": limit,
        }
        if unread_only:
            params["unread_only"] = "true"

        response = self._request("GET", "/v1/inboxes/me/messages", params=params)
        return MessageList.model_validate(response.json())

    def receive_webhook(self, payload: WebhookPayload) -> WebhookResponse:
        """Forward an incoming email webhook to the API.

        This is primarily for testing or when you are proxying
        webhooks through your own service.

        Args:
            payload: The webhook data (sender, recipient, subject, etc.).

        Returns:
            WebhookResponse with status and optional message_id.
        """
        response = self._request(
            "POST",
            "/v1/webhooks/mailgun",
            data=payload.model_dump(by_alias=True),
        )
        return WebhookResponse.model_validate(response.json())


class AsyncAgentSuiteClient:
    """Asynchronous client for the Agent Suite API.

    Provides the same interface as ``AgentSuiteClient`` but all
    methods are ``async`` and use ``httpx.AsyncClient`` under the hood.

    Usage:
        async with AsyncAgentSuiteClient(base_url="...", api_key="...") as client:
            inbox = await client.create_inbox()
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        api_key: Optional[str] = None,
        timeout: float = _DEFAULT_TIMEOUT,
        max_retries: int = _DEFAULT_MAX_RETRIES,
        backoff_factor: float = _DEFAULT_BACKOFF_FACTOR,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            headers=_build_headers(api_key),
            timeout=timeout,
        )

    async def close(self) -> None:
        """Close the underlying HTTP connection pool."""
        await self._client.aclose()

    async def __aenter__(self) -> "AsyncAgentSuiteClient":
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()

    # ── Internal helpers ──────────────────────────────────────────

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> httpx.Response:
        """Execute an async HTTP request with retry logic."""
        import asyncio

        last_exception: Optional[Exception] = None

        for attempt in range(self.max_retries + 1):
            try:
                response = await self._client.request(
                    method,
                    path,
                    json=json,
                    data=data,
                    params=params,
                )

                if response.status_code in _RETRYABLE_STATUS_CODES:
                    if attempt < self.max_retries:
                        await self._async_sleep_backoff(attempt, response)
                        continue

                _handle_error(response)
                return response

            except (httpx.ConnectError, httpx.TimeoutException) as exc:
                last_exception = exc
                if attempt < self.max_retries:
                    await self._async_sleep_backoff(attempt)
                    continue
                raise AgentSuiteError(
                    message=f"Connection failed after {self.max_retries + 1} attempts: {exc}",
                ) from exc

        raise last_exception or AgentSuiteError("Request failed")  # type: ignore[arg-type]

    async def _async_sleep_backoff(
        self,
        attempt: int,
        response: Optional[httpx.Response] = None,
    ) -> None:
        """Async sleep with exponential backoff."""
        import asyncio

        if response is not None:
            retry_after = response.headers.get("Retry-After")
            if retry_after:
                try:
                    await asyncio.sleep(float(retry_after))
                    return
                except ValueError:
                    pass

        delay = self.backoff_factor * (2 ** attempt)
        await asyncio.sleep(delay)

    # ── Public API ────────────────────────────────────────────────

    async def health_check(self) -> Dict[str, str]:
        """Check API health status."""
        response = await self._request("GET", "/health")
        return response.json()

    async def create_inbox(self) -> Inbox:
        """Create a new inbox with a unique email address and API key."""
        response = await self._request("POST", "/v1/inboxes")
        return Inbox.model_validate(response.json())

    async def get_inbox(self) -> InboxPublic:
        """Get the current authenticated inbox details."""
        response = await self._request("GET", "/v1/inboxes/me")
        return InboxPublic.model_validate(response.json())

    async def send_email(
        self,
        to: str,
        subject: str,
        body: str,
        html_body: Optional[str] = None,
    ) -> SendResponse:
        """Send an email via AWS SES."""
        message = MessageCreate(
            to=to,
            subject=subject,
            body=body,
            html_body=html_body,
        )
        response = await self._request(
            "POST",
            "/v1/inboxes/me/send",
            json=message.model_dump(exclude_none=True),
        )
        return SendResponse.model_validate(response.json())

    async def list_messages(
        self,
        skip: int = 0,
        limit: int = 50,
        unread_only: bool = False,
    ) -> MessageList:
        """List received messages for the authenticated inbox."""
        params: Dict[str, Any] = {
            "skip": skip,
            "limit": limit,
        }
        if unread_only:
            params["unread_only"] = "true"

        response = await self._request(
            "GET", "/v1/inboxes/me/messages", params=params
        )
        return MessageList.model_validate(response.json())

    async def receive_webhook(self, payload: WebhookPayload) -> WebhookResponse:
        """Forward an incoming email webhook to the API."""
        response = await self._request(
            "POST",
            "/v1/webhooks/mailgun",
            data=payload.model_dump(by_alias=True),
        )
        return WebhookResponse.model_validate(response.json())
