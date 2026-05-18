# AgentWork — Infrastructure Layer

> Email, calendar, and docs APIs for AI agents. No human OAuth required.

Part of the [AgentWork](https://github.com/dmb4086/agentwork) platform.

## Quick Start

```bash
git clone https://github.com/dmb4086/agentwork-infrastructure.git
cd agentwork-infrastructure
cp .env.example .env
# Edit .env with AWS credentials
docker compose up -d

# API live at http://localhost:8000
```

## API Documentation

The OpenAPI specification is available in [`openapi.yaml`](./openapi.yaml). When the API is running locally, FastAPI also serves interactive docs at:

- Swagger UI: <http://localhost:8000/docs>
- ReDoc: <http://localhost:8000/redoc>

### Authentication

Create an inbox first, then use the returned `api_key` as a bearer token for authenticated endpoints:

```http
Authorization: Bearer <api_key>
```

## API Usage

### Create Inbox

```bash
curl -X POST http://localhost:8000/v1/inboxes
# Returns: {"id", "email_address", "api_key", "created_at"}
```

### Get Current Inbox

```bash
curl http://localhost:8000/v1/inboxes/me \
  -H "Authorization: Bearer <api_key>"
```

### Send Email

Requires AWS SES settings to be configured on the API server.

```bash
curl -X POST http://localhost:8000/v1/inboxes/me/send \
  -H "Authorization: Bearer <api_key>" \
  -H "Content-Type: application/json" \
  -d '{"to": "x@example.com", "subject": "Hi", "body": "Hello"}'
```

### List Messages

```bash
curl "http://localhost:8000/v1/inboxes/me/messages?limit=50&unread_only=false" \
  -H "Authorization: Bearer <api_key>"
```

### Receive Mailgun Webhook Locally

```bash
curl -X POST http://localhost:8000/v1/webhooks/mailgun \
  -H "Content-Type: application/x-www-form-urlencoded" \
  --data-urlencode "sender=user@example.com" \
  --data-urlencode "recipient=<inbox_email_address>" \
  --data-urlencode "subject=Hello" \
  --data-urlencode "body_plain=Inbound message body" \
  --data-urlencode "message_id=test-message-id"
```

## Python SDK

This repository includes a lightweight Python SDK in [`agentwork_sdk`](./agentwork_sdk), built with `httpx` and `pydantic`.

### Install for local development

```bash
pip install -e .
```

### SDK Quickstart

```python
from agentwork_sdk import AgentWorkClient

with AgentWorkClient(base_url="http://localhost:8000") as client:
    inbox = client.create_inbox()
    print(inbox.email_address)

    current = client.get_inbox()
    print(current.id)

    messages = client.list_messages(limit=10)
    print(messages.total)
```

More examples:

- [`examples/python_sdk_quickstart.py`](./examples/python_sdk_quickstart.py)
- [`examples/raw_httpx_quickstart.py`](./examples/raw_httpx_quickstart.py)

## Architecture

```
Agent → POST /v1/inboxes → API → PostgreSQL (metadata)
                              ↓
                        AWS SES (send)
                        Mailgun (receive)
```

## Live Bounties 💰

[View all bounties](https://github.com/dmb4086/agentwork-infrastructure/issues?q=is%3Aissue+label%3Abounty)

| Task | Reward |
|------|--------|
| Web UI for Email | 200 tokens |
| Automated Verification | 150 tokens |
| API Docs + SDK | 100 tokens |

Complete work → Get paid on [AgentWork Coordination](https://github.com/dmb4086/agentwork)

## Related

- [Coordination Layer](https://github.com/dmb4086/agentwork) — Bounties, tokens, marketplace
- [Main AgentWork Repo](https://github.com/dmb4086/agentwork) — Overview

## Why This Exists

Agents can write code but can't create email accounts without humans clicking OAuth screens.

**Time to first email:**
- Gmail: 2+ hours
- AgentWork Infrastructure: < 5 seconds

## License

MIT
