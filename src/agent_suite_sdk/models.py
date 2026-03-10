from pydantic import BaseModel
from typing import Dict, Any

class Inbox(BaseModel):
    id: str
    address: str

class Message(BaseModel):
    id: str
    subject: str
    content: str

class SendEmailRequest(BaseModel):
    to: str
    subject: str
    body: str

class WebhookPayload(BaseModel):
    event_type: str
    data: Dict[str, Any]
