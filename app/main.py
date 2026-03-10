import logging
from typing import List, Optional

import boto3
from botocore.exceptions import ClientError
from fastapi import FastAPI, Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from starlette.datastructures import UploadFile

from app.core.config import get_settings
from app.db.database import get_db, engine, Base
from app.models import models
from app.schemas import schemas
from app.services.email_verification import verify_email, verify_mailgun_webhook_signature
from app.services.attachment_service import parse_and_store_attachments, get_s3_client

logger = logging.getLogger(__name__)

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Agent Suite", version="0.1.0")
security = HTTPBearer()
settings = get_settings()


def get_inbox_by_api_key(api_key: str, db: Session):
    return db.query(models.Inbox).filter(
        models.Inbox.api_key == api_key,
        models.Inbox.is_active == True
    ).first()


def verify_api_key(credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)):
    inbox = get_inbox_by_api_key(credentials.credentials, db)
    if not inbox:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )
    return inbox


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "agent-suite"}


@app.post("/v1/inboxes", response_model=schemas.InboxResponse, status_code=status.HTTP_201_CREATED)
def create_inbox(db: Session = Depends(get_db)):
    """Create a new inbox. Returns email address and API key."""
    import uuid
    
    # Generate unique email address
    unique_id = uuid.uuid4().hex[:12]
    email_address = f"{unique_id}@agents.dev"
    
    inbox = models.Inbox(email_address=email_address)
    db.add(inbox)
    db.commit()
    db.refresh(inbox)
    
    return inbox


@app.get("/v1/inboxes/me", response_model=schemas.InboxPublic)
def get_my_inbox(inbox: models.Inbox = Depends(verify_api_key)):
    """Get current inbox details."""
    return inbox


@app.post("/v1/inboxes/me/send")
def send_email(
    message: schemas.MessageCreate,
    inbox: models.Inbox = Depends(verify_api_key),
    db: Session = Depends(get_db)
):
    """Send an email using AWS SES."""
    if not settings.aws_access_key_id:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AWS SES not configured"
        )
    
    try:
        ses_client = boto3.client(
            'ses',
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key,
            region_name=settings.aws_region
        )
        
        response = ses_client.send_email(
            Source=settings.ses_from_email or inbox.email_address,
            Destination={'ToAddresses': [message.to]},
            Message={
                'Subject': {'Data': message.subject},
                'Body': {
                    'Text': {'Data': message.body},
                    'Html': {'Data': message.html_body} if message.html_body else {'Data': message.body}
                }
            }
        )
        
        # Store sent message
        sent_msg = models.Message(
            inbox_id=inbox.id,
            sender=inbox.email_address,
            recipient=message.to,
            subject=message.subject,
            body_text=message.body,
            message_id=response['MessageId']
        )
        db.add(sent_msg)
        db.commit()
        
        return {
            "status": "sent",
            "message_id": response['MessageId'],
            "to": message.to
        }
        
    except ClientError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"SES error: {str(e)}"
        )


@app.get("/v1/inboxes/me/messages", response_model=schemas.MessageList)
def list_messages(
    skip: int = 0,
    limit: int = 50,
    unread_only: bool = False,
    inbox: models.Inbox = Depends(verify_api_key),
    db: Session = Depends(get_db)
):
    """List received messages for this inbox."""
    query = db.query(models.Message).filter(models.Message.inbox_id == inbox.id)
    
    if unread_only:
        query = query.filter(models.Message.is_read == False)
    
    total = query.count()
    messages = query.order_by(models.Message.received_at.desc()).offset(skip).limit(limit).all()
    
    return schemas.MessageList(total=total, messages=messages)


@app.post("/v1/webhooks/mailgun")
async def mailgun_webhook(
    request: Request,
    db: Session = Depends(get_db),
):
    """Receive incoming email from Mailgun with verification and attachment handling.

    Performs the following checks on each incoming email:
    1. Verifies Mailgun webhook signature (if signing key is configured)
    2. Validates SPF/DKIM authentication results
    3. Filters spam based on configurable score threshold (default > 5)
    4. Parses and stores attachments in S3

    Emails that fail spam filtering are rejected with a 400 response.
    """
    # Parse form data (Mailgun sends multipart/form-data)
    form = await request.form()

    sender = form.get("sender", "")
    recipient = form.get("recipient", "")
    subject = form.get("subject", "")
    body_plain = form.get("body-plain", "") or form.get("body_plain", "")
    body_html = form.get("body-html", "") or form.get("body_html", "")
    message_id = form.get("Message-Id", "") or form.get("message_id", "")

    # Mailgun webhook signature verification
    if settings.mailgun_signing_key:
        timestamp = form.get("timestamp", "")
        token = form.get("token", "")
        signature = form.get("signature", "")
        if not verify_mailgun_webhook_signature(
            settings.mailgun_signing_key, timestamp, token, signature
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid webhook signature",
            )

    # Email verification (SPF/DKIM/Spam)
    spf_header = form.get("X-Mailgun-Spf", "")
    dkim_header = form.get("X-Mailgun-Dkim-Check-Result", "")
    spam_score_header = form.get("X-Mailgun-SSscore", "") or form.get("spam-score", "")

    verification = verify_email(
        spf_header=spf_header,
        dkim_header=dkim_header,
        spam_score_header=spam_score_header,
        spam_threshold=settings.spam_score_threshold,
    )

    # Reject spam
    if verification.is_spam:
        logger.warning(
            "Rejected spam email from %s (score: %s)",
            sender,
            verification.spam_score,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Email rejected: {verification.rejection_reason}",
        )

    # Find inbox by recipient email
    inbox = db.query(models.Inbox).filter(
        models.Inbox.email_address == recipient,
        models.Inbox.is_active == True
    ).first()

    if not inbox:
        return {"status": "dropped"}

    # Store message with verification data
    message = models.Message(
        inbox_id=inbox.id,
        sender=sender,
        recipient=recipient,
        subject=subject,
        body_text=body_plain,
        body_html=body_html,
        message_id=message_id,
        spf_pass=verification.spf_pass,
        dkim_pass=verification.dkim_pass,
        spam_score=verification.spam_score,
        is_verified=verification.is_verified,
    )
    db.add(message)
    db.flush()  # Get the message ID without committing

    # Handle attachments
    attachment_count = int(form.get("attachment-count", "0") or "0")
    if attachment_count > 0:
        files = []
        for i in range(1, attachment_count + 1):
            file = form.get(f"attachment-{i}")
            if file and isinstance(file, UploadFile):
                files.append(file)

        if files:
            s3_client = None
            if settings.s3_bucket and settings.aws_access_key_id:
                s3_client = get_s3_client(
                    settings.aws_access_key_id,
                    settings.aws_secret_access_key,
                    settings.aws_region,
                )

            await parse_and_store_attachments(
                files=files,
                message_id=message.id,
                db=db,
                s3_client=s3_client,
                bucket=settings.s3_bucket,
                s3_prefix=settings.s3_prefix,
            )

    db.commit()

    # TODO: Trigger user webhook if configured

    return {
        "status": "received",
        "message_id": str(message.id),
        "verified": verification.is_verified,
        "spam_score": verification.spam_score,
    }
