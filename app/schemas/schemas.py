from datetime import datetime
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel, EmailStr


# Inbox schemas
class InboxCreate(BaseModel):
    pass  # No fields needed - we generate everything


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


# Message schemas
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
    
    class Config:
        from_attributes = True


class MessageList(BaseModel):
    total: int
    messages: List[MessageResponse]
