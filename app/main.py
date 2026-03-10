from fastapi import FastAPI, Depends, HTTPException, status, Form, UploadFile, File
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import List, Optional
import boto3
import json
import uuid
from botocore.exceptions import ClientError

from app.core.config import get_settings
from app.db.database import get_db, engine, Base
from app.models import models
from app.schemas import schemas

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


def _passed(value: str) -> bool:
    normalized = (value or "").strip().lower()
    return normalized in {"pass", "passed", "true", "yes", "1", "neutral"}


def _upload_attachments(files: Optional[List[UploadFile]]) -> List[dict]:
    if not files:
        return []

    attachment_meta = []
    s3_enabled = bool(
        settings.s3_bucket
        and settings.aws_access_key_id
        and settings.aws_secret_access_key
    )
    s3_client = None
    if s3_enabled:
        s3_client = boto3.client(
            "s3",
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key,
            region_name=settings.aws_region,
        )

    for upload in files:
        body = upload.file.read()
        meta = {
            "filename": upload.filename,
            "content_type": upload.content_type,
            "size": len(body),
        }
        if s3_client:
            key = f"mail-attachments/{uuid.uuid4().hex}-{upload.filename}"
            s3_client.put_object(
                Bucket=settings.s3_bucket,
                Key=key,
                Body=body,
                ContentType=upload.content_type or "application/octet-stream",
            )
            meta["storage"] = "s3"
            meta["bucket"] = settings.s3_bucket
            meta["key"] = key
        else:
            meta["storage"] = "inline"
        attachment_meta.append(meta)
    return attachment_meta


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "agent-suite"}


@app.post("/v1/inboxes", response_model=schemas.InboxResponse, status_code=status.HTTP_201_CREATED)
def create_inbox(db: Session = Depends(get_db)):
    """Create a new inbox. Returns email address and API key."""
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
    sender: str = Form(...),
    recipient: str = Form(...),
    subject: str = Form(""),
    body_plain: str = Form(""),
    body_html: str = Form(""),
    message_id: str = Form(""),
    dkim: str = Form(""),
    SPF: str = Form(""),
    spam_score: str = Form("0"),
    attachment_1: Optional[UploadFile] = File(None),
    attachment_2: Optional[UploadFile] = File(None),
    attachment_3: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db)
):
    """Receive incoming email from Mailgun with lightweight verification metadata."""
    inbox = db.query(models.Inbox).filter(
        models.Inbox.email_address == recipient,
        models.Inbox.is_active == True
    ).first()

    if not inbox:
        return {"status": "dropped"}

    score = float(spam_score or 0)
    if score > 5:
        return {"status": "rejected", "reason": "spam", "spam_score": score}

    attachments = [f for f in [attachment_1, attachment_2, attachment_3] if f is not None]
    attachment_meta = _upload_attachments(attachments)

    message = models.Message(
        inbox_id=inbox.id,
        sender=sender,
        recipient=recipient,
        subject=subject,
        body_text=body_plain,
        body_html=body_html,
        message_id=message_id,
        attachments_meta=json.dumps(attachment_meta),
        spam_score=str(score),
        dkim_passed=_passed(dkim),
        spf_passed=_passed(SPF),
    )
    db.add(message)
    db.commit()

    return {
        "status": "received",
        "message_id": str(message.id),
        "attachments": attachment_meta,
        "dkim_passed": message.dkim_passed,
        "spf_passed": message.spf_passed,
        "spam_score": score,
    }
