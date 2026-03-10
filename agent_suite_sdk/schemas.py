from pydantic import BaseModel, EmailStr
from uuid import UUID
from datetime import datetime
from typing import List, Optional

class InboxResponse(BaseModel):
    id: UUID
    email_address: str
    api_key: str
    created_at: datetime

class InboxPublic(BaseModel):
    id: UUID
    email_address: str
    created_at: datetime

class MessageCreate(BaseModel):
    to: EmailStr
    subject: str
    body: str
    html_body: Optional[str] = None

class MessageResponse(BaseModel):
    id: UUID
    sender: str
    recipient: str
    subject: Optional[str]
    body_text: Optional[str]
    received_at: datetime
    is_read: bool

class MessageList(BaseModel):
    total: int
    messages: List[MessageResponse]
