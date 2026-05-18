from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr


class InboxResponse(BaseModel):
    id: UUID
    email_address: EmailStr
    api_key: str
    created_at: datetime


class InboxPublic(BaseModel):
    id: UUID
    email_address: EmailStr
    created_at: datetime


class SendEmailResult(BaseModel):
    status: str
    message_id: str
    to: EmailStr


class Message(BaseModel):
    id: UUID
    sender: str
    recipient: str
    subject: Optional[str] = None
    body_text: Optional[str] = None
    received_at: datetime
    is_read: bool


class MessageList(BaseModel):
    total: int
    messages: List[Message]


class WebhookResult(BaseModel):
    status: str
    message_id: Optional[str] = None
