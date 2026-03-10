import httpx
from typing import List, Dict, Any
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from .models import Inbox, Message, SendEmailRequest, WebhookPayload
from .exceptions import APIError

class AgentSuiteClient:
    def __init__(self, api_key: str, base_url: str = "https://api.agent-suite.com/v1"):
        self.api_key = api_key
        self.base_url = base_url
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(httpx.RequestError)
    )
    async def _request(self, method: str, endpoint: str, **kwargs) -> Any:
        url = f"{self.base_url}{endpoint}"
        async with httpx.AsyncClient() as client:
            response = await client.request(method, url, headers=self.headers, **kwargs)
            if not response.is_success:
                raise APIError(f"API Request failed: {response.text}", status_code=response.status_code)
            
            # Return JSON if there is content, else return True for empty 200/204 responses
            return response.json() if response.content else True

    async def create_inbox(self, name: str) -> Inbox:
        data = await self._request("POST", "/inboxes", json={"name": name})
        return Inbox(**data)

    async def send_email(self, to: str, subject: str, body: str) -> bool:
        payload = SendEmailRequest(to=to, subject=subject, body=body)
        await self._request("POST", "/emails", json=payload.model_dump())
        return True

    async def list_messages(self, inbox_id: str) -> List[Message]:
        data = await self._request("GET", "/messages", params={"inbox_id": inbox_id})
        return [Message(**item) for item in data]

    async def receive_webhook(self, payload: Dict[str, Any]) -> bool:
        webhook_data = WebhookPayload(**payload)
        await self._request("POST", "/webhooks", json=webhook_data.model_dump())
        return True
