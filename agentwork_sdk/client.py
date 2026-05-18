from __future__ import annotations

from typing import Any, Dict, Optional

import httpx

from .models import InboxPublic, InboxResponse, MessageList, SendEmailResult


class AgentWorkError(Exception):
    """Raised when the AgentWork API returns an error response."""

    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message
        super().__init__(f"AgentWork API error {status_code}: {message}")


class AgentWorkClient:
    """Small Python SDK for AgentWork Infrastructure.

    The client supports both unauthenticated inbox creation and authenticated
    inbox operations using the returned API key.
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        api_key: Optional[str] = None,
        timeout: float = 10.0,
        max_retries: int = 2,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self.max_retries = max_retries
        self._client = httpx.Client(base_url=self.base_url, timeout=timeout)

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "AgentWorkClient":
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def _headers(self) -> Dict[str, str]:
        headers = {"Accept": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def _request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        last_exc: Optional[httpx.HTTPError] = None
        for attempt in range(self.max_retries + 1):
            try:
                response = self._client.request(method, path, headers=self._headers(), **kwargs)
                if response.status_code >= 500 and attempt < self.max_retries:
                    continue
                if response.status_code >= 400:
                    detail = self._extract_error(response)
                    raise AgentWorkError(response.status_code, detail)
                return response
            except (httpx.ConnectError, httpx.ReadTimeout, httpx.RemoteProtocolError) as exc:
                last_exc = exc
                if attempt >= self.max_retries:
                    raise
        raise RuntimeError(f"Request failed: {last_exc}")

    @staticmethod
    def _extract_error(response: httpx.Response) -> str:
        try:
            payload = response.json()
        except ValueError:
            return response.text
        detail = payload.get("detail") if isinstance(payload, dict) else None
        return str(detail or payload)

    def create_inbox(self) -> InboxResponse:
        """Create a new inbox and store its API key on this client."""
        response = self._request("POST", "/v1/inboxes")
        inbox = InboxResponse.model_validate(response.json())
        self.api_key = inbox.api_key
        return inbox

    def get_inbox(self) -> InboxPublic:
        response = self._request("GET", "/v1/inboxes/me")
        return InboxPublic.model_validate(response.json())

    def send_email(
        self,
        to: str,
        subject: str,
        body: str,
        html_body: Optional[str] = None,
    ) -> SendEmailResult:
        payload = {
            "to": to,
            "subject": subject,
            "body": body,
            "html_body": html_body,
        }
        response = self._request("POST", "/v1/inboxes/me/send", json=payload)
        return SendEmailResult.model_validate(response.json())

    def list_messages(
        self,
        skip: int = 0,
        limit: int = 50,
        unread_only: bool = False,
    ) -> MessageList:
        response = self._request(
            "GET",
            "/v1/inboxes/me/messages",
            params={"skip": skip, "limit": limit, "unread_only": unread_only},
        )
        return MessageList.model_validate(response.json())

    def receive_webhook(
        self,
        sender: str,
        recipient: str,
        subject: str = "",
        body_plain: str = "",
        body_html: str = "",
        message_id: str = "",
    ) -> Dict[str, Any]:
        """Post a Mailgun-style webhook payload.

        This is useful for local testing of inbound email handling.
        """
        response = self._request(
            "POST",
            "/v1/webhooks/mailgun",
            data={
                "sender": sender,
                "recipient": recipient,
                "subject": subject,
                "body_plain": body_plain,
                "body_html": body_html,
                "message_id": message_id,
            },
        )
        return response.json()
