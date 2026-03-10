import httpx
from typing import List, Optional
from .schemas import InboxResponse, InboxPublic, MessageCreate, MessageList

class AgentSuiteClient:
    def __init__(self, api_key: Optional[str] = None, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
        self.client = httpx.AsyncClient(base_url=self.base_url, headers=self.headers)

    async def create_inbox(self) -> InboxResponse:
        """Creates a new inbox and returns the API Key."""
        response = await self.client.post("/v1/inboxes")
        response.raise_for_status()
        data = response.json()
        # Update headers if we just created the account
        self.client.headers.update({"Authorization": f"Bearer {data['api_key']}"})
        return InboxResponse(**data)

    async def get_my_inbox(self) -> InboxPublic:
        """Gets current inbox details."""
        response = await self.client.get("/v1/inboxes/me")
        response.raise_for_status()
        return InboxPublic(**response.json())

    async def send_email(self, to: str, subject: str, body: str, html_body: Optional[str] = None):
        """Sends an email."""
        payload = {
            "to": to,
            "subject": subject,
            "body": body,
            "html_body": html_body
        }
        response = await self.client.post("/v1/inboxes/me/send", json=payload)
        response.raise_for_status()
        return response.json()

    async def list_messages(self, skip: int = 0, limit: int = 50, unread_only: bool = False) -> MessageList:
        """Lists received messages."""
        params = {"skip": skip, "limit": limit, "unread_only": unread_only}
        response = await self.client.get("/v1/inboxes/me/messages", params=params)
        response.raise_for_status()
        return MessageList(**response.json())

    async def close(self):
        """Closes the client connection."""
        await self.client.aclose()
