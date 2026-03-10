# Agent Suite SDK - Usage Examples

This directory contains examples for using the Agent Suite SDK.

## Basic Usage

```python
from agent_suite_sdk import AgentSuiteClient

# Initialize client
client = AgentSuiteClient(
    api_key="your-api-key",
    base_url="http://localhost:8000"  # or production URL
)

# Create an inbox
inbox = client.create_inbox()
print(f"Email: {inbox.email_address}")
print(f"API Key: {inbox.api_key}")  # Save this!

# Send an email
client.send_email(
    inbox_id=inbox.id,
    to="recipient@example.com",
    subject="Hello from AI Agent",
    body="This email was sent by an AI agent!"
)

# List messages
messages = client.list_messages(inbox_id=inbox.id)
print(f"Total messages: {messages.total}")
for msg in messages.messages:
    print(f"  - {msg.subject} from {msg.from_}")

# Clean up
client.close()
```

## Context Manager Usage

```python
from agent_suite_sdk import AgentSuiteClient

with AgentSuiteClient(api_key="your-key") as client:
    inbox = client.create_inbox()
    client.send_email(
        inbox_id=inbox.id,
        to="user@example.com",
        subject="Test",
        body="Hello!"
    )
# Client automatically closed
```

## Async Usage

```python
import asyncio
from agent_suite_sdk import AsyncAgentSuiteClient

async def main():
    async with AsyncAgentSuiteClient(api_key="your-key") as client:
        inbox = await client.create_inbox()
        await client.send_email(
            inbox_id=inbox.id,
            to="user@example.com",
            subject="Async email",
            body="Sent asynchronously!"
        )
        
        messages = await client.list_messages(inbox_id=inbox.id)
        print(f"Got {messages.total} messages")

asyncio.run(main())
```

## Webhook Handling

### Flask

```python
from flask import Flask, request
from agent_suite_sdk import AgentSuiteClient

app = Flask(__name__)
client = AgentSuiteClient(api_key="your-key")

@app.route('/webhook', methods=['POST'])
def handle_webhook():
    try:
        data = client.receive_webhook(
            request,
            secret="your-webhook-secret"
        )
        
        if data['event'] == 'email.received':
            email = data['email']
            print(f"New email from {email['from']}: {email['subject']}")
        
        return 'OK', 200
    except Exception as e:
        print(f"Webhook error: {e}")
        return 'Error', 400

if __name__ == '__main__':
    app.run(port=5000)
```

### FastAPI

```python
from fastapi import FastAPI, Request
from agent_suite_sdk import AgentSuiteClient

app = FastAPI()
client = AgentSuiteClient(api_key="your-key")

@app.post('/webhook')
async def handle_webhook(request: Request):
    data = await client.receive_webhook(
        request,
        secret="your-webhook-secret"
    )
    
    event_type = data.get('event')
    email = data.get('email', {})
    
    if event_type == 'email.received':
        print(f"New email: {email.get('subject')}")
    
    return {'status': 'ok'}
```

## Error Handling

```python
from agent_suite_sdk import (
    AgentSuiteClient,
    UnauthorizedError,
    NotFoundError,
    BadRequestError,
    APIError
)

try:
    client = AgentSuiteClient(api_key="invalid-key")
    inbox = client.create_inbox()
    
except UnauthorizedError as e:
    print(f"Invalid API key: {e}")
    
except NotFoundError as e:
    print(f"Resource not found: {e}")
    
except BadRequestError as e:
    print(f"Bad request: {e}")
    
except APIError as e:
    print(f"API error: {e}")
```

## Environment Variables

Set your API key via environment variable:

```bash
export AGENT_SUITE_API_KEY="your-api-key"
```

```python
from agent_suite_sdk import AgentSuiteClient

# No need to pass api_key - reads from AGENT_SUITE_API_KEY
client = AgentSuiteClient()
```

## Production URL

```python
from agent_suite_sdk import AgentSuiteClient

client = AgentSuiteClient(
    api_key="your-key",
    base_url="https://api.agentwork.in"  # Production
)
```
