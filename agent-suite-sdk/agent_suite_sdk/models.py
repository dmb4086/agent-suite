"""Pydantic models for Agent Suite API requests and responses.

All models use strict validation and match the API's JSON schema
defined in docs/openapi.yaml.
"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


# ── Inbox models ──────────────────────────────────────────────────

class Inbox(BaseModel):
    """Full inbox details returned on creation (includes api_key)."""

    id: UUID
    email_address: str
    api_key: str
    created_at: datetime


class InboxPublic(BaseModel):
    """Public inbox details (no api_key)."""

    id: UUID
    email_address: str
    created_at: datetime


# ── Message models ────────────────────────────────────────────────

class MessageCreate(BaseModel):
    """Request body for sending an email."""

    to: EmailStr
    subject: str
    body: str
    html_body: Optional[str] = None


class MessageResponse(BaseModel):
    """A single message returned by the API."""

    id: UUID
    sender: str
    recipient: str
    subject: Optional[str] = None
    body_text: Optional[str] = None
    received_at: datetime
    is_read: bool


class MessageList(BaseModel):
    """Paginated list of messages."""

    total: int
    messages: List[MessageResponse]


class SendResponse(BaseModel):
    """Response after sending an email."""

    status: str
    message_id: str
    to: str


# ── Webhook models ────────────────────────────────────────────────

class WebhookPayload(BaseModel):
    """Incoming webhook payload (e.g. from Mailgun).

    Use this model to parse and validate webhook data
    before forwarding to Agent Suite.
    """

    sender: str
    recipient: str
    subject: str = ""
    body_plain: str = Field(default="", alias="body_plain")
    body_html: str = Field(default="", alias="body_html")
    message_id: str = Field(default="", alias="message_id")


class WebhookResponse(BaseModel):
    """Response from the webhook endpoint."""

    status: str
    message_id: Optional[str] = None
