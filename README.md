# Agent Suite SDK 🧠📧

Python SDK for [Agent Suite API](https://github.com/dmb4086/agentwork-infrastructure) - Email, calendar, and docs APIs for AI agents. No human OAuth required.

[![PyPI](https://img.shields.io/pypi/v/agent-suite-sdk)](https://pypi.org/project/agent-suite-sdk/)
[![Python](https://img.shields.io/pypi/pyversions/agent-suite-sdk)](https://pypi.org/project/agent-suite-sdk/)
[![License](https://img.shields.io/pypi/l/agent-suite-sdk)](LICENSE)

## Why Agent Suite?

AI agents can write code, deploy services, and orchestrate workflows — but they can't create email accounts without humans clicking OAuth screens. **Agent Suite** fixes this.

| | Gmail | Agent Suite |
|---|-------|--------------|
| Time to first email | 2+ hours | < 5 seconds |
| Auth required | OAuth (human) | API key |
| Provisioning | Human creates | `POST /inboxes` |

## Installation

```bash
pip install agent-suite-sdk
```

## Quick Start

```python
from agent_suite_sdk import AgentSuiteClient

# Create client
client = AgentSuiteClient(
    api_key="your-api-key",
    base_url="http://localhost:8000"
)

# Create inbox
inbox = client.create_inbox()
print(f"Email: {inbox.email_address}")  # agent_xxx@agentwork.in

# Send email
client.send_email(
    inbox_id=inbox.id,
    to="user@example.com",
    subject="Hello",
    body="Sent by AI!"
)

# List messages
messages = client.list_messages(inbox_id=inbox.id)
```

## Features

- ✅ **Instant provisioning** - Create email inboxes in < 5 seconds
- ✅ **Python & async** - Sync and async clients
- ✅ **Type safety** - Pydantic models included
- ✅ **Webhooks** - Real-time email event handling
- ✅ **OpenAPI spec** - Full API documentation in `openapi.yaml`

## API Coverage

| Endpoint | Method | SDK Support |
|----------|--------|--------------|
| `/v1/inboxes` | POST | ✅ `create_inbox()` |
| `/v1/inboxes` | GET | ✅ `list_inboxes()` |
| `/v1/inboxes/{id}` | GET | ✅ `get_inbox()` |
| `/v1/inboxes/{id}` | DELETE | ✅ `delete_inbox()` |
| `/v1/inboxes/{id}/send` | POST | ✅ `send_email()` |
| `/v1/inboxes/{id}/messages` | GET | ✅ `list_messages()` |
| `/v1/inboxes/{id}/webhooks` | POST | ✅ `create_webhook()` |

## Documentation

- [OpenAPI Spec](openapi.yaml) - Full API specification
- [Examples](examples/) - Usage examples
- [Quick Start](quickstart.py) - Runnable example

## Requirements

- Python 3.8+
- httpx
- pydantic

## License

MIT
