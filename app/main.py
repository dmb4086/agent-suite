"""
Agent Suite - Email infrastructure for AI agents.
Implements automated email verification as per Bounty #2.
"""
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import List
import boto3
from botocore.exceptions import ClientError
import logging

from app.core.config import get_settings
from app.db.database import get_db, engine, Base
from app.models import models
from app.schemas import schemas
from app.services.email_verification import EmailVerificationService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Agent Suite", version="0.2.0")
security = HTTPBearer()
settings = get_settings()

# Initialize verification service
verification_service = EmailVerificationService(
    s3_bucket=getattr(settings, 's3_attachments_bucket', None),
    aws_region=settings.aws_region
)


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
    return {"status": "ok", "service": "agent-suite", "version": "0.2.0"}


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
def mailgun_webhook(
    sender: str,
    recipient: str,
    subject: str = "",
    body_plain: str = "",
    body_html: str = "",
    message_id: str = "",
    raw_email: str = "",
    # Additional headers (Mailgun sends these)
    x_mailgun_spf: str = "",
    x_mailgun_dkim: str = "",
    authentication_results: str = "",
    db: Session = Depends(get_db)
):
    """
    Receive incoming email from Mailgun with automated verification.
    
    Implements Bounty #2:
    - SPF/DKIM signature verification
    - Spam score filtering (reject if score > 5)
    - Attachment parsing and S3 storage
    - Update /v1/inboxes/me/messages to include attachment metadata
    """
    # Find inbox by recipient email
    inbox = db.query(models.Inbox).filter(
        models.Inbox.email_address == recipient,
        models.Inbox.is_active == True
    ).first()
    
    if not inbox:
        # Silently drop - inbox doesn't exist or inactive
        return {"status": "dropped"}
    
    # Perform email verification
    headers = {
        'Received-SPF': x_mailgun_spf,
        'X-Mailgun-Spf': x_mailgun_spf,
        'X-Mailgun-Dkim': x_mailgun_dkim,
        'Authentication-Results': authentication_results
    }
    
    verification_result = verification_service.verify_email(
        sender=sender,
        recipient=recipient,
        subject=subject,
        body_plain=body_plain,
        body_html=body_html,
        raw_email=raw_email,
        headers=headers
    )
    
    # Check if we should reject the email (spam score > 5)
    if verification_service.should_reject_email(verification_result):
        logger.warning(
            f"Rejecting spam email from {sender}: spam_score={verification_result.spam_score}"
        )
        return {"status": "rejected", "reason": "spam", "score": verification_result.spam_score}
    
    # Store message with verification metadata
    message = models.Message(
        inbox_id=inbox.id,
        sender=sender,
        recipient=recipient,
        subject=subject,
        body_text=body_plain,
        body_html=body_html,
        message_id=message_id,
        raw_data=raw_email,
        spf_pass=verification_result.spf_pass,
        dkim_pass=verification_result.dkim_pass,
        spam_score=verification_result.spam_score,
        is_spam=verification_result.is_spam,
        spam_indicators=verification_result.spam_indicators
    )
    db.add(message)
    db.commit()
    db.refresh(message)
    
    # Store attachments
    for attachment_data in verification_result.attachments:
        attachment = models.Attachment(
            message_id=message.id,
            filename=attachment_data['filename'],
            content_type=attachment_data['content_type'],
            size_bytes=attachment_data['size_bytes'],
            sha256=attachment_data['sha256'],
            s3_key=attachment_data.get('s3_key')
        )
        db.add(attachment)
    
    db.commit()
    
    logger.info(
        f"Email received: from={sender}, spf={verification_result.spf_pass}, "
        f"dkim={verification_result.dkim_pass}, spam_score={verification_result.spam_score:.1f}, "
        f"attachments={len(verification_result.attachments)}"
    )
    
    return {
        "status": "received",
        "message_id": str(message.id),
        "verification": {
            "spf_pass": verification_result.spf_pass,
            "dkim_pass": verification_result.dkim_pass,
            "spam_score": verification_result.spam_score
        },
        "attachments_count": len(verification_result.attachments)
    }
