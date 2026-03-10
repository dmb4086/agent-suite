"""
AgentWork SDK - Python client for AgentWork Infrastructure API
"""
import httpx
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, EmailStr
import asyncio


class Message(BaseModel):
    """Email message model"""
    id: str
    from_email: str
    to_email: str
    subject: str
    body: str
    created_at: str
    read: bool = False
    attachments: List[Dict[str, Any]] = []


class Inbox(BaseModel):
    """Inbox model"""
    email_address: str
    api_key: str
    created_at: str


class AgentWorkClient:
    """
    AgentWork API Client

    A Python SDK for interacting with AgentWork Infrastructure API.

    Example:
        >>> client = AgentWorkClient(api_key="your-api-key")
        >>> inbox = await client.create_inbox()
        >>> messages = await client.list_messages()
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "http://localhost:8000",
        timeout: float = 30.0,
        max_retries: int = 3
    ):
        """
        Initialize AgentWork client

        Args:
            api_key: Your API key (optional for create_inbox)
            base_url: API base URL
            timeout: Request timeout in seconds
            max_retries: Maximum number of retries on failure
        """
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.timeout = timeout
        self.max_retries = max_retries
        self._client = httpx.AsyncClient(timeout=timeout)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def close(self):
        """Close the HTTP client"""
        await self._client.aclose()

    def _get_headers(self) -> Dict[str, str]:
        """Get request headers"""
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        if self.api_key:
            headers['Authorization'] = f'Bearer {self.api_key}'
        return headers

    async def _request(
        self,
        method: str,
        endpoint: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Make HTTP request with retries

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint
            **kwargs: Additional request parameters

        Returns:
            Response JSON

        Raises:
            httpx.HTTPError: Request failed after all retries
        """
        url = f"{self.base_url}{endpoint}"
        headers = self._get_headers()

        for attempt in range(self.max_retries):
            try:
                response = await self._client.request(
                    method=method,
                    url=url,
                    headers=headers,
                    **kwargs
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                if attempt == self.max_retries - 1:
                    raise
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
            except httpx.RequestError as e:
                if attempt == self.max_retries - 1:
                    raise
                await asyncio.sleep(2 ** attempt)

    # Inbox Operations

    async def create_inbox(self) -> Inbox:
        """
        Create a new email inbox

        Returns:
            Inbox object with email address and API key

        Example:
            >>> inbox = await client.create_inbox()
            >>> print(inbox.email_address)
        """
        data = await self._request('POST', '/v1/inboxes')
        return Inbox(**data)

    # Message Operations

    async def list_messages(self) -> List[Message]:
        """
        List all messages in the inbox

        Returns:
            List of Message objects

        Example:
            >>> messages = await client.list_messages()
            >>> for msg in messages:
            ...     print(f"From: {msg.from_email}, Subject: {msg.subject}")
        """
        data = await self._request('GET', '/v1/inboxes/me/messages')
        return [Message(**msg) for msg in data]

    async def send_email(
        self,
        to: str,
        subject: str,
        body: str
    ) -> Dict[str, Any]:
        """
        Send an email

        Args:
            to: Recipient email address
            subject: Email subject
            body: Email body

        Returns:
            Send result

        Example:
            >>> result = await client.send_email(
            ...     to="recipient@example.com",
            ...     subject="Hello",
            ...     body="This is a test email"
            ... )
        """
        payload = {
            'to': to,
            'subject': subject,
            'body': body
        }
        return await self._request(
            'POST',
            '/v1/inboxes/me/send',
            json=payload
        )

    async def get_message(self, message_id: str) -> Message:
        """
        Get a specific message by ID

        Args:
            message_id: Message ID

        Returns:
            Message object
        """
        data = await self._request(
            'GET',
            f'/v1/inboxes/me/messages/{message_id}'
        )
        return Message(**data)

    async def delete_message(self, message_id: str) -> Dict[str, Any]:
        """
        Delete a message

        Args:
            message_id: Message ID

        Returns:
            Delete result
        """
        return await self._request(
            'DELETE',
            f'/v1/inboxes/me/messages/{message_id}'
        )

    # Calendar Operations (if available)

    async def list_events(self) -> List[Dict[str, Any]]:
        """
        List calendar events

        Returns:
            List of event objects
        """
        return await self._request('GET', '/v1/inboxes/me/events')

    async def create_event(
        self,
        title: str,
        start_time: str,
        end_time: str,
        description: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a calendar event

        Args:
            title: Event title
            start_time: Event start time (ISO format)
            end_time: Event end time (ISO format)
            description: Event description

        Returns:
            Created event
        """
        payload = {
            'title': title,
            'start_time': start_time,
            'end_time': end_time,
            'description': description
        }
        return await self._request(
            'POST',
            '/v1/inboxes/me/events',
            json=payload
        )


# Sync wrapper for synchronous usage
class AgentWorkClientSync:
    """Synchronous wrapper for AgentWorkClient"""

    def __init__(self, *args, **kwargs):
        self._async_client = AgentWorkClient(*args, **kwargs)

    def _run_async(self, coro):
        """Run async coroutine synchronously"""
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If already in async context, create new loop
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, coro)
                return future.result()
        else:
            return loop.run_until_complete(coro)

    def create_inbox(self) -> Inbox:
        """Create inbox (sync)"""
        return self._run_async(self._async_client.create_inbox())

    def list_messages(self) -> List[Message]:
        """List messages (sync)"""
        return self._run_async(self._async_client.list_messages())

    def send_email(self, to: str, subject: str, body: str) -> Dict[str, Any]:
        """Send email (sync)"""
        return self._run_async(
            self._async_client.send_email(to, subject, body)
        )

    def close(self):
        """Close client"""
        self._run_async(self._async_client.close())
