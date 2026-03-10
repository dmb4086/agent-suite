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


# Verification schemas (Bounty #2)
class VerificationStatus(BaseModel):
    """Email verification status."""
    spf_pass: Optional[bool]
    dkim_pass: Optional[bool]
    spam_score: float
    is_spam: bool
    spam_indicators: List[str] = []


class AttachmentResponse(BaseModel):
    """Attachment metadata in API responses."""
    id: UUID
    filename: str
    content_type: Optional[str]
    size_bytes: Optional[int]
    sha256: Optional[str]
    created_at: datetime
    download_url: Optional[str] = None
    
    class Config:
        from_attributes = True


# Message schemas
class MessageCreate(BaseModel):
    to: EmailStr
    subject: str
    body: str
    html_body: Optional[str] = None


class MessageResponse(BaseModel):
    """Full message response including verification and attachments."""
    id: UUID
    sender: str
    recipient: str
    subject: Optional[str]
    body_text: Optional[str]
    received_at: datetime
    is_read: bool
    
    # Verification metadata (Bounty #2)
    verification: Optional[VerificationStatus] = None
    
    # Attachments (Bounty #2)
    attachments: List[AttachmentResponse] = []
    
    class Config:
        from_attributes = True


class MessageBrief(BaseModel):
    """Brief message info for list views."""
    id: UUID
    sender: str
    subject: Optional[str]
    received_at: datetime
    is_read: bool
    has_attachments: bool = False
    is_spam: bool = False
    
    class Config:
        from_attributes = True


class MessageList(BaseModel):
    total: int
    messages: List[MessageBrief]
