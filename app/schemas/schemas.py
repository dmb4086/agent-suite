from datetime import datetime
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel, EmailStr


class InboxCreate(BaseModel):
    pass


class InboxResponse(BaseModel):
    id: UUID
    email_address: str
    api_key: str
    created_at: datetime

    class Config:
        from_attributes = True


class InboxPublic(BaseModel):
    id: UUID
    email_address: str
    created_at: datetime

    class Config:
        from_attributes = True


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
    attachments_meta: Optional[str] = None
    spam_score: Optional[str] = None
    dkim_passed: Optional[bool] = None
    spf_passed: Optional[bool] = None

    class Config:
        from_attributes = True


class MessageList(BaseModel):
    total: int
    messages: List[MessageResponse]
