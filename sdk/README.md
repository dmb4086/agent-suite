# AgentWork SDK

Python SDK for AgentWork Infrastructure API - Email, calendar, and docs APIs for AI agents.

## Installation

```bash
pip install agent-suite-sdk
```

Or install from source:

```bash
git clone https://github.com/dmb4086/agentwork-infrastructure.git
cd agentwork-infrastructure
pip install -e ./sdk
```

## Quick Start

### Async Usage

```python
from agent_suite_sdk import AgentWorkClient

async with AgentWorkClient() as client:
    # Create inbox (no API key needed)
    inbox = await client.create_inbox()
    print(f"Email: {inbox.email_address}")

    # Set API key for operations
    client.api_key = inbox.api_key

    # Send email
    await client.send_email(
        to="recipient@example.com",
        subject="Hello",
        body="Test email"
    )

    # List messages
    messages = await client.list_messages()
    for msg in messages:
        print(f"{msg.subject}")
```

### Sync Usage

```python
from agent_suite_sdk import AgentWorkClientSync

client = AgentWorkClientSync(api_key="your-api-key")
messages = client.list_messages()
client.close()
```

## Features

- ✅ **Async and Sync Support** - Use async/await or traditional sync calls
- ✅ **Type Safety** - Full Pydantic models for request/response validation
- ✅ **Automatic Retries** - Built-in retry logic with exponential backoff
- ✅ **Error Handling** - Comprehensive exception handling
- ✅ **Calendar Integration** - Create and manage calendar events

## API Reference

### AgentWorkClient

Main async client for AgentWork API.

#### Initialization

```python
client = AgentWorkClient(
    api_key="your-api-key",  # Optional
    base_url="http://localhost:8000",
    timeout=30.0,
    max_retries=3
)
```

#### Methods

##### `create_inbox() -> Inbox`

Create a new email inbox.

```python
inbox = await client.create_inbox()
print(inbox.email_address)  # abc123@mail.example.com
print(inbox.api_key)  # sk_live_abc123
```

##### `list_messages() -> List[Message]`

List all messages in inbox.

```python
messages = await client.list_messages()
for msg in messages:
    print(f"{msg.from_email}: {msg.subject}")
```

##### `send_email(to: str, subject: str, body: str) -> Dict`

Send an email.

```python
result = await client.send_email(
    to="recipient@example.com",
    subject="Hello",
    body="Test email"
)
```

##### `get_message(message_id: str) -> Message`

Get a specific message.

```python
msg = await client.get_message("msg_abc123")
print(msg.body)
```

##### `delete_message(message_id: str) -> Dict`

Delete a message.

```python
await client.delete_message("msg_abc123")
```

### Models

#### Inbox

- `email_address: str` - Inbox email address
- `api_key: str` - API key for authentication
- `created_at: str` - Creation timestamp

#### Message

- `id: str` - Message ID
- `from_email: str` - Sender email
- `to_email: str` - Recipient email
- `subject: str` - Email subject
- `body: str` - Email body
- `created_at: str` - Timestamp
- `read: bool` - Read status
- `attachments: List[Dict]` - Attachments

## Error Handling

The SDK automatically retries failed requests with exponential backoff.

```python
try:
    messages = await client.list_messages()
except httpx.HTTPError as e:
    print(f"Request failed: {e}")
```

## Examples

See `/examples/basic_usage.py` for complete examples.

## Development

### Running Tests

```bash
pip install -e ".[dev]"
pytest tests/
```

### Building Package

```bash
python -m build
```

## License

MIT

## Links

- [API Documentation](./docs/api.md)
- [OpenAPI Spec](./openapi.yaml)
- [GitHub Repository](https://github.com/dmb4086/agentwork-infrastructure)

---

🤖 Created by OpenClaw Bounty Bot
