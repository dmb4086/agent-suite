# Phase 1 MVP Plan: Agent-Native Email API

## Goal
Build working API for programmatic email:
- `POST /v1/inboxes` → Create inbox instantly
- `POST /v1/inboxes/{id}/send` → Send email
- `GET /v1/inboxes/{id}/messages` → List received
- Webhooks for incoming email

## Architecture
Hybrid approach:
- **Receiving**: Mailgun routes → Webhook → Our API
- **Sending**: AWS SES API
- **Storage**: PostgreSQL (metadata) + S3 (raw emails)
- **IMAP**: Custom lightweight (reads from DB)

## Stack
- FastAPI (Python)
- PostgreSQL + SQLAlchemy
- Pydantic models
- Docker + docker-compose
- AWS SDK (boto3)

## Tasks (Atomic)

### Task 1: Project Bootstrap
- FastAPI app structure
- Docker setup
- PostgreSQL connection
- Basic health endpoint

### Task 2: Database Models
- Inbox model (id, email_address, api_key, created_at)
- Message model (id, inbox_id, sender, recipient, subject, body, received_at)
- Migrations

### Task 3: Inbox API
- POST /v1/inboxes
- Generate unique email address
- Return API key for inbox
- GET /v1/inboxes/{id}

### Task 4: Send Email (AWS SES)
- POST /v1/inboxes/{id}/send
- Use AWS SES to send
- Store sent message in DB

### Task 5: Receive Webhook (Mailgun)
- POST /v1/webhooks/mailgun
- Parse incoming email
- Store in DB
- Trigger user webhook if configured

### Task 6: List Messages
- GET /v1/inboxes/{id}/messages
- Pagination
- Filter by read/unread

### Task 7: Testing
- pytest setup
- Test inboxes creation
- Test send/receive flow

## Verification
```bash
# Create inbox
curl -X POST http://localhost:8000/v1/inboxes

# Send email
curl -X POST http://localhost:8000/v1/inboxes/{id}/send \
  -H "Authorization: Bearer {api_key}" \
  -d '{"to": "test@example.com", "subject": "Hello", "body": "World"}'

# List messages
curl http://localhost:8000/v1/inboxes/{id}/messages \
  -H "Authorization: Bearer {api_key}"
```
