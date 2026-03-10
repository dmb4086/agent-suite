import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Text, ForeignKey, Boolean, Uuid
from app.db.database import Base


def generate_api_key():
    return f"as_{uuid.uuid4().hex}"


class Inbox(Base):
    __tablename__ = "inboxes"
    
    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email_address = Column(String(255), unique=True, index=True, nullable=False)
    api_key = Column(String(255), unique=True, index=True, default=generate_api_key)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)


class Message(Base):
    __tablename__ = "messages"
    
    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    inbox_id = Column(Uuid(as_uuid=True), ForeignKey("inboxes.id"), index=True)
    sender = Column(String(255), nullable=False)
    recipient = Column(String(255), nullable=False)
    subject = Column(String(500))
    body_text = Column(Text)
    body_html = Column(Text)
    received_at = Column(DateTime, default=datetime.utcnow)
    is_read = Column(Boolean, default=False)
    message_id = Column(String(255), index=True)  # External message ID
    raw_data = Column(Text)  # Store raw email for debugging
