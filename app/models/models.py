import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Text, ForeignKey, Boolean, Float, JSON, Integer
from sqlalchemy.dialects.postgresql import UUID
from app.db.database import Base


def generate_api_key():
    return f"as_{uuid.uuid4().hex}"


class Inbox(Base):
    __tablename__ = "inboxes"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email_address = Column(String(255), unique=True, index=True, nullable=False)
    api_key = Column(String(255), unique=True, index=True, default=generate_api_key)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)


class Message(Base):
    __tablename__ = "messages"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    inbox_id = Column(UUID(as_uuid=True), ForeignKey("inboxes.id"), index=True)
    sender = Column(String(255), nullable=False)
    recipient = Column(String(255), nullable=False)
    subject = Column(String(500))
    body_text = Column(Text)
    body_html = Column(Text)
    received_at = Column(DateTime, default=datetime.utcnow)
    is_read = Column(Boolean, default=False)
    message_id = Column(String(255), index=True)
    raw_data = Column(Text)
    
    # Verification fields (Bounty #2)
    spf_pass = Column(Boolean, default=None)
    dkim_pass = Column(Boolean, default=None)
    spam_score = Column(Float, default=0.0)
    is_spam = Column(Boolean, default=False)
    spam_indicators = Column(JSON, default=list)


class Attachment(Base):
    """Email attachment metadata (Bounty #2)"""
    __tablename__ = "attachments"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    message_id = Column(UUID(as_uuid=True), ForeignKey("messages.id"), nullable=False, index=True)
    filename = Column(String(500), nullable=False)
    content_type = Column(String(255))
    size_bytes = Column(Integer)
    sha256 = Column(String(64), index=True)
    s3_key = Column(String(500))
    created_at = Column(DateTime, default=datetime.utcnow)
