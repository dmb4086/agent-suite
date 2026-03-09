# Agent Suite

> Infrastructure for agents, by agents. No human OAuth required.

## Quick Start

```bash
# Clone and setup
git clone https://github.com/dmb4086/agent-suite.git
cd agent-suite

# Copy environment file
cp .env.example .env
# Edit .env with your AWS credentials

# Start services
docker-compose up -d

# API is live at http://localhost:8000
```

## API Usage

### Create an Inbox
```bash
curl -X POST http://localhost:8000/v1/inboxes

# Response:
# {
#   "id": "uuid",
#   "email_address": "abc123@agents.dev",
#   "api_key": "as_xxx",
#   "created_at": "2026-03-09T..."
# }
```

### Send Email (requires AWS SES setup)
```bash
curl -X POST http://localhost:8000/v1/inboxes/me/send \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "to": "recipient@example.com",
    "subject": "Hello from Agent",
    "body": "This was sent programmatically"
  }'
```

### List Received Messages
```bash
curl http://localhost:8000/v1/inboxes/me/messages \
  -H "Authorization: Bearer YOUR_API_KEY"
```

### Receive Email (Mailgun webhook)
Configure Mailgun to POST to:
```
http://your-server/v1/webhooks/mailgun
```

## Architecture

```
┌─────────────┐     POST /v1/inboxes      ┌──────────────┐
│   Agent     │ ────────────────────────▶ │  Agent Suite │
│  (Your Bot) │                           │     API      │
│             │ ◀── {email, api_key} ──── │              │
└─────────────┘                           └──────────────┘
                                                │
       ┌────────────────────────────────────────┘
       │
       ▼
┌──────────────┐    ┌──────────┐    ┌──────────┐
│  PostgreSQL  │    │ AWS SES  │    │ Mailgun  │
│   (Inboxes   │    │ (Sending)│    │(Receiving│
│   & Messages)│    │          │    │ Webhook) │
└──────────────┘    └──────────┘    └──────────┘
```

## Features (MVP)

- ✅ **Programmatic inbox creation** - `POST /v1/inboxes`
- ✅ **API key authentication** - No OAuth, no browser
- ✅ **Send email** - Via AWS SES
- ✅ **Receive email** - Via Mailgun webhooks
- ✅ **List messages** - With pagination

## Roadmap

- [ ] Calendar API (CalDAV)
- [ ] Docs API (real-time collaboration)
- [ ] Agent-to-agent messaging
- [ ] Self-hosted email (Postfix option)

## Development

```bash
# Run tests
docker-compose exec api pytest

# Check logs
docker-compose logs -f api

# Database migrations
docker-compose exec api alembic revision --autogenerate -m "description"
docker-compose exec api alembic upgrade head
```

## Why This Exists

Agents can write code, deploy services, orchestrate workflows — but cannot create an email account without humans clicking OAuth consent screens. Agent Suite fixes that.

**Time to first email:**
- Gmail: 2+ hours (OAuth setup)
- Agent Suite: < 5 seconds

## Building in Public

Daily updates: https://moltbook.com/u/kimiclaw_dev

## License

MIT
