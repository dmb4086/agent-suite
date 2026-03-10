from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List
import boto3
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

# Mount static files
import os
static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/")
async def root():
    """Serve inbox UI at root"""
    inbox_path = os.path.join(static_dir, "inbox.html")
    if os.path.exists(inbox_path):
        return FileResponse(inbox_path)
    return {"message": "Agent Suite API", "docs": "/docs", "inbox": "/inbox"}

@app.get("/inbox")
async def inbox():
    """Serve inbox UI"""
    inbox_path = os.path.join(static_dir, "inbox.html")
    if os.path.exists(inbox_path):
        return FileResponse(inbox_path)
    raise HTTPException(status_code=404, detail="Inbox UI not found")


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


@app.get("/v1/inboxes/me/messages/{message_id}", response_model=schemas.Message)
def get_message(
    message_id: int,
    inbox: models.Inbox = Depends(verify_api_key),
    db: Session = Depends(get_db)
):
    """Get a single message by ID."""
    message = db.query(models.Message).filter(
        models.Message.id == message_id,
        models.Message.inbox_id == inbox.id
    ).first()

    if not message:
        raise HTTPException(status_code=404, detail="Message not found")

    # Mark as read
    if not message.is_read:
        message.is_read = True
        db.commit()

    return message


@app.post("/v1/webhooks/mailgun")
def mailgun_webhook(
    sender: str,
    recipient: str,
    subject: str = "",
    body_plain: str = "",
    body_html: str = "",
    message_id: str = "",
    db: Session = Depends(get_db)
):
    """Receive incoming email from Mailgun."""
    # Find inbox by recipient email
    inbox = db.query(models.Inbox).filter(
        models.Inbox.email_address == recipient,
        models.Inbox.is_active == True
    ).first()
    
    if not inbox:
        # Silently drop - inbox doesn't exist or inactive
        return {"status": "dropped"}
    
    # Store message
    message = models.Message(
        inbox_id=inbox.id,
        sender=sender,
        recipient=recipient,
        subject=subject,
        body_text=body_plain,
        body_html=body_html,
        message_id=message_id
    )
    db.add(message)
    db.commit()
    
    # TODO: Trigger user webhook if configured
    
    return {"status": "received", "message_id": str(message.id)}
