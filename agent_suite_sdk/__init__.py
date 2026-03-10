"""
Agent Suite SDK - Python client for AI agent email infrastructure.

Usage:
    from agent_suite_sdk import AgentSuiteClient
    
    client = AgentSuiteClient(api_key="your-api-key")
    inbox = client.create_inbox()
    print(inbox.email_address)
    
    # Send email
    client.send_email(inbox_id=inbox.id, to="test@example.com", subject="Hi", body="Hello")
    
    # Receive webhooks
    client.receive_webhook()  # For Flask/FastAPI integration
"""

import os
from typing import Optional, List, Dict, Any, Literal
from datetime import datetime
import asyncio

try:
    import httpx
except ImportError:
    raise ImportError("Please install httpx: pip install httpx")

try:
    from pydantic import BaseModel, Field
except ImportError:
    raise ImportError("Please install pydantic: pip install pydantic")


# ============== Models ==============

class Inbox(BaseModel):
    """Email inbox model."""
    id: str
    email_address: str  # Using str instead of EmailStr to avoid extra dependency
    api_key: Optional[str] = None  # Only returned on creation
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None


class Email(BaseModel):
    """Email message model."""
    id: str
    inbox_id: str
    from_: str = Field(alias="from")
    to: str
    subject: str
    body: str
    body_type: Literal["text", "html"] = "text"
    received_at: Optional[datetime] = None
    read: bool = False
    attachments: Optional[List[Dict[str, Any]]] = None

    class Config:
        populate_by_name = True


class Webhook(BaseModel):
    """Webhook model."""
    id: str
    inbox_id: str
    url: str
    events: List[str]
    active: bool = True
    created_at: Optional[datetime] = None


class EmailListResponse(BaseModel):
    """Response for listing emails."""
    messages: List[Email]
    total: int


class InboxListResponse(BaseModel):
    """Response for listing inboxes."""
    inboxes: List[Inbox]
    total: int


# ============== Client ==============

class AgentSuiteClient:
    """
    Python SDK for Agent Suite API.
    
    Example:
        client = AgentSuiteClient(api_key="your-key")
        
        # Create inbox
        inbox = client.create_inbox()
        
        # Send email
        client.send_email(
            inbox_id=inbox.id,
            to="user@example.com",
            subject="Hello",
            body="Message body"
        )
        
        # List messages
        messages = client.list_messages(inbox_id=inbox.id)
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "http://localhost:8000",
        timeout: float = 30.0,
    ):
        """
        Initialize the client.
        
        Args:
            api_key: Your API key. Can also set AGENT_SUITE_API_KEY env var.
            base_url: Base URL of the API. Defaults to localhost:8000.
            timeout: Request timeout in seconds.
        """
        self.api_key = api_key or os.environ.get("AGENT_SUITE_API_KEY")
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        
        if not self.api_key:
            raise ValueError("api_key is required. Set AGENT_SUITE_API_KEY env var.")
        
        self._client = httpx.Client(
            base_url=self.base_url,
            timeout=self.timeout,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
        )
    
    def _request(self, method: str, path: str, **kwargs) -> Any:
        """Make HTTP request with error handling."""
        try:
            response = self._client.request(method, path, **kwargs)
            response.raise_for_status()
            
            if response.status_code == 204:
                return None
            
            return response.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                raise UnauthorizedError("Invalid or missing API key")
            elif e.response.status_code == 404:
                raise NotFoundError(f"Resource not found: {path}")
            elif e.response.status_code == 400:
                error_data = e.response.json() if e.response.text else {}
                raise BadRequestError(
                    error_data.get("message", str(e))
                )
            else:
                raise APIError(f"HTTP {e.response.status_code}: {e}")
        except httpx.RequestError as e:
            raise APIError(f"Request failed: {e}")
    
    # ============== Inbox Operations ==============
    
    def create_inbox(self, metadata: Optional[Dict[str, Any]] = None) -> Inbox:
        """
        Create a new inbox.
        
        Args:
            metadata: Optional metadata for the inbox.
            
        Returns:
            Inbox object with email_address and api_key.
            
        Example:
            inbox = client.create_inbox()
            print(f"Email: {inbox.email_address}")
            print(f"API Key: {inbox.api_key}")  # Save this!
        """
        data = {}
        if metadata:
            data["metadata"] = metadata
        
        result = self._request("POST", "/v1/inboxes", json=data)
        return Inbox(**result)
    
    def get_inbox(self, inbox_id: str) -> Inbox:
        """
        Get inbox details.
        
        Args:
            inbox_id: The inbox ID.
            
        Returns:
            Inbox object.
        """
        result = self._request("GET", f"/v1/inboxes/{inbox_id}")
        return Inbox(**result)
    
    def list_inboxes(
        self,
        limit: int = 50,
        offset: int = 0,
    ) -> InboxListResponse:
        """
        List all inboxes.
        
        Args:
            limit: Maximum number of results.
            offset: Pagination offset.
            
        Returns:
            InboxListResponse with inboxes and total count.
        """
        params = {"limit": limit, "offset": offset}
        result = self._request("GET", "/v1/inboxes", params=params)
        return InboxListResponse(**result)
    
    def delete_inbox(self, inbox_id: str) -> None:
        """
        Delete an inbox.
        
        Args:
            inbox_id: The inbox ID to delete.
        """
        self._request("DELETE", f"/v1/inboxes/{inbox_id}")
    
    # ============== Email Operations ==============
    
    def send_email(
        self,
        inbox_id: str,
        to: str,
        subject: str,
        body: str,
        body_type: Literal["text", "html"] = "text",
        from_: Optional[str] = None,
        reply_to: Optional[str] = None,
        attachments: Optional[List[str]] = None,
    ) -> Email:
        """
        Send an email from an inbox.
        
        Args:
            inbox_id: The inbox ID to send from.
            to: Recipient email address.
            subject: Email subject.
            body: Email body content.
            body_type: "text" or "html". Defaults to "text".
            from_: Custom sender address (optional).
            reply_to: Reply-to address (optional).
            attachments: List of file paths to attach (optional).
            
        Returns:
            Email object.
            
        Example:
            client.send_email(
                inbox_id="inbox_xxx",
                to="user@example.com",
                subject="Hello",
                body="<html><body>Hello!</body></html>",
                body_type="html"
            )
        """
        data = {
            "to": to,
            "subject": subject,
            "body": body,
            "body_type": body_type,
        }
        
        if from_:
            data["from"] = from_
        if reply_to:
            data["reply_to"] = reply_to
        if attachments:
            data["attachments"] = attachments
        
        result = self._request("POST", f"/v1/inboxes/{inbox_id}/send", json=data)
        return Email(**result)
    
    def list_messages(
        self,
        inbox_id: str,
        limit: int = 50,
        offset: int = 0,
        unread_only: bool = False,
    ) -> EmailListResponse:
        """
        List messages in an inbox.
        
        Args:
            inbox_id: The inbox ID.
            limit: Maximum number of results.
            offset: Pagination offset.
            unread_only: Only return unread messages.
            
        Returns:
            EmailListResponse with messages and total count.
        """
        params = {
            "limit": limit,
            "offset": offset,
            "unread_only": str(unread_only).lower(),
        }
        result = self._request(
            "GET", 
            f"/v1/inboxes/{inbox_id}/messages",
            params=params
        )
        return EmailListResponse(**result)
    
    def get_message(self, inbox_id: str, message_id: str) -> Email:
        """
        Get a specific message.
        
        Args:
            inbox_id: The inbox ID.
            message_id: The message ID.
            
        Returns:
            Email object.
        """
        result = self._request(
            "GET",
            f"/v1/inboxes/{inbox_id}/messages/{message_id}"
        )
        return Email(**result)
    
    # ============== Webhook Operations ==============
    
    def create_webhook(
        self,
        inbox_id: str,
        url: str,
        events: List[str],
        secret: Optional[str] = None,
    ) -> Webhook:
        """
        Create a webhook for inbox events.
        
        Args:
            inbox_id: The inbox ID.
            url: Webhook endpoint URL.
            events: List of events to subscribe to:
                - email.received
                - email.sent
                - email.failed
            secret: Optional secret for signature verification.
            
        Returns:
            Webhook object.
            
        Example:
            client.create_webhook(
                inbox_id="inbox_xxx",
                url="https://myapp.com/webhook",
                events=["email.received"]
            )
        """
        data = {"url": url, "events": events}
        if secret:
            data["secret"] = secret
        
        result = self._request(
            "POST",
            f"/v1/inboxes/{inbox_id}/webhooks",
            json=data
        )
        return Webhook(**result)
    
    def list_webhooks(self, inbox_id: str) -> List[Webhook]:
        """
        List webhooks for an inbox.
        
        Args:
            inbox_id: The inbox ID.
            
        Returns:
            List of Webhook objects.
        """
        result = self._request("GET", f"/v1/inboxes/{inbox_id}/webhooks")
        return [Webhook(**w) for w in result.get("webhooks", [])]
    
    def delete_webhook(self, inbox_id: str, webhook_id: str) -> None:
        """
        Delete a webhook.
        
        Args:
            inbox_id: The inbox ID.
            webhook_id: The webhook ID to delete.
        """
        self._request(
            "DELETE",
            f"/v1/inboxes/{inbox_id}/webhooks/{webhook_id}"
        )
    
    # ============== Webhook Reception ==============
    
    @staticmethod
    def receive_webhook(
        request,
        secret: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Process incoming webhook request.
        
        Use this in your Flask/FastAPI endpoint:
        
        Flask:
            @app.route('/webhook', methods=['POST'])
            def handle_webhook():
                data = client.receive_webhook(request, secret="my-secret")
                if data['event'] == 'email.received':
                    print(f"New email: {data['email']['subject']}")
                return 'OK'
        
        FastAPI:
            @app.post('/webhook')
            async def handle_webhook(request: Request):
                data = await client.receive_webhook(request, secret="my-secret")
                ...
        
        Args:
            request: Flask Request or FastAPI Request object.
            optional secret: Secret used when creating the webhook.
            
        Returns:
            Parsed webhook payload with keys: event, email, timestamp
        """
        import hmac
        import hashlib
        import json
        
        # Get request body
        if hasattr(request, 'json'):
            body = request.json()
        elif hasattr(request, 'body'):
            import asyncio
            body = asyncio.get_event_loop().run_until_complete(request.body())
            body = json.loads(body)
        else:
            body = request.get_data(as_text=True)
            body = json.loads(body)
        
        # Verify signature if secret provided
        if secret:
            signature = request.headers.get('X-Webhook-Signature', '')
            expected = hmac.new(
                secret.encode(),
                json.dumps(body).encode(),
                hashlib.sha256
            ).hexdigest()
            
            if not hmac.compare_digest(signature, expected):
                raise UnauthorizedError("Invalid webhook signature")
        
        return body
    
    # ============== Context Manager ==============
    
    def close(self):
        """Close the HTTP client."""
        self._client.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


# ============== Async Client ==============

class AsyncAgentSuiteClient:
    """Async version of AgentSuiteClient."""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "http://localhost:8000",
        timeout: float = 30.0,
    ):
        self.api_key = api_key or os.environ.get("AGENT_SUITE_API_KEY")
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        
        if not self.api_key:
            raise ValueError("api_key is required.")
        
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=self.timeout,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
        )
    
    async def _request(self, method: str, path: str, **kwargs) -> Any:
        try:
            response = await self._client.request(method, path, **kwargs)
            response.raise_for_status()
            
            if response.status_code == 204:
                return None
            
            return response.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                raise UnauthorizedError("Invalid or missing API key")
            elif e.response.status_code == 404:
                raise NotFoundError(f"Resource not found: {path}")
            else:
                raise APIError(f"HTTP {e.response.status_code}: {e}")
    
    async def create_inbox(self, metadata: Optional[Dict] = None) -> Inbox:
        data = metadata or {}
        result = await self._request("POST", "/v1/inboxes", json=data)
        return Inbox(**result)
    
    async def send_email(
        self,
        inbox_id: str,
        to: str,
        subject: str,
        body: str,
        body_type: Literal["text", "html"] = "text",
    ) -> Email:
        data = {
            "to": to,
            "subject": subject,
            "body": body,
            "body_type": body_type,
        }
        result = await self._request(
            "POST",
            f"/v1/inboxes/{inbox_id}/send",
            json=data
        )
        return Email(**result)
    
    async def list_messages(
        self,
        inbox_id: str,
        limit: int = 50,
        unread_only: bool = False,
    ) -> EmailListResponse:
        params = {"limit": limit, "unread_only": str(unread_only).lower()}
        result = await self._request(
            "GET",
            f"/v1/inboxes/{inbox_id}/messages",
            params=params
        )
        return EmailListResponse(**result)
    
    async def close(self):
        await self._client.aclose()
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()


# ============== Exceptions ==============

class AgentSuiteError(Exception):
    """Base exception for Agent Suite SDK."""
    pass

class UnauthorizedError(AgentSuiteError):
    """Raised when API key is invalid or missing."""
    pass

class NotFoundError(AgentSuiteError):
    """Raised when resource is not found."""
    pass

class BadRequestError(AgentSuiteError):
    """Raised when request is invalid."""
    pass

class APIError(AgentSuiteError):
    """Raised for other API errors."""
    pass


# ============== Exports ==============

__all__ = [
    "AgentSuiteClient",
    "AsyncAgentSuiteClient",
    "Inbox",
    "Email",
    "Webhook",
    "EmailListResponse",
    "InboxListResponse",
    "AgentSuiteError",
    "UnauthorizedError",
    "NotFoundError",
    "BadRequestError",
    "APIError",
]
